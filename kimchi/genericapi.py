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

from functools import partial
import json
from urllib.parse import urljoin

import requests

def _get(url, **kwargs):
    r = requests.get(url, **kwargs)
    return json.loads(r.text)

def _post(url, payload, **kwargs):
    r = requests.post(url, data=json.dumps(payload), **kwargs)
    return json.loads(r.text)

def _put(url, payload, **kwargs):
    r = requests.put(url, data=json.dumps(payload), **kwargs)
    return json.loads(r.text)

def _delete(url, **kwargs):
    r = requests.delete(url.rstrip('/'), **kwargs)
    return json.loads(r.text)


class GenericAPI(object):
    def __init__(self, the_url):
        self.the_url = the_url if the_url[-1] is '/' else the_url + '/'

    def __getattr__(self, key):
        new_base = urljoin(self.the_url, key)
        return self.__class__(the_url=new_base)

    def __getitem__(self, key):
        return self.__getattr__(key)

    def __call__(self, method='GET', payload=None, **kwargs):
        if payload is None:
            payload = {}
        url = self.the_url
        print("Calling {0} on {1}".format(method, url))
        if method is 'GET':
            return get(url, **kwargs)
        elif method is 'PUT':
            return put(url, payload, **kwargs)
        elif method is 'POST':
            return post(url, payload, **kwargs)
        elif method is 'DELETE':
            return delete(url, **kwargs)

    def get(self, **kwargs):
        return _get(self.the_url, **kwargs)

    def post(self, payload, **kwargs):
        return _post(self.the_url, payload, **kwargs)

    def put(self, payload=None, **kwargs):
        return _put(self.the_url, payload, **kwargs)

    def delete(self, **kwargs):
        return _delete(self.the_url, **kwargs)
