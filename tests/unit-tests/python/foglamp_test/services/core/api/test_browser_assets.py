# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END
import random
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
BASE_URL = 'localhost:8081'
headers = {"Content-Type": 'application/json'}

test_data_asset_code = 'TESTAPI'
sensor_code_1 = 'x'
sensor_code_2 = 'y'

pytestmark = pytest.mark.asyncio


async def add_master_data(rows=0):
    """
    For test data: 1 record is created with user_ts = (current time - 10 seconds)
                   1 record is created with user_ts = (current time - 10 minutes)
                   1 record is created with user_ts = (current time - 1 hour)
                   other records are created with user_ts = (current time - 10 hour)
    """
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
        await conn.execute("""INSERT INTO foglamp.readings(asset_code,read_key,reading,user_ts,ts)
                           VALUES($1, $2, $3, $4, $5);""", test_data_asset_code, uid,
                           json.dumps({sensor_code_1: x, sensor_code_2: y}), ts, datetime.now(tz=timezone.utc))
    await conn.close()
    return uid_list, x_list, y_list, ts_list


async def delete_master_data():
    conn = await asyncpg.connect(database=__DB_NAME)
    await conn.execute('''DELETE from foglamp.readings WHERE asset_code IN ($1)''', test_data_asset_code)
    await conn.close()


@pytest.allure.feature("api")
@pytest.allure.story("assets-browser")
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
        asyncio.get_event_loop().run_until_complete(delete_master_data())

    def setup_method(self, method):
        pass

    def teardown_method(self, method):
        pass

    def group_date_time(self, unit=None):
        """
        Groups date_time values in groups of similar unit needed for grouping query
        Example: for date_time '2017-09-19 05:00:54.000' and unit = minute
        will return distinct list of 2017-09-19 05:00
        """
        grouped_ts = []
        if unit == "second":
            date_time_length = 19
        elif unit == "minute":
            date_time_length = 16
        elif unit == "hour":
            date_time_length = 13
        else:
            date_time_length = 19
        for elements in self.test_data_ts_list:
            if elements[:date_time_length] not in grouped_ts:
                grouped_ts.append(elements[:date_time_length])
        return grouped_ts

    # TODO: Add tests for negative cases. Currently only positive test cases have been added.
    # Also add tests with skip param

    """
    Tests for get asset readings
    """
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
                assert 21 == elements['count']

    async def test_get_asset_readings(self):
        """
        Verify that if more than 20 readings, only 20 are returned as the default limit for asset_code
        http://localhost:8082/foglamp/asset/TESTAPI
        """
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

        # Verify that limit 1 returns the last inserted reading only
        assert 1 == len(retval)
        assert retval[0]['reading'][sensor_code_1] == self.test_data_x_val_list[-1]
        assert retval[0]['reading'][sensor_code_2] == self.test_data_y_val_list[-1]
        assert retval[0]['timestamp'] == self.test_data_ts_list[-1]

    async def test_get_asset_readings_q_sec(self):
        """
        Verify that if more than 20 readings, only last n sec readings are returned
        when seconds is passed as query parameter
        http://localhost:8082/foglamp/asset/TESTAPI?seconds=15
        """
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/asset/{}?seconds={}'.format(test_data_asset_code, 15))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)

        # Since we have only 1 record for last 15 seconds in test data
        assert 1 == len(retval)
        assert retval[0]['reading'][sensor_code_1] == self.test_data_x_val_list[-1]
        assert retval[0]['reading'][sensor_code_2] == self.test_data_y_val_list[-1]
        assert retval[0]['timestamp'] == self.test_data_ts_list[-1]

    async def test_get_asset_readings_q_min(self):
        """
        Verify that if more than 20 readings, only last n min readings are returned
        when minutes is passed as query parameter
        http://localhost:8082/foglamp/asset/TESTAPI?minutes=15
        """
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/asset/{}?minutes={}'.format(test_data_asset_code, 15))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)

        # Since we have only 2 record for last 15 minutes in test data
        assert 2 == len(retval)
        assert retval[0]['reading'][sensor_code_1] == self.test_data_x_val_list[-1]
        assert retval[0]['reading'][sensor_code_2] == self.test_data_y_val_list[-1]
        assert retval[0]['timestamp'] == self.test_data_ts_list[-1]
        assert retval[1]['reading'][sensor_code_1] == self.test_data_x_val_list[-2]
        assert retval[1]['reading'][sensor_code_2] == self.test_data_y_val_list[-2]
        assert retval[1]['timestamp'] == self.test_data_ts_list[-2]

    async def test_get_asset_readings_q_hrs(self):
        """
        Verify that if more than 20 readings, only last n hrs readings are returned
        when hours is passed as query parameter
        http://localhost:8082/foglamp/asset/TESTAPI?hours=2
        """
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/asset/{}?hours={}'.format(test_data_asset_code, 2))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)

        # Since we have only 3 record for last 2 hours in test data
        assert 3 == len(retval)
        assert retval[0]['reading'][sensor_code_1] == self.test_data_x_val_list[-1]
        assert retval[0]['reading'][sensor_code_2] == self.test_data_y_val_list[-1]
        assert retval[0]['timestamp'] == self.test_data_ts_list[-1]
        assert retval[1]['reading'][sensor_code_1] == self.test_data_x_val_list[-2]
        assert retval[1]['reading'][sensor_code_2] == self.test_data_y_val_list[-2]
        assert retval[1]['timestamp'] == self.test_data_ts_list[-2]
        assert retval[2]['reading'][sensor_code_1] == self.test_data_x_val_list[-3]
        assert retval[2]['reading'][sensor_code_2] == self.test_data_y_val_list[-3]
        assert retval[2]['timestamp'] == self.test_data_ts_list[-3]

    async def test_get_asset_readings_q_time_complex(self):
        """
        Verify that if a combination of hrs, min, sec is used, shortest period will apply
        http://localhost:8082/foglamp/asset/TESTAPI?hours=20&minutes=20&seconds=20&limit=20
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
        assert retval[0]['reading'][sensor_code_1] == self.test_data_x_val_list[-1]
        assert retval[0]['reading'][sensor_code_2] == self.test_data_y_val_list[-1]
        assert retval[0]['timestamp'] == self.test_data_ts_list[-1]

    """
    Tests for get asset readings for single sensor
    """
    async def test_get_asset_sensor_readings(self):
        """
        Verify that if more than 20 readings for an assets sensor value, only 20 are returned as the default limit
        http://localhost:8082/foglamp/asset/TESTAPI/x
        """
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/asset/{}/{}'.format(test_data_asset_code, sensor_code_1))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)
        assert 20 == len(retval)

    async def test_get_asset_sensor_readings_q_limit(self):
        """
        Verify that if more than 20 readings, limited readings for a sensor value are returned when querying with limit
        http://localhost:8082/foglamp/asset/TESTAPI/x?limit=1
        """
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/asset/{}/{}?limit={}'.format(test_data_asset_code, sensor_code_1, 1))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)
        assert 1 == len(retval)
        assert retval[0][sensor_code_1] == self.test_data_x_val_list[-1]
        assert retval[0]['timestamp'] == self.test_data_ts_list[-1]

    async def test_get_asset_sensor_readings_q_sec(self):
        """
        Verify that if more than 20 readings, only last n sec readings for a sensor value are returned when
        seconds is passed as query parameter
        http://localhost:8082/foglamp/asset/TESTAPI/x?seconds=120
        """
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/asset/{}/{}?seconds={}'.format(test_data_asset_code, sensor_code_1, 120))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)
        assert 1 == len(retval)
        assert retval[0][sensor_code_1] == self.test_data_x_val_list[-1]
        assert retval[0]['timestamp'] == self.test_data_ts_list[-1]

    async def test_get_asset_sensor_readings_q_min(self):
        """
        Verify that if more than 20 readings, only last n min readings for a sensor value are returned when
        minutes is passed as query parameter
        http://localhost:8082/foglamp/asset/TESTAPI/x?minutes=20
        """
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/asset/{}/{}?minutes={}'.format(test_data_asset_code, sensor_code_1, 20))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)
        assert 2 == len(retval)
        assert retval[0][sensor_code_1] == self.test_data_x_val_list[-1]
        assert retval[0]['timestamp'] == self.test_data_ts_list[-1]
        assert retval[1][sensor_code_1] == self.test_data_x_val_list[-2]
        assert retval[1]['timestamp'] == self.test_data_ts_list[-2]

    async def test_get_asset_sensor_readings_q_hrs(self):
        """
        Verify that if more than 20 readings, only last n hr readings for a sensor value are returned when
        hours is passed as query parameter
        http://localhost:8082/foglamp/asset/TESTAPI/x?hours=2
        """
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/asset/{}/{}?hours={}'.format(test_data_asset_code, sensor_code_1, 2))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)
        assert 3 == len(retval)
        assert retval[0][sensor_code_1] == self.test_data_x_val_list[-1]
        assert retval[0]['timestamp'] == self.test_data_ts_list[-1]
        assert retval[1][sensor_code_1] == self.test_data_x_val_list[-2]
        assert retval[1]['timestamp'] == self.test_data_ts_list[-2]
        assert retval[2][sensor_code_1] == self.test_data_x_val_list[-3]
        assert retval[2]['timestamp'] == self.test_data_ts_list[-3]

    async def test_get_asset_sensor_readings_q_time_complex(self):
        """
        Verify that if a combination of hrs, min, sec is used, shortest period will apply for sensor reading
        http://localhost:8082/foglamp/asset/TESTAPI/x?hours=20&minutes=20&seconds=120&limit=20
        """
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/asset/{}/{}?hours={}&minutes={}&seconds={}&limit={}'
                     .format(test_data_asset_code, sensor_code_1, 20, 20, 120, 20))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)
        assert 1 == len(retval)
        assert retval[0][sensor_code_1] == self.test_data_x_val_list[-1]
        assert retval[0]['timestamp'] == self.test_data_ts_list[-1]

    """
    Tests for min/max/averages of a set of sensor readings
    """
    @pytest.mark.xfail(reason="FOGL-547")
    async def test_get_asset_sensor_readings_stats(self):
        """
        Verify that if more than 20 readings for an assets sensor value,
        summary of only 20 readings are returned as the default limit
        http://localhost:8082/foglamp/asset/TESTAPI/x/summary
        """
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/asset/{}/{}/summary'.format(test_data_asset_code, sensor_code_1))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)

        assert 1 == len(retval)
        # Verify with last 20 records [1:] of test data since we are querying for default limit of 20
        assert retval[sensor_code_1]['min'] == min(self.test_data_x_val_list[1:])
        assert retval[sensor_code_1]['average'] == sum(self.test_data_x_val_list[1:])/len(self.test_data_x_val_list[1:])
        assert retval[sensor_code_1]['max'] == max(self.test_data_x_val_list[1:])

    @pytest.mark.xfail(reason="FOGL-547")
    async def test_get_asset_sensor_readings_stats_q_sec(self):
        """
        Verify that if more than 20 readings, summary of only last n sec readings for a sensor value are returned when
        seconds is passed as query parameter
        http://localhost:8082/foglamp/asset/TESTAPI/x/summary?seconds=180
        """
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/asset/{}/{}/summary?seconds={}'.format(test_data_asset_code, sensor_code_1, 180))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)

        assert 1 == len(retval)
        # We have 1 record in test data for last 180 sec
        assert retval[sensor_code_1]['min'] == self.test_data_x_val_list[-1]
        assert retval[sensor_code_1]['average'] == self.test_data_x_val_list[-1]
        assert retval[sensor_code_1]['max'] == self.test_data_x_val_list[-1]

    @pytest.mark.xfail(reason="FOGL-547")
    async def test_get_asset_sensor_readings_stats_q_min(self):
        """
        Verify that if more than 20 readings, summary of only last n min readings for a sensor value are returned when
        minutes is passed as query parameter
        http://localhost:8082/foglamp/asset/TESTAPI/x?minutes=20
        """
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/asset/{}/{}/summary?minutes={}'.format(test_data_asset_code, sensor_code_1, 20))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)

        assert 1 == len(retval)
        avg = sum(self.test_data_x_val_list[-2:])/len(self.test_data_x_val_list[-2:])
        # We have 2 records in test data for last 20 min
        assert retval[sensor_code_1]['min'] == min(self.test_data_x_val_list[-2:])
        assert retval[sensor_code_1]['average'] == avg
        assert retval[sensor_code_1]['max'] == max(self.test_data_x_val_list[-2:])

    @pytest.mark.xfail(reason="FOGL-547")
    async def test_get_asset_sensor_readings_stats_q_hrs(self):
        """
        Verify that if more than 20 readings, summary of only last n hrs readings for a sensor value are returned when
        hours is passed as query parameter
        http://localhost:8082/foglamp/asset/TESTAPI/x?hours=2
        """
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/asset/{}/{}/summary?hours={}'.format(test_data_asset_code, sensor_code_1, 2))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)

        assert 1 == len(retval)
        avg = sum(self.test_data_x_val_list[-3:])/len(self.test_data_x_val_list[-3:])
        # We have 3 records in test data for last 2 hours
        assert retval[sensor_code_1]['min'] == min(self.test_data_x_val_list[-3:])
        assert retval[sensor_code_1]['average'] == avg
        assert retval[sensor_code_1]['max'] == max(self.test_data_x_val_list[-3:])

    @pytest.mark.xfail(reason="FOGL-547")
    async def test_get_asset_sensor_readings_stats_q_time_complex(self):
        """
        Verify that if a combination of hrs, min, sec is used, shortest period will apply for sensor reading
        combined with limit of 20 (AND condition)
        http://localhost:8082/foglamp/asset/TESTAPI/x/summary?hours=20&minutes=20&seconds=180&limit=20
        """
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/asset/{}/{}/summary?hours={}&minutes={}&seconds={}&limit={}'
                     .format(test_data_asset_code, sensor_code_1, 20, 20, 180, 20))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)

        assert 1 == len(retval)
        assert retval[sensor_code_1]['min'] == self.test_data_x_val_list[-1]
        assert retval[sensor_code_1]['average'] == self.test_data_x_val_list[-1]
        assert retval[sensor_code_1]['max'] == self.test_data_x_val_list[-1]

    """
    Tests for time averaged sensor values
    """
    @pytest.mark.xfail(reason="FOGL-547")
    async def test_get_asset_sensor_readings_time_avg(self):
        """
        Verify that series data is grouped by default on seconds
        http://localhost:8082/foglamp/asset/TESTAPI/x/series
        """
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/asset/{}/{}/series'.format(test_data_asset_code, sensor_code_1))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)

        # Find unique set of times grouped by seconds from test data
        grouped_ts_sec = self.group_date_time(unit="second")

        # Verify the length of groups and value of last element. Test data has only 1 record for last second's group
        assert len(grouped_ts_sec) == len(retval)
        assert retval[-1]["average"] == self.test_data_x_val_list[-1]
        assert retval[-1]["max"] == self.test_data_x_val_list[-1]
        assert retval[-1]["min"] == self.test_data_x_val_list[-1]
        assert retval[-1]["time"] == grouped_ts_sec[-1]

    @pytest.mark.xfail(reason="FOGL-547")
    async def test_get_asset_sensor_readings_time_avg_q_group_sec(self):
        """
        Verify that series data is grouped by seconds
        http://localhost:8082/foglamp/asset/TESTAPI/x/series?group=seconds
        """
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/asset/{}/{}/series?group=seconds'.format(test_data_asset_code, sensor_code_1))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)

        # Find unique set of times grouped by seconds from test data
        grouped_ts_sec = self.group_date_time(unit="second")

        # Grouped by 'YYY-MM-DD hh:mm:ss' returns 4 data points, verify the last data point with last value of test data
        assert len(grouped_ts_sec) == len(retval)
        assert retval[-1]["average"] == self.test_data_x_val_list[-1]
        assert retval[-1]["max"] == self.test_data_x_val_list[-1]
        assert retval[-1]["min"] == self.test_data_x_val_list[-1]
        assert retval[-1]["time"] == grouped_ts_sec[-1]

    @pytest.mark.xfail(reason="FOGL-547")
    async def test_get_asset_sensor_readings_time_avg_q_group_min(self):
        """
        Verify that series data is grouped by minutes
        http://localhost:8082/foglamp/asset/TESTAPI/x/series?group=minutes
        """
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/asset/{}/{}/series?group=minutes'.format(test_data_asset_code, sensor_code_1))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)
        # Find unique set of times grouped by minutes from test data
        grouped_ts_min = self.group_date_time(unit="minute")

        # Grouped by 'YYY-MM-DD hh:mm' returns 4 data points, verify the last data point with last value of test data
        assert len(grouped_ts_min) == len(retval)
        assert retval[-1]["average"] == self.test_data_x_val_list[-1]
        assert retval[-1]["max"] == self.test_data_x_val_list[-1]
        assert retval[-1]["min"] == self.test_data_x_val_list[-1]
        assert retval[-1]["time"] == grouped_ts_min[-1]

    @pytest.mark.xfail(reason="FOGL-547")
    async def test_get_asset_sensor_readings_time_avg_q_group_hrs(self):
        """
        Verify that series data is grouped by hours
        http://localhost:8082/foglamp/asset/TESTAPI/x/series?group=hours
        """
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/asset/{}/{}/series?group=hours'.format(test_data_asset_code, sensor_code_1))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)
        # Find unique set of times grouped by hours from test data
        grouped_ts_hrs = self.group_date_time(unit="hour")

        # Verify the values of a group, We know last 2 records of test data were created within the same hour
        assert len(grouped_ts_hrs) == len(retval)
        assert retval[-1]["average"] == sum(self.test_data_x_val_list[-2:]) / len(self.test_data_x_val_list[-2:])
        assert retval[-1]["max"] == max(self.test_data_x_val_list[-2:])
        assert retval[-1]["min"] == min(self.test_data_x_val_list[-2:])
        assert retval[-1]["time"] == grouped_ts_hrs[-1]

    @pytest.mark.xfail(reason="FOGL-547")
    async def test_get_asset_sensor_readings_time_avg_q_limit_group_hrs(self):
        """
        Verify that series data is grouped by hours and limits are working
        http://localhost:8082/foglamp/asset/TESTAPI/x/series?group=hours&limit=1
        """
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/asset/{}/{}/series?group=hours&limit={}'
                     .format(test_data_asset_code, sensor_code_1, 1))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)

        # Find unique set of times grouped by hours from test data
        grouped_ts_hrs = self.group_date_time(unit="hour")

        # Verify the values of a group, We know first 19 records of test data were created within the same hour
        assert 1 == len(retval)
        assert retval[-1]["average"] == sum(self.test_data_x_val_list[:19]) / len(self.test_data_x_val_list[:19])
        assert retval[-1]["max"] == max(self.test_data_x_val_list[:19])
        assert retval[-1]["min"] == min(self.test_data_x_val_list[:19])
        assert retval[-1]["time"] == grouped_ts_hrs[0]

    @pytest.mark.xfail(reason="FOGL-547")
    async def test_get_asset_sensor_readings_time_avg_q_time(self):
        """
        Verify that series data is grouped by seconds (default) and time range (last n minutes) is working
        http://localhost:8082/foglamp/asset/TESTAPI/x/series?minutes=20
        """
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/asset/{}/{}/series?minutes={}'.format(test_data_asset_code, sensor_code_1, 20))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)

        # Find unique set of times grouped by seconds (default grouping) from test data
        grouped_ts = self.group_date_time()

        # Verify the values of a group (default by sec), has 2 records only when querying for last 20 min
        # For last n min, grouped by 'YYY-MM-DD hh:mm:ss' verify with last and second last test data
        assert 2 == len(retval)
        assert retval[-1]["average"] == self.test_data_x_val_list[-1]
        assert retval[-1]["max"] == self.test_data_x_val_list[-1]
        assert retval[-1]["min"] == self.test_data_x_val_list[-1]
        assert retval[-1]["time"] == grouped_ts[-1]

        assert retval[-2]["average"] == self.test_data_x_val_list[-2]
        assert retval[-2]["max"] == self.test_data_x_val_list[-2]
        assert retval[-2]["min"] == self.test_data_x_val_list[-2]
        assert retval[-2]["time"] == grouped_ts[-2]

    @pytest.mark.xfail(reason="FOGL-547")
    async def test_get_asset_sensor_readings_time_avg_q_group_time_limit(self):
        """
        Verify that if a combination of hrs, min, sec is used, shortest period will apply with specified grouping
        http://localhost:8082/foglamp/asset/TESTAPI/x/series?hours=20&minutes=20&seconds=180&limit=20&group=hours
        """
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/asset/{}/{}/series?hours={}&minutes={}&seconds={}&limit={}&group=hours'
                     .format(test_data_asset_code, sensor_code_1, 20, 20, 280, 20))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        retval = json.loads(r)

        # Find unique set of times grouped by hours from test data
        grouped_ts = self.group_date_time(unit="hour")

        # Verify the values of a group, has 1 record only (shortest time) and hourly grouping
        # For example in last 180 sec, grouped by 'YYY-MM-DD hh' is equal to last record of test data
        assert 1 == len(retval)
        assert retval[-1]["average"] == self.test_data_x_val_list[-1]
        assert retval[-1]["max"] == self.test_data_x_val_list[-1]
        assert retval[-1]["min"] == self.test_data_x_val_list[-1]
        assert retval[-1]["time"] == grouped_ts[-1]
