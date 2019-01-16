# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test system/python/test_smoke.py

"""
import os
import subprocess
import http.client
import json
import time
import shutil
import pytest


__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2018 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

TEMPLATE_NAME = "template.json"
SENSOR_VALUE = 10


def _remove_data_file(file_path=None):
    if os.path.exists(file_path):
        os.remove(file_path)


def _remove_directories(dir_path=None):
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path, ignore_errors=True)


@pytest.fixture
def start_south_coap(reset_and_start_foglamp, start_south, foglamp_url, south_plugin="coap", asset_name="smoke"):
    """ This fixture clone a south repo and starts both south and north instance
        reset_and_start_foglamp: Fixture that resets and starts foglamp, no explicit invocation, called at start
        start_south: Fixture that starts any south service with given configuration
        start_north: Fixture that starts PI north task"""

    # Define the template file for fogbench
    fogbench_template_path = os.path.join(
        os.path.expandvars('${FOGLAMP_ROOT}'), 'data/{}'.format(TEMPLATE_NAME))
    f = open(fogbench_template_path, "w")
    f.write(
        '[{"name": "%s", "sensor_values": '
        '[{"name": "sensor", "type": "number", "min": %d, "max": %d, "precision": 0}]}]' % (
            asset_name, SENSOR_VALUE, SENSOR_VALUE))
    f.close()

    # Call the start south service fixture
    start_south(south_plugin, foglamp_url)

    # Provide the fixture value
    yield start_south_coap

    # Cleanup code that runs after the caller test is over
    _remove_data_file(fogbench_template_path)
    _remove_directories("/tmp/foglamp-south-{}".format(south_plugin))


def test_end_to_end(start_south_coap, foglamp_url, wait_time, asset_name="smoke"):
    """ Test that data is inserted in FogLAMP and sent to PI
        start_south_north: Fixture that starts FogLAMP with south and north instance"""

    conn = http.client.HTTPConnection(foglamp_url)
    time.sleep(wait_time)
    subprocess.run(["cd $FOGLAMP_ROOT/extras/python; python3 -m fogbench -t ../../data/{}; cd -".format(TEMPLATE_NAME)],
                   shell=True, check=True)
    time.sleep(wait_time)
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
    assert {'sensor': SENSOR_VALUE} == retval[0]["reading"]
