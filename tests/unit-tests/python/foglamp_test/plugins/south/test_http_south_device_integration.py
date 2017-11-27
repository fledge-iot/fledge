# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Unit test for foglamp.device.http_south"""

import requests
import pytest

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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_post_sensor_reading_bad_1(self):
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

    @pytest.mark.asyncio
    async def test_post_sensor_reading_bad_2(self):
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
        assert "readings must be a dictionary" == retval['error']

