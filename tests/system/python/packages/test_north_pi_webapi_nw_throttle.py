# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test sending data to PI using Web API under a distorted network.

"""

__author__ = "Deepanshu Yadav"
__copyright__ = "Copyright (c) 2022 Dianomic Systems Inc"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

import subprocess
import http.client
import pytest
import os
import time
import utils
import json
from pathlib import Path
import urllib.parse

from network_impairment import distort_network, reset_network

ASSET = "Sine-FOGL-6333"
DATAPOINT = "sinusoid"
NORTH_TASK_NAME = "NorthReadingsToPI_WebAPI"
SOUTH_SERVICE_NAME = "Sinusoid-FOGL-6333"
# This  gives the path of directory where fledge is cloned. test_file < packages < python < system < tests < ROOT
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
SCRIPTS_DIR_ROOT = "{}/tests/system/python/scripts/package/".format(PROJECT_ROOT)


@pytest.fixture
def reset_fledge(wait_time):
    try:
        subprocess.run(["cd {} && ./reset"
                       .format(SCRIPTS_DIR_ROOT)], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "reset package script failed!"


def verify_ping(fledge_url, north_catch_up_time):
    get_url = "/fledge/ping"
    ping_result = utils.get_request(fledge_url, get_url)
    assert "dataRead" in ping_result
    assert "dataSent" in ping_result
    assert 0 < ping_result['dataRead'], "South data NOT seen in ping header"

    assert ping_result['dataRead'] == ping_result['dataSent'], "Could not send all" \
                                                               " the data even after " \
                                                               "waiting {} " \
                                                               "seconds.".format(north_catch_up_time)


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


def change_category(fledge_url, cat_name, config_item, value):
    """
    Changes the value of configuration item in the given category.
    Args:
        fledge_url: The url of the Fledge API.
        cat_name: The category name.
        config_item: The configuration item to be changed.
        value: The new value of configuration item.
    Returns: returns the value of changed category or raises error.
    """
    conn = http.client.HTTPConnection(fledge_url)
    body = {"value": str(value)}
    json_data = json.dumps(body)
    conn.request("PUT", '/fledge/category/{}/{}'.format(cat_name, config_item), json_data)
    r = conn.getresponse()
    # assert 200 == r.status, 'Could not change config item'
    print(r.status)
    r = r.read().decode()
    conn.close()
    retval = json.loads(r)
    print(retval)


def disable_schedule(fledge_url, sch_name):
    """
        Disables schedule.
        Args:
            fledge_url: The url of the Fledge API.
            sch_name: The name of schedule to be disabled.
        Returns: Response of disabling schedule in json.
        """
    conn = http.client.HTTPConnection(fledge_url)
    conn.request("PUT", '/fledge/schedule/disable', json.dumps({"schedule_name": sch_name}))
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    assert "scheduleId" in jdoc
    return


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

    af_hierarchy_level = "fledge/room1/machine1"
    af_hierarchy_level_list = af_hierarchy_level.split("/")
    type_id = 1
    recorded_datapoint = "{}measurement_{}".format(type_id, asset_name)
    # Name of asset in the PI server
    PI_ASSET_NAME = "{}-type{}".format(asset_name, type_id)

    while (data_from_pi is None or data_from_pi == []) and retry_count < retries:
        data_from_pi = read_data_from_pi_web_api(pi_host, pi_admin, pi_passwd, pi_db, af_hierarchy_level_list,
                                                 PI_ASSET_NAME, {recorded_datapoint})
        retry_count += 1
        time.sleep(wait_time * 2)

    if data_from_pi is None or retry_count == retries:
        assert False, "Failed to read data from PI"

    return data_from_pi


@pytest.fixture
def start_south_north(add_south, start_north_task_omf_web_api, remove_data_file,
                      fledge_url, pi_host, pi_port, pi_admin, pi_passwd,
                      start_north_omf_as_a_service, start_north_as_service, asset_name=ASSET):
    """ This fixture
        clean_setup_fledge_packages: purge the fledge* packages and install latest for given repo url
        add_south: Fixture that adds a south service with given configuration
        start_north_task_omf_web_api: Fixture that starts PI north task
        remove_data_file: Fixture that remove data file created during the tests """

    south_plugin = "sinusoid"
    # south_branch does not matter as these are archives.fledge-iot.org version install
    _config = {"assetName": {"value": ASSET}}
    add_south(south_plugin, None, fledge_url, config=_config,
              service_name=SOUTH_SERVICE_NAME, installation_type='package')
    if not start_north_as_service:
        start_north_task_omf_web_api(fledge_url, pi_host, pi_port, pi_user=pi_admin, pi_pwd=pi_passwd)
    else:
        start_north_omf_as_a_service(fledge_url, pi_host, pi_port, pi_user=pi_admin, pi_pwd=pi_passwd)

    yield start_south_north


class TestPackagesSinusoid_PI_WebAPI:

    def test_omf_in_impaired_network(self, clean_setup_fledge_packages, reset_fledge,
                                     start_south_north, read_data_from_pi_web_api,
                                     fledge_url, pi_host, pi_admin, pi_passwd, pi_db,
                                     wait_time, retries, skip_verify_north_interface,
                                     south_service_wait_time, north_catch_up_time, pi_port,
                                     interface_for_impairment, packet_delay, rate_limit,
                                     asset_name=ASSET):
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

        duration = south_service_wait_time + north_catch_up_time
        distort_network(interface=interface_for_impairment, traffic="outbound",
                        latency=packet_delay,
                        rate_limit=rate_limit, ip=pi_host, port=pi_port, duration=duration)

        # allow the south service to run for sometime
        time.sleep(5)
        change_category(fledge_url, SOUTH_SERVICE_NAME + "Advanced", "readingsPerSec", 3000)

        # Wait for south service to accumulate some readings
        time.sleep(south_service_wait_time)

        # now shutdown the south service
        disable_schedule(fledge_url, SOUTH_SERVICE_NAME)

        # Wait for north task or service to send these accumulated readings.
        time.sleep(north_catch_up_time)

        # clear up all the distortions on this network.
        reset_network(interface=interface_for_impairment)
        verify_ping(fledge_url, north_catch_up_time)
        # verify_asset(fledge_url)
        # verify_statistics_map(fledge_url, skip_verify_north_interface)
        # verify_asset_tracking_details(fledge_url, skip_verify_north_interface)
        #
        if not skip_verify_north_interface:
            data_pi = _verify_egress(read_data_from_pi_web_api, pi_host,
                                     pi_admin, pi_passwd, pi_db, wait_time, retries,
                                     asset_name)
            print(type(data_pi))
            print(data_pi)
