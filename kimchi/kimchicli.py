#!/usr/bin/env python3

# Copyright 2015 Gary Martin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import cmd
import random
import sys
from functools import partial

from hashlib import sha1
from kimchi.genericapi import GenericAPI as Connector
from kimchi.arangodbapi import (Arango, ArangoError, Document, Edge,
                                SimpleQuery, Traversal)

DEF_CHAIN_ORDER = 2
MAX_REPLIES = 30
MAX_REPLY_LENGTH = 15


class Brain(object):
    def __init__(self, dbname="chains", chainorder=DEF_CHAIN_ORDER):
        conn = Connector('http://127.0.0.1:8529')
        sysdb = Arango(conn._db._system._api.database)
        try:
            sysdb.create({'name': dbname})
        except ArangoError as e:
            if e.code != 409:
                raise
        db = conn._db[dbname]
        self.docs = Document(db)
        self.edges = Edge(db)
        self.simple_query = SimpleQuery(db)
        self.traversal = Traversal(db)

        self.collection_name = "chains"
        self.edge_collection_name = "links"
        self.control_collection_name = "control"
        self.chainorder = self.get_or_set_brain_info('chainorder', chainorder)
        self.stop = self.get_or_set_brain_info('stop', '////////')

    def get_or_set_brain_info(self, key, value):
        collection = self.control_collection_name
        try:
            docs = self.simple_query.by_example(
                collection, {'_key': key})
        except KeyError:
            docs = []
        if docs:
            return docs[0]['value']
        doc = self.docs.create(
            {'_key': key, 'value': value},
            params={'collection': collection, 'createCollection': True})
        return value

    def add_nodes(self, nodegenerator):
        handles = []
        collection = self.collection_name
        nodes = [n for n in nodegenerator]
        full_length = len(nodes)
        for i, node in enumerate(nodes):
            data = {
                '_key': sha1(str(node).encode('utf8')).hexdigest(),
                'base_word': node[0],
                'node': node,
            }
            full_data = {
                'outbound_distance': full_length - i,  # distance to end
                'inbound_distance': i + 1,  # distance from start
            }
            full_data.update(data)
            try:
                docres = self.docs.create(full_data, params={
                    'collection': collection, 'createCollection': True})
            except ArangoError:
                docres = self.simple_query.by_example(collection, data)[0]
                updated = False
                for key in ('outbound_distance', 'inbound_distance'):
                    if key not in docres:
                        updated = True
                    elif docres[key] < full_data[key]:
                        full_data[key] = docres[key]
                    elif docres[key] > full_data[key]:
                        updated = True
                if updated:
                    self.docs.update(docres['_id'], full_data, params={
                        'collection': collection})
            handles.append(docres['_id'])
        return handles

    def add_edges(self, handles):
        current_handle, *rest = handles
        collection = self.edge_collection_name
        for next_handle in rest:
            data = {
                '_key': sha1(
                    str((current_handle, next_handle)).encode('utf8')
                ).hexdigest(),
            }
            try:
                self.edges.create(data, params={
                    'collection': collection, 'createCollection': True,
                    'from': current_handle, 'to': next_handle})
            except ArangoError:
                pass
            current_handle = next_handle

    def get_node_by_handle(self, handle):
        return self.docs[handle]

    def get_node_by_key(self, key):
        return self.docs[self.collection_name][key]

    def get_nodes_by_first_word(self, word):
        return self.simple_query.by_example(
            self.collection_name, {'base_word': word}, limit=10)

    def get_edge_by_handle(self, handle):
        return self.edges[handle]

    def get_edge_by_key(self, key):
        return self.docs[self.edge_collection_name][key]

    def chunk_msg(self, msg):
        words = [self.stop] + msg.split() + [self.stop]
        while len(words) < self.chainorder:
            words.append(self.stop)
        return (words[i:i + self.chainorder + 1]
                for i in range(1 + len(words) - self.chainorder))

    def learn(self, msg, reply=False):
        nodes_to_add = self.chunk_msg(msg)
        nodes = self.add_nodes(nodes_to_add)
        self.add_edges(nodes)

    def get_word_chain(self, doc, direction):
        visitor = """
            if (! result || ! result.visited) { return; }
            if (result.visited.vertices) {
              result.visited.vertices.push(vertex.base_word);
            }
            if (result.visited.paths) {
              var cpath = [];
              path.vertices.forEach(function (v) {
                cpath.push(v.base_word);
              });
              result.visited.paths.push(cpath);
            }
        """

        filterfn = """
            if (path && path.length + vertex.%s > %d) {
              return 'exclude';
            }
        """ % (direction + "_distance", MAX_REPLY_LENGTH) 

        result = self.traversal.traverse(
            doc['_id'],
            self.edge_collection_name,
            direction=direction,
            maxDepth=MAX_REPLY_LENGTH,
            filterfn=filterfn,
            visitor=visitor)

        if 'result' not in result:
            return []
        paths = result['result']['visited']['paths']
        returnpaths = [p[:-1] for p in paths if p[-1] == self.stop]
        return returnpaths

    def generate_candidate_reply(self, word_list):
        sorted_words = sorted(word_list, key=len)[::-1]
        replies = []
        for word in sorted_words:
            print(word)
            docs = self.get_nodes_by_first_word(word)
            random.shuffle(docs)
            for doc in docs:
                forward_words = self.get_word_chain(doc, "outbound")
                reverse_words = self.get_word_chain(doc, "inbound")
                for forward_chain in forward_words:
                    for reverse_chain in reverse_words:
                        reply = reverse_chain[::-1] + forward_chain[1:]
                        replies.append((self.score(reply, word_list), reply))
                if len(replies) > MAX_REPLIES:
                    break
            if len(replies) > MAX_REPLIES:
                break
        if replies:
            return random.choice(sorted(replies)[::-1])[1]

    def score(self, words, original):
        if not words:
            return 0.0
        return 1.0
        # words used less in the brain should improve score?
        # sum(1 / len(self.get_nodes_by_first_word(w)) for w in words)
        max_word_length = max(len(w) for w in words)
        average_word_length = sum(len(w) for w in words) / len(words)
        return (max_word_length * average_word_length *
                len(set(words) - set(original)))

    def generate_replies(self, msg):
        words = msg.split()
        #starttime = time.time()
        #while time.time() - starttime < 0.25:
        cr = self.generate_candidate_reply(words)
        if not cr:
            cr = ["I have nothing to say about that"]
        return ' '.join(cr)


def run():
    parser = argparse.ArgumentParser(description="A chat bot")

    # database options
    db_parser = argparse.ArgumentParser(add_help=False)
    db_parser.add_argument(
        '--dbname', default='chains',
        help="Database to use.")

    # simulation options
    modelling_parser = argparse.ArgumentParser(add_help=False)
    modelling_parser.add_argument(
        '--chain-order', type=int, default=1,
        help="Set the simulation chain size parameter.")

    # learning options
    learning_parser = argparse.ArgumentParser(add_help=False)
    learning_parser.add_argument(
        'infile', metavar='INFILE', nargs='?', type=argparse.FileType('r'),
        default=sys.stdin,
        help="An input file from which to learn")

    # reply options
    reply_parser = argparse.ArgumentParser(add_help=False)
    reply_parser.add_argument(
        'message', metavar='MSG', nargs='+', action='append',
        help="Specify a message to respond to.")

    subparsers = parser.add_subparsers(title='Subcommands', dest='subcommand')
    subparsers.required = True

    ### learn command ###
    learn_subparser = subparsers.add_parser(
        'learn', help="add source data to the corpus",
        parents=[learning_parser, db_parser, modelling_parser])
    learn_subparser.set_defaults(func=do_learn)

    ### response command
    reply_subparser = subparsers.add_parser(
        'reply', help="send a message to get a reply back",
        parents=[reply_parser, db_parser, modelling_parser])
    reply_subparser.set_defaults(func=do_response)

    ### shell command
    shell_subparser = subparsers.add_parser(
        'shell', help="enter an interactive shell",
        parents=[db_parser, modelling_parser])
    shell_subparser.set_defaults(func=do_shell)

    dargs = vars(parser.parse_args())

    for option in ('file', 'message'):
        if dargs.get(option):
            dargs[option] = [x for xs in dargs[option] for x in xs]

    dargs['func'](dargs)


def do_learn(dargs):
    # TODO - add sensible behaviour for when no files are specified (stdin?)
    brain = get_brain(dargs)
    for i, msg in enumerate(dargs['infile']):
        if i % 100 == 0:
            print(i)
        brain.learn(msg)


def do_response(dargs):
    brain = get_brain(dargs)
    for msg in dargs['message'] if dargs['message'] else []:
        print(brain.generate_replies(msg))


def do_shell(dargs):
    BrainShell(dargs).cmdloop()


def get_brain(dargs):
    return Brain(dargs['dbname'], dargs['chain_order'])


class BrainShell(cmd.Cmd):
    """Command processor for Kimchi"""
    intro = ("+--------------------------------------+\n"
             "|                                      |\n"
             "| #   #  ##### #   #  #### #   # ##### |\n"
             "| #  #     #   ## ## #     #   #   #   |\n"
             "| ###      #   # # # #     #####   #   |\n"
             "| #  #     #   #   # #     #   #   #   |\n"
             "| #   #  ##### #   #  #### #   # ##### |\n"
	     "|                                      |\n"
             "+--------------------------------------+\n")
    prompt = "kimchi> "

    def __init__(self, dargs, *args, **kwargs):
        self.brain = get_brain(dargs)
        self.last_line = None
        super(BrainShell, self).__init__(*args, **kwargs)

    def do_EOF(self, line):
        return self.do_quit(line)

    def do_quit(self, line):
        if len(line.split()) > 1:
            self.default(line)
        else:
            print('Bye')
            return True

    def default(self, line):
        self.do_learn(line)
        self.last_line = line

    def emptyline(self):
        if self.last_line is not None:
            self.do_reply(self.last_line)

    def do_setbrain(self, line):
        sl = line.split()
        db, c_o = sl[:2] if len(sl) > 1 else (sl[0], DEF_CHAIN_ORDER)
        self.brain = get_brain({'dbname': db, 'chain_order': c_o})

    def do_learn(self, line):
        self.last_line = None
        self.brain.learn(line)

    def do_reply(self, line):
        self.last_line = None
        reply = self.brain.generate_replies(line)
        print(reply)


if __name__ == '__main__':
    run()
