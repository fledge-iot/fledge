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

last_count = 0


async def set_statistics_test_data(val):
    conn = await asyncpg.connect(database=__DB_NAME)
    await conn.execute('''UPDATE foglamp.statistics SET value = $1, previous_value = $2''', val, 0)
    await conn.close()


async def get_stats_keys_count():
    conn = await asyncpg.connect(database=__DB_NAME)
    res = await conn.fetchrow(''' SELECT count(*) FROM statistics ''')
    await conn.close()
    return res['count']


async def get_stats_collector_schedule_interval():
    conn = await asyncpg.connect(database=__DB_NAME)
    res = await conn.fetchrow(''' SELECT schedule_interval FROM schedules WHERE process_name= $1 LIMIT 1 ''',
                              'stats collector')
    time_str = res['schedule_interval']
    await conn.close()
    return time_str.seconds


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

    @pytest.mark.run(order=1)
    async def test_get_statistics_history(self):
        stats_collector_schedule_interval = await get_stats_collector_schedule_interval()
        # Wait for 15 (as per the task schedule) seconds
        # to get 1 more batch of statistics updated value in statistics_history
        # FIXME: we should not wait in actual; but execute the task itself
        await asyncio.sleep(stats_collector_schedule_interval)

        total_batch_keys = await get_stats_keys_count()

        r = requests.get(BASE_URL + '/statistics/history')
        res = r.json()
        assert 200 == r.status_code
        assert stats_collector_schedule_interval == res['interval']

        global last_count
        last_count = len(res['statistics']) * total_batch_keys

        # use fixtures
        await set_statistics_test_data(10)  # for new batch
        # FIXME: we should not wait in actual; but execute the task itself
        await asyncio.sleep(stats_collector_schedule_interval)

        r2 = requests.get(BASE_URL + '/statistics/history')
        res2 = r2.json()

        updated_count = len(res2['statistics']) * total_batch_keys

        assert 1 == len(res2['statistics']) - len(res['statistics'])
        assert last_count + total_batch_keys == updated_count

        assert 10 == res2['statistics'][-1]['BUFFERED']
        assert 10 == res2['statistics'][-1]['DISCARDED']
        assert 10 == res2['statistics'][-1]['UNSENT']
        assert 10 == res2['statistics'][-1]['SENT_1']
        assert 10 == res2['statistics'][-1]['SENT_2']
        assert 10 == res2['statistics'][-1]['UNSNPURGED']
        assert 10 == res2['statistics'][-1]['READINGS']
        assert 10 == res2['statistics'][-1]['PURGED']

        last_count = updated_count
        # use fixtures
        await set_statistics_test_data(0)

    @pytest.mark.run(order=2)
    async def test_get_statistics_history_with_limit(self):
        """ Verify return <limit> set of records
        """
        stats_collector_schedule_interval = await get_stats_collector_schedule_interval()
        # Wait for 15 (as per the task schedule) seconds
        # to get 1 more batch of statistics updated value in statistics_history
        # FIXME: we should not wait in actual; but execute the task itself
        await asyncio.sleep(stats_collector_schedule_interval)

        r = requests.get(BASE_URL + '/statistics/history?limit=2')
        res = r.json()
        assert 200 == r.status_code

        # verify returned record count based on limit
        assert 2 == len(res['statistics'])
        assert stats_collector_schedule_interval == res['interval']

        previous_time = -1  # make it better
        is_greater_time = False

        # Verify history timestamp is in ascending order
        for r in res['statistics']:
            history_ts = datetime.strptime(r['history_ts'], "%Y-%m-%d %H:%M:%S")

            # convert time in seconds
            time = history_ts.hour*60*60 + history_ts.minute*60 + history_ts.second

            # compare history timestamp
            if time >= previous_time:
                previous_time = time
                is_greater_time = True
            else:
                is_greater_time = False
                break

        assert is_greater_time is True

    @pytest.mark.parametrize("request_params, response_code, response_message", [
        ('?limit=invalid', 400, "Limit must be a positive integer"),
        ('?limit=-1', 400, "Limit must be a positive integer")
    ])
    async def test_get_statistics_history_limit_with_bad_data(self, request_params, response_code, response_message):
        r = requests.get(BASE_URL + '/statistics/history{}'.format(request_params))
        assert response_code == r.status_code
        assert response_message == r.reason
