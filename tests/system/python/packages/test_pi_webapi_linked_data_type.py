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
SOUTH_PLUGINS_LIST = ["sinusoid", "randomwalk"]
NORTH_INSTANCE_NAME = "NorthReadingsToPI_WebAPI"
# This  gives the path of directory where fledge is cloned. test_file < packages < python < system < tests < ROOT
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
SCRIPTS_DIR_ROOT = "{}/tests/system/python/scripts/package/".format(PROJECT_ROOT)
DATA_DIR_ROOT = "{}/tests/system/python/packages/data/".format(PROJECT_ROOT)
AF_HIERARCHY_LEVEL = '/testpilinkeddata/testpilinkeddatalvl2/testpilinkeddatalvl3'

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

def get_data_from_fledge(fledge_url):
    record = dict()
    get_url = "/fledge/asset/{}?limit=10000".format(ASSET)
    jdoc = utils.get_request(fledge_url, urllib.parse.quote(get_url, safe='?,=,&,/'))
    for plugin  in SOUTH_PLUGINS_LIST:
        record[plugin] = list(map(lambda val: val['reading'][plugin], filter(lambda item: list(item['reading'].keys())[0] == plugin, jdoc) ))
    return(record)

def verify_equality_between_fledge_and_pi(data_from_fledge, data_from_pi):
    matched = ""
    for plugin in SOUTH_PLUGINS_LIST:
        listA = sorted(data_from_fledge[plugin])
        listB = sorted(data_from_pi[plugin])
        print('Data from fledge for {} --> '.format(plugin), listA)
        print('Data from PI for {} --> '.format(plugin), listB)
        if listA == listB:
            matched = "Equal"
        else:
            matched = "Data of {} is unequal".format(plugin)
            break
    return(matched)

@pytest.fixture
def start_south_north(add_south, start_north_task_omf_web_api, add_filter, remove_data_file,
                      fledge_url, pi_host, pi_port, pi_admin, pi_passwd, pi_db,
                      start_north_omf_as_a_service, enable_schedule, 
                      clear_pi_system_through_pi_web_api, asset_name=ASSET):
    """ This fixture starts the sinusoid plugin and north pi web api plugin. Also puts a filter
        to insert reading id as a datapoint when we send the data to north.
        clean_setup_fledge_packages: purge the fledge* packages and install latest for given repo url
        add_south: Fixture that adds a south service with given configuration
        start_north_task_omf_web_api: Fixture that starts PI north task
        remove_data_file: Fixture that remove data file created during the tests """
        
    af_hierarchy_level_list = AF_HIERARCHY_LEVEL.split("/")
    poll_rate=1
    
    _config = {"assetName": {"value": "{}".format(ASSET)}}
    for south_plugin in SOUTH_PLUGINS_LIST:
        add_south(south_plugin, None, fledge_url, config=_config, 
                  service_name="{0}_{1}".format(ASSET, south_plugin), installation_type='package', start_service=False)
        time.sleep(10)
        
        data = {"readingsPerSec": "{}".format(poll_rate)}
        put_url="/fledge/category/{0}_{1}Advanced".format(ASSET, south_plugin)
        utils.put_request(fledge_url, urllib.parse.quote(put_url, safe='?,=,&,/'), data)
        
        enable_schedule(fledge_url, "{0}_{1}".format(ASSET, south_plugin))
        poll_rate+=5
    
    start_north_omf_as_a_service(fledge_url, pi_host, pi_port, pi_user=pi_admin, pi_pwd=pi_passwd, pi_use_legacy="false",
                                 service_name=NORTH_INSTANCE_NAME, default_af_location=AF_HIERARCHY_LEVEL)

class Test_linked_data_PIWebAPI:
    def test_linked_data(self, clean_setup_fledge_packages, reset_fledge, start_south_north, read_data_from_pi_web_api,
                             fledge_url, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries, pi_port, disable_schedule,
                             verify_hierarchy_and_get_datapoints_from_pi_web_api,clear_pi_system_through_pi_web_api, 
                             skip_verify_north_interface, asset_name=ASSET):
        
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
        
        time.sleep(wait_time)
        
        for south_plugin in SOUTH_PLUGINS_LIST:
            disable_schedule(fledge_url,"{}_{}".format(ASSET, south_plugin))
            
        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url)
        verify_statistics_map(fledge_url, skip_verify_north_interface)
        verify_asset_tracking_details(fledge_url, skip_verify_north_interface)
        
        # Checking if hierarchy created properly or not, and retrieveing data from PI Server
        data_from_pi = verify_hierarchy_and_get_datapoints_from_pi_web_api(pi_host, pi_admin, pi_passwd, pi_db, AF_HIERARCHY_LEVEL, ASSET, SOUTH_PLUGINS_LIST)
        assert len(data_from_pi) >= len(SOUTH_PLUGINS_LIST), "Datapoint does not exist"
        print('Data from PI Web API')
        print(data_from_pi)
        
        data_from_fledge = get_data_from_fledge(fledge_url)
        print('data fledge retrieved')
        print(data_from_fledge)
        
        # For verifying data send to PI Server from fledge is same.
        check_data = verify_equality_between_fledge_and_pi(data_from_fledge, data_from_pi)
        assert check_data == 'Equal', "Data is not equal"