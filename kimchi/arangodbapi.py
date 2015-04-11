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

from genericapi import GenericAPI as Connector
from hashlib import sha1


class ArangoError(Exception):
    def __init__(self, code, errmsg, path, data=None):
        self.code = code
        self.errmsg = errmsg
        self.path = path
        self.data = data


class Arango(object):
    def __init__(self, conn):
        self.conn = conn

    def _check_exception_required(self, resp, data=None):
        if resp['error']:
            raise ArangoError(code=resp['code'],
                              errmsg=resp['errorMessage'],
                              path=self.conn.the_url,
                              data=data)

    def create(self, data, params=None):
        if params is None:
            params = {}
        resp = self.conn.post(data, params=params)
        self._check_exception_required(resp, data)
        return resp['result'] if 'result' in resp else resp

    def list(self, params=None):
        if params is None:
            params = {}
        resp = self.conn.get(params=params)
        self._check_exception_required(resp)
        return resp['result'] if 'result' in resp else resp

    def read(self, name, params=None):
        if params is None:
            params = {}
        resp = self.conn[name].get(params=params)
        self._check_exception_required(resp)
        return resp['result'] if 'result' in resp else resp

    def delete(self, name, params=None):
        if params is None:
            params = {}
        resp = self.conn[name].delete(params=params)
        self._check_exception_required(resp, {'name': name})
        return resp['result']


# convenience classes for some useful api endpoints

class DatabaseManagement(Arango):
    def __init__(self, conn):
        # assume connection is up to _db/_system
        self.conn = conn._api.database


class Document(Arango):
    def __init__(self, conn):
        self.conn = conn._api.document


class Edge(Arango):
    def __init__(self, conn):
        self.conn = conn._api.edge


class Traversal(Arango):
    def __init__(self, conn):
        self.conn = conn._api.traversal

    def traverse(self, startVertex, edge_collection, minDepth=None,
                 maxDepth=None, direction='outbound', visitor=None,
                 params=None):
        data = {
            'startVertex': startVertex,
            'edgeCollection': edge_collection,
            'direction': direction,
        }
        if minDepth is not None:
            data['minDepth'] = minDepth
        if maxDepth is not None:
            data['maxDepth'] = maxDepth
        if visitor is not None:
            data['visitor'] = visitor
        if params is None:
            params = {}
        return self.conn.post(data, params=params)

class SimpleQuery(Arango):
    def __init__(self, conn):
        self.conn = conn._api.simple
        self.cursor = conn._api.cursor

    def by_example(self, collection, example, limit=None):
        data = {
            'collection': collection,
            'example': example,
        }
        if limit is not None:
            data['limit'] = limit

        resp = self.conn['by-example'].put(data)
        results = resp['result']
        while resp['hasMore']:
            resp = self.cursor[resp['id']].put()
            results.append(resp['result'])
        return results

