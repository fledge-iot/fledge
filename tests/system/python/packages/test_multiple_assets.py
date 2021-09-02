# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test Multiple Assets System tests:
        Creates large number of assets and verifies them.
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
import platform

# This  gives the path of directory where fledge is cloned. test_file < packages < python < system < tests < ROOT
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
SCRIPTS_DIR_ROOT = "{}/tests/system/python/packages/data/".format(PROJECT_ROOT)
FLEDGE_ROOT = os.environ.get('FLEDGE_ROOT')
BENCHMARK_SOUTH_SVC_NAME = "BenchMark #"
ASSET_NAME = "random"
PER_BENCHMARK_ASSET_COUNT = 150


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
        os_platform = platform.platform()
        pkg_mgr = 'yum' if 'centos' in os_platform or 'redhat' in os_platform else 'apt'
        subprocess.run(["sudo {} install -y fledge-south-benchmark".format(pkg_mgr)], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "installation of benchmark package failed"


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


def verify_ping(fledge_url):
    get_url = "/fledge/ping"
    ping_result = utils.get_request(fledge_url, get_url)
    assert "dataRead" in ping_result
    assert 0 < ping_result['dataRead'], "data NOT seen in ping header"
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


class TestMultiAssets:
    def test_multiple_assets_with_restart(self, remove_and_add_pkgs, reset_fledge, fledge_url, wait_time):
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
        verify_ping(fledge_url)
        verify_asset(fledge_url, total_assets)

        put_url = "/fledge/restart"
        utils.put_request(fledge_url, urllib.parse.quote(put_url))
        # Wait for fledge to restart
        time.sleep(wait_time)

        verify_ping(fledge_url)
        verify_asset(fledge_url, total_assets)

        verify_asset_tracking_details(fledge_url, total_assets, total_benchmark_services, PER_BENCHMARK_ASSET_COUNT)

    def test_add_multiple_assets_before_after_restart(self, reset_fledge, fledge_url, wait_time):
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
        verify_ping(fledge_url)
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
        verify_ping(fledge_url)
        verify_asset(fledge_url, total_assets)

        verify_asset_tracking_details(fledge_url, total_assets, total_benchmark_services * 2, PER_BENCHMARK_ASSET_COUNT)

    def test_multiple_assets_with_reconfig(self, reset_fledge, fledge_url, wait_time):
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
        verify_ping(fledge_url)
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
        verify_ping(fledge_url)
        verify_asset(fledge_url, total_assets)

        verify_asset_tracking_details(fledge_url, total_assets, total_benchmark_services, num_assets)
