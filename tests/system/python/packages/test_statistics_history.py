# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test Multiple Assets System tests:
        Creates large number of assets and verifies them.
"""

__author__ = "Yash Tatkondawar"
__copyright__ = "Copyright (c) 2023 Dianomic Systems, Inc."

import base64
import http.client
import json
import os
import ssl
import subprocess
import time
import urllib.parse
from pathlib import Path

import pytest
import utils
from pytest import PKG_MGR

# This  gives the path of directory where fledge is cloned. test_file < packages < python < system < tests < ROOT
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
SCRIPTS_DIR_ROOT = "{}/tests/system/python/packages/data/".format(PROJECT_ROOT)
FLEDGE_ROOT = os.environ.get('FLEDGE_ROOT')
SOUTH_SERVICE_NAME = "Sine #1"
ASSET_NAME = "{}_sinusoid_assets".format(time.strftime("%Y%m%d"))
NOTIF_SERVICE_NAME = "notification"
NOTIF_INSTANCE_NAME = "notify #1"
AF_HIERARCHY_LEVEL = "{0}_multipleassets/{0}_multipleassetslvl2/{0}_multipleassetslvl3".format(time.strftime("%Y%m%d"))

@pytest.fixture
def reset_fledge(wait_time):
    try:
        subprocess.run(["cd {}/tests/system/python/scripts/package && ./reset"
                       .format(PROJECT_ROOT)], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "reset package script failed!"

    # Wait for fledge server to start
    time.sleep(wait_time)


@pytest.fixture
def start_south_north(start_north_omf_as_a_service, add_south, fledge_url,
                      pi_host, pi_port, pi_admin, pi_passwd, clear_pi_system_through_pi_web_api, pi_db):
    
    af_hierarchy_level_list = AF_HIERARCHY_LEVEL.split("/")
    dp_list = ['']
    asset_dict = {}
    clear_pi_system_through_pi_web_api(pi_host, pi_admin, pi_passwd, pi_db,
                                       af_hierarchy_level_list, asset_dict)

    south_plugin = "sinusoid"
    # south_branch does not matter as these are archives.fledge-iot.org version install
    add_south(south_plugin, None, fledge_url, service_name=SOUTH_SERVICE_NAME, installation_type='package')
    response = start_north_omf_as_a_service(fledge_url, pi_host, pi_port, pi_user=pi_admin, pi_pwd=pi_passwd,
                                            default_af_location=AF_HIERARCHY_LEVEL)
    north_schedule_id = response["id"]

    yield start_south_north

@pytest.fixture
def add_notification_service(service_branch, fledge_url, wait_time):
    try:
        subprocess.run(["sudo apt install -y fledge-service-notification"], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "notification service installation failed"

    # Enable service
    data = {"name": NOTIF_SERVICE_NAME, "type": "notification", "enabled": "true"}
    print (data)
    utils.post_request(fledge_url, "/fledge/service", data)

    # Wait and verify service created or not
    time.sleep(wait_time)
    verify_service_added(fledge_url, NOTIF_SERVICE_NAME)

    payload = {"name": "test #1", "description": "test notification instance", "rule": "Threshold", "rule_config": {"source": "Statistics History", "asset": "READINGS"}, 
                "channel": "asset", "delivery_config": {"enable": "true"}, "notification_type": "retriggered", "retrigger_time": "30", "enabled": True}
    post_url = "/fledge/notification"
    utils.post_request(fledge_url, post_url, payload)
    
    get_url = "/fledge/notification"
    resp = utils.get_request(fledge_url, get_url)
    assert "test #1" in [s["name"] for s in resp["notifications"]]


def verify_restart(fledge_url, retries):
    for i in range(retries):
        time.sleep(30)
        get_url = '/fledge/ping'
        ping_result = utils.get_request(fledge_url, get_url)
        if ping_result['uptime'] > 0:
            return
    assert ping_result['uptime'] > 0

def verify_service_added(fledge_url, name):
    get_url = "/fledge/service"
    result = utils.get_request(fledge_url, get_url)
    assert len(result["services"])
    assert name in [s["name"] for s in result["services"]]

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


def verify_asset(fledge_url, total_assets, count, wait_time):
    # Check whether "total_assets" are created or not by calling "/fledge/asset" endpoint for "count" number of iterations
    # In each iteration sleep for wait_time * 6, i.e., 60 seconds..
    for i in range(count):
        get_url = "/fledge/asset"
        result = utils.get_request(fledge_url, get_url)
        asset_created = len(result)
        if (total_assets == asset_created):
            print("Total {} asset created".format(asset_created))
            return
        # Fledge takes 60 seconds to create 100 assets.
        # Added sleep for "wait_time * 6", So that we can changes sleep time by changing value of wait_time from the jenkins job in future if required.
        time.sleep(wait_time * 6)
    assert total_assets == len(result)


def verify_asset_tracking_details(fledge_url, total_assets, total_benchmark_services, num_assets):
    tracking_details = utils.get_asset_tracking_details(fledge_url, "Ingest")
    assert len(tracking_details["track"]), "Failed to track Ingest event"
    assert total_assets == len(tracking_details["track"])
    for service_count in range(total_benchmark_services):
        for asset_count in range(num_assets):
            service_name = SOUTH_SERVICE_NAME + "{}".format(service_count + 1)
            asset_name = ASSET_NAME + "-{}{}".format(service_count + 1, asset_count + 1)
            assert service_name in [s["service"] for s in tracking_details["track"]]
            assert asset_name in [s["asset"] for s in tracking_details["track"]]
            assert "Benchmark" in [s["plugin"] for s in tracking_details["track"]]


def _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries, total_benchmark_services, num_assets_per_service):

    af_hierarchy_level_list = AF_HIERARCHY_LEVEL.split("/")
    type_id = 1
    
    for s in range(1, total_benchmark_services+1):
      for a in range(1, num_assets_per_service+1):
        retry_count = 0
        data_from_pi = None
        asset_name = "random_multiple_assets-" + str(s) + str(a)
        print(asset_name)
        recorded_datapoint = "{}".format(asset_name)
        # Name of asset in the PI server
        pi_asset_name = "{}".format(asset_name)
    
        while (data_from_pi is None or data_from_pi == []) and retry_count < retries:
            data_from_pi = read_data_from_pi_web_api(pi_host, pi_admin, pi_passwd, pi_db, af_hierarchy_level_list,
                                                     pi_asset_name, '')
            if data_from_pi is None:
                retry_count += 1
                time.sleep(wait_time)
    
        if data_from_pi is None or retry_count == retries:
            assert False, "Failed to read data from PI"


class TestStatisticsHistory:
    def test_stats(self, reset_fledge, start_south_north, add_notification_service, fledge_url,
                 wait_time, skip_verify_north_interface, retries):
        time.sleep(wait_time * 4)

        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        
        # When rule is triggered, there should be audit entries for NTFSN
        get_url = "/fledge/audit?source=NTFSN"
        resp1 = utils.get_request(fledge_url, get_url)
        assert len(resp1['audit'])
        assert "test #1" in [s["details"]["name"] for s in resp1["audit"]]
        for audit_detail in resp1['audit']:
            if "test #1" == audit_detail['details']['name']:
                assert "NTFSN" == audit_detail['source']
        # Waiting for 60 sec to get more NTFSN entries
        time.sleep(60)
        resp2 = utils.get_request(fledge_url, get_url)
        assert len(resp2['audit']) - len(resp1['audit']) == 2, "ERROR: NTFSN not triggered properly"
