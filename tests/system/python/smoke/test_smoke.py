# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test system/python/test_smoke.py

"""
import os
import subprocess
import http.client
import json
import time
import pytest
import utils


__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

TEMPLATE_NAME = "template.json"
SENSOR_VALUE = 10


def get_ping_status(fledge_url):
    _connection = http.client.HTTPConnection(fledge_url)
    _connection.request("GET", '/fledge/ping')
    r = _connection.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    return jdoc


def get_statistics_map(fledge_url):
    _connection = http.client.HTTPConnection(fledge_url)
    _connection.request("GET", '/fledge/statistics')
    r = _connection.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    return utils.serialize_stats_map(jdoc)


@pytest.fixture
def start_south_coap(reset_and_start_fledge, add_south, remove_data_file, remove_directories, south_branch,
                     fledge_url, south_plugin="coap", asset_name="smoke"):
    """ This fixture clone a south repo and starts both south and north instance
        reset_and_start_fledge: Fixture that resets and starts fledge, no explicit invocation, called at start
        add_south: Fixture that adds a south service with given configuration
        remove_data_file: Fixture that remove data file created during the tests
        remove_directories: Fixture that remove directories created during the tests"""

    # Define the template file for fogbench
    fogbench_template_path = os.path.join(
        os.path.expandvars('${FLEDGE_ROOT}'), 'data/{}'.format(TEMPLATE_NAME))
    with open(fogbench_template_path, "w") as f:
        f.write(
            '[{"name": "%s", "sensor_values": '
            '[{"name": "sensor", "type": "number", "min": %d, "max": %d, "precision": 0}]}]' % (
                asset_name, SENSOR_VALUE, SENSOR_VALUE))

    add_south(south_plugin, south_branch, fledge_url, service_name="coap")

    yield start_south_coap

    # Cleanup code that runs after the caller test is over
    remove_data_file(fogbench_template_path)
    remove_directories("/tmp/fledge-south-{}".format(south_plugin))


def test_smoke(start_south_coap, fledge_url, wait_time, asset_name="smoke"):
    """ Test that data is inserted in Fledge
        start_south_coap: Fixture that starts Fledge with south coap plugin
        Assertions:
            on endpoint GET /fledge/asset
            on endpoint GET /fledge/asset/<asset_name>
    """

    conn = http.client.HTTPConnection(fledge_url)
    time.sleep(wait_time)
    subprocess.run(["cd $FLEDGE_ROOT/extras/python; python3 -m fogbench -t ../../data/{}; cd -".format(TEMPLATE_NAME)],
                   shell=True, check=True)
    time.sleep(wait_time)

    ping_response = get_ping_status(fledge_url)
    assert 1 == ping_response["dataRead"]
    assert 0 == ping_response["dataSent"]

    actual_stats_map = get_statistics_map(fledge_url)
    assert 1 == actual_stats_map[asset_name.upper()]
    assert 1 == actual_stats_map['READINGS']

    conn.request("GET", '/fledge/asset')
    r = conn.getresponse()

    assert 200 == r.status
    r = r.read().decode()
    retval = json.loads(r)
    assert len(retval) == 1
    assert asset_name == retval[0]["assetCode"]
    assert 1 == retval[0]["count"]

    conn.request("GET", '/fledge/asset/{}'.format(asset_name))
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    retval = json.loads(r)
    assert {'sensor': SENSOR_VALUE} == retval[0]["reading"]

    tracking_details = utils.get_asset_tracking_details(fledge_url, "Ingest")
    assert len(tracking_details["track"]), "Failed to track Ingest event"
    tracked_item = tracking_details["track"][0]
    assert "coap" == tracked_item["service"]
    assert "smoke" == tracked_item["asset"]
    assert "coap" == tracked_item["plugin"]
