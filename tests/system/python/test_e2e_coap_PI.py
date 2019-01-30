# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test system/python/test_e2e_coap_PI.py

"""
import os
import subprocess
import http.client
import json
import time
import pytest


__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

TEMPLATE_NAME = "template.json"
SENSOR_VALUE = 20


@pytest.fixture
def start_south_north(reset_and_start_foglamp, start_south, start_north_pi_server_c, remove_data_file,
                      remove_directories, south_branch, foglamp_url, pi_host, pi_port,
                      north_plugin, pi_token, south_plugin="coap", asset_name="end_to_end_coap"):
    """ This fixture clone a south repo and starts both south and north instance
        reset_and_start_foglamp: Fixture that resets and starts foglamp, no explicit invocation, called at start
        start_south: Fixture that starts any south service with given configuration
        start_north_pi_server_c: Fixture that starts PI north task
        remove_data_file: Fixture that remove data file created during the tests
        remove_directories: Fixture that remove directories created during the tests"""

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
    start_south(south_plugin, south_branch, foglamp_url, service_name="coap")

    # Call the start north task fixture
    start_north_pi_server_c(foglamp_url, pi_host, pi_port, north_plugin, pi_token)

    # Provide the fixture value
    yield start_south_north

    # Cleanup code that runs after the caller test is over
    remove_data_file(fogbench_template_path)
    remove_directories("/tmp/foglamp-south-{}".format(south_plugin))


def test_end_to_end(start_south_north, read_data_from_pi, foglamp_url, pi_host, pi_admin, pi_passwd, pi_db,
                    wait_time, retries, asset_name="end_to_end_coap"):
    """ Test that data is inserted in FogLAMP and sent to PI
        start_south_north: Fixture that starts FogLAMP with south and north instance
        read_data_from_pi: Fixture to read data from PI
        Assertions:
            on endpoint GET /foglamp/asset
            on endpoint GET /foglamp/asset/<asset_name>
            data received from PI is same as data sent"""

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
    assert len(retval) == 1
    assert asset_name == retval[0]["assetCode"]
    assert 1 == retval[0]["count"]

    conn.request("GET", '/foglamp/asset/{}'.format(asset_name))
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    retval = json.loads(r)
    assert {'sensor': SENSOR_VALUE} == retval[0]["reading"]

    retry_count = 0
    data_from_pi = None
    while (data_from_pi is None or data_from_pi == []) and retry_count < retries:
        data_from_pi = read_data_from_pi(pi_host, pi_admin, pi_passwd, pi_db, asset_name, {"sensor"})
        retry_count += 1
        time.sleep(wait_time*2)

    if data_from_pi is None or retry_count == retries:
        assert False, "Failed to read data from PI"

    assert data_from_pi["sensor"][-1] == SENSOR_VALUE
