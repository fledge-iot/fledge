# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import time
import json

import asyncpg
import http.client
import pytest
import asyncio

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# Module attributes
__DB_NAME = "foglamp"
BASE_URL = 'localhost:8082'
headers = {"Content-Type": 'application/json'}

test_data = {'key': 'TESTAPI', 'description': 'RESTAPI Test Config',
              'value': {'item1': {'description': 'desc', 'type': 'string', 'default': 'def'}}}
pytestmark = pytest.mark.asyncio


async def add_master_data():
    conn = await asyncpg.connect(database=__DB_NAME)
    await conn.execute('''DELETE from foglamp.configuration WHERE key IN ($1)''', test_data['key'])
    await conn.execute("""INSERT INTO foglamp.configuration(key, description, value) VALUES($1, $2, $3);""",
                       test_data['key'], test_data['description'], json.dumps(test_data['value']))
    await conn.close()


async def delete_master_data():
    conn = await asyncpg.connect(database=__DB_NAME)
    # await conn.execute('''DELETE from foglamp.configuration WHERE key IN ($1)''', test_data['key'])
    await conn.close()


class TestConfigMgr:
    @classmethod
    def setup_class(cls):
        asyncio.get_event_loop().run_until_complete(add_master_data())
        from subprocess import call
        call(["foglamp", "start"])
        time.sleep(2)

    @classmethod
    def teardown_class(cls):
        from subprocess import call
        call(["foglamp", "stop"])
        asyncio.get_event_loop().run_until_complete(delete_master_data())

    def setup_method(self, method):
        pass

    def teardown_method(self, method):
        pass

    # TODO: Add tests for negative cases. Currently only positive test cases have been added.

    async def test_get_categories(self):
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/categories')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)
        all_items = [elements['key'].strip() for elements in retval['categories']]
        assert test_data['key'] in all_items

    async def test_get_category(self):
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/category/{}'.format(test_data['key']))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)
        assert test_data['value'] == retval

    async def test_get_category_item(self):
        pass

    async def test_edit_category_item(self):
        pass

    async def test_unset_category_item(self):
        pass

    async def test_put_config_new_item(self):
        pass

    async def test_put_config_merge_item(self):
        pass

    async def test_unset_config_merge_item(self):
        pass