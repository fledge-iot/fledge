# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test Browser Assets REST API """


import os
import shutil
import http.client
import time
import json
import pytest
from datetime import datetime


__author__ = "Ashish Jabble, Vaibhav Singhal"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

ASSET_NAME = 'test-loudness'
SENSOR = 'loudness'
SENSOR_VALUES = [1, 2, 3, 4, 5, 6]
SOUTH_PLUGIN_NAME = 'dummyplugin'
SERVICE_NAME = 'TestBrowserAPI'


def validate_date_format(dt_txt, fmt):
    try:
        datetime.strptime(dt_txt, fmt)
    except ValueError:
        return False
    else:
         return True


class TestBrowserAssets:

    @pytest.fixture
    def start_south(self, reset_and_start_fledge, remove_directories, fledge_url, south_plugin=SOUTH_PLUGIN_NAME):
        """ This fixture clone a south repo and starts south instance
            reset_and_start_fledge: Fixture that resets and starts fledge, no explicit invocation, called at start
            remove_directories: Fixture that remove directories created during the tests"""

        # Create a south plugin
        plugin_dir = os.path.join(os.path.expandvars('${FLEDGE_ROOT}'), 'python/fledge/plugins/south/dummyplugin')
        plugin_file = os.path.join(os.path.expandvars('${FLEDGE_ROOT}'), 'tests/system/python/data/dummyplugin.py')
        try:
            os.mkdir(plugin_dir)
        except FileExistsError:
            print("Directory ", plugin_dir, " already exists")

        shutil.copy2(plugin_file, plugin_dir)
        # Create south service
        conn = http.client.HTTPConnection(fledge_url)
        data = {"name": "{}".format(SERVICE_NAME), "type": "South", "plugin": "{}".format(south_plugin),
                "enabled": "true", "config": {}}
        conn.request("POST", '/fledge/service', json.dumps(data))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        retval = json.loads(r)
        assert SERVICE_NAME == retval["name"]

        yield self.start_south

        # Cleanup code that runs after the caller test is over
        remove_directories(plugin_dir)

    def test_get_asset_counts(self, start_south, fledge_url, wait_time):
        """Test that browsing an asset gives correct asset name and asset count"""
        time.sleep(wait_time * 2)
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/asset')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert ASSET_NAME == jdoc[0]["assetCode"]
        assert 6 == jdoc[0]["count"]

    def test_get_asset(self, fledge_url):
        """Test that browsing an asset gives correct asset values"""
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/asset/{}'.format(ASSET_NAME))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        i = 0
        for val in SENSOR_VALUES:
            assert {SENSOR: val} == jdoc[i]['reading']
            i += 1

    @pytest.mark.parametrize(("query", "expected_count", "expected_values"), [
        ('?limit=1', 1, [SENSOR_VALUES[0]]),
        ('?limit=1&skip=1', 1, [SENSOR_VALUES[1]]),
        ('?seconds=59', 2, SENSOR_VALUES[0:2]),
        ('?minutes=15', 4, SENSOR_VALUES[0:4]),
        ('?hours=4', 5, SENSOR_VALUES[0:5]),
        ('?hours=20&minutes=20&seconds=59&limit=20', 2, SENSOR_VALUES[0:2]), # Verify that if a combination of hrs, min, sec is used, shortest period will apply
        ('?limit=&hours=&minutes=&seconds=', 6, SENSOR_VALUES)
        # In case of empty params, all values are returned
    ])
    def test_get_asset_query(self, fledge_url, query, expected_count, expected_values):
        """Test that browsing an asset with query parameters gives correct asset values"""
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/asset/{}{}'.format(ASSET_NAME, query))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc) == expected_count
        i = 0
        for item in expected_values:
            assert {SENSOR: item} == jdoc[i]['reading']
            i += 1

    @pytest.mark.parametrize("request_params, response_code, response_message", [
        ('?limit=invalid', 400, "Limit must be a positive integer"),
        ('?limit=-1', 400, "Limit must be a positive integer"),
        ('?skip=invalid', 400, "Skip/Offset must be a positive integer"),
        ('?skip=-1', 400, "Skip/Offset must be a positive integer"),
        ('?minutes=-1', 400, "Time must be a positive integer"),
        ('?minutes=blah', 400, "Time must be a positive integer"),
        ('?seconds=-1', 400, "Time must be a positive integer"),
        ('?seconds=blah', 400, "Time must be a positive integer"),
        ('?hours=-1', 400, "Time must be a positive integer"),
        ('?hours=blah', 400, "Time must be a positive integer")
    ])
    def test_get_asset_query_bad_data(self, fledge_url, request_params, response_code, response_message):
        """Test that browsing an asset with invalid query parameters generates http errors"""
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/asset/{}{}'.format(ASSET_NAME, request_params))
        r = conn.getresponse()
        conn.close()
        assert response_code == r.status
        assert response_message == r.reason

    def test_get_asset_reading(self, fledge_url):
        """Test that browsing an asset's data point gives correct asset data point values"""
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/asset/{}/{}'.format(ASSET_NAME, SENSOR))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        i = 0
        for val in SENSOR_VALUES:
            assert val == jdoc[i][SENSOR]
            i += 1

    @pytest.mark.parametrize(("query", "expected_count", "expected_values"), [
        ('?limit=1', 1, [SENSOR_VALUES[0]]),
        ('?limit=1&skip=1', 1, [SENSOR_VALUES[1]]),
        ('?seconds=59', 2, SENSOR_VALUES[0:2]),
        ('?minutes=15', 4, SENSOR_VALUES[0:4]),
        ('?hours=4', 5, SENSOR_VALUES[0:5]),
        ('?hours=20&minutes=20&seconds=59&limit=20', 2, SENSOR_VALUES[0:2]), # Verify that if a combination of hrs, min, sec is used, shortest period will apply
        ('?limit=&hours=&minutes=&seconds=', 6, SENSOR_VALUES)
        # In case of empty params, all values are returned
    ])
    def test_get_asset_readings_query(self, fledge_url, query, expected_count, expected_values):
        """Test that browsing an asset's data point with query parameters gives correct asset data point values"""
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/asset/{}/{}{}'.format(ASSET_NAME, SENSOR, query))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc) == expected_count
        i = 0
        for item in expected_values:
            assert item == jdoc[i][SENSOR]
            i += 1

    def test_get_asset_summary(self, fledge_url):
        """Test that browsing an asset's summary gives correct min, max and average values"""
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/asset/{}/summary'.format(ASSET_NAME))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        summary = jdoc[0][SENSOR]
        avg = sum(SENSOR_VALUES) / len(SENSOR_VALUES)
        assert avg == summary['average']
        assert max(SENSOR_VALUES) == summary['max']
        assert min(SENSOR_VALUES) == summary['min']

    def test_get_asset_readings_summary_invalid_sensor(self, fledge_url):
        """Test that browsing a non existing asset's data point summary gives blank min, max and average values"""
        conn = http.client.HTTPConnection(fledge_url)
        invalid_sensor = "invalid"
        conn.request("GET", '/fledge/asset/{}/{}/summary'.format(ASSET_NAME, invalid_sensor))
        r = conn.getresponse()
        assert 404 == r.status
        assert '{} reading key is not found'.format(invalid_sensor) == r.reason

    def test_get_asset_readings_summary(self, fledge_url):
        """Test that browsing an asset's data point summary gives correct min, max and average values"""
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/asset/{}/{}/summary'.format(ASSET_NAME, SENSOR))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        summary = jdoc[SENSOR]
        avg = sum(SENSOR_VALUES) / len(SENSOR_VALUES)
        assert avg == summary['average']
        assert max(SENSOR_VALUES) == summary['max']
        assert min(SENSOR_VALUES) == summary['min']

    def test_get_asset_series(self, fledge_url):
        """Test that browsing an asset's data point time series gives correct min, max and average values
         for all timestamps"""
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/asset/{}/{}/series'.format(ASSET_NAME, SENSOR))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        i = 0
        # Min, average and max values of a time series data is noting but the value itself if readings were ingested at
        # different timestamps
        for val in SENSOR_VALUES:
            assert val == jdoc[i]['min']
            assert val == jdoc[i]['average']
            assert val == jdoc[i]['max']
            i += 1

    @pytest.mark.parametrize(("query", "expected_count", "expected_values"), [
        ('?limit=1', 1, [SENSOR_VALUES[0]]),
        ('?limit=1&skip=1', 1, [SENSOR_VALUES[1]]),
        ('?seconds=59', 2, SENSOR_VALUES[0:2]),
        ('?minutes=15', 4, SENSOR_VALUES[0:4]),
        ('?hours=4', 5, SENSOR_VALUES[0:5]),
        ('?hours=20&minutes=20&seconds=59&limit=20', 2, SENSOR_VALUES[0:2]), # Verify that if a combination of hrs, min, sec is used, shortest period will apply
        ('?limit=&hours=&minutes=&seconds=', 6, SENSOR_VALUES)
        # In case of empty params, all values are returned
    ])
    def test_get_asset_series_query_time_limit(self, fledge_url, query, expected_count, expected_values):
        """Test that browsing an asset's data point time series with query parameter
         gives correct min, max and average values for all timestamps"""
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/asset/{}/{}/series{}'.format(ASSET_NAME, SENSOR, query))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc) == expected_count
        i = 0
        for item in expected_values:
            assert item == jdoc[i]['min']
            assert item == jdoc[i]['average']
            assert item == jdoc[i]['max']
            i += 1

    def test_get_asset_series_query_group_sec(self, fledge_url):
        """Test that browsing an asset's data point time series with seconds grouping
                 gives correct min, max and average values"""
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/asset/{}/{}/series{}'.format(ASSET_NAME, SENSOR, '?group=seconds'))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc) == 6
        for i in range(0, len(jdoc)):
            assert SENSOR_VALUES[i] == jdoc[i]['min']
            assert SENSOR_VALUES[i] == jdoc[i]['average']
            assert SENSOR_VALUES[i] == jdoc[i]['max']
            assert validate_date_format(jdoc[i]['timestamp'], '%Y-%m-%d %H:%M:%S'), "timestamp format do not match"

    def test_get_asset_series_query_group_min(self, fledge_url):
        """Test that browsing an asset's data point time series with minutes grouping
                         gives correct min, max and average values"""
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/asset/{}/{}/series{}'.format(ASSET_NAME, SENSOR, '?group=minutes'))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc) == 5

        assert (sum(SENSOR_VALUES[0:2]) / len(SENSOR_VALUES[0:2])) == jdoc[0]['average']
        assert min(SENSOR_VALUES[0:2]) == jdoc[0]['min']
        assert max(SENSOR_VALUES[0:2]) == jdoc[0]['max']
        assert validate_date_format(jdoc[0]['timestamp'], '%Y-%m-%d %H:%M'), "timestamp format do not match"

        for i in range(1, len(jdoc) - 1):
            assert SENSOR_VALUES[i + 1] == jdoc[i]['min']
            assert SENSOR_VALUES[i + 1] == jdoc[i]['average']
            assert SENSOR_VALUES[i + 1] == jdoc[i]['max']
            assert validate_date_format(jdoc[i + 1]['timestamp'], '%Y-%m-%d %H:%M'), "timestamp format do not match"

    def test_get_asset_series_query_group_hrs(self, fledge_url):
        """Test that browsing an asset's data point time series with hour grouping
                                 gives correct min, max and average values"""
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/asset/{}/{}/series{}'.format(ASSET_NAME, SENSOR, '?group=hours'))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc) == 3

        assert (sum(SENSOR_VALUES[0:4]) / len(SENSOR_VALUES[0:4])) == jdoc[0]['average']
        assert min(SENSOR_VALUES[0:4]) == jdoc[0]['min']
        assert max(SENSOR_VALUES[0:4]) == jdoc[0]['max']
        assert validate_date_format(jdoc[0]['timestamp'], '%Y-%m-%d %H'), "timestamp format do not match"

        for i in range(4, 6):
            assert SENSOR_VALUES[i] == jdoc[i - 3]['min']
            assert SENSOR_VALUES[i] == jdoc[i - 3]['average']
            assert SENSOR_VALUES[i] == jdoc[i - 3]['max']
            assert validate_date_format(jdoc[i - 3]['timestamp'], '%Y-%m-%d %H'), "timestamp format do not match"

    def test_get_asset_sensor_readings_invalid_group(self, fledge_url):
        """Test that browsing an asset's data point time series with invalid grouping
                                 gives http error"""
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/asset/{}/{}/series?group=blah'.format(ASSET_NAME, SENSOR))
        r = conn.getresponse()
        conn.close()
        assert r.status == 400
        assert r.reason == "blah is not a valid group"
