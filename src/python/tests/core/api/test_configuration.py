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
BASE_URL = 'localhost'
PORT = 8082
headers = {"Content-Type": 'application/json'}

pytestmark = pytest.mark.asyncio


async def add_master_data():
    conn = await asyncpg.connect(database=__DB_NAME)
    await conn.execute('''DELETE from foglamp.configuration WHERE key IN ('TEST_V', 'TEST_B')''')
    await conn.execute('''insert into foglamp.configuration(key, description, value)
        values('TEST_V', 'REST API Test Config Manager for pre values', '{"item1": {"key1": "value1"}}')''')
    await conn.execute('''insert into foglamp.configuration(key, description)
        values('TEST_B', 'REST API Test Config Manager for blank values')''')
    await conn.close()
    await asyncio.sleep(4)


async def delete_master_data():
    conn = await asyncpg.connect(database=__DB_NAME)
    await conn.execute('''DELETE from foglamp.configuration WHERE key IN ('TEST_V', 'TEST_B')''')
    await conn.close()
    await asyncio.sleep(4)


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
        pass

    async def test_get_category(self):
        pass

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