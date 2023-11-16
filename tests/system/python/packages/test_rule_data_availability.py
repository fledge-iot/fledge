# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test data availability notification rule system tests:
        Creates notification instance with data availability rule
        and notify asset plugin for triggering the notifications based on CONCH.
"""

__author__ = "Yash Tatkondawar"
__copyright__ = "Copyright (c) 2023 Dianomic Systems, Inc."


import os
import subprocess
import time
import urllib.parse
import json
from pathlib import Path
import http
from datetime import datetime
import pytest
import utils
from pytest import PKG_MGR

# This  gives the path of directory where fledge is cloned. test_file < packages < python < system < tests < ROOT
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
SCRIPTS_DIR_ROOT = "{}/tests/system/python/packages/data/".format(PROJECT_ROOT)
FLEDGE_ROOT = os.environ.get('FLEDGE_ROOT')
SOUTH_SERVICE_NAME = "Sine #1"
SOUTH_DP_NAME="sinusoid"
SOUTH_ASSET_NAME = "{}_sinusoid_assets".format(time.strftime("%Y%m%d"))
NORTH_PLUGIN = "OMF"
TASK_NAME = "EDS #1"
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
def reset_eds():
    eds_reset_url = "/api/v1/Administration/Storage/Reset"
    con = http.client.HTTPConnection("localhost", 5590)
    con.request("POST", eds_reset_url, "")
    resp = con.getresponse()
    assert 204 == resp.status

@pytest.fixture
def check_eds_installed():
    dpkg_list = os.popen('dpkg --list osisoft.edgedatastore >/dev/null; echo $?')
    ls_output = dpkg_list.read()
    assert ls_output == "0\n", "EDS not installed. Please install it first!"
    eds_data_url = "/api/v1/diagnostics/productinformation"
    con = http.client.HTTPConnection("localhost", 5590)
    con.request("GET", eds_data_url)
    resp = con.getresponse()
    r = json.loads(resp.read().decode())
    assert len(r) != 0, "EDS not installed. Please install it first!"

@pytest.fixture
def start_south(add_south, fledge_url):
    south_plugin = "sinusoid"
    config = {"assetName": {"value": SOUTH_ASSET_NAME}}
    # south_branch does not matter as these are archives.fledge-iot.org version install
    add_south(south_plugin, None, fledge_url, service_name=SOUTH_SERVICE_NAME, installation_type='package', config=config)


@pytest.fixture
def start_north(fledge_url, enabled=True):
    conn = http.client.HTTPConnection(fledge_url)
    data = {"name": TASK_NAME,
            "plugin": NORTH_PLUGIN,
            "type": "north",
            "enabled": enabled,
            "config": {"PIServerEndpoint": {"value": "Edge Data Store"},
                       "NamingScheme": {"value": "Backward compatibility"}}
            }
    post_url = "/fledge/service"
    utils.post_request(fledge_url, post_url, data)

@pytest.fixture
def start_notification(fledge_url, add_service, add_notification_instance,wait_time, retries):
    
    # Install and Add Notification Service
    add_service(fledge_url, "notification", None, retries, installation_type='package', service_name=NOTIF_SERVICE_NAME)
    
    # Wait and verify service created or not
    time.sleep(wait_time)
    verify_service_added(fledge_url, NOTIF_SERVICE_NAME)
    
    # Add Notification Instance
    rule_config = {"auditCode": "CONAD,SCHAD"}
    delivery_config = {"enable": "true"}
    add_notification_instance(fledge_url, "asset", None, rule_config=rule_config, delivery_config=delivery_config, 
                              rule_plugin="DataAvailability", installation_type='package', notification_type="retriggered",
                              notification_instance_name="test #1", retrigger_time=5)
    
    # Verify Notification Instance created or not
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

        assert 1 <= sent, "Failed to send data to Edge Data Store"
    return ping_result

def verify_eds_data():
    eds_data_url = "/api/v1/tenants/default/namespaces/default/streams/1measurement_{}/Data/Last".format(SOUTH_ASSET_NAME)
    print (eds_data_url)
    con = http.client.HTTPConnection("localhost", 5590)
    con.request("GET", eds_data_url)
    resp = con.getresponse()
    r = json.loads(resp.read().decode())
    return r

class TestDataAvailabilityAuditBasedNotificationRuleOnIngress:
    def test_data_availability_multiple_audit(self, clean_setup_fledge_packages, reset_fledge, start_notification, 
                                              start_south, fledge_url, skip_verify_north_interface, wait_time, retries):
        """ Test NTFSN triggered or not with CONAD, SCHAD.
            clean_setup_fledge_packages: Fixture to remove and install latest fledge packages
            reset_fledge: Fixture to reset fledge
            start_south: Fixtures to add and start south services
            start_notification: Fixture to add and start notification service with rule and delivery plugins
            Assertions:
                on endpoint GET /fledge/audit
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/category """
        time.sleep(wait_time)

        verify_ping(fledge_url, True, wait_time, retries)

        get_url = "/fledge/audit?source=NTFSN"
        resp1 = utils.get_request(fledge_url, get_url)
        print (len(resp1['audit']))
        assert len(resp1['audit'])
        
        assert "test #1" in [s["details"]["name"] for s in resp1["audit"]]
        for audit_detail in resp1['audit']:
            if "test #1" == audit_detail['details']['name']:
                assert "NTFSN" == audit_detail['source'], "ERROR: NTFSN not triggered properly on CONAD or SCHAD"

    def test_data_availability_single_audit(self, fledge_url, skip_verify_north_interface, wait_time, retries):
        """ Test NTFSN triggered or not with CONCH in sinusoid plugin.
                on endpoint GET /fledge/audit
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/category """
        get_url = "/fledge/audit?source=NTFSN"
        resp1 = utils.get_request(fledge_url, get_url)

        # Change the configuration of rule plugin
        put_url = "/fledge/category/ruletest #1"
        data = {"auditCode": "CONCH"}
        utils.put_request(fledge_url, urllib.parse.quote(put_url), data)
        
        # Change the configuration of sinusoid plugin
        put_url = "/fledge/category/Sine #1Advanced"
        data = {"readingsPerSec": "10"}
        utils.put_request(fledge_url, urllib.parse.quote(put_url), data)

        time.sleep(wait_time)
        get_url = "/fledge/audit?source=NTFSN"
        resp2 = utils.get_request(fledge_url, get_url)
        assert len(resp2['audit']) - len(resp1['audit']) == 1, "ERROR: NTFSN not triggered properly on CONCH"

    def test_data_availability_all_audit(self, fledge_url, add_south, skip_verify_north_interface, wait_time, retries):
        """ Test NTFSN triggered or not with all audit changes.
                on endpoint GET /fledge/audit
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/category """
        get_url = "/fledge/audit?source=NTFSN"
        resp1 = utils.get_request(fledge_url, get_url)

        # Change the configuration of rule plugin
        put_url = "/fledge/category/ruletest #1"
        data = {"auditCode": "*"}
        utils.put_request(fledge_url, urllib.parse.quote(put_url), data)
        
        # Add new service
        south_plugin = "sinusoid"
        config = {"assetName": {"value": "sine-test"}}
        # south_branch does not matter as these are archives.fledge-iot.org version install
        add_south(south_plugin, None, fledge_url, service_name="sine-test", installation_type='package', config=config)

        time.sleep(wait_time)
        get_url = "/fledge/audit?source=NTFSN"
        resp2 = utils.get_request(fledge_url, get_url)
        assert len(resp2['audit']) > len(resp1['audit']), "ERROR: NTFSN not triggered properly with * audit code"

class TestDataAvailabilityAssetBasedNotificationRuleOnIngress:
    def test_data_availability_asset(self, fledge_url, add_south, skip_verify_north_interface, wait_time, retries):
        """ Test NTFSN triggered or not with all audit changes.
                on endpoint GET /fledge/audit
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/category """
        get_url = "/fledge/audit?source=NTFSN"
        resp1 = utils.get_request(fledge_url, get_url)

        # Change the configuration of rule plugin
        put_url = "/fledge/category/ruletest #1"
        data = {"auditCode": "", "assetCode": SOUTH_ASSET_NAME}
        utils.put_request(fledge_url, urllib.parse.quote(put_url), data)

        time.sleep(wait_time)
        get_url = "/fledge/audit?source=NTFSN"
        resp2 = utils.get_request(fledge_url, get_url)
        assert len(resp2['audit']) > len(resp1['audit']), "ERROR: NTFSN not triggered properly with asset code"

class TestDataAvailabilityBasedNotificationRuleOnEgress:
    def test_data_availability_north(self, check_eds_installed, reset_fledge, start_notification, reset_eds, 
                                     start_north, fledge_url, wait_time, skip_verify_north_interface, add_south, retries):
        """ Test NTFSN triggered or not with configuration change in north EDS plugin.
            start_north: Fixtures to add and start south services
            Assertions:
                on endpoint GET /fledge/audit
                on endpoint GET /fledge/ping """
        
        # Change the configuration of rule plugin
        put_url = "/fledge/category/ruletest #1"
        data = {"auditCode": "", "assetCode": SOUTH_ASSET_NAME}
        utils.put_request(fledge_url, urllib.parse.quote(put_url), data)
        
        # Add new service
        south_plugin = "sinusoid"
        config = {"assetName": {"value": SOUTH_ASSET_NAME}}
        # south_branch does not matter as these are archives.fledge-iot.org version install
        add_south(south_plugin, None, fledge_url, service_name="sine-test", installation_type='package', config=config)

        get_url = "/fledge/audit?source=NTFSN"
        resp1 = utils.get_request(fledge_url, get_url)
        
        time.sleep(wait_time)
        get_url = "/fledge/audit?source=NTFSN"
        resp2 = utils.get_request(fledge_url, get_url)
        assert len(resp2['audit']) > len(resp1['audit']), "ERROR: NTFSN not triggered properly with asset code"
        
        time.sleep(wait_time)
        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        r = verify_eds_data()
        assert SOUTH_DP_NAME in r, "Data in EDS not found!"
        ts = r.get("Time")
        assert ts.find(datetime.now().strftime("%Y-%m-%d")) != -1, "Latest data not found in EDS!"
