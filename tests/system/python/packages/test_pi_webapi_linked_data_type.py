# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test sending data to PI using Web API

"""

__author__ = "Mohit Singh Tomar"
__copyright__ = "Copyright (c) 2019 Dianomic Systems Inc"
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
import base64
import ssl
import csv

from pprint import pprint

ASSET = "FOGL-7303"
ASSET_DICT = {ASSET: ['sinusoid', 'randomwalk', 'sinusoid_exp', 'randomwalk_exp']}
SOUTH_PLUGINS_LIST = ["sinusoid", "randomwalk"]
NORTH_INSTANCE_NAME = "NorthReadingsToPI_WebAPI"
FILTER = "expression"
print("Asset Dict -->", ASSET_DICT) 
# This  gives the path of directory where fledge is cloned. test_file < packages < python < system < tests < ROOT
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
SCRIPTS_DIR_ROOT = "{}/tests/system/python/scripts/package/".format(PROJECT_ROOT)
DATA_DIR_ROOT = "{}/tests/system/python/packages/data/".format(PROJECT_ROOT)
AF_HIERARCHY_LEVEL = '/testpilinkeddata/testpilinkeddatalvl2/testpilinkeddatalvl3'
AF_HIERARCHY_LEVEL_LIST = AF_HIERARCHY_LEVEL.split("/")[1:]
print('AF HEIR -->', AF_HIERARCHY_LEVEL_LIST)

@pytest.fixture
def reset_fledge(wait_time):
    try:
        subprocess.run(["cd {} && ./reset".format(SCRIPTS_DIR_ROOT)], shell=True, check=True)
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

def verify_asset(fledge_url):
    get_url = "/fledge/asset"
    result = utils.get_request(fledge_url, get_url)
    assert len(result), "No asset found"
    assert ASSET in [s["assetCode"] for s in result]
    
def verify_statistics_map(fledge_url, skip_verify_north_interface):
    get_url = "/fledge/statistics"
    jdoc = utils.get_request(fledge_url, get_url)
    actual_stats_map = utils.serialize_stats_map(jdoc)
    assert 1 <= actual_stats_map[ASSET.upper()]
    assert 1 <= actual_stats_map['READINGS']
    if not skip_verify_north_interface:
        assert 1 <= actual_stats_map['Readings Sent']
        assert 1 <= actual_stats_map[NORTH_INSTANCE_NAME]
        
def verify_asset_tracking_details(fledge_url, skip_verify_north_interface):
    tracking_details = utils.get_asset_tracking_details(fledge_url, "Ingest")
    assert len(tracking_details["track"]), "Failed to track Ingest event"
    for item in tracking_details["track"]:
        tracked_item= item
        assert ASSET == tracked_item["asset"]
        assert tracked_item["plugin"].lower() in SOUTH_PLUGINS_LIST

    if not skip_verify_north_interface:
        egress_tracking_details = utils.get_asset_tracking_details(fledge_url, "Egress")
        assert len(egress_tracking_details["track"]), "Failed to track Egress event"
        tracked_item = egress_tracking_details["track"][0]
        assert ASSET == tracked_item["asset"]
        assert "OMF" == tracked_item["plugin"]

def get_data_from_fledge(fledge_url, PLUGINS_LIST):
    record = dict()
    get_url = "/fledge/asset/{}?limit=10000".format(ASSET)
    jdoc = utils.get_request(fledge_url, urllib.parse.quote(get_url, safe='?,=,&,/'))
    for plugin  in PLUGINS_LIST:
        record[plugin] = list(map(lambda val: val['reading'][plugin], filter(lambda item: (len(item['reading'].keys())==1 and list(item['reading'].keys())[0] == plugin) or (len(item['reading'].keys())==2 and (plugin in list(item['reading'].keys()))), jdoc) ))
    return(record)

def verify_equality_between_fledge_and_pi(data_from_fledge, data_from_pi, PLUGINS_LIST):
    matched = ""
    for plugin in PLUGINS_LIST:
        listA = sorted(data_from_fledge[plugin])
        listB = sorted(data_from_pi[plugin])
        if listA == listB:
            matched = "Equal"
        else:
            matched = "Data of {} is unequal".format(plugin)
            break
    return(matched)

def verify_filter_added(fledge_url):
    get_url = "/fledge/filter"
    result = utils.get_request(fledge_url, get_url)["filters"]
    assert len(result)
    list_of_filters = list(map(lambda val: val['name'], result))
    for plugin in SOUTH_PLUGINS_LIST:
        assert "{}_exp".format(plugin) in list_of_filters

def verify_service_added(fledge_url, ):
    get_url = "/fledge/south"
    result = utils.get_request(fledge_url, urllib.parse.quote(get_url, safe='?,=,&,/'))['services']
    assert len(result)
    list_of_southbounds = list(map(lambda val: val['name'], result))
    for plugin in SOUTH_PLUGINS_LIST:
        assert "{}_{}".format(ASSET, plugin) in list_of_southbounds

    get_url = "/fledge/north"
    result = utils.get_request(fledge_url, get_url)
    assert len(result)
    list_of_northbounds = list(map(lambda val: val['name'], result))
    assert NORTH_INSTANCE_NAME in list_of_northbounds

    get_url = "/fledge/service"
    result = utils.get_request(fledge_url, urllib.parse.quote(get_url, safe='?,=,&,/'))['services']
    assert len(result)
    list_of_services = list(map(lambda val: val['name'], result))
    for plugin in SOUTH_PLUGINS_LIST:
        assert "{}_{}".format(ASSET, plugin) in list_of_services
    assert NORTH_INSTANCE_NAME in list_of_services

def verify_data_between_fledge_and_piwebapi(fledge_url, pi_host, pi_admin, pi_passwd, pi_db, AF_HIERARCHY_LEVEL, ASSET, PLUGINS_LIST, verify_hierarchy_and_get_datapoints_from_pi_web_api, wait_time):
    # Wait until All data loaded to PI server properly
    time.sleep(wait_time)
    # Checking if hierarchy created properly or not, and retrieveing data from PI Server
    data_from_pi = verify_hierarchy_and_get_datapoints_from_pi_web_api(pi_host, pi_admin, pi_passwd, pi_db, AF_HIERARCHY_LEVEL, ASSET, ASSET_DICT[ASSET])
    assert len(data_from_pi) > 0, "Datapoint does not exist"
    print('Data from PI Web API')
    print(data_from_pi)
    # Getting Data from fledge
    data_from_fledge = dict()
    data_from_fledge = get_data_from_fledge(fledge_url, PLUGINS_LIST)
    print('data fledge retrieved')
    print(data_from_fledge)
    
    # For verifying data send to PI Server from fledge is same.
    check_data = verify_equality_between_fledge_and_pi(data_from_fledge, data_from_pi, PLUGINS_LIST)
    assert check_data == 'Equal', "Data is not equal"

def add_configure_filter(add_filter, fledge_url, south_plugin):
    filter_cfg = {"enable": "true", "expression": "log({})".format(south_plugin), "name": "{}_exp".format(south_plugin)}
    add_filter("expression", None, "{}_exp".format(south_plugin), filter_cfg, fledge_url, "{}_{}".format(ASSET, south_plugin), installation_type='package')

@pytest.fixture
def start_south_north(add_south, start_north_task_omf_web_api, add_filter, remove_data_file,
                      fledge_url, pi_host, pi_port, pi_admin, pi_passwd, pi_db,
                      start_north_omf_as_a_service, enable_schedule, asset_name=ASSET):
    """ This fixture starts the sinusoid plugin and north pi web api plugin. Also puts a filter
        to insert reading id as a datapoint when we send the data to north.
        clean_setup_fledge_packages: purge the fledge* packages and install latest for given repo url
        add_south: Fixture that adds a south service with given configuration
        start_north_task_omf_web_api: Fixture that starts PI north task
        remove_data_file: Fixture that remove data file created during the tests """
    
    poll_rate=1
    
    _config = {"assetName": {"value": "{}".format(ASSET)}}
    for south_plugin in SOUTH_PLUGINS_LIST:
        add_south(south_plugin, None, fledge_url, config=_config, 
                  service_name="{0}_{1}".format(ASSET, south_plugin), installation_type='package', start_service=False)
        time.sleep(10)
        
        data = {"readingsPerSec": "{}".format(poll_rate)}
        put_url="/fledge/category/{0}_{1}Advanced".format(ASSET, south_plugin)
        utils.put_request(fledge_url, urllib.parse.quote(put_url, safe='?,=,&,/'), data)
        
        poll_rate+=5
    
    start_north_omf_as_a_service(fledge_url, pi_host, pi_port, pi_user=pi_admin, pi_pwd=pi_passwd, pi_use_legacy="false",
                                 service_name=NORTH_INSTANCE_NAME, default_af_location=AF_HIERARCHY_LEVEL)

class Test_linked_data_PIWebAPI:
    # @pytest.mark.skip(reason="no way of currently testing this")
    def test_linked_data(self, clean_setup_fledge_packages, reset_fledge, start_south_north, fledge_url, 
                         pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries, pi_port, enable_schedule, disable_schedule, 
                         verify_hierarchy_and_get_datapoints_from_pi_web_api, clear_pi_system_through_pi_web_api, 
                         skip_verify_north_interface, asset_name=ASSET):
        
        """ Test that check data is inserted in Fledge and sent to PI are equal
            clean_setup_fledge_packages: Fixture for removing fledge from system completely if it is already present 
                                         and reinstall it baased on commandline arguments.
            reset_fledge: Fixture that reset and cleanup the fledge 
            start_south_north: Fixture that add south and north instance
            enable_schedule: Fixture for enabling schedules or services
            disable_schedule: Fixture for disabling schedules or services
            verify_hierarchy_and_get_datapoints_from_pi_web_api: Fixture to read data from PI and Verify hierarchy
            clear_pi_system_through_pi_web_api: Fixture for cleaning up PI Server
            skip_verify_north_interface: Flag for assertion of data using PI web API
            
            Assertions:
                on endpoint GET /fledge/statistics
                on endpoint GET /fledge/service
                on endpoint GET /fledge/asset/<asset_name>
                data received from PI is same as data sent"""

        clear_pi_system_through_pi_web_api(pi_host, pi_admin, pi_passwd, pi_db, AF_HIERARCHY_LEVEL_LIST, ASSET_DICT)
        
        for south_plugin in SOUTH_PLUGINS_LIST:
            enable_schedule(fledge_url, "{0}_{1}".format(ASSET, south_plugin))
        
        # Wait until south, north services are created and some data is loaded
        time.sleep(wait_time)
        
        for south_plugin in SOUTH_PLUGINS_LIST:
            disable_schedule(fledge_url,"{}_{}".format(ASSET, south_plugin))
            
        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_service_added(fledge_url)
        verify_asset(fledge_url)
        verify_statistics_map(fledge_url, skip_verify_north_interface)
        verify_asset_tracking_details(fledge_url, skip_verify_north_interface)
        
        # Verify Data from fledge sent to PI Server is same.
        verify_data_between_fledge_and_piwebapi(fledge_url, pi_host, pi_admin, pi_passwd, pi_db, AF_HIERARCHY_LEVEL, ASSET, SOUTH_PLUGINS_LIST, verify_hierarchy_and_get_datapoints_from_pi_web_api, wait_time)
    
    # @pytest.mark.skip(reason="no way of currently testing this")
    def test_linked_data_with_reconfig(self, reset_fledge, start_south_north, fledge_url, pi_host, pi_admin, pi_passwd, add_filter, pi_db, wait_time, 
                                       retries, pi_port, enable_schedule, disable_schedule, verify_hierarchy_and_get_datapoints_from_pi_web_api, 
                                       clear_pi_system_through_pi_web_api, skip_verify_north_interface, asset_name=ASSET):
                
        """ Test that apply filter and check data is inserted in Fledge and sent to PI are equal.
            reset_fledge: Fixture that reset and cleanup the fledge 
            start_south_north: Fixture that add south and north instance
            add_filter: Fixture that adds filter to the Services
            enable_schedule: Fixture for enabling schedules or services
            disable_schedule: Fixture for disabling schedules or services
            verify_hierarchy_and_get_datapoints_from_pi_web_api: Fixture to read data from PI and Verify hierarchy
            clear_pi_system_through_pi_web_api: Fixture for cleaning up PI Server
            skip_verify_north_interface: Flag for assertion of data using PI web API
            
            Assertions:
                on endpoint GET /fledge/statistics
                on endpoint GET /fledge/service
                on endpoint GET /fledge/asset/<asset_name>
                on endpoint GET /fledge/filter
                data received from PI is same as data sent"""
        
        clear_pi_system_through_pi_web_api(pi_host, pi_admin, pi_passwd, pi_db, AF_HIERARCHY_LEVEL_LIST, ASSET_DICT)
        
        for south_plugin in SOUTH_PLUGINS_LIST:
            add_configure_filter(add_filter, fledge_url, south_plugin)
            enable_schedule(fledge_url, "{0}_{1}".format(ASSET, south_plugin))
            
        # Wait until south, north services and filters are created and some data is loaded
        time.sleep(wait_time)
        
        for south_plugin in SOUTH_PLUGINS_LIST:
            disable_schedule(fledge_url,"{}_{}".format(ASSET, south_plugin))
        
        verify_asset(fledge_url)
        verify_service_added(fledge_url)
        verify_statistics_map(fledge_url, skip_verify_north_interface)
        verify_asset_tracking_details(fledge_url, skip_verify_north_interface)
        verify_filter_added(fledge_url)

        # Verify Data from fledge sent to PI Server is same.
        verify_data_between_fledge_and_piwebapi(fledge_url, pi_host, pi_admin, pi_passwd, pi_db, AF_HIERARCHY_LEVEL, ASSET, ASSET_DICT[ASSET], verify_hierarchy_and_get_datapoints_from_pi_web_api, wait_time)