# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END
import random
import time
import json

import asyncpg
import http.client
import pytest
import asyncio
import uuid
from datetime import datetime, timezone, timedelta

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# Module attributes
__DB_NAME = "foglamp"
BASE_URL = 'localhost:8082'
headers = {"Content-Type": 'application/json'}

test_data_asset_code = 'TESTAPI'

pytestmark = pytest.mark.asyncio


async def add_master_data(rows=0):
    conn = await asyncpg.connect(database=__DB_NAME)
    await conn.execute('''DELETE from foglamp.readings WHERE asset_code IN ($1)''', test_data_asset_code)
    uid_list = []
    x_list = []
    y_list = []
    ts_list = []
    for i in range(rows):
        uid = uuid.uuid4()
        uid_list.append(uid)
        x = random.randint(1, 100)
        y = random.uniform(1.0, 100.0)
        # Insert some time based data
        if i == 18:
            ts = (datetime.now(tz=timezone.utc) - timedelta(hours=1))
        elif i == 19:
            ts = (datetime.now(tz=timezone.utc) - timedelta(minutes=10))
        elif i == 20:
            ts = (datetime.now(tz=timezone.utc) - timedelta(seconds=10))
        else:
            ts = (datetime.now(tz=timezone.utc) - timedelta(hours=10))
        x_list.append(x)
        y_list.append(y)
        ts_list.append(((ts + timedelta(milliseconds=.000500)).astimezone()).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3])
        await conn.execute("""INSERT INTO foglamp.readings(asset_code,read_key,reading,user_ts,ts) VALUES($1, $2, $3, $4, $5);""",
                           test_data_asset_code, uid,
                           json.dumps({'x': x, 'y': y}), ts, datetime.now(tz=timezone.utc))
    await conn.close()
    return uid_list, x_list, y_list, ts_list

async def delete_master_data():
    conn = await asyncpg.connect(database=__DB_NAME)
    await conn.execute('''DELETE from foglamp.readings WHERE asset_code IN ($1)''', test_data_asset_code)
    await conn.close()


@pytest.allure.feature("api")
@pytest.allure.story("browser-assets")
class TestBrowseAssets:
    test_data_uid_list = []
    test_data_x_val_list = []
    test_data_y_val_list = []
    test_data_ts_list = []

    @classmethod
    def setup_class(cls):
        cls.test_data_uid_list, cls.test_data_x_val_list, cls.test_data_y_val_list, cls.test_data_ts_list = \
            asyncio.get_event_loop().run_until_complete(add_master_data(21))

    @classmethod
    def teardown_class(cls):
        # asyncio.get_event_loop().run_until_complete(delete_master_data())
        pass

    def setup_method(self, method):
        pass

    def teardown_method(self, method):
        pass

    # TODO: Add tests for negative cases. Currently only positive test cases have been added.

    async def test_get_all_assets(self):
        """
        Verify that Asset contains the test data and readings count is equal to the number of readings inserted
        """
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/asset')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)
        all_items = [elements['asset_code'] for elements in retval]
        assert test_data_asset_code in all_items
        for elements in retval:
            if elements['asset_code'] == test_data_asset_code:
                assert len(self.test_data_uid_list) == elements['count']

    async def test_get_asset_readings(self):
        """
        Verify that if more than 20 readings, only 20 are returned as the default limit for asset_code
        """
        # Assert that if more than 20 readings, only 20 are returned as the default limit
        # http://localhost:8082/foglamp/asset/TESTAPI

        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/asset/{}'.format(test_data_asset_code))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)
        assert 20 == len(retval)

    async def test_get_asset_readings_q_limit(self):
        """
        Verify that if more than 20 readings, limited readings are returned for asset_code when querying with limit
        http://localhost:8082/foglamp/asset/TESTAPI?limit=1
        """
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/asset/{}?limit={}'.format(test_data_asset_code, 1))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)
        assert 1 == len(retval)
        assert retval[0]['reading']['x'] == self.test_data_x_val_list[-1]
        assert retval[0]['reading']['y'] == self.test_data_y_val_list[-1]
        assert retval[0]['timestamp'] == self.test_data_ts_list[-1]

    async def test_get_asset_readings_q_sec(self):
        """
        Verify that if more than 20 readings, only last n sec readings are returned when seconds is passed as query parameter
        http://localhost:8082/foglamp/asset/TESTAPI?seconds=15
        """
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/asset/{}?seconds={}'.format(test_data_asset_code, 15))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)
        assert 1 == len(retval)
        assert retval[0]['reading']['x'] == self.test_data_x_val_list[-1]
        assert retval[0]['reading']['y'] == self.test_data_y_val_list[-1]
        assert retval[0]['timestamp'] == self.test_data_ts_list[-1]

    async def test_get_asset_readings_q_min(self):
        """
        Verify that if more than 20 readings, only last n min readings are returned when minutes is passed as query parameter
        http://localhost:8082/foglamp/asset/TESTAPI?minutes=15
        """
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/asset/{}?minutes={}'.format(test_data_asset_code, 15))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)
        assert 2 == len(retval)
        assert retval[0]['reading']['x'] == self.test_data_x_val_list[-1]
        assert retval[0]['reading']['y'] == self.test_data_y_val_list[-1]
        assert retval[0]['timestamp'] == self.test_data_ts_list[-1]
        assert retval[1]['reading']['x'] == self.test_data_x_val_list[-2]
        assert retval[1]['reading']['y'] == self.test_data_y_val_list[-2]
        assert retval[1]['timestamp'] == self.test_data_ts_list[-2]

    async def test_get_asset_readings_q_hrs(self):
        """
        Verify that if more than 20 readings, only last n hrs readings are returned when hours is passed as query parameter
        http://localhost:8082/foglamp/asset/TESTAPI?hours=2
        """
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/asset/{}?hours={}'.format(test_data_asset_code, 2))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)
        assert 3 == len(retval)
        assert retval[0]['reading']['x'] == self.test_data_x_val_list[-1]
        assert retval[0]['reading']['y'] == self.test_data_y_val_list[-1]
        assert retval[0]['timestamp'] == self.test_data_ts_list[-1]
        assert retval[1]['reading']['x'] == self.test_data_x_val_list[-2]
        assert retval[1]['reading']['y'] == self.test_data_y_val_list[-2]
        assert retval[1]['timestamp'] == self.test_data_ts_list[-2]
        assert retval[2]['reading']['x'] == self.test_data_x_val_list[-3]
        assert retval[2]['reading']['y'] == self.test_data_y_val_list[-3]
        assert retval[2]['timestamp'] == self.test_data_ts_list[-3]

    async def test_get_asset_readings_q_time_complex(self):
        """
        Verify that if more than 20 readings, only last n hrs readings are returned when hours is passed as query parameter
        Also, that if a combination of hrs, min, sec is used, shorted period will apply
        http://localhost:8082/foglamp/asset/TESTAPI??hours=20&minutes=20&seconds=20&limit=20
        """
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/asset/{}?hours={}&minutes={}&seconds={}&limit={}'.format(test_data_asset_code,
                                                                                               20, 20, 20, 20))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)
        assert 1 == len(retval)
        assert retval[0]['reading']['x'] == self.test_data_x_val_list[-1]
        assert retval[0]['reading']['y'] == self.test_data_y_val_list[-1]
        assert retval[0]['timestamp'] == self.test_data_ts_list[-1]


    async def test_get_asset_sensor_readings(self):
        # Assert that if more than 20 readings, only 20 are returned as the default limit
        # http://localhost:8082/foglamp/asset/TESTAPI/x
        pass

    async def test_get_asset_sensor_readings_q_limit(self):
        pass

    async def test_get_asset_sensor_readings_q_min(self):
        pass

    async def test_get_asset_sensor_readings_q_hrs(self):
        pass

    async def test_get_asset_sensor_readings_q_time(self):
        pass

    async def test_get_asset_sensor_readings_stats(self):
        # Assert that if more than 20 readings, only 20 are returned as the default limit
        # http://localhost:8082/foglamp/asset/TESTAPI/x/summary
        pass

    async def test_get_asset_sensor_readings_stats_q_limit(self):
        pass

    async def test_get_asset_sensor_readings_stats_q_min(self):
        pass

    async def test_get_asset_sensor_readings_stats_q_hrs(self):
        pass

    async def test_get_asset_sensor_readings_stats_q_time(self):
        pass

    async def test_get_asset_sensor_readings_time_avg(self):
        # Assert that if more than 20 readings, only 20 are returned as the default limit
        # http://localhost:8082/foglamp/asset/TESTAPI/x/series?group=hours
        pass

    async def test_get_asset_sensor_readings_time_avg_q_group(self):
        pass

    async def test_get_asset_sensor_readings_time_avg_q_limit(self):
        pass

    async def test_get_asset_sensor_readings_time_avg_q_min(self):
        pass

    async def test_get_asset_sensor_readings_time_avg_q_hrs(self):
        pass

    async def test_get_asset_sensor_readings_time_avg_q_time(self):
        pass