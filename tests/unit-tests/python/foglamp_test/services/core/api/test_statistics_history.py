# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import asyncpg
import asyncio
from datetime import datetime
import requests
import pytest

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

__DB_NAME = "foglamp"
BASE_URL = 'http://localhost:8081/foglamp'

pytestmark = pytest.mark.asyncio


async def set_statistics_test_data(val):
    conn = await asyncpg.connect(database=__DB_NAME)
    await conn.execute('''UPDATE foglamp.statistics SET value = $1, previous_value = $2''', val, 0)
    await conn.close()


@pytest.allure.feature("api")
@pytest.allure.story("statistics-history")
class TestStatisticsHistory:

    @classmethod
    def setup_class(cls):
        # start foglamp
        pass

    @classmethod
    def teardown_class(cls):
        # stop foglamp
        pass

    async def test_get_statistics_history(self):
        r = requests.get(BASE_URL + '/statistics/history')
        res = r.json()

        assert 200 == r.status_code
        last_count = len(res['statistics']) * 8

        # use fixture
        await set_statistics_test_data(10)

        assert 15 == res['interval']

        # Wait for 15 (as per the task schedule) seconds
        # to get 1 more batch of statistics updated value in statistics_history
        # FIXME: we should not wait in actual; but execute the task itself
        await asyncio.sleep(15)

        r2 = requests.get(BASE_URL + '/statistics/history')
        res2 = r2.json()

        updated_count = len(res2['statistics']) * 8

        assert last_count + 8 == updated_count

        assert 10 == res2['statistics'][-1]['BUFFERED']
        assert 10 == res2['statistics'][-1]['DISCARDED']
        assert 10 == res2['statistics'][-1]['UNSENT']
        assert 10 == res2['statistics'][-1]['SENT_1']
        assert 10 == res2['statistics'][-1]['SENT_2']
        assert 10 == res2['statistics'][-1]['UNSNPURGED']
        assert 10 == res2['statistics'][-1]['READINGS']
        assert 10 == res2['statistics'][-1]['PURGED']

        # use fixtures
        await set_statistics_test_data(0)

    async def test_get_statistics_history_with_limit(self):
        """ Verify return <limit> set of records
        """
        r = requests.get(BASE_URL + '/statistics/history?limit=2')
        res = r.json()
        assert 200 == r.status_code

        # Wait for 15 (as per the task schedule) seconds
        # to get 1 more batch of statistics updated value in statistics_history
        # FIXME: we should not wait in actual; but execute the task itself
        await asyncio.sleep(15)

        # verify returned record count based on limit
        assert 2 == len(res['statistics'])
        assert 15 == res['interval']

        previous_time = -1  # make it better
        is_greater_time = False

        # Verify history timestamp is in ascending order
        for r in res['statistics']:
            date = datetime.strptime(r['history_ts'], "%Y-%m-%d %H:%M:%S")

            # convert time in seconds
            time = date.hour*60*60 + date.minute*60 + date.second

            # compare history timestamp
            if time >= previous_time:
                previous_time = time
                is_greater_time = True
            else:
                is_greater_time = False
                break

        assert is_greater_time is True

    async def test_get_statistics_history_limit_with_bad_data(self):
        r = requests.get(BASE_URL + '/statistics/history?limit=x')
        res = r.json()
        """ should return:
                400 | Bad request error, for limit parameter
            returns:
                "error": {
                    "message": "[ValueError]invalid literal for int() with base 10: 'x'",
                    "code": 500
                }
        """
        assert 400 == res['error']['code']
