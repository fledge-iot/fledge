# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test statistics history notification rule system tests:
        Creates notification instance with source as statistics history in threshold rule
        and notify asset plugin for triggering the notifications based on rules.
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
SOUTH_ASSET_NAME = "{}_sinusoid_assets".format(time.strftime("%Y%m%d"))
NOTIF_SERVICE_NAME = "notification"
NOTIF_INSTANCE_NAME = "notify #1"
AF_HIERARCHY_LEVEL = "{0}_teststatslvl1/{0}_teststatslvl2/{0}_teststatslvl3".format(time.strftime("%Y%m%d"))

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
def start_south(add_south, fledge_url):
    south_plugin = "sinusoid"
    config = {"assetName": {"value": SOUTH_ASSET_NAME}}
    # south_branch does not matter as these are archives.fledge-iot.org version install
    add_south(south_plugin, None, fledge_url, service_name=SOUTH_SERVICE_NAME, installation_type='package', config=config)


@pytest.fixture
def start_north(start_north_omf_as_a_service, fledge_url,
                      pi_host, pi_port, pi_admin, pi_passwd, clear_pi_system_through_pi_web_api, pi_db):
    
    af_hierarchy_level_list = AF_HIERARCHY_LEVEL.split("/")
    dp_list = ['sinusoid']
    asset_dict = {}
    asset_dict[SOUTH_ASSET_NAME] = dp_list
    clear_pi_system_through_pi_web_api(pi_host, pi_admin, pi_passwd, pi_db,
                                       af_hierarchy_level_list, asset_dict)

    response = start_north_omf_as_a_service(fledge_url, pi_host, pi_port, pi_user=pi_admin, pi_pwd=pi_passwd,
                                            default_af_location=AF_HIERARCHY_LEVEL)

    yield start_north

@pytest.fixture
def add_notification_service(fledge_url, wait_time, enabled="true"):
    try:
        subprocess.run(["sudo {} install -y fledge-service-notification fledge-notify-asset".format(pytest.PKG_MGR)], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "notification service installation failed"

    # Enable service
    data = {"name": NOTIF_SERVICE_NAME, "type": "notification", "enabled": enabled}
    print (data)
    utils.post_request(fledge_url, "/fledge/service", data)

    # Wait and verify service created or not
    time.sleep(wait_time)
    verify_service_added(fledge_url, NOTIF_SERVICE_NAME)

@pytest.fixture
def add_notification_instance(fledge_url, enabled=True):
    payload = {
        "name": "test #1",
        "description": "test notification instance",
        "rule": "Threshold",
        "rule_config": {
            "source": "Statistics History",
            "asset": "READINGS",
            "trigger_value": "10.0",
        },
        "channel": "asset",
        "delivery_config": {"enable": "true"},
        "notification_type": "retriggered",
        "retrigger_time": "30",
        "enabled": enabled,
    }
    post_url = "/fledge/notification"
    utils.post_request(fledge_url, post_url, payload)
    
    notification_url = "/fledge/notification"
    resp = utils.get_request(fledge_url, notification_url)
    assert "test #1" in [s["name"] for s in resp["notifications"]]

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

def _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries):

    af_hierarchy_level_list = AF_HIERARCHY_LEVEL.split("/")
    retry_count = 0
    data_from_pi = None
    # Name of asset in the PI server
    pi_asset_name = "{}".format(SOUTH_ASSET_NAME)

    while (data_from_pi is None or data_from_pi == []) and retry_count < retries:
        data_from_pi = read_data_from_pi_web_api(pi_host, pi_admin, pi_passwd, pi_db, af_hierarchy_level_list,
                                                    pi_asset_name, '')
        if data_from_pi is None:
            retry_count += 1
            time.sleep(wait_time)

    if data_from_pi is None or retry_count == retries:
        assert False, "Failed to read data from PI"


class TestStatisticsHistoryBasedNotificationRuleOnIngress:
    def test_stats_readings_south(self, clean_setup_fledge_packages, reset_fledge, start_south, add_notification_service, add_notification_instance, fledge_url,
                 skip_verify_north_interface, wait_time, retries):
        """ Test NTFSN triggered or not with source as statistics history and name as READINGS in threshold rule.
            clean_setup_fledge_packages: Fixture to remove and install latest fledge packages
            reset_fledge: Fixture to reset fledge
            start_south: Fixtures to add and start south services
            add_notification_service: Fixture to add notification service with rule and delivery plugins
            Assertions:
                on endpoint GET /fledge/audit
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/statistics/history """
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
        # Waiting for 60 sec to get 2 more NTFSN entries if rule is triggered properly
        time.sleep(60)
        resp2 = utils.get_request(fledge_url, get_url)
        assert len(resp2['audit']) - len(resp1['audit']) == 2, "ERROR: NTFSN not triggered properly"
        
        get_url = "/fledge/statistics/history?minutes=10"
        r = utils.get_request(fledge_url, get_url)
        if "READINGS" in r["statistics"][0]:
            assert 0 < r["statistics"][0]["READINGS"]

    def test_stats_south_asset_ingest(self, fledge_url, wait_time, skip_verify_north_interface, retries):
        """ Test NTFSN triggered or not with source as statistics history and name as ingested south asset in threshold rule.
            Assertions:
                on endpoint GET /fledge/audit
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/statistics/history """
        # Change the config of threshold, name of statistics - READINGS replaced with statistics key name - Sine #1-Ingest
        put_url = "/fledge/category/ruletest #1"
        data = {"asset": "Sine #1-Ingest"}
        utils.put_request(fledge_url, urllib.parse.quote(put_url), data)
        
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
        
        get_url = "/fledge/statistics/history?minutes=10"
        r = utils.get_request(fledge_url, get_url)
        if "Sine #1-Ingest" in r["statistics"][0]:
            assert 0 < r["statistics"][0]["Sine #1-Ingest"]
        
    def test_stats_south_asset(self, fledge_url, wait_time, skip_verify_north_interface, retries):
        """ Test NTFSN triggered or not with source as statistics history and name as south asset name in threshold rule.
            Assertions:
                on endpoint GET /fledge/audit
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/statistics/history """
        # Change the config of threshold, name of statistics - Sine #1-Ingest replaced with statistics key name - 20230420_SINUSOID_ASSETS
        put_url = "/fledge/category/ruletest #1"
        data = {"asset": SOUTH_ASSET_NAME.upper()}
        utils.put_request(fledge_url, urllib.parse.quote(put_url), data)
        
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
        
        get_url = "/fledge/statistics/history?minutes=10"
        r = utils.get_request(fledge_url, get_url)
        if SOUTH_ASSET_NAME.upper() in r["statistics"][0]:
            assert 0 < r["statistics"][0][SOUTH_ASSET_NAME.upper()]


class TestStatisticsHistoryBasedNotificationRuleOnEgress:
    def test_stats_readings_north(self, start_north, fledge_url,
                 wait_time, skip_verify_north_interface, retries, read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db):
        """ Test NTFSN triggered or not with source as statistics history and name as READINGS in threshold rule.
            clean_setup_fledge_packages: Fixture to remove and install latest fledge packages
            reset_fledge: Fixture to reset fledge
            start_south_north: Fixtures to add and start south and north services
            add_notification_service: Fixture to add notification service with rule and delivery plugins
            Assertions:
                on endpoint GET /fledge/audit
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/statistics/history """
        # Change the config of threshold, name of statistics - Sine #1-Ingest replaced with statistics key name - 20230420_SINUSOID_ASSETS
        put_url = "/fledge/category/ruletest #1"
        data = {"asset": "Readings Sent"}
        utils.put_request(fledge_url, urllib.parse.quote(put_url), data)

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
        assert len(resp2['audit']) - len(resp1['audit']) == 2, "ERROR: NTFSN for north not triggered properly"
        
        get_url = "/fledge/statistics/history?minutes=10"
        r = utils.get_request(fledge_url, get_url)
        if "Readings Sent" in r["statistics"][0]:
            assert 0 < r["statistics"][0]["Readings Sent"]

        _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries)
