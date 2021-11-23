# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test OPCUA System tests:
        * Prerequisite:
        a) On First instance
        - Install fledge-south-opcua and fledge-south-s2opcua
        - Install fledge-north-opcua
        - Use Prosys OPCUA simulator with set of simulated data with all supoorted data types
        - Use Prosys OPCUA client to connect north opcua server and then browse around the objects
        that Fledge is creating And those subscriptions to second fledge instance
        Download:
         Prosys OPCUA client from https://downloads.prosysopc.com/opc-ua-client-downloads.php
         Prosys OPCUA server from https://downloads.prosysopc.com/opc-ua-simulation-server-downloads.php

        b) On Second instance (manual process)
        - Install fledge, fledge-south-opcua packages And Make sure Fledge is in running mode with reset data

        * Test:
        - Add south service with opcua/s2opcua plugin
        - Create data points with supported types from simulator
        - Verify the readings of data is correct and that will be from an asset API
        - Add north service with opcua plugin
        - Publish data to north-opcua and use another Fledge instance to read the data and compare the data
        between two instances
"""

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2021 Dianomic Systems, Inc."

import subprocess
import time
import utils
import pytest
import platform
import urllib.parse
from typing import Tuple

""" First FL instance IP Address """
FL1_INSTANCE_IP = "192.168.1.8"
""" Second FL instance IP Address """
FL2_INSTANCE_IP = "192.168.1.7"
""" Packages list for FL instances """
PKG_LIST = "fledge-south-opcua fledge-south-s2opcua fledge-north-opcua"
""" opcua south plugin name """
OPCUA_SOUTH_PLUGIN_NAME = "opcua"
""" s2opcua south plugin name """
S2OPCUA_SOUTH_PLUGIN_NAME = "s2opcua"
""" Service name with opcua south plugin """
OPCUA_SOUTH_SVC_NAME = "OPCUA #1"
""" Service name with s2opcua south plugin """
S2OPCUA_SOUTH_SVC_NAME = "S2 OPC-UA"
""" opcua north plugin name """
OPCUA_NORTH_PLUGIN_NAME = "opcua"
""" Service name with opcua north plugin """
OPCUA_NORTH_SVC_NAME = "OPCUA"
""" opcua readings asset count as configured in Prosys simulation server """
OPCUA_ASSET_COUNT = 12
""" s2opcua readings asset count as configured in Prosys simulation server """
S2OPCUA_ASSET_COUNT = 12
""" Asset prefix for opcua south plugin """
OPCUA_ASSET_NAME = "opcua"
""" Asset prefix for s2opcua south plugin """
S2OPCUA_ASSET_NAME = "s2opcua"
""" Server URL used in south opcua and s2opcua plugin configuration to get readings data """
OPCUA_SERVER_URL = "opc.tcp://{}:53530/OPCUA/SimulationServer".format(FL1_INSTANCE_IP)
""" Server URL used in north opcua plugin configuration for to pull the data """
OPCUA_NORTH_SERVER_URL = "opc.tcp://{}:4840/fledge/server".format(FL1_INSTANCE_IP)
""" Supported data types lists and in tuple format (data type, node identifier, data value) 
as given Prosys Simulation settings. NOTE: Create in an order and node display name as is """
SUPPORTED_DATA_TYPES = [("Boolean", 1008, 0), ("SByte", 1009, -128), ("Byte", 1010, 128), ("Int16", 1011, -32768),
                        ("UInt16", 1012, 65535), ("Int32", 1013, -2147483648), ("UInt32", 1014, 4294967295),
                        ("Int64", 1015, -9223372036854775808), ("UInt64", 1016, 18446744073709551615),
                        ("Float", 1017, -3.4E38), ("Double", 1018, 1.7E308), ("String", 1019, "0.0")]
""" Subscription plugin configuration used for both opcua and s2opcua south plugins """
SUBSCRIPTION = ["ns=3;i={}".format(SUPPORTED_DATA_TYPES[0][1]), "ns=3;i={}".format(SUPPORTED_DATA_TYPES[1][1]),
                "ns=3;i={}".format(SUPPORTED_DATA_TYPES[2][1]), "ns=3;i={}".format(SUPPORTED_DATA_TYPES[3][1]),
                "ns=3;i={}".format(SUPPORTED_DATA_TYPES[4][1]), "ns=3;i={}".format(SUPPORTED_DATA_TYPES[5][1]),
                "ns=3;i={}".format(SUPPORTED_DATA_TYPES[6][1]), "ns=3;i={}".format(SUPPORTED_DATA_TYPES[7][1]),
                "ns=3;i={}".format(SUPPORTED_DATA_TYPES[8][1]), "ns=3;i={}".format(SUPPORTED_DATA_TYPES[9][1]),
                "ns=3;i={}".format(SUPPORTED_DATA_TYPES[10][1]), "ns=3;i={}".format(SUPPORTED_DATA_TYPES[11][1])
                ]
""" OPCUA objects which will be used when we pull the data from north opcua to second FL instance (FL2_INSTANCE_IP) """
OPCUA_OBJECTS = [("{}{}".format(OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[0][1]), 2001, "false"),
                 ("{}{}".format(OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[0][1]), 2002, -128),
                 ("{}{}".format(OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[0][1]), 2003, 128),
                 ("{}{}".format(OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[0][1]), 2004, -32768),
                 ("{}{}".format(OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[0][1]), 2005, 65535),
                 ("{}{}".format(OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[0][1]), 2006, -2147483648),
                 ("{}{}".format(OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[0][1]), 2007, 4294967295),
                 ("{}{}".format(OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[0][1]), 2008, -9223372036854775808),
                 ("{}{}".format(OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[0][1]), 2009, 18446744073709551615),
                 ("{}{}".format(OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[0][1]), 2010, -3.4E38),
                 ("{}{}".format(OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[0][1]), 2011, 1.7E308),
                 ("{}{}".format(OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[0][1]), 2012, "0.0"),
                 ("{}{}".format(S2OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[0][1]), 2013, 0),
                 ("{}{}".format(S2OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[0][1]), 2014, -128),
                 ("{}{}".format(S2OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[0][1]), 2015, 128),
                 ("{}{}".format(S2OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[0][1]), 2016, -32768),
                 ("{}{}".format(S2OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[0][1]), 2017, 65535),
                 ("{}{}".format(S2OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[0][1]), 2018, -2147483648),
                 ("{}{}".format(S2OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[0][1]), 2019, 4294967295),
                 ("{}{}".format(S2OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[0][1]), 2020, -9223372036854775808),
                 ("{}{}".format(S2OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[0][1]), 2021, 18446744073709551615),
                 ("{}{}".format(S2OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[0][1]), 2022, -3.4E38),
                 ("{}{}".format(S2OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[0][1]), 2023, 1.7E308),
                 ("{}{}".format(S2OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[0][1]), 2024, "0.0")
                 ]

""" Subscription plugin configuration used for north opcua plugin """
SUBSCRIPTION2 = ["ns=2;s={}{}".format(OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[0][1]),
                 "ns=2;s={}{}".format(OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[1][1]),
                 "ns=2;s={}{}".format(OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[2][1]),
                 "ns=2;s={}{}".format(OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[3][1]),
                 "ns=2;s={}{}".format(OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[4][1]),
                 "ns=2;s={}{}".format(OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[5][1]),
                 "ns=2;s={}{}".format(OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[6][1]),
                 "ns=2;s={}{}".format(OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[7][1]),
                 "ns=2;s={}{}".format(OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[8][1]),
                 "ns=2;s={}{}".format(OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[9][1]),
                 "ns=2;s={}{}".format(OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[10][1]),
                 "ns=2;s={}{}".format(OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[11][1]),
                 "ns=2;s={}{}".format(S2OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[0][0]),
                 "ns=2;s={}{}".format(S2OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[1][0]),
                 "ns=2;s={}{}".format(S2OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[2][0]),
                 "ns=2;s={}{}".format(S2OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[3][0]),
                 "ns=2;s={}{}".format(S2OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[4][0]),
                 "ns=2;s={}{}".format(S2OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[5][0]),
                 "ns=2;s={}{}".format(S2OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[6][0]),
                 "ns=2;s={}{}".format(S2OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[7][0]),
                 "ns=2;s={}{}".format(S2OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[8][0]),
                 "ns=2;s={}{}".format(S2OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[9][0]),
                 "ns=2;s={}{}".format(S2OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[10][0]),
                 "ns=2;s={}{}".format(S2OPCUA_ASSET_NAME, SUPPORTED_DATA_TYPES[11][0])
                 ]


@pytest.fixture
def install_pkg():
    """ Fixture used for to install packages and only used in First FL instance """
    try:
        os_platform = platform.platform()
        pkg_mgr = 'yum' if 'centos' in os_platform or 'redhat' in os_platform else 'apt'
        subprocess.run(["sudo {} install -y {}".format(pkg_mgr, PKG_LIST)], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "{} one of installation package failed".format(PKG_LIST)


def add_service(fledge_url: str, wait_time: int, name: str, _type: str, plugin: str, config: dict) -> None:
    """ Used to add any service """
    data = {
        "name": name,
        "type": _type,
        "plugin": plugin,
        "enabled": "true",
        "config": config
    }
    utils.post_request(fledge_url, "/fledge/service", data)
    # extra wait time needed
    time.sleep(2 * wait_time)


def get_ping_data(fledge_url: str, key: str, asset_count: int) -> Tuple[int, str]:
    """ Used to get ping info """
    ping_info = utils.get_request(fledge_url, "/fledge/ping")
    assert key in ping_info
    total_read = asset_count
    # Special handling requires when both plugin runs
    if ping_info[key] > asset_count:
        total_read = OPCUA_ASSET_COUNT + S2OPCUA_ASSET_COUNT
    return total_read, ping_info[key]


def get_asset_readings(fledge_url: str, asset_prefix: str, plugin_name: str, data: list) -> None:
    """ Used to get asset readings for an asset code """
    for obj in data:
        asset_suffix = str(obj[1]) if plugin_name == OPCUA_SOUTH_PLUGIN_NAME else obj[0]
        asset_name = "{}{}".format(asset_prefix, asset_suffix)
        jdoc = utils.get_request(fledge_url, "/fledge/asset/{}".format(asset_name))
        if jdoc:
            result = jdoc[0]['reading'][str(asset_suffix)]
            print("Asset Reading Jdoc: {} \nExpected:{} == Actual:{}".format(jdoc[0]['reading'], obj[2], result))
            # TODO: FOGL-6076 - readings mismatched for some data types
            if asset_suffix not in ("SByte", "Byte", "Int16", "Int32", "UInt64", "1016", "Float", "1017",
                                    "Double", "1018", "2007", "2008", "2009", "2010", "2011", "2014",
                                    "2016", "2019", "2020", "2021", "2022", "2023"):
                # For opcua plugin it is treated as false Not 0
                if asset_suffix == "1008":
                    assert "false" == result
                else:
                    assert obj[2] == result
            else:
                print("Verification skipped for an asset: {}; Due to Bug exists. See FOGL-6076".format(asset_name))
        else:
            print("Reading not found for an asset code: {}".format(asset_name))


def verify_service(fledge_url: str, retries: int, svc_name: str, plugin_name: str, _type: str,
                   asset_count: int) -> None:
    """ Used for verification of any service"""
    get_url = "/fledge/south" if _type == "Southbound" else "/fledge/north"
    while retries:
        result = utils.get_request(fledge_url, get_url)
        if _type == "Southbound":
            if len(result["services"]):
                svc_info = [s for s in result["services"] if s['name'] == svc_name]
                if 'status' in svc_info[0] and svc_info[0]['status'] != "":
                    assert svc_name == svc_info[0]['name']
                    assert 'running' == svc_info[0]['status']
                    assert plugin_name == svc_info[0]['plugin']['name']
                    assert asset_count == len(svc_info[0]['assets'])
                    break
        else:
            if len(result):
                svc_info = [s for s in result if s['name'] == svc_name]
                if 'status' in svc_info[0] and svc_info[0]['status'] != "":
                    assert svc_name == svc_info[0]['name']
                    assert 'north_C' == svc_info[0]['processName']
                    assert 'running' == svc_info[0]['status']
                    # assert total_read == svc_info[0]['sent']
                    assert OPCUA_NORTH_PLUGIN_NAME == svc_info[0]['plugin']['name']
                    break
        retries -= 1
    if retries == 0:
        assert False, "TIMEOUT! Data NOT seen for {} with endpoint {}".format(svc_name, get_url)


def verify_asset_and_readings(fledge_url: str, total_assets: int, asset_name: str, plugin_name: str,
                              data: list) -> None:
    """ Used for verification of assets and readings """
    result = utils.get_request(fledge_url, "/fledge/asset")
    assert len(result), "No asset found"
    assert total_assets == len(result)
    get_asset_readings(fledge_url, asset_name, plugin_name, data)


def verify_asset_tracking_details(fledge_url: str, total_assets: int, svc_name: str, asset_name_prefix: str,
                                  plugin_name: str, event: str, data: list) -> None:
    """ Used for verification of asset tracker details """
    tracking_details = utils.get_request(fledge_url,  urllib.parse.quote("/fledge/track?service={}&event={}".format(
        svc_name, event), safe='?,=,&,/'))
    assert len(tracking_details["track"]), "Failed to track Ingest event"
    assert total_assets == len(tracking_details["track"])
    for record in tracking_details['track']:
        for idx, val in enumerate(data):
            asset = "{}{}".format(asset_name_prefix, val[0]) if plugin_name == S2OPCUA_SOUTH_PLUGIN_NAME else \
                "{}{}".format(asset_name_prefix, str(val[1]))
            if asset in record['asset']:
                print("Asset Tracking JDoc: {} \nExpected:{} == Actual:{}".format(record, asset, record['asset']))
                assert asset == record['asset']
                assert event == record['event']
                assert plugin_name == record['plugin']
                assert svc_name == record['service']
                break


class TestSouthOPCUA:
    """ To test south opcua plugins """

    # NOTE: Below test can be mark as skip if already executed as this requires only to be run once on an instance
    # @pytest.mark.skip(reason="Already installed the packages")
    def test_clean_install(self, clean_setup_fledge_packages, install_pkg):
        pass

    def test_setup(self, reset_and_start_fledge):
        pass

    @pytest.mark.parametrize("plugin_name, svc_name, asset_name, asset_count", [
        (OPCUA_SOUTH_PLUGIN_NAME, OPCUA_SOUTH_SVC_NAME, OPCUA_ASSET_NAME, OPCUA_ASSET_COUNT),
        (S2OPCUA_SOUTH_PLUGIN_NAME, S2OPCUA_SOUTH_SVC_NAME, S2OPCUA_ASSET_NAME, S2OPCUA_ASSET_COUNT)
    ])
    def test_asset_readings_and_tracker_entry(self, fledge_url, retries, wait_time, plugin_name, svc_name, asset_name,
                                              asset_count):
        print("a) Adding {} south service...".format(svc_name))
        config = {
            "asset": {
                "value": asset_name
            },
            "url": {
                "value": OPCUA_SERVER_URL
            },
            "subscription": {
                "value": {
                    "subscriptions": SUBSCRIPTION
                }
            }
        }
        add_service(fledge_url, wait_time, svc_name, "south", plugin_name, config)
        print("b) Verifying {} south service and its details...".format(svc_name))
        verify_service(fledge_url, retries, svc_name, plugin_name, "Southbound", asset_count)
        print("c) Verifying data read in ping...")
        total_read_count, data_read = get_ping_data(fledge_url, "dataRead", asset_count)
        assert total_read_count == data_read
        print("d) Verifying assets and readings...")
        verify_asset_and_readings(fledge_url, total_read_count, asset_name, plugin_name, SUPPORTED_DATA_TYPES)
        print("e) Verifying Ingest asset tracker entry...")
        verify_asset_tracking_details(fledge_url, asset_count, svc_name, asset_name, plugin_name, "Ingest",
                                      SUPPORTED_DATA_TYPES)


class TestNorthOPCUA:
    """ To test north opcua plugin """
    @pytest.mark.parametrize("asset_name, asset_count,", [
        (OPCUA_ASSET_NAME, OPCUA_ASSET_COUNT),
        (S2OPCUA_ASSET_NAME, S2OPCUA_ASSET_COUNT)
    ])
    def test_service_and_sent_readings(self, fledge_url, retries, wait_time, asset_name, asset_count):
        get_north_svc = utils.get_request(fledge_url, "/fledge/north")
        if not get_north_svc:
            print("a) Adding {} north service...".format(OPCUA_NORTH_PLUGIN_NAME))
            config = {
                "url":
                    {
                        "value": OPCUA_NORTH_SERVER_URL
                    }
            }
            add_service(fledge_url, wait_time, OPCUA_NORTH_SVC_NAME, "north", OPCUA_NORTH_PLUGIN_NAME, config)
        print("b) Verifying {} north service and its details...".format(OPCUA_NORTH_SVC_NAME))
        verify_service(fledge_url, retries, OPCUA_NORTH_SVC_NAME, OPCUA_NORTH_PLUGIN_NAME, "Northbound", asset_count)
        print("c) Verifying data sent in ping...")
        total_read_count, data_read = get_ping_data(fledge_url, "dataSent", asset_count)
        assert total_read_count == data_read
        print("d) Verifying Egress asset tracker entry...")
        verify_asset_tracking_details(fledge_url, total_read_count, OPCUA_NORTH_SVC_NAME, asset_name,
                                      OPCUA_NORTH_PLUGIN_NAME, "Egress", SUPPORTED_DATA_TYPES)


class TestPublishNorthOPCUA:
    """ Publish the readings data to north using the fledge-north-opcua and use another FL instance to read the data.
        Comparison of readings data between two FL instances to confirm data is correctly transmitted.
    """

    def test_data_to_another_fl_instance(self, wait_time, retries):
        rest_api_url = "{}:8081".format(FL2_INSTANCE_IP)
        asset_count = OPCUA_ASSET_COUNT + S2OPCUA_ASSET_COUNT
        print("Verifying publishing of data to another {} FL instance".format(FL2_INSTANCE_IP))
        print("a) Adding {} south service...".format(OPCUA_SOUTH_SVC_NAME))
        config = {
            "asset": {
                "value": OPCUA_ASSET_NAME
            },
            "url": {
                "value": OPCUA_NORTH_SERVER_URL
            },
            "subscription": {
                "value": {
                    "subscriptions": SUBSCRIPTION2
                }
            }
        }
        add_service(rest_api_url, wait_time, OPCUA_SOUTH_SVC_NAME, "south",
                    OPCUA_SOUTH_PLUGIN_NAME, config)
        print("b) Verifying {} south service and its details...".format(OPCUA_SOUTH_SVC_NAME))
        verify_service(rest_api_url, retries, OPCUA_SOUTH_SVC_NAME, OPCUA_SOUTH_PLUGIN_NAME, "Southbound", asset_count)
        print("c) Verifying data read in ping...")
        total_read_count, data_read = get_ping_data(rest_api_url, "dataRead", asset_count)
        assert total_read_count == data_read
        print("d) Verifying assets and readings...")
        verify_asset_and_readings(rest_api_url, total_read_count, OPCUA_ASSET_NAME, OPCUA_SOUTH_PLUGIN_NAME,
                                  OPCUA_OBJECTS)
        print("e) Verifying Ingest asset tracker entry...")
        verify_asset_tracking_details(rest_api_url, asset_count, OPCUA_SOUTH_SVC_NAME, OPCUA_ASSET_NAME,
                                      OPCUA_SOUTH_PLUGIN_NAME, "Ingest", OPCUA_OBJECTS)
