# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test OMF North Service System tests:
        Tests OMF as a north service along with reconfiguration.
"""

__author__ = "Yash Tatkondawar"
__copyright__ = "Copyright (c) 2021 Dianomic Systems, Inc."

import subprocess
import time
import urllib.parse
from pathlib import Path
import pytest
import utils

south_plugin = "sinusoid"
south_asset_name = "sinusoid"
south_service_name = "Sine #1"
north_plugin = "OMF"
north_service_name = "NorthReadingsToPI_WebAPI"
north_schedule_id = ""
filter1_name = "SF1"
filter2_name = "MD1"
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


@pytest.fixture
def start_south_north(add_south, start_north_omf_as_a_service, fledge_url,
                      pi_host, pi_port, pi_admin, pi_passwd):
    global north_schedule_id

    add_south(south_plugin, None, fledge_url, service_name="{}".format(south_service_name), installation_type='package')

    response = start_north_omf_as_a_service(fledge_url, pi_host, pi_port, pi_user=pi_admin, pi_pwd=pi_passwd)
    north_schedule_id = response["id"]

    yield start_south_north


@pytest.fixture
def add_configure_filter(add_filter, fledge_url):
    filter_cfg_scale = {"enable": "true"}
    add_filter("scale", None, filter1_name, filter_cfg_scale, fledge_url, north_service_name,
               installation_type='package')

    yield add_configure_filter


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

    get_url = "/fledge/north"
    result = utils.get_request(fledge_url, get_url)
    assert len(result)
    assert north_service_name in [s["name"] for s in result]

    get_url = "/fledge/service"
    result = utils.get_request(fledge_url, get_url)
    assert len(result["services"])
    assert south_service_name in [s["name"] for s in result["services"]]
    assert north_service_name in [s["name"] for s in result["services"]]


def verify_filter_added(fledge_url):
    get_url = "/fledge/filter"
    result = utils.get_request(fledge_url, get_url)
    assert len(result["filters"])
    assert filter1_name in [s["name"] for s in result["filters"]]
    return result


def verify_asset(fledge_url):
    get_url = "/fledge/asset"
    result = utils.get_request(fledge_url, get_url)
    assert len(result), "No asset found"
    assert south_asset_name in [s["assetCode"] for s in result]


def verify_asset_tracking_details(fledge_url, skip_verify_north_interface):
    tracking_details = utils.get_asset_tracking_details(fledge_url, "Ingest")
    assert len(tracking_details["track"]), "Failed to track Ingest event"
    tracked_item = tracking_details["track"][0]
    assert south_service_name == tracked_item["service"]
    assert south_asset_name == tracked_item["asset"]
    assert south_asset_name == tracked_item["plugin"]

    if not skip_verify_north_interface:
        egress_tracking_details = utils.get_asset_tracking_details(fledge_url, "Egress")
        assert len(egress_tracking_details["track"]), "Failed to track Egress event"
        tracked_item = egress_tracking_details["track"][0]
        assert north_service_name == tracked_item["service"]
        assert south_asset_name == tracked_item["asset"]
        assert north_plugin == tracked_item["plugin"]


def _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries, asset_name):
    retry_count = 0
    data_from_pi = None

    af_hierarchy_level = "fledge/room1/machine1"
    af_hierarchy_level_list = af_hierarchy_level.split("/")
    type_id = 1
    recorded_datapoint = "{}measurement_{}".format(type_id, asset_name)
    # Name of asset in the PI server
    pi_asset_name = "{}-type{}".format(asset_name, type_id)

    while (data_from_pi is None or data_from_pi == []) and retry_count < retries:
        data_from_pi = read_data_from_pi_web_api(pi_host, pi_admin, pi_passwd, pi_db, af_hierarchy_level_list,
                                                 pi_asset_name, {recorded_datapoint})
        retry_count += 1
        time.sleep(wait_time * 2)

    if data_from_pi is None or retry_count == retries:
        assert False, "Failed to read data from PI"


class TestOMFNorthService:
    def test_omf_service_with_restart(self, clean_setup_fledge_packages, reset_fledge, start_south_north,
                                      read_data_from_pi_web_api, skip_verify_north_interface, fledge_url,
                                      wait_time, retries, pi_host, pi_port, pi_admin, pi_passwd, pi_db):
        """ Test OMF as a North service before and after restarting fledge.
            clean_setup_fledge_packages: Fixture to remove and install latest fledge packages
            reset_fledge: Fixture to reset fledge
            start_south_north: Adds and configures south(sinusoid) and north(OMF) service
            read_data_from_pi_web_api: Fixture to read data from PI web API
            skip_verify_north_interface: Flag for assertion of data using PI web API
            Assertions:
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/south
                on endpoint GET /fledge/north
                on endpoint GET /fledge/filter
                on endpoint GET /fledge/service
                on endpoint GET /fledge/statistics
                on endpoint GET /fledge/asset
                on endpoint GET /fledge/track"""

        # Wait until south and north services are created and some data is loaded
        time.sleep(wait_time)

        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url)
        verify_service_added(fledge_url)
        verify_statistics_map(fledge_url, skip_verify_north_interface)
        verify_asset_tracking_details(fledge_url, verify_asset_tracking_details)

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

        if not skip_verify_north_interface:
            assert old_ping_result['dataSent'] < new_ping_result['dataSent']
            _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                           south_asset_name)

    def test_omf_service_with_enable_disable(self, reset_fledge, start_south_north, read_data_from_pi_web_api,
                                             skip_verify_north_interface,
                                             fledge_url, wait_time, retries, pi_host, pi_port, pi_admin, pi_passwd,
                                             pi_db):
        """ Test OMF as a North service by enabling and disabling it.
            reset_fledge: Fixture to reset fledge
            start_south_north: Adds and configures south(sinusoid) and north(OMF) service
            read_data_from_pi_web_api: Fixture to read data from PI web API
            skip_verify_north_interface: Flag for assertion of data using PI web API
            Assertions:
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/south
                on endpoint GET /fledge/north
                on endpoint GET /fledge/filter
                on endpoint GET /fledge/service
                on endpoint GET /fledge/statistics
                on endpoint GET /fledge/asset
                on endpoint GET /fledge/track"""

        # Wait until south and north services are created and some data is loaded
        time.sleep(wait_time)

        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url)
        verify_service_added(fledge_url)
        verify_statistics_map(fledge_url, skip_verify_north_interface)
        verify_asset_tracking_details(fledge_url, skip_verify_north_interface)

        data = {"enabled": "false"}
        put_url = "/fledge/schedule/{}".format(north_schedule_id)
        resp = utils.put_request(fledge_url, urllib.parse.quote(put_url), data)
        assert False == resp['schedule']['enabled']

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

        if not skip_verify_north_interface:
            assert old_ping_result['dataSent'] < new_ping_result['dataSent']
            _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                           south_asset_name)

    def test_omf_service_with_delete_add(self, reset_fledge, start_south_north, read_data_from_pi_web_api,
                                         start_north_omf_as_a_service,
                                         skip_verify_north_interface, fledge_url, wait_time, retries, pi_host, pi_port,
                                         pi_admin, pi_passwd, pi_db):
        """ Test OMF as a North service by deleting and adding north service.
            reset_fledge: Fixture to reset fledge
            start_south_north: Adds and configures south(sinusoid) and north(OMF) service
            read_data_from_pi_web_api: Fixture to read data from PI web API
            skip_verify_north_interface: Flag for assertion of data using PI web API
            Assertions:
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/south
                on endpoint GET /fledge/north
                on endpoint GET /fledge/filter
                on endpoint GET /fledge/service
                on endpoint GET /fledge/statistics
                on endpoint GET /fledge/asset
                on endpoint GET /fledge/track"""

        global north_schedule_id

        # Wait until south and north services are created and some data is loaded
        time.sleep(wait_time)

        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url)
        verify_service_added(fledge_url)
        verify_statistics_map(fledge_url, skip_verify_north_interface)
        verify_asset_tracking_details(fledge_url, skip_verify_north_interface)

        delete_url = "/fledge/service/{}".format(north_service_name)
        resp = utils.delete_request(fledge_url, delete_url)
        assert "Service {} deleted successfully.".format(north_service_name) == resp['result']

        response = start_north_omf_as_a_service(fledge_url, pi_host, pi_port, pi_user=pi_admin,
                                                           pi_pwd=pi_passwd)
        north_schedule_id = response["id"]

        old_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)

        # Wait for read and sent readings to increase
        time.sleep(wait_time)

        new_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        # Verifies whether Read and Sent readings are increasing after delete/add of north service
        assert old_ping_result['dataRead'] < new_ping_result['dataRead']

        if not skip_verify_north_interface:
            assert old_ping_result['dataSent'] < new_ping_result['dataSent']
            _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                           south_asset_name)

    def test_omf_service_with_reconfig(self, reset_fledge, start_south_north, read_data_from_pi_web_api,
                                       skip_verify_north_interface, fledge_url,
                                       wait_time, retries, pi_host, pi_port, pi_admin, pi_passwd, pi_db):
        """ Test OMF as a North service by reconfiguring it.
            reset_fledge: Fixture to reset fledge
            start_south_north: Adds and configures south(sinusoid) and north(OMF) service
            read_data_from_pi_web_api: Fixture to read data from PI web API
            skip_verify_north_interface: Flag for assertion of data using PI web API
            Assertions:
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/south
                on endpoint GET /fledge/north
                on endpoint GET /fledge/filter
                on endpoint GET /fledge/service
                on endpoint GET /fledge/statistics
                on endpoint GET /fledge/asset
                on endpoint GET /fledge/track"""

        # Wait until south and north services are created and some data is loaded
        time.sleep(wait_time)

        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url)
        verify_service_added(fledge_url)
        verify_statistics_map(fledge_url, skip_verify_north_interface)
        verify_asset_tracking_details(fledge_url, skip_verify_north_interface)

        # Good reconfiguration to check data is sent
        data = {"SendFullStructure": "false"}
        put_url = "/fledge/category/{}".format(north_service_name)
        resp = utils.put_request(fledge_url, urllib.parse.quote(put_url), data)
        assert "false" == resp["SendFullStructure"]["value"]

        old_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)

        # Wait for read and sent readings to increase
        time.sleep(wait_time)

        new_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        # Verifies whether Read and Sent readings are increasing after delete/add of north service
        assert old_ping_result['dataRead'] < new_ping_result['dataRead']
        if not skip_verify_north_interface:
            assert old_ping_result['dataSent'] < new_ping_result['dataSent']

        # Bad reconfiguration to check data is not sent
        data = {"PIWebAPIUserId": "Admin"}
        put_url = "/fledge/category/{}".format(north_service_name)
        resp = utils.put_request(fledge_url, urllib.parse.quote(put_url), data)
        assert "Admin" == resp["PIWebAPIUserId"]["value"]

        old_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)

        # Wait for read and sent readings to increase
        time.sleep(wait_time)

        new_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        # Verifies whether Read and Sent readings are increasing after delete/add of north service
        assert old_ping_result['dataRead'] < new_ping_result['dataRead']

        if not skip_verify_north_interface:
            assert old_ping_result['dataSent'] == new_ping_result['dataSent']
            _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                           south_asset_name)


class TestOMFNorthServicewithFilters:
    def test_omf_service_with_filter(self, reset_fledge, start_south_north, add_configure_filter,
                                     read_data_from_pi_web_api,
                                     skip_verify_north_interface, fledge_url, wait_time, retries, pi_host, pi_port,
                                     pi_admin, pi_passwd, pi_db):
        """ Test OMF as a North service with filters.
            reset_fledge: Fixture to reset fledge
            start_south_north: Adds and configures south(sinusoid) and north(OMF) service
            read_data_from_pi_web_api: Fixture to read data from PI web API
            skip_verify_north_interface: Flag for assertion of data using PI web API
            Assertions:
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/south
                on endpoint GET /fledge/north
                on endpoint GET /fledge/filter
                on endpoint GET /fledge/service
                on endpoint GET /fledge/statistics
                on endpoint GET /fledge/asset
                on endpoint GET /fledge/track"""

        # Wait until south, north services and filters are created and some data is loaded
        time.sleep(wait_time)

        old_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url)
        verify_service_added(fledge_url)
        verify_filter_added(fledge_url)
        verify_statistics_map(fledge_url, skip_verify_north_interface)
        verify_asset_tracking_details(fledge_url, skip_verify_north_interface)

        # Wait for read and sent readings to increase
        time.sleep(wait_time)

        new_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        # Verifies whether Read and Sent readings are increasing after delete/add of north service
        assert old_ping_result['dataRead'] < new_ping_result['dataRead']

        if not skip_verify_north_interface:
            assert old_ping_result['dataSent'] < new_ping_result['dataSent']
            _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                           south_asset_name)

    def test_omf_service_with_disable_enable_filter(self, reset_fledge, start_south_north, add_configure_filter,
                                                    read_data_from_pi_web_api,
                                                    skip_verify_north_interface, fledge_url, wait_time, retries,
                                                    pi_host, pi_port, pi_admin, pi_passwd, pi_db):
        """ Test OMF as a North service with enable/disable of filters.
            reset_fledge: Fixture to reset fledge
            start_south_north: Adds and configures south(sinusoid) and north(OMF) service
            read_data_from_pi_web_api: Fixture to read data from PI web API
            skip_verify_north_interface: Flag for assertion of data using PI web API
            Assertions:
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/south
                on endpoint GET /fledge/north
                on endpoint GET /fledge/filter
                on endpoint GET /fledge/service
                on endpoint GET /fledge/statistics
                on endpoint GET /fledge/asset
                on endpoint GET /fledge/track"""

        # Wait until south, north services and filters are created and some data is loaded
        time.sleep(wait_time)

        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url)
        verify_service_added(fledge_url)
        verify_filter_added(fledge_url)
        verify_statistics_map(fledge_url, skip_verify_north_interface)
        verify_asset_tracking_details(fledge_url, skip_verify_north_interface)

        data = {"enable": "false"}
        put_url = "/fledge/category/{}_SF1".format(north_service_name)
        resp = utils.put_request(fledge_url, urllib.parse.quote(put_url), data)
        assert "false" == resp['enable']['value']

        data = {"enable": "true"}
        put_url = "/fledge/category/{}_SF1".format(north_service_name)
        resp = utils.put_request(fledge_url, urllib.parse.quote(put_url), data)
        assert "true" == resp['enable']['value']

        old_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)

        # Wait for read and sent readings to increase
        time.sleep(wait_time)

        new_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        # Verifies whether Read and Sent readings are increasing after disable/enable
        assert old_ping_result['dataRead'] < new_ping_result['dataRead']

        if not skip_verify_north_interface:
            assert old_ping_result['dataSent'] < new_ping_result['dataSent']
            _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                           south_asset_name)

    def test_omf_service_with_filter_reconfig(self, reset_fledge, start_south_north, add_configure_filter,
                                              read_data_from_pi_web_api,
                                              skip_verify_north_interface, fledge_url, wait_time, retries, pi_host,
                                              pi_port, pi_admin, pi_passwd, pi_db):
        """ Test OMF as a North service with reconfiguration of filters.
            reset_fledge: Fixture to reset fledge
            start_south_north: Adds and configures south(sinusoid) and north(OMF) service
            read_data_from_pi_web_api: Fixture to read data from PI web API
            skip_verify_north_interface: Flag for assertion of data using PI web API
            Assertions:
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/south
                on endpoint GET /fledge/north
                on endpoint GET /fledge/filter
                on endpoint GET /fledge/service
                on endpoint GET /fledge/statistics
                on endpoint GET /fledge/asset
                on endpoint GET /fledge/track"""

        # Wait until south, north services and filters are created and some data is loaded
        time.sleep(wait_time)

        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url)
        verify_service_added(fledge_url)
        verify_filter_added(fledge_url)
        verify_statistics_map(fledge_url, skip_verify_north_interface)
        verify_asset_tracking_details(fledge_url, skip_verify_north_interface)

        data = {"factor": "50"}
        put_url = "/fledge/category/{}_SF1".format(north_service_name)
        resp = utils.put_request(fledge_url, urllib.parse.quote(put_url), data)
        assert "50.0" == resp['factor']['value']

        old_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)

        # Wait for read and sent readings to increase
        time.sleep(wait_time)

        new_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        # Verifies whether Read and Sent readings are increasing after disable/enable
        assert old_ping_result['dataRead'] < new_ping_result['dataRead']

        if not skip_verify_north_interface:
            assert old_ping_result['dataSent'] < new_ping_result['dataSent']
            _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                           south_asset_name)

    @pytest.mark.skip(reason="FOGL-5215: Deleting a service doesn't delete its filter categories")
    def test_omf_service_with_delete_add(self, reset_fledge, start_south_north, add_configure_filter, add_filter,
                                         read_data_from_pi_web_api,
                                         start_north_omf_as_a_service, skip_verify_north_interface,
                                         fledge_url, wait_time, retries, pi_host, pi_port, pi_admin, pi_passwd, pi_db):
        """ Test OMF as a North service by deleting and adding north service.
            reset_fledge: Fixture to reset fledge
            start_south_north: Adds and configures south(sinusoid) and north(OMF) service
            read_data_from_pi_web_api: Fixture to read data from PI web API
            skip_verify_north_interface: Flag for assertion of data using PI web API
            Assertions:
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/south
                on endpoint GET /fledge/north
                on endpoint GET /fledge/filter
                on endpoint GET /fledge/service
                on endpoint GET /fledge/statistics
                on endpoint GET /fledge/asset
                on endpoint GET /fledge/track"""

        global north_schedule_id

        # Wait until south, north services and filters are created and some data is loaded
        time.sleep(wait_time)

        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url)
        verify_service_added(fledge_url)
        verify_filter_added(fledge_url)
        verify_statistics_map(fledge_url, skip_verify_north_interface)
        verify_asset_tracking_details(fledge_url, skip_verify_north_interface)

        delete_url = "/fledge/service/{}".format(north_service_name)
        resp = utils.delete_request(fledge_url, delete_url)
        assert "Service {} deleted successfully.".format(north_service_name) == resp['result']

        response = start_north_omf_as_a_service(fledge_url, pi_host, pi_port, pi_user=pi_admin,
                                                           pi_pwd=pi_passwd)
        north_schedule_id = response["id"]

        filter_cfg_scale = {"enable": "true"}
        add_filter("scale", None, "SF2", filter_cfg_scale, fledge_url, north_service_name, installation_type='package')

        verify_service_added(fledge_url)
        verify_filter_added(fledge_url)

        old_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)

        # Wait for read and sent readings to increase
        time.sleep(wait_time)

        new_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        # Verifies whether Read and Sent readings are increasing after delete/add of north service
        assert old_ping_result['dataRead'] < new_ping_result['dataRead']

        if not skip_verify_north_interface:
            assert old_ping_result['dataSent'] < new_ping_result['dataSent']
            _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                           south_asset_name)

    def test_omf_service_with_delete_add_filter(self, reset_fledge, start_south_north, add_configure_filter, add_filter,
                                                read_data_from_pi_web_api,
                                                skip_verify_north_interface, fledge_url, wait_time, retries, pi_host,
                                                pi_port, pi_admin, pi_passwd, pi_db):
        """ Test OMF as a North service by deleting filter attached to north service.
            reset_fledge: Fixture to reset fledge
            start_south_north: Adds and configures south(sinusoid) and north(OMF) service
            read_data_from_pi_web_api: Fixture to read data from PI web API
            skip_verify_north_interface: Flag for assertion of data using PI web API
            Assertions:
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/south
                on endpoint GET /fledge/north
                on endpoint GET /fledge/filter
                on endpoint GET /fledge/service
                on endpoint GET /fledge/statistics
                on endpoint GET /fledge/asset
                on endpoint GET /fledge/track"""

        # Wait until south, north services and filters are created and some data is loaded
        time.sleep(wait_time)

        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url)
        verify_service_added(fledge_url)
        verify_filter_added(fledge_url)
        verify_statistics_map(fledge_url, skip_verify_north_interface)
        verify_asset_tracking_details(fledge_url, skip_verify_north_interface)

        data = {"pipeline": []}
        put_url = "/fledge/filter/{}/pipeline?allow_duplicates=true&append_filter=false" \
            .format(north_service_name)
        utils.put_request(fledge_url, urllib.parse.quote(put_url, safe='?,=,&,/'), data)

        delete_url = "/fledge/filter/{}".format(filter1_name)
        resp = utils.delete_request(fledge_url, delete_url)
        assert "Filter {} deleted successfully".format(filter1_name) == resp['result']

        filter_cfg_scale = {"enable": "true"}
        add_filter("scale", None, filter1_name, filter_cfg_scale, fledge_url, north_service_name,
                   installation_type='package')

        verify_filter_added(fledge_url)

        old_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)

        # Wait for read and sent readings to increase
        time.sleep(wait_time)

        new_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        # Verifies whether Read and Sent readings are increasing after delete/add of north service
        assert old_ping_result['dataRead'] < new_ping_result['dataRead']

        if not skip_verify_north_interface:
            assert old_ping_result['dataSent'] < new_ping_result['dataSent']
            _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                           south_asset_name)

    def test_omf_service_with_filter_reorder(self, reset_fledge, start_south_north, add_configure_filter, add_filter,
                                             read_data_from_pi_web_api,
                                             skip_verify_north_interface, fledge_url, wait_time, retries, pi_host,
                                             pi_port, pi_admin, pi_passwd, pi_db):
        """ Test OMF as a North service by reordering filters attached to north service.
            reset_fledge: Fixture to reset fledge
            start_south_north: Adds and configures south(sinusoid) and north(OMF) service
            read_data_from_pi_web_api: Fixture to read data from PI web API
            skip_verify_north_interface: Flag for assertion of data using PI web API
            Assertions:
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/south
                on endpoint GET /fledge/north
                on endpoint GET /fledge/filter
                on endpoint GET /fledge/service
                on endpoint GET /fledge/statistics
                on endpoint GET /fledge/asset
                on endpoint GET /fledge/track"""

        # Wait until south, north services and filters are created and some data is loaded
        time.sleep(wait_time)

        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url)
        verify_service_added(fledge_url)
        verify_filter_added(fledge_url)
        verify_statistics_map(fledge_url, skip_verify_north_interface)
        verify_asset_tracking_details(fledge_url, skip_verify_north_interface)

        # Adding second filter
        filter_cfg_meta = {"enable": "true"}
        add_filter("metadata", None, filter2_name, filter_cfg_meta, fledge_url, north_service_name,
                   installation_type='package')

        result = verify_filter_added(fledge_url)
        assert filter2_name in [s["name"] for s in result["filters"]]

        # Verify the filter pipeline order
        get_url = "/fledge/filter/{}/pipeline".format(north_service_name)
        resp = utils.get_request(fledge_url, get_url)
        assert filter1_name == resp['result']['pipeline'][0]
        assert filter2_name == resp['result']['pipeline'][1]

        data = {"pipeline": ["{}".format(filter2_name), "{}".format(filter1_name)]}
        put_url = "/fledge/filter/{}/pipeline?allow_duplicates=true&append_filter=false" \
            .format(north_service_name)
        utils.put_request(fledge_url, urllib.parse.quote(put_url, safe='?,=,&,/'), data)

        # Verify the filter pipeline order after reordering
        get_url = "/fledge/filter/{}/pipeline".format(north_service_name)
        resp = utils.get_request(fledge_url, get_url)
        assert filter2_name == resp['result']['pipeline'][0]
        assert filter1_name == resp['result']['pipeline'][1]

        old_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)

        # Wait for read and sent readings to increase
        time.sleep(wait_time)

        new_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        # Verifies whether Read and Sent readings are increasing after reordering of filters
        assert old_ping_result['dataRead'] < new_ping_result['dataRead']

        if not skip_verify_north_interface:
            assert old_ping_result['dataSent'] < new_ping_result['dataSent']
            _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                           south_asset_name)
