# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test system/python/end_to_end_csv.py

"""
import pytest
import os
import subprocess
import http.client
import json
import time
import shutil
import base64
import ssl

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2018 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


CSV_NAME = "sample.csv"
CSV_HEADER = "temperature"
CSV_DATA = 2.5
SENSOR_NAME = CSV_HEADER

# Number of tries to make to read PI data and to read North configuration
NUM_RETRIES = 3
# Sleep interval between each tries
SLEEP_INTERVAL = 10


@pytest.fixture
def start_south_north(reset_and_start_foglamp, south_plugin, asset_name, foglamp_url, pi_host, pi_port,
                      north_plugin, pi_token):
    """ This fixture clone a south repo and starts both south and north instance """
    assert os.environ.get('FOGLAMP_ROOT') is not None
    south_config = {"assetName": {"value": "{}".format(asset_name)}, "csvFilename": {"value": "{}".format(CSV_NAME)},
                    "ingestMode": {"value": "batch"}}
    data = {"name": "play", "type": "South", "plugin": "{}".format(south_plugin), "enabled": "true",
            "config": south_config}

    conn = http.client.HTTPConnection(foglamp_url)
    subprocess.run(["rm -rf /tmp/foglamp-south-{}".format(south_plugin)], shell=True, check=True)
    subprocess.run(["rm -rf -d ${FOGLAMP_ROOT}/python/foglamp/plugins/south/*/"], shell=True, check=True)
    subprocess.run(["git clone https://github.com/foglamp/foglamp-south-{}.git /tmp/foglamp-south-{}".
                   format(south_plugin, south_plugin)], shell=True, check=True)
    subprocess.run(["cp -r /tmp/foglamp-south-{}/python/foglamp/plugins/south/* $FOGLAMP_ROOT/python/foglamp/plugins/south/".format(south_plugin)], shell=True, check=True)
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
    assert retval["name"] == "play"

    data = {"name": "North_Readings_to_PI",
            "plugin": "{}".format(north_plugin),
            "type": "north",
            "schedule_type": 3,
            "schedule_day": 0,
            "schedule_time": 0,
            "schedule_repeat": 30,
            "schedule_enabled": "false"}
    conn.request("POST", '/foglamp/scheduled/task', json.dumps(data))
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    retval = json.loads(r)
    assert retval["name"] == "North_Readings_to_PI"

    retry_count = 0
    config_status = None
    while config_status != 200 and retry_count < NUM_RETRIES:
        conn.request("GET", '/foglamp/category/North_Readings_to_PI/producerToken')
        r = conn.getresponse()
        config_status = r.status
        r.read().decode()
        retry_count += 1
        time.sleep(SLEEP_INTERVAL)

    if config_status != 200 or retry_count == NUM_RETRIES:
        assert False, "North plugin config load failed in {} tries".format(NUM_RETRIES)

    data = {"URL": "https://{}:{}/ingress/messages".format(pi_host, pi_port), "producerToken": "{}".format(pi_token)}
    conn.request("PUT", '/foglamp/category/North_Readings_to_PI', json.dumps(data))
    r = conn.getresponse()
    assert 200 == r.status
    r.read().decode()

    data = {"schedule_name": "{}".format("North_Readings_to_PI")}
    conn.request("PUT", '/foglamp/schedule/enable', json.dumps(data))
    r = conn.getresponse()
    assert 200 == r.status
    r.read().decode()
    yield start_south_north
    _remove_csv_files(csv_file_path)
    _remove_directories("/tmp/foglamp-south-{}".format(south_plugin))


def _remove_csv_files(file_path=None):
    if os.path.exists(file_path):
        os.remove(file_path)


def _remove_directories(dir_path=None):
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path, ignore_errors=True)


def _read_data_from_pi(host, port, admin, password, pi_database, asset):
    """ This method reads data from pi web api """
    dbs = None
    element = None
    url_elements_list = None
    url_assets_list = None
    web_id = None

    username_password = "{}:{}".format(admin, password)
    userAndPass = base64.b64encode(username_password.encode('ascii')).decode("ascii")
    headers = {'Authorization': 'Basic %s' % userAndPass}

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
                if el["Name"] == SENSOR_NAME:
                    value = el["Value"]["Value"]
                    # After Value is stored, delete this element
                    conn.request("DELETE", '/piwebapi/elements/{}'.format(web_id), headers=headers)
                    res = conn.getresponse()
                    res.read()
                    return value
    except (KeyError, Exception):
        return None


def test_end_to_end(start_south_north, foglamp_url, pi_host, pi_port, pi_admin, pi_passwd, pi_db, asset_name):
    """ Test that data is inserted in FogLAMP and sent to PI"""
    conn = http.client.HTTPConnection(foglamp_url)
    time.sleep(SLEEP_INTERVAL)
    conn.request("GET", '/foglamp/asset')
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    retval = json.loads(r)
    assert retval[0]["assetCode"] == asset_name
    assert retval[0]["count"] == 1

    conn.request("GET", '/foglamp/asset/{}'.format(asset_name))
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    retval = json.loads(r)
    assert retval[0]["reading"] == {'{}'.format(CSV_HEADER): '{}'.format(CSV_DATA)}

    retry_count = 0
    data_from_pi = None
    while data_from_pi is None and retry_count < NUM_RETRIES:
        data_from_pi = _read_data_from_pi(pi_host, pi_port, pi_admin, pi_passwd, pi_db, asset_name)
        retry_count += 1
        time.sleep(SLEEP_INTERVAL)

    if data_from_pi is None or retry_count == NUM_RETRIES:
        assert False, "Failed to read data from PI"
    assert data_from_pi == str(CSV_DATA)
