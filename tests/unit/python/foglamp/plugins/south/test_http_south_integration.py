# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Integration test for foglamp.south.http_south"""
import asyncio
import asyncpg
import requests
import pytest


__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


__DB_NAME = "foglamp"
BASE_URL = 'http://localhost:6683/sensor-reading'
headers = {"Content-Type": 'application/json'}

async def delete_test_data():
    conn = await asyncpg.connect(database=__DB_NAME)
    await conn.execute('''DELETE from foglamp.readings WHERE asset_code IN ('sensor1', 'sensor2')''')
    await conn.close()
    await asyncio.sleep(4)

# TODO: Fix all below failing tests after FOGL-858 is fixed

@pytest.allure.story("south")
class TestHttpSouthDeviceIntegration(object):
    """Integration tests for foglamp.south.coap.IngestReadings"""

    @classmethod
    def teardown_class(cls):
        asyncio.get_event_loop().run_until_complete(delete_test_data())

    def test_post_sensor_reading_ok(self):
        data =  """{
            "timestamp": "2017-01-02T01:02:03.23232Z-05:00",
            "asset": "sensor1",
            "key": "80a43623-ebe5-40d6-8d80-3f892da9b3b4",
            "readings": {
                "velocity": "500",
                "temperature": {
                    "value": "32",
                    "unit": "kelvin"
                }
            }
        }"""

        r = requests.post(BASE_URL, data=data, headers=headers)
        retval = dict(r.json())

        # Assert the POST request response
        assert 200 == retval['status']
        assert 'success' == retval['result']


    def test_missing_timestamp(self):
        data =  """{
            "asset": "sensor1",
            "key": "80a43623-ebe5-40d6-8d80-3f892da9b3b4",
            "readings": {
                "velocity": "500",
                "temperature": {
                    "value": "32",
                    "unit": "kelvin"
                }
            }
        }"""

        r = requests.post(BASE_URL, data=data, headers=headers)
        retval = dict(r.json())

        # Assert the POST request response
        assert 400 == retval['status']
        assert retval['error'].startswith('timestamp can not be None')


    def test_missing_asset(self):
        data =  """{
            "timestamp": "2017-01-02T01:02:03.23232Z-05:00",
            "key": "80a43623-ebe5-40d6-8d80-3f892da9b3b4",
            "readings": {
                "velocity": "500",
                "temperature": {
                    "value": "32",
                    "unit": "kelvin"
                }
            }
        }"""

        r = requests.post(BASE_URL, data=data, headers=headers)
        retval = dict(r.json())

        # Assert the POST request response
        assert 400 == retval['status']
        assert retval['error'].startswith('asset can not be None')


    def test_missing_key(self):
        data =  """{
            "timestamp": "2017-01-02T01:02:03.23232Z-05:00",
            "asset": "sensor1",
            "readings": {
                "velocity": "500",
                "temperature": {
                    "value": "32",
                    "unit": "kelvin"
                }
            }
        }"""

        r = requests.post(BASE_URL, data=data, headers=headers)
        retval = dict(r.json())

        # Assert the POST request response
        # TODO: Check why code is considering it ok and returns 200 instead of 400
        assert 200 == retval['status']
        assert 'success' == retval['result']


    def test_missing_reading(self):
        data =  """{
            "timestamp": "2017-01-02T01:02:03.23232Z-05:00",
            "asset": "sensor1",
            "key": "80a43623-ebe5-40d6-8d80-3f892da9b3b4"
        }"""

        r = requests.post(BASE_URL, data=data, headers=headers)
        retval = dict(r.json())

        # Assert the POST request response
        assert 400 == retval['status']
        assert retval['error'].startswith('readings must be a dictionary')


    def test_post_sensor_reading_readings_not_dict(self):
        data =  """{
            "timestamp": "2017-01-02T01:02:03.23232Z-05:00",
            "asset": "sensor2",
            "key": "80a43623-ebe5-40d6-8d80-3f892da9b3b4",
            "readings": "500"
        }"""

        r = requests.post(BASE_URL, data=data, headers=headers)
        retval = dict(r.json())

        # Assert the POST request response
        assert 400 == retval['status']
        assert retval['error'].startswith('readings must be a dictionary')


    def test_post_sensor_reading_bad_delimiter(self):
        data =  """{
            "timestamp": "2017-01-02T01:02:03.23232Z-05:00",
            "asset": "sensor1",
            "key": "80a43623-ebe5-40d6-8d80-3f892da9b3b4",
            "readings": {
                "velocity": "500",
                "temperature": {
                    "value": "32",
                    "unit": "kelvin"
                }
        }"""

        r = requests.post(BASE_URL, data=data, headers=headers)
        retval = dict(r.json())

        # Assert the POST request response
        assert 400 == retval['status']
        assert retval['error'].startswith("Expecting ',' delimiter:")

