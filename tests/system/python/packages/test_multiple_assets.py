# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test Multiple Assets System tests:
        Creates large number of assets and verifies them.
"""

__author__ = "Yash Tatkondawar"
__copyright__ = "Copyright (c) 2021 Dianomic Systems, Inc."

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
BENCHMARK_SOUTH_SVC_NAME = "BenchMark #"
ASSET_NAME = "random_multiple_assets"
PER_BENCHMARK_ASSET_COUNT = 150
AF_HIERARCHY_LEVEL = "multipleassets/multipleassetslvl2/multipleassetslvl3"


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
def remove_and_add_pkgs(package_build_version):
    try:
        subprocess.run(["cd {}/tests/system/python/scripts/package && ./remove"
                       .format(PROJECT_ROOT)], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "remove package script failed!"

    try:
        subprocess.run(["cd {}/tests/system/python/scripts/package/ && ./setup {}"
                       .format(PROJECT_ROOT, package_build_version)], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "setup package script failed"

    try:
        subprocess.run(["sudo {} install -y fledge-south-benchmark".format(PKG_MGR)], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "installation of benchmark package failed"


@pytest.fixture
def start_north(start_north_omf_as_a_service, fledge_url,
                      pi_host, pi_port, pi_admin, pi_passwd, clear_pi_system_through_pi_web_api, pi_db):
    global north_schedule_id

    af_hierarchy_level_list = AF_HIERARCHY_LEVEL.split("/")
    # There is one data points here.
    # 1. no data point (Asset name be used in this case.)
    dp_list = ['']
    asset_dict = {}

    no_of_services = 6
    for service_count in range(no_of_services):
        for asst_count in range(PER_BENCHMARK_ASSET_COUNT):
            asset_name = ASSET_NAME + "-{}{}".format(service_count + 1, asst_count + 1)
            asset_dict[asset_name] = dp_list

    clear_pi_system_through_pi_web_api(pi_host, pi_admin, pi_passwd, pi_db,
                                       af_hierarchy_level_list, asset_dict)

    response = start_north_omf_as_a_service(fledge_url, pi_host, pi_port, pi_user=pi_admin, pi_pwd=pi_passwd,
                                            default_af_location=AF_HIERARCHY_LEVEL)
    north_schedule_id = response["id"]

    yield start_north


def add_benchmark(fledge_url, name, count):
    data = {
        "name": name,
        "type": "south",
        "plugin": "Benchmark",
        "enabled": True,
        "config": {
            "asset": {
                "value": "{}-{}".format(ASSET_NAME, count)
            },
            "numAssets": {
                "value": "{}".format(PER_BENCHMARK_ASSET_COUNT)
            }
        }
    }
    post_url = "/fledge/service"
    utils.post_request(fledge_url, post_url, data)


def verify_service_added(fledge_url, name):
    get_url = "/fledge/south"
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


def verify_asset(fledge_url, total_assets):
    get_url = "/fledge/asset"
    result = utils.get_request(fledge_url, get_url)
    assert len(result), "No asset found"
    assert total_assets == len(result)


def verify_asset_tracking_details(fledge_url, total_assets, total_benchmark_services, num_assets):
    tracking_details = utils.get_asset_tracking_details(fledge_url, "Ingest")
    assert len(tracking_details["track"]), "Failed to track Ingest event"
    assert total_assets == len(tracking_details["track"])
    for service_count in range(total_benchmark_services):
        for asset_count in range(num_assets):
            service_name = BENCHMARK_SOUTH_SVC_NAME + "{}".format(service_count + 1)
            asset_name = ASSET_NAME + "-{}{}".format(service_count + 1, asset_count + 1)
            assert service_name in [s["service"] for s in tracking_details["track"]]
            assert asset_name in [s["asset"] for s in tracking_details["track"]]
            assert "Benchmark" in [s["plugin"] for s in tracking_details["track"]]


def _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries, total_benchmark_services):

    af_hierarchy_level_list = AF_HIERARCHY_LEVEL.split("/")
    type_id = 1
    
    for s in range(1,total_benchmark_services+1):
      for a in range(1,PER_BENCHMARK_ASSET_COUNT+1):
        retry_count = 0
        data_from_pi = None
        asset_name = "random-" + str(s) + str(a)
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


class TestMultiAssets:
    def test_multiple_assets_with_restart(self, remove_and_add_pkgs, reset_fledge, start_north, read_data_from_pi_web_api,
                                          skip_verify_north_interface, fledge_url,
                                          wait_time, retries, pi_host, pi_port, pi_admin, pi_passwd, pi_db):
        """ Test multiple benchmark services with multiple assets are created in fledge, also verifies assets after
            restarting fledge.
            remove_and_add_pkgs: Fixture to remove and install latest fledge packages
            reset_fledge: Fixture to reset fledge
            Assertions:
                on endpoint GET /fledge/south
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/asset"""

        total_benchmark_services = 6
        total_assets = PER_BENCHMARK_ASSET_COUNT * total_benchmark_services

        for count in range(total_benchmark_services):
            service_name = BENCHMARK_SOUTH_SVC_NAME + "{}".format(count + 1)
            add_benchmark(fledge_url, service_name, count + 1)
            verify_service_added(fledge_url, service_name)

        # Wait until total_assets are created
        time.sleep(PER_BENCHMARK_ASSET_COUNT + 2 * wait_time)
        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url, total_assets)

        put_url = "/fledge/restart"
        utils.put_request(fledge_url, urllib.parse.quote(put_url))
        # Wait for fledge to restart
        time.sleep(wait_time * 2)

        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url, total_assets)

        verify_asset_tracking_details(fledge_url, total_assets, total_benchmark_services, PER_BENCHMARK_ASSET_COUNT)

        old_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)

        # Wait for read and sent readings to increase
        time.sleep(wait_time)

        new_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        # Verifies whether Read and Sent readings are increasing after restart
        assert old_ping_result['dataRead'] < new_ping_result['dataRead']

        if not skip_verify_north_interface:
            assert old_ping_result['dataSent'] < new_ping_result['dataSent']
            _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                           total_benchmark_services)

        # FIXME: If sleep is removed then the next test fails
        time.sleep(wait_time * 2)

    def test_add_multiple_assets_before_after_restart(self, reset_fledge, start_north, read_data_from_pi_web_api,
                                                      skip_verify_north_interface, fledge_url,
                                                      wait_time, retries, pi_host, pi_port, pi_admin, pi_passwd, pi_db):
        """ Test addition of multiple assets before and after restarting fledge.
            reset_fledge: Fixture to reset fledge
            Assertions:
                on endpoint GET /fledge/south
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/asset"""

        total_benchmark_services = 3
        # Total number of assets that would be created
        total_assets = PER_BENCHMARK_ASSET_COUNT * total_benchmark_services

        for count in range(total_benchmark_services):
            service_name = BENCHMARK_SOUTH_SVC_NAME + "{}".format(count + 1)
            add_benchmark(fledge_url, service_name, count + 1)
            verify_service_added(fledge_url, service_name)

        # Wait until total_assets are created
        time.sleep(PER_BENCHMARK_ASSET_COUNT + 2 * wait_time)
        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url, total_assets)

        verify_asset_tracking_details(fledge_url, total_assets, total_benchmark_services, PER_BENCHMARK_ASSET_COUNT)

        put_url = "/fledge/restart"
        utils.put_request(fledge_url, urllib.parse.quote(put_url))
        # Wait for fledge to restart
        time.sleep(wait_time * 3)

        # We are adding more total_assets number of assets
        total_assets = total_assets * 2

        for count in range(total_benchmark_services):
            service_name = BENCHMARK_SOUTH_SVC_NAME + "{}".format(count + 4)
            add_benchmark(fledge_url, service_name, count + 4)
            verify_service_added(fledge_url, service_name)

        # Wait until total_assets are created
        time.sleep(PER_BENCHMARK_ASSET_COUNT + 2 * wait_time)
        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url, total_assets)

        verify_asset_tracking_details(fledge_url, total_assets, total_benchmark_services * 2, PER_BENCHMARK_ASSET_COUNT)

        old_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)

        # Wait for read and sent readings to increase
        time.sleep(wait_time)

        new_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        # Verifies whether Read and Sent readings are increasing after restart
        assert old_ping_result['dataRead'] < new_ping_result['dataRead']

        if not skip_verify_north_interface:
            assert old_ping_result['dataSent'] < new_ping_result['dataSent']
            _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                           total_benchmark_services)

    def test_multiple_assets_with_reconfig(self, reset_fledge, start_north, read_data_from_pi_web_api, skip_verify_north_interface,
                                           fledge_url,
                                           wait_time, retries, pi_host, pi_port, pi_admin, pi_passwd, pi_db):
        """ Test addition of multiple assets with reconfiguration of south service.
            reset_fledge: Fixture to reset fledge
            Assertions:
                on endpoint GET /fledge/south
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/asset"""

        total_benchmark_services = 3
        num_assets = 2 * PER_BENCHMARK_ASSET_COUNT
        # Total number of assets that would be created
        total_assets = PER_BENCHMARK_ASSET_COUNT * total_benchmark_services

        for count in range(total_benchmark_services):
            service_name = BENCHMARK_SOUTH_SVC_NAME + "{}".format(count + 1)
            add_benchmark(fledge_url, service_name, count + 1)
            verify_service_added(fledge_url, service_name)

        # Wait until total_assets are created
        time.sleep(PER_BENCHMARK_ASSET_COUNT + 2 * wait_time)
        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url, total_assets)

        verify_asset_tracking_details(fledge_url, total_assets, total_benchmark_services, PER_BENCHMARK_ASSET_COUNT)

        # With reconfig, number of assets are doubled in each south service
        payload = {"numAssets": "{}".format(num_assets)}
        for count in range(total_benchmark_services):
            service_name = BENCHMARK_SOUTH_SVC_NAME + "{}".format(count + 1)
            put_url = "/fledge/category/{}".format(service_name)
            utils.put_request(fledge_url, urllib.parse.quote(put_url), payload)

        # In reconfig number of assets are doubled
        total_assets = total_assets * 2

        # Wait until total_assets are created
        time.sleep(num_assets + 2 * wait_time)
        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url, total_assets)

        verify_asset_tracking_details(fledge_url, total_assets, total_benchmark_services, num_assets)

        old_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)

        # Wait for read and sent readings to increase
        time.sleep(wait_time)

        new_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        # Verifies whether Read and Sent readings are increasing after restart
        assert old_ping_result['dataRead'] < new_ping_result['dataRead']

        if not skip_verify_north_interface:
            assert old_ping_result['dataSent'] < new_ping_result['dataSent']
            _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                           total_benchmark_services)
