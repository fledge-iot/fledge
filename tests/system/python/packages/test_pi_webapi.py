# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test sending data to PI using Web API

"""

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2019 Dianomic Systems Inc"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

import subprocess
import http.client
import pytest
import os
import time
import utils
from pathlib import Path
import urllib.parse

TEMPLATE_NAME = "template.json"
ASSET = "FOGL-2964-e2e-CoAP-PIWebAPI"
DATAPOINT = "sensor"
DATAPOINT_VALUE = 20
NORTH_TASK_NAME = "NorthReadingsToPI_WebAPI"
SOUTH_SERVICE_NAME = "CoAP FOGL-2964"
# This  gives the path of directory where fledge is cloned. test_file < packages < python < system < tests < ROOT
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
SCRIPTS_DIR_ROOT = "{}/tests/system/python/scripts/package/".format(PROJECT_ROOT)
AF_HIERARCHY_LEVEL = 'testpiwebapi/testpiwebapilvl2/testpiwebapilvl3'


@pytest.fixture
def reset_fledge(wait_time):
    try:
        subprocess.run(["cd {} && ./reset"
                       .format(SCRIPTS_DIR_ROOT)], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "reset package script failed!"


def verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries):
    get_url = "/fledge/ping"
    ping_result = utils.get_request(fledge_url, get_url)
    assert "dataRead" in ping_result
    assert "dataSent" in ping_result
    assert 0 < ping_result['dataRead'], "South data NOT seen in ping header"

    retry_count = 1
    sent = 0
    if not skip_verify_north_interface:
        while retries > retry_count:
            sent = ping_result["dataSent"]
            if sent >= 1:
                break
            else:
                time.sleep(wait_time)

            retry_count += 1
            ping_result = utils.get_request(fledge_url, get_url)

        assert 1 <= sent, "Failed to send data via PI Web API using Basic auth"
    return ping_result


def verify_statistics_map(fledge_url, skip_verify_north_interface):
    get_url = "/fledge/statistics"
    jdoc = utils.get_request(fledge_url, get_url)
    actual_stats_map = utils.serialize_stats_map(jdoc)
    assert 1 <= actual_stats_map[ASSET.upper()]
    assert 1 <= actual_stats_map['READINGS']
    if not skip_verify_north_interface:
        assert 1 <= actual_stats_map['Readings Sent']
        assert 1 <= actual_stats_map[NORTH_TASK_NAME]


def verify_asset(fledge_url):
    get_url = "/fledge/asset"
    result = utils.get_request(fledge_url, get_url)
    assert len(result), "No asset found"
    assert ASSET in [s["assetCode"] for s in result]


def verify_asset_tracking_details(fledge_url, skip_verify_north_interface):
    tracking_details = utils.get_asset_tracking_details(fledge_url, "Ingest")
    assert len(tracking_details["track"]), "Failed to track Ingest event"
    tracked_item = tracking_details["track"][0]
    assert ASSET == tracked_item["asset"]
    assert "coap" == tracked_item["plugin"]

    if not skip_verify_north_interface:
        egress_tracking_details = utils.get_asset_tracking_details(fledge_url, "Egress")
        assert len(egress_tracking_details["track"]), "Failed to track Egress event"
        tracked_item = egress_tracking_details["track"][0]
        assert ASSET == tracked_item["asset"]
        assert "OMF" == tracked_item["plugin"]


def _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries, asset_name):
    retry_count = 0
    data_from_pi = None

    af_hierarchy_level_list = AF_HIERARCHY_LEVEL.split("/")
    type_id = 1
    recorded_datapoint = asset_name
    # Name of asset in the PI server
    PI_ASSET_NAME = asset_name

    while (data_from_pi is None or data_from_pi == []) and retry_count < retries:
        data_from_pi = read_data_from_pi_web_api(pi_host, pi_admin, pi_passwd, pi_db, af_hierarchy_level_list,
                                                 ASSET, '')
        retry_count += 1
        time.sleep(wait_time * 2)

    if data_from_pi is None or retry_count == retries:
        assert False, "Failed to read data from PI"

    assert int(data_from_pi) == DATAPOINT_VALUE


@pytest.fixture
def start_south_north(add_south, start_north_task_omf_web_api, remove_data_file,
                      fledge_url, pi_host, pi_port, pi_admin, pi_passwd,
                      clear_pi_system_through_pi_web_api, pi_db, asset_name=ASSET):
    """ This fixture
        clean_setup_fledge_packages: purge the fledge* packages and install latest for given repo url
        add_south: Fixture that adds a south service with given configuration
        start_north_task_omf_web_api: Fixture that starts PI north task
        remove_data_file: Fixture that remove data file created during the tests """

    af_hierarchy_level_list = AF_HIERARCHY_LEVEL.split("/")
    # There are two data points here. 1. DATAPOINT
    # 2. no data point (Asset name be used in this case.)
    dp_list = [DATAPOINT, '']
    asset_dict = {}
    asset_dict[ASSET] = dp_list
    clear_pi_system_through_pi_web_api(pi_host, pi_admin, pi_passwd, pi_db,
                                       af_hierarchy_level_list, asset_dict)

    # Define the template file for fogbench
    fogbench_template_path = os.path.join(
        os.path.expandvars('${FLEDGE_ROOT}'), 'data/{}'.format(TEMPLATE_NAME))
    with open(fogbench_template_path, "w") as f:
        f.write(
            '[{"name": "%s", "sensor_values": '
            '[{"name": "%s", "type": "number", "min": %d, "max": %d, "precision": 0}]}]' % (
                asset_name, DATAPOINT, DATAPOINT_VALUE, DATAPOINT_VALUE))

    south_plugin = "coap"
    # south_branch does not matter as these are archives.fledge-iot.org version install
    add_south(south_plugin, None, fledge_url, service_name=SOUTH_SERVICE_NAME, installation_type='package')
    start_north_task_omf_web_api(fledge_url, pi_host, pi_port, pi_user=pi_admin, pi_pwd=pi_passwd,
                                 default_af_location=AF_HIERARCHY_LEVEL)

    yield start_south_north

    # Cleanup code that runs after the caller test is over
    remove_data_file(fogbench_template_path)


class TestPackagesCoAP_PI_WebAPI:

    def test_omf_task(self, clean_setup_fledge_packages, reset_fledge, start_south_north, read_data_from_pi_web_api,
                        fledge_url, pi_host, pi_admin, pi_passwd, pi_db, fogbench_host, fogbench_port,
                        wait_time, retries, skip_verify_north_interface, asset_name=ASSET):
        """ Test that data is inserted in Fledge and sent to PI
            start_south_north: Fixture that add south and north instance
            read_data_from_pi: Fixture to read data from PI
            skip_verify_north_interface: Flag for assertion of data using PI web API
            Assertions:
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/statistics
                on endpoint GET /fledge/asset
                on endpoint GET /fledge/asset/<asset_name>
                data received from PI is same as data sent"""

        conn = http.client.HTTPConnection(fledge_url)
        # Time to get coap service started
        time.sleep(2)
        subprocess.run(
            ["cd $FLEDGE_ROOT/extras/python; python3 -m fogbench -t ../../data/{} --host {} --port {}; cd -".format(TEMPLATE_NAME, fogbench_host, fogbench_port)],
            shell=True, check=True)

        time.sleep(wait_time)

        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url)
        verify_statistics_map(fledge_url, skip_verify_north_interface)
        verify_asset_tracking_details(fledge_url, skip_verify_north_interface)

        if not skip_verify_north_interface:
            _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                           asset_name)

    def test_omf_task_with_reconfig(self, reset_fledge, start_south_north, read_data_from_pi_web_api,
                                       skip_verify_north_interface, fledge_url, fogbench_host, fogbench_port,
                                       wait_time, retries, pi_host, pi_port, pi_admin, pi_passwd, pi_db,
                                       asset_name=ASSET):
        """ Test OMF as a North task by reconfiguring it.
            reset_fledge: Fixture to reset fledge
            start_south_north: Adds and configures south and north (OMF)
            read_data_from_pi_web_api: Fixture to read data from PI web API
            skip_verify_north_interface: Flag for assertion of data using PI web API
            Assertions:
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/statistics
                on endpoint GET /fledge/asset
                on endpoint GET /fledge/track"""

        conn = http.client.HTTPConnection(fledge_url)
        # Time to get coap service started
        time.sleep(2)
        subprocess.run(
            ["cd $FLEDGE_ROOT/extras/python; python3 -m fogbench -t ../../data/{} --host {} --port {}; cd -".format(TEMPLATE_NAME, fogbench_host, fogbench_port)],
            shell=True, check=True)

        time.sleep(wait_time)

        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url)
        verify_statistics_map(fledge_url, skip_verify_north_interface)
        verify_asset_tracking_details(fledge_url, skip_verify_north_interface)

        # Good reconfiguration to check data is sent
        data = {"SendFullStructure": "false"}
        put_url = "/fledge/category/{}".format(NORTH_TASK_NAME)
        resp = utils.put_request(fledge_url, urllib.parse.quote(put_url), data)
        assert "false" == resp["SendFullStructure"]["value"]

        old_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)

        conn = http.client.HTTPConnection(fledge_url)
        subprocess.run(
            ["cd $FLEDGE_ROOT/extras/python; python3 -m fogbench -t ../../data/{} --host {} --port {}; cd -".format(TEMPLATE_NAME, fogbench_host, fogbench_port)],
            shell=True, check=True)

        # Wait for the OMF schedule to run.
        time.sleep(wait_time * 2)

        new_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        # Verifies whether Read and Sent readings are increasing after delete/add of north service
        assert old_ping_result['dataRead'] < new_ping_result['dataRead']
        if not skip_verify_north_interface:
            assert old_ping_result['dataSent'] < new_ping_result['dataSent']

        # Bad reconfiguration to check data is not sent
        data = {"PIWebAPIUserId": "Inv@lidRandomUserID"}
        put_url = "/fledge/category/{}".format(NORTH_TASK_NAME)
        resp = utils.put_request(fledge_url, urllib.parse.quote(put_url), data)
        assert "Inv@lidRandomUserID" == resp["PIWebAPIUserId"]["value"]

        old_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)

        # Wait for the OMF schedule to run and then send the new data.
        # Otherwise, it sends the data with old config. 
        time.sleep(wait_time * 2)

        conn = http.client.HTTPConnection(fledge_url)
        subprocess.run(
            ["cd $FLEDGE_ROOT/extras/python; python3 -m fogbench -t ../../data/{} --host {} --port {}; cd -".format(TEMPLATE_NAME, fogbench_host, fogbench_port)],
            shell=True, check=True)

        # Wait for the OMF schedule to run.
        time.sleep(wait_time * 2)

        new_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        # Verifies whether Read and Sent readings are increasing after delete/add of north service
        assert old_ping_result['dataRead'] < new_ping_result['dataRead']

        if not skip_verify_north_interface:
            assert old_ping_result['dataSent'] == new_ping_result['dataSent']
            _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                           asset_name)
