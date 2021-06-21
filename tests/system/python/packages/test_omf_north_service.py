# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test OMF North Service System tests:
        Tests OMF as a north service along with reconfiguration.
"""

__author__ = "Yash Tatkondawar"
__copyright__ = "Copyright (c) 2021 Dianomic Systems, Inc."

import subprocess
import http.client
import json
import os
import time
import urllib.parse
from pathlib import Path
import pytest
import utils


south_plugin = "sinusoid"
south_asset_name = "sinusoid"
south_service_name="Sine #1"
north_plugin = "OMF"
north_service_name="NorthReadingsToPI_WebAPI"
north_schedule_id=""
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

    # Wait for fledge server to start
    time.sleep(wait_time)


@pytest.fixture
#def start_south_north(clean_setup_fledge_packages, add_south, start_north_pi_server_c_web_api_service, fledge_url, 
#                        pi_host, pi_port, pi_admin, pi_passwd):
def start_south_north(add_south, start_north_pi_server_c_web_api_service, fledge_url, 
                        pi_host, pi_port, pi_admin, pi_passwd):    
    global north_schedule_id
    
    add_south(south_plugin, None, fledge_url, service_name="{}".format(south_service_name), installation_type='package')
    
    response = start_north_pi_server_c_web_api_service(fledge_url, pi_host, pi_port, pi_user=pi_admin, pi_pwd=pi_passwd)
    north_schedule_id = response["id"]

    yield start_south_north


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
    assert 1 <= actual_stats_map[south_asset_name.upper()]
    assert 1 <= actual_stats_map['READINGS']
    if not skip_verify_north_interface:
        assert 1 <= actual_stats_map['Readings Sent']
        assert 1 <= actual_stats_map[north_service_name]


def verify_service_added(fledge_url):
    get_url = "/fledge/south"
    result = utils.get_request(fledge_url, get_url)
    assert len(result["services"])
    assert south_service_name in [s["name"] for s in result["services"]]
    
    get_url = "/fledge/service"
    result = utils.get_request(fledge_url, get_url)
    assert len(result["services"])
    assert south_service_name in [s["name"] for s in result["services"]]
    assert north_service_name in [s["name"] for s in result["services"]]


def verify_asset(fledge_url):
    get_url = "/fledge/asset"
    result = utils.get_request(fledge_url, get_url)
    assert len(result), "No asset found"
    assert south_asset_name in [s["assetCode"] for s in result]


def verify_asset_tracking_details(fledge_url):
    tracking_details = utils.get_asset_tracking_details(fledge_url, "Ingest")
    assert len(tracking_details["track"]), "Failed to track Ingest event"
    tracked_item = tracking_details["track"][0]
    assert south_service_name == tracked_item["service"]
    assert south_asset_name == tracked_item["asset"]
    assert south_asset_name == tracked_item["plugin"]

    egress_tracking_details = utils.get_asset_tracking_details(fledge_url, "Egress")
    assert len(egress_tracking_details["track"]), "Failed to track Egress event"
    tracked_item = egress_tracking_details["track"][0]
    assert north_service_name == tracked_item["service"]
    assert south_asset_name == tracked_item["asset"]
    assert north_plugin == tracked_item["plugin"]


class TestOMFNorthService:
    def test_omf_service_with_restart(self, reset_fledge, start_south_north, skip_verify_north_interface, fledge_url, wait_time, retries):
        """ Test OMF as a North service before and after restarting fledge.
            remove_and_add_pkgs: Fixture to remove and install latest fledge packages
            reset_fledge: Fixture to reset fledge
            start_south_north: Adds and configures south(sinusoid) and north(OMF) service
            Assertions:
                on endpoint GET /fledge/south
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/asset"""        
        
        # Wait until south and north services are created
        time.sleep(wait_time)
        
        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)        
        verify_asset(fledge_url)
        verify_service_added(fledge_url)        
        verify_statistics_map(fledge_url, skip_verify_north_interface)

        put_url = "/fledge/restart"
        utils.put_request(fledge_url, urllib.parse.quote(put_url))
        
        # Wait for fledge to restart
        time.sleep(wait_time * 2)

        old_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        
        # Wait for read and sent readings to increase
        time.sleep(wait_time)
        
        new_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        # Verifies whether Read and Sent readings are increasing after restart
        assert old_ping_result['dataRead'] < new_ping_result['dataRead']
        assert old_ping_result['dataSent'] < new_ping_result['dataSent']

    def test_omf_service_with_enable_disable(self, reset_fledge, start_south_north, skip_verify_north_interface, fledge_url, wait_time, retries):
        """ Test OMF as a North service by enabling and disabling it.
            remove_and_add_pkgs: Fixture to remove and install latest fledge packages
            reset_fledge: Fixture to reset fledge
            start_south_north: Adds and configures south(sinusoid) and north(OMF) service
            Assertions:
                on endpoint GET /fledge/south
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/asset"""                
        
        # Wait until south and north services are created
        time.sleep(wait_time)
        
        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)        
        verify_asset(fledge_url)
        verify_service_added(fledge_url)        
        verify_statistics_map(fledge_url, skip_verify_north_interface)
        
        data = {"enabled": "false"}
        put_url = "/fledge/schedule/{}".format(north_schedule_id)
        resp = utils.put_request(fledge_url, urllib.parse.quote(put_url), data)
        assert False == resp['schedule']['enabled']
        
        # Wait for service to disable
        time.sleep(wait_time)        
        
        data = {"enabled": "true"}
        put_url = "/fledge/schedule/{}".format(north_schedule_id)
        resp = utils.put_request(fledge_url, urllib.parse.quote(put_url), data)
        assert True == resp['schedule']['enabled']
        
        old_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        
        # Wait for read and sent readings to increase
        time.sleep(wait_time)
        
        new_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        # Verifies whether Read and Sent readings are increasing after disable/enable
        assert old_ping_result['dataRead'] < new_ping_result['dataRead']
        assert old_ping_result['dataSent'] < new_ping_result['dataSent']


    def test_omf_service_with_delete_add(self, reset_fledge, start_south_north, start_north_pi_server_c_web_api_service, skip_verify_north_interface, fledge_url, wait_time, retries, pi_host, pi_port, pi_admin, pi_passwd):
        """ Test OMF as a North service by deleting and adding north service.
            remove_and_add_pkgs: Fixture to remove and install latest fledge packages
            reset_fledge: Fixture to reset fledge
            start_south_north: Adds and configures south(sinusoid) and north(OMF) service
            Assertions:
                on endpoint GET /fledge/south
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/asset"""               
        
        global north_schedule_id
        
        # Wait until south and north services are created
        time.sleep(wait_time)
        
        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)        
        verify_asset(fledge_url)
        verify_service_added(fledge_url)        
        verify_statistics_map(fledge_url, skip_verify_north_interface)
        
        delete_url = "/fledge/service/{}".format(north_service_name)
        resp = utils.delete_request(fledge_url, delete_url)
        assert "Service {} deleted successfully.".format(north_service_name) == resp['result']
        
        # Wait for service to get deleted
        time.sleep(wait_time)
    
        response = start_north_pi_server_c_web_api_service(fledge_url, pi_host, pi_port, pi_user=pi_admin, pi_pwd=pi_passwd)
        north_schedule_id = response["id"]
        
        old_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        
        # Wait for read and sent readings to increase
        time.sleep(wait_time)
        
        new_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        # Verifies whether Read and Sent readings are increasing after delete/add of north service
        assert old_ping_result['dataRead'] < new_ping_result['dataRead']
        assert old_ping_result['dataSent'] < new_ping_result['dataSent']

    def test_omf_service_with_reconfig(self, reset_fledge, start_south_north, skip_verify_north_interface, fledge_url, wait_time, retries):
        """ Test OMF as a North service by reconfiguring it.
            remove_and_add_pkgs: Fixture to remove and install latest fledge packages
            reset_fledge: Fixture to reset fledge
            start_south_north: Adds and configures south(sinusoid) and north(OMF) service
            Assertions:
                on endpoint GET /fledge/south
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/asset"""                
        
        # Wait until south and north services are created
        time.sleep(wait_time)
        
        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)        
        verify_asset(fledge_url)
        verify_service_added(fledge_url)        
        verify_statistics_map(fledge_url, skip_verify_north_interface)
        
        # Good reconfiguration to check data is not sent
        data = {"SendFullStructure": "false"}
        put_url = "/fledge/category/{}".format(north_service_name)
        resp = utils.put_request(fledge_url, urllib.parse.quote(put_url), data)
        assert "false" == resp["SendFullStructure"]["value"]
        
        # Wait for service reconfiguration
        time.sleep(wait_time)        
        
        old_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        
        # Wait for read and sent readings to increase
        time.sleep(wait_time)
        
        new_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        # Verifies whether Read and Sent readings are increasing after delete/add of north service
        assert old_ping_result['dataRead'] < new_ping_result['dataRead']
        assert old_ping_result['dataSent'] < new_ping_result['dataSent']
        
        # Bad reconfiguration to check data is not sent
        data = {"PIWebAPIUserId": "Admin"}
        put_url = "/fledge/category/{}".format(north_service_name)
        resp = utils.put_request(fledge_url, urllib.parse.quote(put_url), data)
        assert "Admin" == resp["PIWebAPIUserId"]["value"]
        
        # Wait for service reconfiguration
        time.sleep(wait_time)        
        
        old_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        
        # Wait for read and sent readings to increase
        time.sleep(wait_time)
        
        new_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        # Verifies whether Read and Sent readings are increasing after delete/add of north service
        assert old_ping_result['dataRead'] < new_ping_result['dataRead']
        assert old_ping_result['dataSent'] == new_ping_result['dataSent']        
        