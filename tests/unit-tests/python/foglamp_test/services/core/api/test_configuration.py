# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

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
BASE_URL = 'localhost:8081'
headers = {"Content-Type": 'application/json'}

test_data = {'key': 'TESTAPI', 'description': 'RESTAPI Test Config',
             'value': {'item1': {'description': 'desc', 'type': 'string', 'default': 'def', 'value': 'def'}}}
pytestmark = pytest.mark.asyncio


async def add_master_data():
    conn = await asyncpg.connect(database=__DB_NAME)
    await conn.execute('''DELETE from foglamp.configuration WHERE key IN ($1)''', test_data['key'])
    await conn.execute("""INSERT INTO foglamp.configuration(key, description, value) VALUES($1, $2, $3);""",
                       test_data['key'], test_data['description'], json.dumps(test_data['value']))
    await conn.close()


async def delete_master_data():
    conn = await asyncpg.connect(database=__DB_NAME)
    await conn.execute('''DELETE from foglamp.configuration WHERE key IN ($1)''', test_data['key'])
    await conn.close()


@pytest.allure.feature("api")
@pytest.allure.story("configuration-manager")
class TestConfigMgr:
    @classmethod
    def setup_class(cls):
        asyncio.get_event_loop().run_until_complete(add_master_data())
        # from subprocess import call
        # call(["foglamp", "start"])
        # # TODO: Due to lengthy start up, now tests need a better way to start foglamp or poll some
        # #       external process to check if foglamp has started.
        # time.sleep(20)

    @classmethod
    def teardown_class(cls):
        # from subprocess import call
        # call(["foglamp", "stop"])
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
        conn = http.client.HTTPConnection(BASE_URL)
        test_data_item = [key for key in test_data['value']][0]
        test_data_item_value = test_data['value'][test_data_item]
        conn.request("GET", '/foglamp/category/{}/{}'.format(test_data['key'], test_data_item))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)
        assert test_data_item_value == retval

    async def test_set_category_item_value(self):
        conn = http.client.HTTPConnection(BASE_URL)
        test_data_item = [key for key in test_data['value']][0]
        test_data_item_value = test_data['value'][test_data_item]
        body = {"value": 'some_value'}
        json_data = json.dumps(body)
        conn.request("PUT", '/foglamp/category/{}/{}'.format(test_data['key'], test_data_item), json_data)
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)
        test_data_item_value.update(body)
        assert test_data_item_value == retval

    async def test_edit_category_item_value(self):
        conn = http.client.HTTPConnection(BASE_URL)
        test_data_item = [key for key in test_data['value']][0]
        test_data_item_value = test_data['value'][test_data_item]
        body = {"value": 'updated_value'}
        json_data = json.dumps(body)
        conn.request("PUT", '/foglamp/category/{}/{}'.format(test_data['key'], test_data_item), json_data)
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)
        test_data_item_value.update(body)
        assert test_data_item_value == retval

    async def test_unset_config_item(self):
        conn = http.client.HTTPConnection(BASE_URL)
        test_data_item = [key for key in test_data['value']][0]

        conn.request("DELETE", '/foglamp/category/{}/{}/value'.format(test_data['key'], test_data_item))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        retval = json.loads(r)
        test_data['value'][test_data_item]['value'] = ''
        assert test_data['value'][test_data_item] == retval

        # Fetch category item value again and verify it is set to blank
        conn.request("GET", '/foglamp/category/{}/{}'.format(test_data['key'], test_data_item))
        r = conn.getresponse()
        assert 200 == r.status
        conn.close()
        assert test_data['value'][test_data_item] == retval

    @pytest.mark.skip(reason="FOGL-481")
    async def test_merge_category(self):
        # TODO: Delete all prints after verification of todo comments
        conn = http.client.HTTPConnection(BASE_URL)
        body = {'value': {'item2': {'description': 'desc2', 'type': 'string', 'default': 'def2'}}}
        test_data_item = [key for key in body['value']][0]
        print("ITEM::", test_data_item)
        test_data_item_value = body['value'][test_data_item]
        json_data = json.dumps(test_data_item_value)
        print("PUT", '/foglamp/category/{}/{}'.format(test_data['key'], test_data_item), json_data)

        # TODO: FOGL-481: Returns 500 error, Bug?
        # Endpoint not defined for adding (merging) a new config item to existing config?
        conn.request("PUT", '/foglamp/category/{}/{}'.format(test_data['key'], test_data_item), json_data)
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)
        print(retval)
        test_data['value'].update(body['value'])
        print("test_data_new", test_data)
        assert test_data == retval

    async def test_check_error_code_message(self):
        conn = http.client.HTTPConnection(BASE_URL)
        body = {"key1": "invalid_key", "value1": 'invalid_value'}
        json_data = json.dumps(body)
        conn.request("PUT", '/foglamp/category/{}/{}'.format('key', 'value'), json_data)
        r = conn.getresponse()

        assert 200 == r.status
        s = r.read().decode()
        retval = json.loads(s)

        assert 400 == retval['error']['code']
        assert 'Missing required value for value' == retval['error']['message']
        conn.close()
