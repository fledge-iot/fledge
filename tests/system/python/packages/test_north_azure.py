# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test sending data to Azure-IoT-Hub using fledge-north-azure plugin

"""

__author__ = "Mohit Singh Tomar"
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
from azure.storage.blob import BlobServiceClient
import pandas as pd
import json

# This  gives the path of directory where fledge is cloned. test_file < packages < python < system < tests < ROOT
PROJECT_ROOT = subprocess.getoutput("git rev-parse --show-toplevel")
SCRIPTS_DIR_ROOT = "{}/tests/system/python/scripts/package/".format(PROJECT_ROOT)
SOUTH_SERVICE_NAME = "FOGL-7352_sysinfo"
SOUTH_PLUGIN = "systeminfo"
# ASSET = "FOGL-7352_system"
NORTH_SERVICE_NAME = "FOGL-7352_azure"
NORTH_PLUGIN_NAME = "azure-iot"
NORTH_PLUGIN_DISCOVERY_NAME = "azure_iot"
LOCALJSONFILE = "azure.json"

@pytest.fixture
def reset_fledge(wait_time):
    try:
        subprocess.run(["cd {} && ./reset"
                       .format(SCRIPTS_DIR_ROOT)], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "reset package script failed!"


def read_data_from_azure_storage_container(azure_storage_account_url,azure_storage_account_key, azure_storage_container):
    
    try:
        t1=time.time()
        blob_service_client_instance = BlobServiceClient(account_url=azure_storage_account_url, credential=azure_storage_account_key)

        container_client = blob_service_client_instance.get_container_client(container=azure_storage_container)

        blob_list = container_client.list_blobs()

        for blob in blob_list:
            BLOBNAME = blob.name
            print(f"Name: {blob.name}")


        blob_client_instance = blob_service_client_instance.get_blob_client(azure_storage_container, BLOBNAME, snapshot=None)
        with open(LOCALJSONFILE, "wb") as my_blob:
            blob_data = blob_client_instance.download_blob()
            blob_data.readinto(my_blob)
        t2=time.time()
        print(("It takes %s seconds to download "+BLOBNAME) % (t2 - t1))

        # {iothub}    /{partition}/{YYYY}/{MM}/{DD}/{HH}/{mm}  
        # foglamp-test/01        /2023  /04  /15  /20   /08.json
        # LOCALFILE is the file path
        # dataframe_blobdata = pd.read_csv(LOCALJSONFILE)
        # print('the size of the data is: %d rows and  %d columns' % dataframe_blobdata.shape)
        
        with open(LOCALJSONFILE) as handler:
            data = handler.readlines()
            
        print(data)
        return data
        
    except (Exception) as ex:
        print("Failed to read data due to {}".format(ex))
        return None
        

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

        assert 1 <= sent, "Failed to send data to Azure-IoT-Hub"
    return ping_result


def verify_statistics_map(fledge_url, skip_verify_north_interface):
    get_url = "/fledge/statistics"
    jdoc = utils.get_request(fledge_url, get_url)
    actual_stats_map = utils.serialize_stats_map(jdoc)
    assert 1 <= actual_stats_map["{}-Ingest".format(SOUTH_SERVICE_NAME)]
    assert 1 <= actual_stats_map['READINGS']
    if not skip_verify_north_interface:
        assert 1 <= actual_stats_map['Readings Sent']
        assert 1 <= actual_stats_map[NORTH_SERVICE_NAME]


def verify_asset(fledge_url, ASSET):
    get_url = "/fledge/asset"
    result = utils.get_request(fledge_url, get_url)
    assert len(result), "No asset found"
    assert any(filter(lambda x: ASSET in x, [s["assetCode"] for s in result]))


def verify_asset_tracking_details(fledge_url, skip_verify_north_interface, ASSET):
    tracking_details = utils.get_asset_tracking_details(fledge_url, "Ingest")
    assert len(tracking_details["track"]), "Failed to track Ingest event"
    tracked_item = tracking_details["track"][0]
    assert ASSET in tracked_item["asset"]
    assert "systeminfo" == tracked_item["plugin"]

    egress_tracking_details = utils.get_asset_tracking_details(fledge_url, "Egress")
    assert len(egress_tracking_details["track"]), "Failed to track Egress event"
    tracked_item = egress_tracking_details["track"][0]
    assert ASSET in tracked_item["asset"]
    assert NORTH_PLUGIN_DISCOVERY_NAME == tracked_item["plugin"]


def _verify_egress(azure_storage_account_url, azure_storage_account_key, azure_storage_container, wait_time, retries, ASSET):
    retry_count = 0
    data_from_azure = None
    
    while (data_from_azure is None or len(data_from_azure) == 0) and retry_count < retries:
        data_from_azure = read_data_from_azure_storage_container(azure_storage_account_url,azure_storage_account_key, azure_storage_container)

        # print(data_from_azure)
        if data_from_azure is None:
            retry_count += 1
            time.sleep(wait_time)
        
    if data_from_azure is None or retry_count == retries:
        assert False, "Failed to read data from Azure IoT Hub"
    
    asset_collected  = list()
    for ele in data_from_azure:
      asset_collected.extend(list(map(lambda d: d['asset'], json.loads(ele)["Body"])))
    
    assert any(filter(lambda x: ASSET in x, asset_collected))
    
@pytest.fixture
def add_south_north(add_south, add_north, fledge_url, azure_host, azure_device, azure_key):
    """ This fixture
        add_south: Fixture that adds a south service with given configuration
        add_north: Fixture that adds a north service with given configuration

    """
    # south_branch does not matter as these are archives.fledge-iot.org version install
    add_south(SOUTH_PLUGIN, None, fledge_url, service_name=SOUTH_SERVICE_NAME, start_service=False, installation_type='package')
    
    _config = {
        "primaryConnectionString": {"value":"HostName={};DeviceId={};SharedAccessKey={}".format(azure_host, azure_device, azure_key)}
        }
    # north_branch does not matter as these are archives.fledge-iot.org version install
    add_north(fledge_url, NORTH_PLUGIN_NAME, None, installation_type='package', north_instance_name=NORTH_SERVICE_NAME, 
              config=_config, enabled=False, plugin_discovery_name=NORTH_PLUGIN_DISCOVERY_NAME, is_task=False)
    
def config_south(fledge_url, ASSET):
    payload = {"assetNamePrefix": "{}".format(ASSET)}
    put_url = "/fledge/category/{}".format(SOUTH_SERVICE_NAME)
    utils.put_request(fledge_url, urllib.parse.quote(put_url), payload)

class TestNorthAzureIoTHubDevicePlugin:
    
    def test_send(self, clean_setup_fledge_packages, reset_fledge, add_south_north, fledge_url, enable_schedule, 
                  disable_schedule, azure_host, azure_device, azure_key, wait_time, retries, skip_verify_north_interface,
                  azure_storage_account_url, azure_storage_account_key, azure_storage_container):
        
        """ Test that check data is inserted in Fledge and sent to Azure-IoT Hub.
            clean_setup_fledge_packages: Fixture for removing fledge from system completely if it is already present 
                                         and reinstall it baased on commandline arguments.
            reset_fledge: Fixture that reset and cleanup the fledge 
            add_south_north: Fixture that add south and north instance in disable mode
            enable_schedule: Fixture for enabling schedules or services
            disable_schedule: Fixture for disabling schedules or services
            
        """
        # Update Asset name
        ASSET = "test1_FOGL-7352_system"
        config_south(fledge_url, ASSET)
        
        # Enable South Service for 30 Seonds
        enable_schedule(fledge_url, SOUTH_SERVICE_NAME)
        time.sleep(wait_time * 3)
        disable_schedule(fledge_url, SOUTH_SERVICE_NAME)
        
        # Enable North Service for sending data to Azure-IOT-Hub
        enable_schedule(fledge_url, NORTH_SERVICE_NAME)
        
        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url, ASSET)
        verify_statistics_map(fledge_url, skip_verify_north_interface)
        verify_asset_tracking_details(fledge_url, skip_verify_north_interface, ASSET)
        
        # Azure Iot Hub take 130 seconds to show the data sents to it
        time.sleep(130)
        
        if not skip_verify_north_interface:
            _verify_egress(azure_storage_account_url, azure_storage_account_key, azure_storage_container, wait_time, retries, ASSET)

    def test_mqtt_over_websocket_reconfig(self, reset_fledge, add_south_north, fledge_url, enable_schedule, disable_schedule,
                                          azure_host, azure_device, azure_key, azure_storage_account_url, azure_storage_account_key, 
                                          azure_storage_container, wait_time, retries, skip_verify_north_interface):
        # Update Asset name
        ASSET = "test2_FOGL-7352_system"
        config_south(fledge_url, ASSET)
        
        # Enable South Service for 10 Seonds
        enable_schedule(fledge_url, SOUTH_SERVICE_NAME)
        time.sleep(wait_time)
        disable_schedule(fledge_url, SOUTH_SERVICE_NAME)
        
        # Enable MQTT over websocket
        payload = {"websockets": "true"}
        put_url = "/fledge/category/{}".format(NORTH_SERVICE_NAME)
        utils.put_request(fledge_url, urllib.parse.quote(put_url), payload)
        
        # Enable North Service for sending data to Azure-IOT-Hub
        enable_schedule(fledge_url, NORTH_SERVICE_NAME)
        
        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url, ASSET)
        verify_statistics_map(fledge_url, skip_verify_north_interface)
        verify_asset_tracking_details(fledge_url, skip_verify_north_interface, ASSET)
        
        # Azure Iot Hub take 130 seconds to show the data sents to it
        time.sleep(130)
        
        if not skip_verify_north_interface:
            _verify_egress(azure_storage_account_url, azure_storage_account_key, azure_storage_container, wait_time, retries, ASSET)
