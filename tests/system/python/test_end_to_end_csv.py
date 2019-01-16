# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test system/python/test_end_to_end_csv.py

"""
import os
import subprocess
import http.client
import json
import time
import shutil
import base64
import ssl
import pytest
from collections import Counter

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2018 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


CSV_NAME = "sample.csv"
CSV_HEADERS = "ivalue,fvalue,svalue"
CSV_DATA = [{'ivalue': 1, 'fvalue': 1.1, 'svalue': 'abc'},
            {'ivalue': 0, 'fvalue': 0.0, 'svalue': 'def'},
            {'ivalue': -1, 'fvalue': -1.1, 'svalue': 'ghi'}]

# Name of the North Task
NORTH_TASK_NAME = "North_Readings_to_PI"

_data_str = {}


def _remove_data_file(file_path=None):
    if os.path.exists(file_path):
        os.remove(file_path)


def _remove_directories(dir_path=None):
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path, ignore_errors=True)


def _read_data_from_pi(host, admin, password, pi_database, asset, sensor):
    """ This method reads data from pi web api """

    # List of pi databases
    dbs = None
    # PI logical grouping of attributes and child elements
    elements = None
    # List of elements
    url_elements_list = None
    # Element's recorded data url
    url_recorded_data = None
    # Resources in the PI Web API are addressed by WebID, parameter used for deletion of element
    web_id = None

    username_password = "{}:{}".format(admin, password)
    username_password_b64 = base64.b64encode(username_password.encode('ascii')).decode("ascii")
    headers = {'Authorization': 'Basic %s' % username_password_b64}

    try:
        conn = http.client.HTTPSConnection(host, context=ssl._create_unverified_context())
        conn.request("GET", '/piwebapi/assetservers', headers=headers)
        res = conn.getresponse()
        r = json.loads(res.read().decode())
        dbs = r["Items"][0]["Links"]["Databases"]

        if dbs is not None:
            conn.request("GET", dbs, headers=headers)
            res = conn.getresponse()
            r = json.loads(res.read().decode())
            for el in r["Items"]:
                if el["Name"] == pi_database:
                    elements = el["Links"]["Elements"]

        if elements is not None:
            conn.request("GET", elements, headers=headers)
            res = conn.getresponse()
            r = json.loads(res.read().decode())
            url_elements_list = r["Items"][0]["Links"]["Elements"]

        if url_elements_list is not None:
            conn.request("GET", url_elements_list, headers=headers)
            res = conn.getresponse()
            r = json.loads(res.read().decode())
            items = r["Items"]
            for el in items:
                if el["Name"] == asset:
                    url_recorded_data = el["Links"]["RecordedData"]
                    web_id = el["WebId"]

        _data_pi = {}
        if url_recorded_data is not None:
            conn.request("GET", url_recorded_data, headers=headers)
            res = conn.getresponse()
            r = json.loads(res.read().decode())
            _items = r["Items"]
            for el in _items:
                _recoded_value_list = []
                for _head in sensor:
                    if el["Name"] == _head:
                        elx = el["Items"]
                        for _el in elx:
                            _recoded_value_list.append(_el["Value"])
                        _data_pi[_head] = _recoded_value_list
            conn.request("DELETE", '/piwebapi/elements/{}'.format(web_id), headers=headers)
            res = conn.getresponse()
            res.read()
            return _data_pi
    except (KeyError, IndexError, Exception):
        return None


@pytest.fixture
def start_south_north(reset_and_start_foglamp, start_south, start_north,
                      foglamp_url, pi_host, pi_port, pi_token, south_plugin="playback",
                      asset_name="end_to_end_csv", north_plugin="PI_Server_V2"):
    """ This fixture clone a south repo and starts both south and north instance
        reset_and_start_foglamp: Fixture that resets and starts foglamp, no explicit invocation, called at start
        start_south: Fixture that starts any south service with given configuration
        start_north: Fixture that starts PI north task"""

    # Define configuration of foglamp south playback service
    south_config = {"assetName": {"value": "{}".format(asset_name)}, "csvFilename": {"value": "{}".format(CSV_NAME)},
                    "ingestMode": {"value": "batch"}}

    # Define the CSV data and create expected lists to be verified later
    csv_file_path = os.path.join(os.path.expandvars('${FOGLAMP_ROOT}'), 'data/{}'.format(CSV_NAME))
    f = open(csv_file_path, "w")
    f.write(CSV_HEADERS)
    _heads = CSV_HEADERS.split(",")
    for c_data in CSV_DATA:
        temp_data = []
        for _head in _heads:
            temp_data.append(str(c_data[_head]))
        row = ','.join(temp_data)
        f.write("\n{}".format(row))
    f.close()

    # Prepare list of values for each header
    for _head in _heads:
        tmp_list = []
        for c_data in CSV_DATA:
            tmp_list.append(c_data[_head])
        _data_str[_head] = tmp_list

    # Call the start south service fixture
    start_south(south_plugin, foglamp_url, config=south_config)

    # Call the start north task fixture
    start_north(foglamp_url, pi_host, pi_port, north_plugin, pi_token)

    # Provide the fixture value
    yield start_south_north

    # Cleanup code that runs after the caller test is over
    _remove_data_file(csv_file_path)
    _remove_directories("/tmp/foglamp-south-{}".format(south_plugin))


def test_end_to_end(start_south_north, foglamp_url, pi_host, pi_admin, pi_passwd, pi_db,
                    wait_time, retries, asset_name="end_to_end_csv"):
    """ Test that data is inserted in FogLAMP and sent to PI
        start_south_north: Fixture that starts FogLAMP with south and north instance"""

    conn = http.client.HTTPConnection(foglamp_url)
    time.sleep(wait_time)
    conn.request("GET", '/foglamp/asset')
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    retval = json.loads(r)
    assert len(retval) > 0
    assert asset_name == retval[0]["assetCode"]
    assert len(CSV_DATA) == retval[0]["count"]

    for _head in CSV_HEADERS.split(","):
        conn.request("GET", '/foglamp/asset/{}/{}'.format(asset_name, _head))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        retval = json.loads(r)
        _actual_read_list = []
        for _el in retval:
            _actual_read_list.append(_el[_head])
        assert Counter(_actual_read_list) == Counter(_data_str[_head])

    retry_count = 0
    data_from_pi = None
    while (data_from_pi is None or data_from_pi == []) and retry_count < retries:
        data_from_pi = _read_data_from_pi(pi_host, pi_admin, pi_passwd, pi_db, asset_name,
                                          CSV_HEADERS.split(","))
        retry_count += 1
        time.sleep(wait_time*2)

    if data_from_pi is None or retry_count == retries:
        assert False, "Failed to read data from PI"

    for _head in CSV_HEADERS.split(","):
        assert Counter(data_from_pi[_head][-len(CSV_DATA):]) == Counter(_data_str[_head])
