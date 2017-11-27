# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Integration test for foglamp.device.http_south"""

import requests
import pytest

pytestmark = pytest.mark.asyncio


__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

BASE_URL = 'http://localhost:6683/sensor-reading'
headers = {"Content-Type": 'application/json'}

@pytest.allure.story("device")
class TestIngestReadings(object):
    """Unit tests for foglamp.device.coap.IngestReadings
    """

    async def test_post_sensor_reading_ok(self):
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


    async def test_missing_timestamp(self):
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


    async def test_missing_asset(self):
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


    async def test_missing_key(self):
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
        assert 200 == retval['status']
        assert 'success' == retval['result']


    async def test_missing_reading(self):
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


    async def test_post_sensor_reading_readings_not_dict(self):
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


    async def test_post_sensor_reading_bad_delimiter(self):
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

