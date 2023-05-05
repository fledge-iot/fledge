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
import json
import sys
import datetime

try:
    subprocess.run(["python3 -m pip install azure-storage-blob==12.13.1"], shell=True, check=True)
except subprocess.CalledProcessError:
    assert False, "Failed to install azure-storage-blob module"

from azure.storage.blob import BlobServiceClient

# This  gives the path of directory where fledge is cloned. test_file < packages < python < system < tests < ROOT
PROJECT_ROOT = subprocess.getoutput("git rev-parse --show-toplevel")
SCRIPTS_DIR_ROOT = "{}/tests/system/python/scripts/package/".format(PROJECT_ROOT)
SOUTH_SERVICE_NAME = "FOGL-7352_sysinfo"
SOUTH_PLUGIN = "systeminfo"
NORTH_SERVICE_NAME = "FOGL-7352_azure"
NORTH_PLUGIN_NAME = "azure-iot"
NORTH_PLUGIN_DISCOVERY_NAME = "azure_iot"
LOCALJSONFILE = "azure.json"
FILTER = "expression"

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
        
        with open(LOCALJSONFILE) as handler:
            data = handler.readlines()
            
        return data
        
    except (Exception) as ex:
        print("Failed to read data due to {}".format(ex))
        return None

def verify_north_stats_on_invalid_config(fledge_url):
    get_url = "/fledge/ping"
    ping_result = utils.get_request(fledge_url, get_url)
    assert "dataRead" in ping_result
    assert ping_result['dataRead'] > 0, "South data NOT seen in ping header"
    assert "dataSent" in ping_result
    assert ping_result['dataSent'] < 1, "Data sent to Azure Iot Hub"

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
def add_south_north_task(add_south, add_north, fledge_url, azure_host, azure_device, azure_key):
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
              config=_config, schedule_repeat_time=10, enabled=False, plugin_discovery_name=NORTH_PLUGIN_DISCOVERY_NAME, is_task=True)
    
@pytest.fixture
def add_south_north_service(add_south, add_north, fledge_url, azure_host, azure_device, azure_key):
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

def update_filter_config(fledge_url, plugin, mode):
    data = {"enable": "{}".format(mode)}
    put_url = "/fledge/category/{}_{}_exp".format(NORTH_SERVICE_NAME, plugin)
    utils.put_request(fledge_url, urllib.parse.quote(put_url, safe='?,=,&,/'), data)

def add_expression_filter(add_filter, fledge_url, NORTH_PLUGIN_NAME):
    filter_cfg = {"enable": "true", "expression": "log(1K-blocks)".format(), "name": "{}_exp".format(NORTH_PLUGIN_NAME)}
    add_filter("{}".format(FILTER), None, "{}_exp".format(NORTH_PLUGIN_NAME), filter_cfg, fledge_url, "{}".format(NORTH_SERVICE_NAME), installation_type='package')

class TestNorthAzureIoTHubDevicePlugin:
    
    def test_send(self, clean_setup_fledge_packages, reset_fledge, add_south_north_service, fledge_url, enable_schedule, 
                  disable_schedule, azure_host, azure_device, azure_key, wait_time, retries, skip_verify_north_interface,
                  azure_storage_account_url, azure_storage_account_key, azure_storage_container):
        
        """ Test that check data is inserted in Fledge and sent to Azure-IoT Hub or not.
            clean_setup_fledge_packages: Fixture for removing fledge from system completely if it is already present 
                                         and reinstall it baased on commandline arguments.
            reset_fledge: Fixture that reset and cleanup the fledge 
            add_south_north_service: Fixture that add south and north instance in disable mode
            enable_schedule: Fixture for enabling schedules or services
            disable_schedule: Fixture for disabling schedules or services
            azure_host: Fixture that provide Hostname of Azure IoT Hub
            azure_device: Fixture that provide ID of Device deployed in Azure IoT Hub
            azure_key: Fixture that provide access key of Azure IoT Hub
            azure_storage_account_url: Fixture that provide URL for accessing Storage Blob of Azure
            azure_storage_account_key: Fixture that provide access key for accessing Storage Blob
            azure_storage_container: Fixture that provides name of container deployed in Azure
        """
        # Update Asset name
        ASSET = "test1_FOGL-7352_system"
        config_south(fledge_url, ASSET)
        
        # Enable South Service for 10 Seonds
        enable_schedule(fledge_url, SOUTH_SERVICE_NAME)
        time.sleep(wait_time)
        disable_schedule(fledge_url, SOUTH_SERVICE_NAME)
        
        # Enable North Service for sending data to Azure-IOT-Hub
        enable_schedule(fledge_url, NORTH_SERVICE_NAME)
        
        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url, ASSET)
        verify_statistics_map(fledge_url, skip_verify_north_interface)
        verify_asset_tracking_details(fledge_url, skip_verify_north_interface, ASSET)
        
        # Storage blob JSON will be created every 2 minutes
        time.sleep(150)
        
        
        _verify_egress(azure_storage_account_url, azure_storage_account_key, azure_storage_container, wait_time, retries, ASSET)

    
    def test_mqtt_over_websocket_reconfig(self, reset_fledge, add_south_north_service, fledge_url, enable_schedule, disable_schedule,
                                          azure_host, azure_device, azure_key, azure_storage_account_url, azure_storage_account_key, 
                                          azure_storage_container, wait_time, retries, skip_verify_north_interface):
        
        """ Test that enable MQTT over websocket then check data inserted into Fledge and sent to Azure-IoT Hub or not.
            
            reset_fledge: Fixture that reset and cleanup the fledge 
            add_south_north_service: Fixture that add south and north instance in disable mode
            enable_schedule: Fixture for enabling schedules or services
            disable_schedule: Fixture for disabling schedules or services
            azure_host: Fixture that provide Hostname of Azure IoT Hub
            azure_device: Fixture that provide ID of Device deployed in Azure IoT Hub
            azure_key: Fixture that provide access key of Azure IoT Hub
            azure_storage_account_url: Fixture that provide URL for accessing Storage Blob of Azure
            azure_storage_account_key: Fixture that provide access key for accessing Storage Blob
            azure_storage_container: Fixture that provides name of container deployed in Azure
        """
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
        
        # Storage blob JSON will be created every 2 minutes
        time.sleep(150)
        
        
        _verify_egress(azure_storage_account_url, azure_storage_account_key, azure_storage_container, wait_time, retries, ASSET)

    
    def test_disable_enable(self, reset_fledge, add_south_north_service, fledge_url, enable_schedule, disable_schedule,
                            azure_host, azure_device, azure_key, azure_storage_account_url, azure_storage_account_key, 
                            azure_storage_container, wait_time, retries, skip_verify_north_interface):
        
        """ Test that enable and disable south and north service perioically then 
            check data inserted into Fledge and sent to Azure-IoT Hub or not.
            
            reset_fledge: Fixture that reset and cleanup the fledge 
            add_south_north_service: Fixture that add south and north instance in disable mode
            enable_schedule: Fixture for enabling schedules or services
            disable_schedule: Fixture for disabling schedules or services
            azure_host: Fixture that provide Hostname of Azure IoT Hub
            azure_device: Fixture that provide ID of Device deployed in Azure IoT Hub
            azure_key: Fixture that provide access key of Azure IoT Hub
            azure_storage_account_url: Fixture that provide URL for accessing Storage Blob of Azure
            azure_storage_account_key: Fixture that provide access key for accessing Storage Blob
            azure_storage_container: Fixture that provides name of container deployed in Azure
        """
        
        for i in range(2):
            # Update Asset name
            ASSET = "test3.{}_FOGL-7352_system".format(i)
            config_south(fledge_url, ASSET)
            
            # Enable South Service for 10 Seonds
            enable_schedule(fledge_url, SOUTH_SERVICE_NAME)
            time.sleep(wait_time)
            disable_schedule(fledge_url, SOUTH_SERVICE_NAME)
            
            # Enable North Service for sending data to Azure-IOT-Hub
            enable_schedule(fledge_url, NORTH_SERVICE_NAME)
            
            verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
            verify_asset(fledge_url, ASSET)
            verify_statistics_map(fledge_url, skip_verify_north_interface)
            
            # Storage blob JSON will be created every 2 minutes
            time.sleep(150)
            disable_schedule(fledge_url, NORTH_SERVICE_NAME)
            
            _verify_egress(azure_storage_account_url, azure_storage_account_key, azure_storage_container, wait_time, retries, ASSET)
    
       
    def test_send_with_filter(self, reset_fledge, add_south_north_service, fledge_url, enable_schedule, disable_schedule,
                              azure_host, azure_device, azure_key, azure_storage_account_url, azure_storage_account_key, 
                              azure_storage_container, wait_time, retries, skip_verify_north_interface, add_filter):
        
        """ Test that attach filters to North service and enable and disable filter periodically 
            then check data inserted into Fledge and sent to Azure-IoT Hub or not.
            
            reset_fledge: Fixture that reset and cleanup the fledge 
            add_south_north_service: Fixture that add south and north instance in disable mode
            enable_schedule: Fixture for enabling schedules or services
            disable_schedule: Fixture for disabling schedules or services
            azure_host: Fixture that provide Hostname of Azure IoT Hub
            azure_device: Fixture that provide ID of Device deployed in Azure IoT Hub
            azure_key: Fixture that provide access key of Azure IoT Hub
            azure_storage_account_url: Fixture that provide URL for accessing Storage Blob of Azure
            azure_storage_account_key: Fixture that provide access key for accessing Storage Blob
            azure_storage_container: Fixture that provides name of container deployed in Azure
            add_filter:Fixture that add filter to south and north Instances
        """
        # Update Asset name
        ASSET = "test4_FOGL-7352_system"
        config_south(fledge_url, ASSET)
        
        # Add Expression filter to North Service
        add_expression_filter(add_filter, fledge_url, NORTH_PLUGIN_NAME)
        
        # Enable South Service for 10 Seonds
        enable_schedule(fledge_url, SOUTH_SERVICE_NAME)
        
        # Enable North Service for sending data to Azure-IOT-Hub
        enable_schedule(fledge_url, NORTH_SERVICE_NAME)
        
        print("On/Off of filter starts")
        count = 0
        while count<3:
            # For Disabling filter
            update_filter_config(fledge_url, NORTH_PLUGIN_NAME, 'false')
            time.sleep(wait_time*2)
            
            # For enabling filter
            update_filter_config(fledge_url, NORTH_PLUGIN_NAME, 'true')
            time.sleep(wait_time*2)
            count+=1
        
        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url, ASSET)
        verify_statistics_map(fledge_url, skip_verify_north_interface)
        verify_asset_tracking_details(fledge_url, skip_verify_north_interface, ASSET)
        
        # Storage blob JSON will be created every 2 minutes
        time.sleep(150)
        
        
        _verify_egress(azure_storage_account_url, azure_storage_account_key, azure_storage_container, wait_time, retries, ASSET)


class TestNorthAzureIoTHubDevicePluginTask:
        
    def test_send_as_a_task(self, reset_fledge, add_south_north_task, fledge_url, enable_schedule, disable_schedule, 
                            azure_host, azure_device, azure_key, azure_storage_account_url, azure_storage_account_key, 
                            azure_storage_container, wait_time, retries, skip_verify_north_interface):
        
        """ Test that creates south and north bound as task and check data is inserted in Fledge and sent to Azure-IoT Hub or not.
            
            reset_fledge: Fixture that reset and cleanup the fledge 
            add_south_north_task: Fixture that add south and north instance in disable mode
            enable_schedule: Fixture for enabling schedules or services
            disable_schedule: Fixture for disabling schedules or services
            azure_host: Fixture that provide Hostname of Azure IoT Hub
            azure_device: Fixture that provide ID of Device deployed in Azure IoT Hub
            azure_key: Fixture that provide access key of Azure IoT Hub
            azure_storage_account_url: Fixture that provide URL for accessing Storage Blob of Azure
            azure_storage_account_key: Fixture that provide access key for accessing Storage Blob
            azure_storage_container: Fixture that provides name of container deployed in Azure
        """
        # Update Asset name
        ASSET = "test5_FOGL-7352_system"
        config_south(fledge_url, ASSET)
        
        # Enable South Service for 10 Seonds
        enable_schedule(fledge_url, SOUTH_SERVICE_NAME)
        time.sleep(wait_time)
        disable_schedule(fledge_url, SOUTH_SERVICE_NAME)
        
        # Enable North Service for sending data to Azure-IOT-Hub
        enable_schedule(fledge_url, NORTH_SERVICE_NAME)
        
        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url, ASSET)
        verify_statistics_map(fledge_url, skip_verify_north_interface)
        verify_asset_tracking_details(fledge_url, skip_verify_north_interface, ASSET)
        
        # Storage blob JSON will be created every 2 minutes
        time.sleep(150)
        
        
        _verify_egress(azure_storage_account_url, azure_storage_account_key, azure_storage_container, wait_time, retries, ASSET)
    
    
    def test_mqtt_over_websocket_reconfig_task(self, reset_fledge, add_south_north_task, fledge_url, enable_schedule, disable_schedule,
                                               azure_host, azure_device, azure_key, azure_storage_account_url, azure_storage_account_key, 
                                               azure_storage_container, wait_time, retries, skip_verify_north_interface):
        
        """ Test that creates south and north bound as task as well as enable MQTT over websocket then
            check data inserted in Fledge and sent to Azure-IoT Hub or not.
            
            reset_fledge: Fixture that reset and cleanup the fledge 
            add_south_north_task: Fixture that add south and north instance in disable mode
            enable_schedule: Fixture for enabling schedules or services
            disable_schedule: Fixture for disabling schedules or services
            azure_host: Fixture that provide Hostname of Azure IoT Hub
            azure_device: Fixture that provide ID of Device deployed in Azure IoT Hub
            azure_key: Fixture that provide access key of Azure IoT Hub
            azure_storage_account_url: Fixture that provide URL for accessing Storage Blob of Azure
            azure_storage_account_key: Fixture that provide access key for accessing Storage Blob
            azure_storage_container: Fixture that provides name of container deployed in Azure
        """
        # Update Asset name
        ASSET = "test6_FOGL-7352_system"
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
        
        # Storage blob JSON will be created every 2 minutes
        time.sleep(150)
        
        
        _verify_egress(azure_storage_account_url, azure_storage_account_key, azure_storage_container, wait_time, retries, ASSET)

    
    def test_disable_enable_task(self, reset_fledge, add_south_north_task, fledge_url, enable_schedule, disable_schedule,
                                 azure_host, azure_device, azure_key, azure_storage_account_url, azure_storage_account_key, 
                                 azure_storage_container, wait_time, retries, skip_verify_north_interface):
        
        """ Test that creates south and north bound as task as enable and disable them periodically then 
            check data inserted in Fledge and sent to Azure-IoT Hub or not.
            
            reset_fledge: Fixture that reset and cleanup the fledge 
            add_south_north_task: Fixture that add south and north instance in disable mode
            enable_schedule: Fixture for enabling schedules or services
            disable_schedule: Fixture for disabling schedules or services
            azure_host: Fixture that provide Hostname of Azure IoT Hub
            azure_device: Fixture that provide ID of Device deployed in Azure IoT Hub
            azure_key: Fixture that provide access key of Azure IoT Hub
            azure_storage_account_url: Fixture that provide URL for accessing Storage Blob of Azure
            azure_storage_account_key: Fixture that provide access key for accessing Storage Blob
            azure_storage_container: Fixture that provides name of container deployed in Azure
        """
        for i in range(2):
            # Update Asset name
            ASSET = "test7.{}_FOGL-7352_system".format(i)
            config_south(fledge_url, ASSET)
            
            # Enable South Service for 10 Seonds
            enable_schedule(fledge_url, SOUTH_SERVICE_NAME)
            time.sleep(wait_time)
            disable_schedule(fledge_url, SOUTH_SERVICE_NAME)
            
            # Enable North Service for sending data to Azure-IOT-Hub
            enable_schedule(fledge_url, NORTH_SERVICE_NAME)
            
            verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
            verify_asset(fledge_url, ASSET)
            verify_statistics_map(fledge_url, skip_verify_north_interface)
            
            # Storage blob JSON will be created every 2 minutes
            time.sleep(150)
            disable_schedule(fledge_url, NORTH_SERVICE_NAME)
            
            _verify_egress(azure_storage_account_url, azure_storage_account_key, azure_storage_container, wait_time, retries, ASSET)
                
    def test_send_with_filter_task(self, reset_fledge, add_south_north_task, fledge_url, enable_schedule, disable_schedule,
                                   azure_host, azure_device, azure_key, azure_storage_account_url, azure_storage_account_key, 
                                   azure_storage_container, wait_time, retries, skip_verify_north_interface, add_filter):
        
        """ Test that creates south and north bound as task and attach filters to North Bound as well as
            enable and disable filters periodically then check data inserted in Fledge and sent to Azure-IoT Hub or not.
            
            reset_fledge: Fixture that reset and cleanup the fledge 
            add_south_north_task: Fixture that add south and north instance in disable mode
            enable_schedule: Fixture for enabling schedules or services
            disable_schedule: Fixture for disabling schedules or services
            azure_host: Fixture that provide Hostname of Azure IoT Hub
            azure_device: Fixture that provide ID of Device deployed in Azure IoT Hub
            azure_key: Fixture that provide access key of Azure IoT Hub
            azure_storage_account_url: Fixture that provide URL for accessing Storage Blob of Azure
            azure_storage_account_key: Fixture that provide access key for accessing Storage Blob
            azure_storage_container: Fixture that provides name of container deployed in Azure
            add_filter: Fixture that add fiter to south or north instances.
        """
        # Update Asset name
        ASSET = "test8_FOGL-7352_system"
        config_south(fledge_url, ASSET)
        
        # Add Expression filter to North Service
        add_expression_filter(add_filter, fledge_url, NORTH_PLUGIN_NAME)
        
        # Enable South Service for 10 Seonds
        enable_schedule(fledge_url, SOUTH_SERVICE_NAME)
        
        # Enable North Service for sending data to Azure-IOT-Hub
        enable_schedule(fledge_url, NORTH_SERVICE_NAME)
        
        print("On/Off of filter starts")
        count = 0
        while count<3:
            # For Disabling filter
            update_filter_config(fledge_url, NORTH_PLUGIN_NAME, 'false')
            time.sleep(wait_time*2)
            
            # For enabling filter
            update_filter_config(fledge_url, NORTH_PLUGIN_NAME, 'true')
            time.sleep(wait_time*2)
            count+=1
        
        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url, ASSET)
        verify_statistics_map(fledge_url, skip_verify_north_interface)
        verify_asset_tracking_details(fledge_url, skip_verify_north_interface, ASSET)
        
        # Storage blob JSON will be created every 2 minutes
        time.sleep(150)
        
        
        _verify_egress(azure_storage_account_url, azure_storage_account_key, azure_storage_container, wait_time, retries, ASSET)



class TestNorthAzureIoTHubDevicePluginInvalidConfig:

    def test_invalid_connstr(self, reset_fledge, add_south, add_north, fledge_url, enable_schedule, disable_schedule, wait_time, retries):
        
        """ Test that checks connection string of north azure plugin is invalid or not.
        
            reset_fledge: Fixture that reset and cleanup the fledge 
            add_south: Fixture that south Instance in disable mode
            add_north: Fixture that add north instance in disable mode
            enable_schedule: Fixture for enabling schedules or services
            disable_schedule: Fixture for disabling schedules or services
        """
        # Add South and North
        add_south(SOUTH_PLUGIN, None, fledge_url, service_name=SOUTH_SERVICE_NAME, start_service=False, installation_type='package')
        
        _config = {
        "primaryConnectionString": {"value":"InvalidConfig"}
        }
        # north_branch does not matter as these are archives.fledge-iot.org version install
        add_north(fledge_url, NORTH_PLUGIN_NAME, None, installation_type='package', north_instance_name=NORTH_SERVICE_NAME, 
                  config=_config, enabled=False, plugin_discovery_name=NORTH_PLUGIN_DISCOVERY_NAME, is_task=False)
        
        # Update Asset name
        ASSET = "test9_FOGL-7352_system"
        config_south(fledge_url, ASSET)
        
        # Enable South Service for 10 Seonds
        enable_schedule(fledge_url, SOUTH_SERVICE_NAME)
        time.sleep(wait_time)
        disable_schedule(fledge_url, SOUTH_SERVICE_NAME)
        
        # Enable North Service for sending data to Azure-IOT-Hub
        enable_schedule(fledge_url, NORTH_SERVICE_NAME)
        
        verify_north_stats_on_invalid_config(fledge_url)

    
    def test_invalid_connstr_sharedkey(self, reset_fledge, add_south, add_north, fledge_url, enable_schedule, disable_schedule, 
                                       wait_time, retries, azure_host, azure_device, azure_key):
        
        """ Test that checks shared key passed to connection string of north azure plugin is invalid or not.
        
            reset_fledge: Fixture that reset and cleanup the fledge 
            add_south: Fixture that south Instance in disable mode
            add_north: Fixture that add north instance in disable mode
            enable_schedule: Fixture for enabling schedules or services
            disable_schedule: Fixture for disabling schedules or services
            azure_host: Fixture that provide Hostname of Azure IoT Hub
            azure_device: Fixture that provide ID of Device deployed in Azure IoT Hub
            azure_key: Fixture that provide access key of Azure IoT Hub
        """
        # Add South and North
        add_south(SOUTH_PLUGIN, None, fledge_url, service_name=SOUTH_SERVICE_NAME, start_service=False, installation_type='package')
        
        _config = {
            "primaryConnectionString": {"value":"HostName={};DeviceId={};SharedAccessKey={}".format(azure_host, azure_device, azure_key[:-5])}
        }
        # north_branch does not matter as these are archives.fledge-iot.org version install
        add_north(fledge_url, NORTH_PLUGIN_NAME, None, installation_type='package', north_instance_name=NORTH_SERVICE_NAME, 
                  config=_config, enabled=False, plugin_discovery_name=NORTH_PLUGIN_DISCOVERY_NAME, is_task=False)
        
        # Update Asset name
        ASSET = "test10_FOGL-7352_system"
        config_south(fledge_url, ASSET)
        
        # Enable South Service for 10 Seonds
        enable_schedule(fledge_url, SOUTH_SERVICE_NAME)
        time.sleep(wait_time)
        disable_schedule(fledge_url, SOUTH_SERVICE_NAME)
        
        # Enable North Service for sending data to Azure-IOT-Hub
        enable_schedule(fledge_url, NORTH_SERVICE_NAME)
        
        verify_north_stats_on_invalid_config(fledge_url)


class TestNorthAzureIoTHubDevicePluginLongRun:
    
    def test_send_long_run(self, clean_setup_fledge_packages, reset_fledge, add_south_north_service, fledge_url, enable_schedule, 
                           disable_schedule, azure_host, azure_device, azure_key, wait_time, retries, skip_verify_north_interface,
                           azure_storage_account_url, azure_storage_account_key, azure_storage_container, run_time):
        
        """ Test that check data is inserted in Fledge and sent to Azure-IoT Hub for long duration based parameter passed.
        
            clean_setup_fledge_packages: Fixture for removing fledge from system completely if it is already present 
                                         and reinstall it baased on commandline arguments.
            reset_fledge: Fixture that reset and cleanup the fledge 
            add_south_north_service: Fixture that add south and north instance in disable mode
            enable_schedule: Fixture for enabling schedules or services
            disable_schedule: Fixture for disabling schedules or services
            azure_host: Fixture that provide Hostname of Azure IoT Hub
            azure_device: Fixture that provide ID of Device deployed in Azure IoT Hub
            azure_key: Fixture that provide access key of Azure IoT Hub
            azure_storage_account_url: Fixture that provide URL for accessing Storage Blob of Azure
            azure_storage_account_key: Fixture that provide access key for accessing Storage Blob
            azure_storage_container: Fixture that provides name of container deployed in Azure
            run_time: Fixture that defines durration for which this test will be executed.
        """        
        START_TIME = datetime.datetime.now()
        current_iteration = 1
        # Update Asset name
        ASSET = "test11_FOGL-7352_system"
        config_south(fledge_url, ASSET)
        
        
        # Enable South Service for ingesting data into fledge
        enable_schedule(fledge_url, SOUTH_SERVICE_NAME)
        
        time.sleep(wait_time)
        # Enable North Service for sending data to Azure-IOT-Hub
        enable_schedule(fledge_url, NORTH_SERVICE_NAME)
        
        while (datetime.datetime.now() - START_TIME).seconds <= (int(run_time) * 60):
            verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
            verify_asset(fledge_url, ASSET)
            verify_statistics_map(fledge_url, skip_verify_north_interface)
            verify_asset_tracking_details(fledge_url, skip_verify_north_interface, ASSET)
            
            # Storage blob JSON will be created every 2 minutes
            time.sleep(150)
            
            
            _verify_egress(azure_storage_account_url, azure_storage_account_key, azure_storage_container, wait_time, retries, ASSET)
                
            print('Successfully ran {} iterations'.format(current_iteration), datetime.datetime.now())
            current_iteration += 1
            current_duration = (datetime.datetime.now() - START_TIME).seconds
        
        # Disable South Service  
        disable_schedule(fledge_url, SOUTH_SERVICE_NAME)
        
        # Disable North Service 
        disable_schedule(fledge_url, NORTH_SERVICE_NAME)
        