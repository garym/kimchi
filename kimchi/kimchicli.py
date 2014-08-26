#!/usr/bin/env python3

# Copyright 2014 Gary Martin
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
from arango import create

DEF_CHAIN_ORDER = 2


class Brain(object):
    def __init__(self, dbname="chains", chainorder=DEF_CHAIN_ORDER):
        conn = create(db=dbname)
        conn.database.create()
        conn.chains.create()
        conn.links.create(type=conn.COLLECTION_EDGES)
        self.conn = conn
        self.chains = conn.chains
        self.links = conn.links

        self.stop = ''
        self.chainorder = chainorder

    def get_node(self, node):
        return self.chains.query.filter(
            "obj.node == {}".format(node)).execute().first

    def get_link(self, doc, next_doc):
        return self.links.query.filter(
            'obj._from == "{}" && obj._to == "{}"'.format(
                doc.id, next_doc.id)).execute().first

    def add_edge(self, node, next_node, edge_data=None):
        doc = self.get_node(node)
        if doc is None:
            doc = self.chains.documents.create({'node': node})
        next_doc = self.get_node(next_node)
        if next_doc is None:
            next_doc = self.chains.documents.create({'node': next_node})
        link = self.get_link(doc, next_doc)
        if link is None:
            self.links.edges.create(
                doc, next_doc, {} if edge_data is None else edge_data)

    def get_nodes_by_first_word(self, word):
        return (c for c in self.chains.query.filter(
            "obj.node[0] == '{}'".format(word)).execute())

    def get_nodes_by_id(self, nid):
        return self.chains.query.filter(
            "obj._id == '{}'".format(nid)).execute().first

    def neighbours(self, doc, direction="any"):
        def wrapper(c, i):
            return i
        return (r for r in self.chains.query.cursor(wrapper=wrapper).over(
            'NEIGHBORS(chains, links, "{}", "{}")'.format(doc.id, direction
                                                          )).execute())
    forward_link = partial(neighbours, direction="outbound")
    reverse_link = partial(neighbours, direction="inbound")

    def gen_key(self, msgparts):
        return self.sep.join((self.prefix, self.sep.join(msgparts)))

    def chunk_msg(self, msg):
        words = [self.stop] + msg.split() + [self.stop]
        while len(words) < self.chainorder:
            words.append(self.stop)
        return ((words[i:i + self.chainorder + 1],
                 words[i + 1:i + self.chainorder + 2])
                for i in range(len(words) - self.chainorder))

    def learn(self, msg, reply=False):
        for (node1, node2) in self.chunk_msg(msg):
            self.add_edge(node1, node2)

    def get_word_chain(self, doc, direction):
        first, second = doc.body['node'][:2]
        if not first:
            return []
        elif direction == 'outbound' and not second:
            return [first, ]
        else:
            neighbours = [n for n in self.neighbours(doc, direction=direction)]
            if not neighbours:
                return [n for n in doc.body['node'] if n]
            new_doc = self.get_nodes_by_id(
                random.choice(neighbours)['vertex']['_id'])
            return [first] + self.get_word_chain(new_doc, direction)

    def generate_candidate_reply(self, word_list):
        word = random.choice(word_list)
        try:
            current_doc = random.choice(
                [d for d in self.get_nodes_by_first_word(word)])
            forward_words = self.get_word_chain(current_doc, "outbound")
            reverse_words = self.get_word_chain(current_doc, "inbound")
            reply = reverse_words[::-1] + forward_words[1:]
        except IndexError:
            reply = []
        return reply

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
    for msg in dargs['infile']:
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
    def __init__(self, dargs, *args, **kwargs):
        self.brain = get_brain(dargs)
        super(BrainShell, self).__init__(*args, **kwargs)

    def do_EOF(self, line):
        print('Bye')
        return True

    def default(self, line):
        self.do_learn(line)
        self.do_reply(line)

    def do_setbrain(self, line):
        sl = line.split()
        db, c_o = sl[:2] if len(sl) > 1 else (sl[0], DEF_CHAIN_ORDER)
        self.brain = get_brain({'dbname': db, 'chain_order': c_o})

    def do_learn(self, line):
        self.brain.learn(line)

    def do_reply(self, line):
        reply = self.brain.generate_replies(line)
        print(reply)


if __name__ == '__main__':
    run()
