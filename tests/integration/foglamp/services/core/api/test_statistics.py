# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import asyncpg
import requests
import pytest

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

__DB_NAME = "foglamp"
BASE_URL = 'http://localhost:8081/foglamp'

pytestmark = pytest.mark.asyncio


async def add_statistics_test_data():
    conn = await asyncpg.connect(database=__DB_NAME)
    await conn.execute('''INSERT INTO foglamp.statistics ( key, description, value, previous_value ) VALUES
    ('READINGS_X', 'The number of readingsX received by FogLAMP since startup', 0, 0)''')
    await conn.close()


async def delete_statistics_test_data():
    conn = await asyncpg.connect(database=__DB_NAME)
    await conn.execute('''DELETE from foglamp.statistics WHERE key = $1''', "READINGS_X")
    await conn.close()


async def update_statistics(val):
    conn = await asyncpg.connect(database=__DB_NAME)
    await conn.execute('''UPDATE foglamp.statistics SET value = $1 WHERE key = $2''', val, "READINGS")
    await conn.close()


@pytest.allure.feature("api")
@pytest.allure.story("statistics")
class TestStatistics:

    @classmethod
    def setup_class(cls):
        # start foglamp
        pass

    @classmethod
    def teardown_class(cls):
        # stop foglamp
        pass

    async def test_get_statistics(self):
        # curl -X GET http://localhost:8081/foglamp/statistics
        r = requests.get(BASE_URL+'/statistics')
        res = r.json()
        assert r.status_code == 200
        assert len(res) == 9

        # sorted by key
        assert res[0]['key'] == 'BUFFERED'
        assert res[0]['value'] == 0
        assert len(res[0]['description']) > 0

        assert res[1]['key'] == 'DISCARDED'
        assert res[1]['value'] == 0
        assert len(res[1]['description']) > 0

        assert res[2]['key'] == 'PURGED'
        assert res[2]['value'] == 0
        assert len(res[2]['description']) > 0

        assert res[3]['key'] == 'READINGS'
        assert res[3]['value'] == 0
        assert len(res[3]['description']) > 0

        assert res[4]['key'] == 'SENT_1'
        assert res[4]['value'] == 0
        assert len(res[4]['description']) > 0

        assert res[5]['key'] == 'SENT_2'
        assert res[5]['value'] == 0
        assert len(res[5]['description']) > 0

        assert res[7]['key'] == 'UNSENT'
        assert res[7]['value'] == 0
        assert len(res[7]['description']) > 0

        assert res[8]['key'] == 'UNSNPURGED'
        assert res[8]['value'] == 0
        assert len(res[8]['description']) > 0

    async def test_get_updated_statistics(self):
        await update_statistics(3)

        r = requests.get(BASE_URL + '/statistics')
        res = r.json()

        assert r.status_code == 200
        assert len(res) == 9

        assert res[3]['key'] == 'READINGS'
        assert res[3]['value'] == 3

        # reset to default
        await update_statistics(0)

    async def test_get_statistics_with_new_key_entry(self):
        await add_statistics_test_data()
        r = requests.get(BASE_URL + '/statistics')
        res = r.json()

        assert r.status_code == 200
        assert len(res) == 10

        # READINGS_X must exists IN keys
        key_entries = [keys["key"] for keys in res]
        assert "READINGS_X" in key_entries

        await delete_statistics_test_data()
