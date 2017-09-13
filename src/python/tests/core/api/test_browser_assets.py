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
from datetime import datetime, timezone

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# Module attributes
__DB_NAME = "foglamp"
BASE_URL = 'localhost:8082'
headers = {"Content-Type": 'application/json'}

test_data = {'asset_code': 'TESTAPI', 'read_key': '8090518d-e63d-4db6-b123-54ea85ced362',
             'reading': {'x': 1, 'y': 1}}
pytestmark = pytest.mark.asyncio


async def add_master_data():
    conn = await asyncpg.connect(database=__DB_NAME)
    await conn.execute('''DELETE from foglamp.readings WHERE asset_code IN ($1)''', test_data['asset_code'])
    await conn.execute("""INSERT INTO foglamp.readings(asset_code,read_key,reading,user_ts) VALUES($1, $2, $3, $4);""",
                       test_data['asset_code'], test_data['read_key'],
                       json.dumps(test_data['reading']), datetime.now(tz=timezone.utc))
    await conn.close()


async def delete_master_data():
    conn = await asyncpg.connect(database=__DB_NAME)
    await conn.execute('''DELETE from foglamp.readings WHERE asset_code IN ($1)''', test_data['asset_code'])
    await conn.close()

@pytest.allure.feature("api")
@pytest.allure.story("browser-assets")
class TestBrowseAssets:
    @classmethod
    def setup_class(cls):
        asyncio.get_event_loop().run_until_complete(add_master_data())
        from subprocess import call
        call(["foglamp", "start"])
        time.sleep(4)

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

    async def test_get_asset_summary(self):
        pass
