# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test sending data to Azure-IOT-Hub using fledge-north-azure plugin

"""

__author__ = "Mohit Singh Tomaar"
__copyright__ = "Copyright (c) 2023 Dianomic Systems Inc"
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

# This  gives the path of directory where fledge is cloned. test_file < packages < python < system < tests < ROOT
PROJECT_ROOT = subprocess.getoutput("git rev-parse --show-toplevel")
SCRIPTS_DIR_ROOT = "{}/tests/system/python/scripts/package/".format(PROJECT_ROOT)
SOUTH_SERVICE_NAME = "FOGL-7352_sysinfo"
SOUTH_PLUGIN = "systeminfo"
ASSET = "system"
NORTH_SERVICE_NAME = "FOGL_7352_azure"
NORTH_PLUGIN_NAME = "azure-iot"
NORTH_PLUGIN_DISCOVERY_NAME = "azure_iot"

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

        assert 1 <= sent, "Failed to send data to Azure-IOT-Hub"
    return ping_result


def verify_statistics_map(fledge_url, skip_verify_north_interface):
    get_url = "/fledge/statistics"
    jdoc = utils.get_request(fledge_url, get_url)
    actual_stats_map = utils.serialize_stats_map(jdoc)
    assert 1 <= actual_stats_map["{}-Ingest".format(SOUTH_SERVICE_NAME)]
    assert 1 <= actual_stats_map['READINGS']
    if not skip_verify_north_interface:
        assert 1 <= actual_stats_map['Readings Sent']


def verify_asset(fledge_url):
    get_url = "/fledge/asset"
    result = utils.get_request(fledge_url, get_url)
    assert len(result), "No asset found"
    assert ASSET in [s["assetCode"] for s in result]


def verify_asset_tracking_details(fledge_url, skip_verify_north_interface):
    tracking_details = utils.get_asset_tracking_details(fledge_url, "Ingest")
    assert len(tracking_details["track"]), "Failed to track Ingest event"
    tracked_item = tracking_details["track"][0]
    assert ASSET in tracked_item["asset"]
    assert "systeminfo" == tracked_item["plugin"]

    if not skip_verify_north_interface:
        egress_tracking_details = utils.get_asset_tracking_details(fledge_url, "Egress")
        assert len(egress_tracking_details["track"]), "Failed to track Egress event"
        tracked_item = egress_tracking_details["track"][0]
        assert ASSET in tracked_item["asset"]


def _verify_egress(fledge_url):
    pass

@pytest.fixture
def add_south_north(add_south, add_north, fledge_url):
    """ This fixture
        add_south: Fixture that adds a south service with given configuration

    """
    # south_branch does not matter as these are archives.fledge-iot.org version install
    add_south(SOUTH_PLUGIN, None, fledge_url, service_name=SOUTH_SERVICE_NAME, start_service=False, installation_type='package')
    
    # south_branch does not matter as these are archives.fledge-iot.org version install
    add_north(fledge_url, NORTH_PLUGIN_NAME, None, installation_type='package', enabled=False, plugin_discovery_name=NORTH_PLUGIN_DISCOVERY_NAME, is_task=False)
    
    
class TestPackagesSysteminfoAzureIOT:
    
    def test_azure_iot_simple(self, clean_setup_fledge_packages, reset_fledge, add_south_north, fledge_url, wait_time, retries):
        pass
    
    @pytest.mark.skip(reason="no way of currently testing this")
    def test_azure_iot_websocket(self, reset_fledge, add_south_north, fledge_url, wait_time, retries):
        pass
    
    @pytest.mark.skip(reason="no way of currently testing this")
    def test_azure_iot_enable_disable(self, reset_fledge, add_south_north, fledge_url, wait_time, retries):
        pass
    
    @pytest.mark.skip(reason="no way of currently testing this")
    def test_azure_iot_task(self, reset_fledge, add_south_north, fledge_url, wait_time, retries):
        pass
    
    @pytest.mark.skip(reason="no way of currently testing this")
    def test_azure_iot_invalid_config(self, reset_fledge, add_south_north, fledge_url, wait_time, retries):
        pass