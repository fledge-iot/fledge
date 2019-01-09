# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test system/python/end_to_end_csv.py

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

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2018 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


CSV_NAME = "sample.csv"
CSV_HEADER = "temperature"
CSV_DATA = 2.5

# Number of tries to make to read PI data and to read North configuration
NUM_RETRIES = 3
# Low sleep interval between each tries, used in internal foglamp process waits
SLEEP_INTERVAL_LOW = 5
# High sleep interval between each tries, used in external pi webapi waits
SLEEP_INTERVAL_HIGH = 10
# Name of the North Task
NORTH_TASK_NAME = "North_Readings_to_PI"


def _start_foglamp_south(south_plugin, asset_name, foglamp_url):
    """Start south service"""

    south_config = {"assetName": {"value": "{}".format(asset_name)}, "csvFilename": {"value": "{}".format(CSV_NAME)},
                    "ingestMode": {"value": "batch"}}
    data = {"name": "play", "type": "South", "plugin": "{}".format(south_plugin), "enabled": "true",
            "config": south_config}

    conn = http.client.HTTPConnection(foglamp_url)
    subprocess.run(["rm -rf /tmp/foglamp-south-{}".format(south_plugin)], shell=True, check=True)
    subprocess.run(["rm -rf $FOGLAMP_ROOT/python/foglamp/plugins/south/foglamp-south-{}".format(south_plugin)], shell=True, check=True)
    subprocess.run(["git clone https://github.com/foglamp/foglamp-south-{}.git /tmp/foglamp-south-{}".
                   format(south_plugin, south_plugin)], shell=True, check=True)
    subprocess.run(["cp -r /tmp/foglamp-south-{}/python/foglamp/plugins/south/* "
                    "$FOGLAMP_ROOT/python/foglamp/plugins/south/".format(south_plugin)], shell=True, check=True)
    subprocess.run(["rm -rf $FOGLAMP_ROOT/data/{}".format(CSV_NAME)], shell=True, check=True)
    csv_file_path = os.path.join(os.path.expandvars('${FOGLAMP_ROOT}'), 'data/{}'.format(CSV_NAME))
    f = open(csv_file_path, "w")
    f.write(CSV_HEADER)
    f.write("\n{}".format(CSV_DATA))
    f.close()

    conn.request("POST", '/foglamp/service', json.dumps(data))
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    retval = json.loads(r)
    assert "play" == retval["name"]
    return csv_file_path


def _start_foglamp_north(foglamp_url, pi_host, pi_port, north_plugin, pi_token):
    """Start north task"""

    conn = http.client.HTTPConnection(foglamp_url)
    data = {"name": NORTH_TASK_NAME,
            "plugin": "{}".format(north_plugin),
            "type": "north",
            "schedule_type": 3,
            "schedule_day": 0,
            "schedule_time": 0,
            "schedule_repeat": 30,
            "schedule_enabled": "true",
            "config": {"producerToken": {"value": pi_token},
                       "URL": {"value": "https://{}:{}/ingress/messages".format(pi_host, pi_port)}
                       }
            }
    conn.request("POST", '/foglamp/scheduled/task', json.dumps(data))
    r = conn.getresponse()
    assert 200 == r.status
    r.read().decode()


def _remove_data_file(file_path=None):
    if os.path.exists(file_path):
        os.remove(file_path)


def _remove_directories(dir_path=None):
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path, ignore_errors=True)


def _read_data_from_pi(host, admin, password, pi_database, asset):
    """ This method reads data from pi web api """

    # List of pi databases
    dbs = None
    # PI logical grouping of attributes and child elements
    element = None
    # List of elements
    url_elements_list = None
    # Element's EndValue
    url_assets_list = None
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
                    element = el["Links"]["Elements"]

        if element is not None:
            conn.request("GET", element, headers=headers)
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
                    url_assets_list = el["Links"]["EndValue"]
                    web_id = el["WebId"]

        if url_assets_list is not None:
            conn.request("GET", url_assets_list, headers=headers)
            res = conn.getresponse()
            r = json.loads(res.read().decode())
            _items = r["Items"]
            for el in _items:
                if el["Name"] == CSV_HEADER:
                    value = el["Value"]["Value"]
                    # After Value is stored, delete this element
                    conn.request("DELETE", '/piwebapi/elements/{}'.format(web_id), headers=headers)
                    res = conn.getresponse()
                    res.read()
                    return value
    except (KeyError, IndexError, Exception):
        return None


@pytest.fixture
def start_south_north(reset_and_start_foglamp, south_plugin, asset_name, foglamp_url, pi_host, pi_port,
                      north_plugin, pi_token):
    """ This fixture clone a south repo and starts both south and north instance """

    # Start foglamp south service
    csv_file_path = _start_foglamp_south(south_plugin, asset_name, foglamp_url)

    # Start foglamp north task
    _start_foglamp_north(foglamp_url, pi_host, pi_port, north_plugin, pi_token)

    # Provide the fixture value
    yield start_south_north

    # Cleanup code that runs after the caller test is over
    _remove_data_file(csv_file_path)
    _remove_directories("/tmp/foglamp-south-{}".format(south_plugin))


def test_end_to_end(start_south_north, foglamp_url, pi_host, pi_port, pi_admin, pi_passwd, pi_db, asset_name):
    """ Test that data is inserted in FogLAMP and sent to PI"""

    conn = http.client.HTTPConnection(foglamp_url)
    time.sleep(SLEEP_INTERVAL_LOW)
    conn.request("GET", '/foglamp/asset')
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    retval = json.loads(r)
    assert len(retval) > 0
    assert asset_name == retval[0]["assetCode"]
    assert 1 == retval[0]["count"]

    conn.request("GET", '/foglamp/asset/{}'.format(asset_name))
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    retval = json.loads(r)
    assert {'{}'.format(CSV_HEADER): '{}'.format(CSV_DATA)} == retval[0]["reading"]

    retry_count = 0
    data_from_pi = None
    while data_from_pi is None and retry_count < NUM_RETRIES:
        data_from_pi = _read_data_from_pi(pi_host, pi_admin, pi_passwd, pi_db, asset_name)
        retry_count += 1
        time.sleep(SLEEP_INTERVAL_HIGH)

    if data_from_pi is None or retry_count == NUM_RETRIES:
        assert False, "Failed to read data from PI"

    assert data_from_pi == str(CSV_DATA)
