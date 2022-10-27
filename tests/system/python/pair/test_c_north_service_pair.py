# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

"""
       A pair system test to verify C north service with south python plugins
"""

__author__ = "Yash Tatkondawar"
__copyright__ = "Copyright (c) 2022 Dianomic Systems, Inc."

import http.client
import json
import subprocess
import time
import urllib.parse
from pathlib import Path

import pytest
import utils

# Local machine
local_south_plugin = "sinusoid"
local_south_asset_name = "north_svc_pair_C_sinusoid"
local_south_service_name = "Sine #1"
local_north_plugin = "httpc"
local_north_service_name = "HN #1"

# Remote machine
remote_south_plugin = "http_south"
remote_south_service_name = "HS #1"
remote_south_asset_name = "north_svc_pair_C_sinusoid"
remote_north_plugin = "OMF"
remote_north_service_name = "NorthReadingsToPI_WebAPI"

north_schedule_id = ""
filter_name = "ScaleFilter #1"

# This  gives the path of directory where fledge is cloned. test_file < packages < python < system < tests < ROOT
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
SCRIPTS_DIR_ROOT = "{}/tests/system/python/scripts/package/".format(PROJECT_ROOT)
# SSH command to make connection with the remote machine
ssh_cmd = "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i"
AF_HIERARCHY_LEVEL = "Cservicepair/Cservicepairlvl1/Cservicepairlvl2"


@pytest.fixture
def reset_fledge_local(wait_time):
    try:
        subprocess.run(["cd {} && ./reset"
                       .format(SCRIPTS_DIR_ROOT)], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "reset package script failed!"


@pytest.fixture
def setup_local(reset_fledge_local, add_south, add_north, fledge_url, remote_ip):
    local_south_config = {"assetName": {"value": remote_south_asset_name}}
    add_south(local_south_plugin, None, fledge_url, config=local_south_config,
              service_name="{}".format(local_south_service_name),
              installation_type='package')
    # Change name of variables such as service_name, plugin_type
    global north_schedule_id
    local_north_config = {"URL": {"value": "http://{}:6683/sensor-reading".format(remote_ip)}}
    response = add_north(fledge_url, local_north_plugin, None, installation_type='package',
                         north_instance_name="{}".format(local_north_service_name),
                         is_task=False, config=local_north_config, enabled=True)
    north_schedule_id = response["id"]

    yield setup_local


@pytest.fixture
def reset_fledge_remote(remote_user, remote_ip, key_path, remote_fledge_path):
    """Fixture that kills fledge, reset database and starts fledge again on a remote machine
            remote_user: User of remote machine
            remote_ip: IP of remote machine
            key_path: Path of key file used for authentication to remote machine
            remote_fledge_path: Path where Fledge is cloned and built
        """
    if remote_fledge_path is None:
        remote_fledge_path = '/home/{}/fledge'.format(remote_user)
    # Reset fledge on remote machine
    subprocess.run([
        "{} {} {}@{} 'cd {}/tests/system/python/scripts/package/ && ./reset'".format(
            ssh_cmd, key_path, remote_user,
            remote_ip, remote_fledge_path)], shell=True, check=True)


@pytest.fixture
def clean_install_fledge_packages_remote(remote_user, remote_ip, key_path, remote_fledge_path, package_build_version):
    """Fixture that kills fledge, reset database and starts fledge again on a remote machine
            remote_user: User of remote machine
            remote_ip: IP of remote machine
            key_path: Path of key file used for authentication to remote machine
            remote_fledge_path: Path where Fledge is cloned and built
        """
    if remote_fledge_path is None:
        remote_fledge_path = '/home/{}/fledge'.format(remote_user)
    # Remove all already installed packages from remote machine
    subprocess.run([
        "{} {} {}@{} 'export FLEDGE_ROOT={};cd "
        "$FLEDGE_ROOT/tests/system/python/scripts/package/ && ./remove'".format(
            ssh_cmd, key_path, remote_user,
            remote_ip, remote_fledge_path)], shell=True, check=True)
    # Installs packages on remote machine based on packages version passed
    subprocess.run([
        "{} {} {}@{} 'export FLEDGE_ROOT={};cd "
        "$FLEDGE_ROOT/tests/system/python/scripts/package/ && ./setup {}'".format(
            ssh_cmd, key_path, remote_user,
            remote_ip, remote_fledge_path, package_build_version)], shell=True, check=True)
    # Installs http_south python plugin on remote machine
    try:
        subprocess.run([
            "{} {} {}@{} 'sudo apt install -y fledge-south-http-south'".format(
                ssh_cmd, key_path, remote_user,
                remote_ip)], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "{} plugin installation failed".format(remote_south_plugin)


@pytest.fixture
def setup_remote(reset_fledge_remote, remote_user, remote_ip, start_north_omf_as_a_service,
                 pi_host, pi_port, pi_admin, pi_passwd,
                 clear_pi_system_through_pi_web_api, pi_db):
    """Fixture that setups remote machine
            reset_fledge_remote: Fixture that kills fledge, reset database and starts fledge again on a remote
                                           machine.
            remote_user: User of remote machine
            remote_ip: IP of remote machine
            pi_host: Host IP of PI machine
            pi_port: Host port of PI machine
            pi_admin: Username of PI machine
            pi_passwd: Password of PI machine
        """

    af_hierarchy_level_list = AF_HIERARCHY_LEVEL.split("/")
    # There are two data points here. 1. sinusoid
    # 2. no data point (Asset name be used in this case.)
    dp_list = ['sinusoid', '']
    asset_dict = {}
    asset_dict[remote_south_asset_name] = dp_list
    clear_pi_system_through_pi_web_api(pi_host, pi_admin, pi_passwd, pi_db,
                                       af_hierarchy_level_list, asset_dict)

    fledge_url = "{}:8081".format(remote_ip)

    # Configure http_south python plugin on remote machine
    conn = http.client.HTTPConnection(fledge_url)
    data = {"name": "{}".format(remote_south_service_name), "type": "South", "plugin": "{}".format(remote_south_plugin),
            "enabled": "true", "config": {"assetNamePrefix": {"value": ""}}}
    conn.request("POST", '/fledge/service', json.dumps(data))
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    retval = json.loads(r)
    assert remote_south_service_name == retval["name"]

    # Configure pi north plugin on remote machine
    global remote_north_schedule_id
    response = start_north_omf_as_a_service(fledge_url, pi_host, pi_port, pi_user=pi_admin, pi_pwd=pi_passwd,
                                            start=True, default_af_location=AF_HIERARCHY_LEVEL)
    remote_north_schedule_id = response["id"]

    yield setup_remote


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

        assert 1 <= sent, "Failed to send data"
    return ping_result


def verify_statistics_map(fledge_url, south_asset_name, north_service_name, skip_verify_north_interface):
    get_url = "/fledge/statistics"
    jdoc = utils.get_request(fledge_url, get_url)
    actual_stats_map = utils.serialize_stats_map(jdoc)
    assert 1 <= actual_stats_map[south_asset_name.upper()]
    assert 1 <= actual_stats_map['READINGS']
    if not skip_verify_north_interface:
        assert 1 <= actual_stats_map['Readings Sent']
        assert 1 <= actual_stats_map[north_service_name]


def verify_service_added(fledge_url, south_service_name, north_service_name):
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


def verify_filter_added(fledge_url, filter_name):
    get_url = "/fledge/filter"
    result = utils.get_request(fledge_url, get_url)
    assert len(result["filters"])
    assert filter_name in [s["name"] for s in result["filters"]]
    return result


def verify_asset(fledge_url, south_asset_name):
    get_url = "/fledge/asset"
    result = utils.get_request(fledge_url, get_url)
    assert len(result), "No asset found"
    assert south_asset_name in [s["assetCode"] for s in result]


def verify_asset_tracking_details(fledge_url, south_service_name, south_asset_name, south_plugin, north_service_name,
                                  north_plugin, skip_verify_north_interface):
    tracking_details = utils.get_asset_tracking_details(fledge_url, "Ingest")
    assert len(tracking_details["track"]), "Failed to track Ingest event"
    tracked_item = tracking_details["track"][0]
    assert south_service_name == tracked_item["service"]
    assert south_asset_name == tracked_item["asset"]
    assert south_plugin == tracked_item["plugin"]

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

    af_hierarchy_level_list = AF_HIERARCHY_LEVEL.split("/")
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


class TestCNorthService:
    def test_north_C_service_with_restart(self, clean_setup_fledge_packages, clean_install_fledge_packages_remote,
                                               setup_local, setup_remote, skip_verify_north_interface, fledge_url,
                                               wait_time, retries, remote_ip, read_data_from_pi_web_api, pi_host,
                                               pi_admin, pi_passwd, pi_db):
        """ Test C plugin as a North service before and after restarting fledge.
            clean_setup_fledge_packages: Fixture to remove and install latest fledge packages
            clean_install_fledge_packages_remote: Fixture to remove and install latest fledge packages on remote machine
            setup_local: Fixture to reset, add and configure plugins on local machine
            setup_remote: Fixture to reset, add and configure plugins on remote machine
            read_data_from_pi_web_api: Fixture to read data from PI web API
            skip_verify_north_interface: Flag for assertion of data using PI web API
            Assertions:
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/south
                on endpoint GET /fledge/north
                on endpoint GET /fledge/service
                on endpoint GET /fledge/statistics
                on endpoint GET /fledge/asset
                on endpoint GET /fledge/track"""

        # Wait until south and north services are created and some data is loaded
        time.sleep(wait_time)

        fledge_url_remote = "{}:8081".format(remote_ip)

        # Verify on local machine
        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url, local_south_asset_name)
        verify_service_added(fledge_url, local_south_service_name, local_north_service_name)
        verify_statistics_map(fledge_url, local_south_asset_name, local_north_service_name, skip_verify_north_interface)
        verify_asset_tracking_details(fledge_url, local_south_service_name, local_south_asset_name, local_south_plugin,
                                      local_north_service_name, local_north_plugin, verify_asset_tracking_details)

        # Verify on remote machine
        verify_ping(fledge_url_remote, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url_remote, remote_south_asset_name)
        verify_service_added(fledge_url_remote, remote_south_service_name, remote_north_service_name)
        verify_statistics_map(fledge_url_remote, remote_south_asset_name, remote_north_service_name,
                              skip_verify_north_interface)
        verify_asset_tracking_details(fledge_url_remote, remote_south_service_name, remote_south_asset_name,
                                      remote_south_plugin, remote_north_service_name, remote_north_plugin,
                                      verify_asset_tracking_details)

        put_url = "/fledge/restart"
        utils.put_request(fledge_url, urllib.parse.quote(put_url))
        utils.put_request(fledge_url_remote, urllib.parse.quote(put_url))

        # Wait for fledge to restart
        time.sleep(wait_time * 2)

        old_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        old_ping_result_remote = verify_ping(fledge_url_remote, skip_verify_north_interface, wait_time, retries)
        # Wait for read and sent readings to increase
        time.sleep(wait_time)
        new_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        new_ping_result_remote = verify_ping(fledge_url_remote, skip_verify_north_interface, wait_time, retries)
        # Verifies whether Read and Sent readings are increasing after restart
        assert old_ping_result['dataRead'] < new_ping_result['dataRead']
        assert old_ping_result_remote['dataRead'] < new_ping_result_remote['dataRead']

        if not skip_verify_north_interface:
            assert old_ping_result['dataSent'] < new_ping_result['dataSent']
            assert old_ping_result_remote['dataSent'] < new_ping_result_remote['dataSent']
            _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                           remote_south_asset_name)

    def test_north_C_service_with_enable_disable(self, setup_local, setup_remote, read_data_from_pi_web_api,
                                                      remote_ip,
                                                      skip_verify_north_interface, fledge_url, wait_time, retries,
                                                      pi_host,
                                                      pi_admin, pi_passwd, pi_db):
        """ Test C plugin as a North service by disabling and enabling it.
            setup_local: Fixture to reset, add and configure plugins on local machine
            setup_remote: Fixture to reset, add and configure plugins on remote machine
            read_data_from_pi_web_api: Fixture to read data from PI web API
            skip_verify_north_interface: Flag for assertion of data using PI web API
            Assertions:
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/south
                on endpoint GET /fledge/north
                on endpoint GET /fledge/service
                on endpoint GET /fledge/statistics
                on endpoint GET /fledge/asset
                on endpoint GET /fledge/track"""

        # Wait until south and north services are created and some data is loaded
        time.sleep(wait_time)

        fledge_url_remote = "{}:8081".format(remote_ip)

        # Verify on local machine
        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url, local_south_asset_name)
        verify_service_added(fledge_url, local_south_service_name, local_north_service_name)
        verify_statistics_map(fledge_url, local_south_asset_name, local_north_service_name, skip_verify_north_interface)
        verify_asset_tracking_details(fledge_url, local_south_service_name, local_south_asset_name, local_south_plugin,
                                      local_north_service_name, local_north_plugin, verify_asset_tracking_details)

        # Verify on remote machine
        verify_ping(fledge_url_remote, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url_remote, remote_south_asset_name)
        verify_service_added(fledge_url_remote, remote_south_service_name, remote_north_service_name)
        verify_statistics_map(fledge_url_remote, remote_south_asset_name, remote_north_service_name,
                              skip_verify_north_interface)
        verify_asset_tracking_details(fledge_url_remote, remote_south_service_name, remote_south_asset_name,
                                      remote_south_plugin, remote_north_service_name, remote_north_plugin,
                                      verify_asset_tracking_details)

        # Disabling local machine north service
        data = {"enabled": "false"}
        put_url = "/fledge/schedule/{}".format(north_schedule_id)
        resp = utils.put_request(fledge_url, urllib.parse.quote(put_url), data)
        assert False == resp['schedule']['enabled']

        # Enabling local machine north service
        data = {"enabled": "true"}
        put_url = "/fledge/schedule/{}".format(north_schedule_id)
        resp = utils.put_request(fledge_url, urllib.parse.quote(put_url), data)
        assert True == resp['schedule']['enabled']

        old_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        old_ping_result_remote = verify_ping(fledge_url_remote, skip_verify_north_interface, wait_time, retries)
        # Wait for read and sent readings to increase
        time.sleep(wait_time)
        new_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        new_ping_result_remote = verify_ping(fledge_url_remote, skip_verify_north_interface, wait_time, retries)
        # Verifies whether Read and Sent readings are increasing after restart
        assert old_ping_result['dataRead'] < new_ping_result['dataRead']
        assert old_ping_result_remote['dataRead'] < new_ping_result_remote['dataRead']

        if not skip_verify_north_interface:
            assert old_ping_result['dataSent'] < new_ping_result['dataSent']
            assert old_ping_result_remote['dataSent'] < new_ping_result_remote['dataSent']
            _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                           remote_south_asset_name)

    def test_north_C_service_with_delete_add(self, setup_local, setup_remote, read_data_from_pi_web_api, remote_ip,
                                                  add_north, skip_verify_north_interface, fledge_url, wait_time,
                                                  retries,
                                                  pi_host, pi_admin, pi_passwd, pi_db):
        """ Test C plugin as a North service by deleting and adding it.
            setup_local: Fixture to reset, add and configure plugins on local machine
            setup_remote: Fixture to reset, add and configure plugins on remote machine
            read_data_from_pi_web_api: Fixture to read data from PI web API
            skip_verify_north_interface: Flag for assertion of data using PI web API
            Assertions:
                on endpoint GET /fledge/ping"""

        # Wait until south and north services are created and some data is loaded
        time.sleep(wait_time)

        fledge_url_remote = "{}:8081".format(remote_ip)

        # Delete and re-add the north service from local machine
        delete_url = "/fledge/service/{}".format(local_north_service_name)
        resp = utils.delete_request(fledge_url, urllib.parse.quote(delete_url))
        assert "Service {} deleted successfully.".format(local_north_service_name) == resp['result']

        local_north_config = {"URL": {"value": "http://{}:6683/sensor-reading".format(remote_ip)}}
        add_north(fledge_url, local_north_plugin, None, installation_type='package',
                  north_instance_name="{}".format(local_north_service_name),
                  is_task=False, config=local_north_config, enabled=True)

        old_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        old_ping_result_remote = verify_ping(fledge_url_remote, skip_verify_north_interface, wait_time, retries)
        # Wait for read and sent readings to increase
        time.sleep(wait_time)
        new_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        new_ping_result_remote = verify_ping(fledge_url_remote, skip_verify_north_interface, wait_time, retries)
        # Verifies whether Read and Sent readings are increasing after restart
        assert old_ping_result['dataRead'] < new_ping_result['dataRead']
        assert old_ping_result_remote['dataRead'] < new_ping_result_remote['dataRead']

        if not skip_verify_north_interface:
            assert old_ping_result['dataSent'] < new_ping_result['dataSent']
            assert old_ping_result_remote['dataSent'] < new_ping_result_remote['dataSent']
            _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                           remote_south_asset_name)

    def test_north_C_service_with_reconfig(self, setup_local, setup_remote, read_data_from_pi_web_api, remote_ip,
                                                skip_verify_north_interface, fledge_url, wait_time, retries, pi_host,
                                                pi_admin, pi_passwd, pi_db):
        """ Test C plugin as a North service by reconfiguring it.
            setup_local: Fixture to reset, add and configure plugins on local machine
            setup_remote: Fixture to reset, add and configure plugins on remote machine
            read_data_from_pi_web_api: Fixture to read data from PI web API
            skip_verify_north_interface: Flag for assertion of data using PI web API
            Assertions:
                on endpoint GET /fledge/ping"""

        # Wait until south and north services are created and some data is loaded
        time.sleep(wait_time)

        fledge_url_remote = "{}:8081".format(remote_ip)

        # Bad reconfiguration to check data is not sent
        data = {"URL": "http://100.1.2.3:6683/sensor-reading"}
        put_url = "/fledge/category/{}".format(local_north_service_name)
        resp = utils.put_request(fledge_url, urllib.parse.quote(put_url), data)
        assert "http://100.1.2.3:6683/sensor-reading" == resp["URL"]["value"]

        # Wait for all readings to be sent to remote machine from local machine
        time.sleep(wait_time)
        old_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        old_ping_result_remote = verify_ping(fledge_url_remote, skip_verify_north_interface, wait_time, retries)
        # Wait for read and sent readings to increase
        time.sleep(wait_time)
        new_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        new_ping_result_remote = verify_ping(fledge_url_remote, skip_verify_north_interface, wait_time, retries)

        # Verifies whether Read readings are increasing on local machine and not increasing on remote machine after
        # reconfig
        assert old_ping_result['dataRead'] < new_ping_result['dataRead']
        assert old_ping_result_remote['dataRead'] == new_ping_result_remote['dataRead']

        # Verifies whether Sent readings are not increasing after reconfig
        if not skip_verify_north_interface:
            assert old_ping_result['dataSent'] == new_ping_result['dataSent']
            assert old_ping_result_remote['dataSent'] == new_ping_result_remote['dataSent']
            _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                           remote_south_asset_name)

    def test_north_C_service_with_filter(self, setup_local, setup_remote, read_data_from_pi_web_api, remote_ip,
                                              add_filter,
                                              skip_verify_north_interface, fledge_url, wait_time, retries, pi_host,
                                              pi_admin, pi_passwd, pi_db):
        """ Test C plugin as a North service by adding filter on it.
            setup_local: Fixture to reset, add and configure plugins on local machine
            setup_remote: Fixture to reset, add and configure plugins on remote machine
            add_filter: Adds and configures a filter
            read_data_from_pi_web_api: Fixture to read data from PI web API
            skip_verify_north_interface: Flag for assertion of data using PI web API
            Assertions:
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/filter"""

        # Wait until south and north services are created and some data is loaded
        time.sleep(wait_time)

        fledge_url_remote = "{}:8081".format(remote_ip)

        filter_cfg_scale = {"enable": "true"}
        add_filter("scale", None, filter_name, filter_cfg_scale, fledge_url, local_north_service_name,
                   installation_type='package')
        verify_filter_added(fledge_url, filter_name)

        old_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        old_ping_result_remote = verify_ping(fledge_url_remote, skip_verify_north_interface, wait_time, retries)
        # Wait for read and sent readings to increase
        time.sleep(wait_time)
        new_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        new_ping_result_remote = verify_ping(fledge_url_remote, skip_verify_north_interface, wait_time, retries)

        # Verifies whether Read and Sent readings are increasing
        assert old_ping_result['dataRead'] < new_ping_result['dataRead']
        assert old_ping_result_remote['dataRead'] < new_ping_result_remote['dataRead']

        if not skip_verify_north_interface:
            assert old_ping_result['dataSent'] < new_ping_result['dataSent']
            assert old_ping_result_remote['dataSent'] < new_ping_result_remote['dataSent']
            _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                           remote_south_asset_name)

    def test_north_C_service_with_filter_enable_disable(self, setup_local, setup_remote, read_data_from_pi_web_api,
                                                             remote_ip, add_filter,
                                                             skip_verify_north_interface, fledge_url, wait_time,
                                                             retries, pi_host,
                                                             pi_admin, pi_passwd, pi_db):
        """ Test C plugin as a North service by enabling/disabling filter.
            setup_local: Fixture to reset, add and configure plugins on local machine
            setup_remote: Fixture to reset, add and configure plugins on remote machine
            add_filter: Adds and configures a filter
            read_data_from_pi_web_api: Fixture to read data from PI web API
            skip_verify_north_interface: Flag for assertion of data using PI web API
            Assertions:
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/filter"""

        # Wait until south and north services are created and some data is loaded
        time.sleep(wait_time)

        fledge_url_remote = "{}:8081".format(remote_ip)

        # Add filter in disbled mode
        filter_cfg_scale = {"enable": "false"}
        add_filter("scale", None, filter_name, filter_cfg_scale, fledge_url, local_north_service_name,
                   installation_type='package')
        verify_filter_added(fledge_url, filter_name)

        # Enable the filter  
        data = {"enable": "true"}
        put_url = "/fledge/category/{}_{}".format(local_north_service_name, filter_name)
        resp = utils.put_request(fledge_url, urllib.parse.quote(put_url), data)
        assert "true" == resp['enable']['value']

        old_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        old_ping_result_remote = verify_ping(fledge_url_remote, skip_verify_north_interface, wait_time, retries)
        # Wait for read and sent readings to increase
        time.sleep(wait_time)
        new_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        new_ping_result_remote = verify_ping(fledge_url_remote, skip_verify_north_interface, wait_time, retries)

        # Verifies whether Read and Sent readings are increasing
        assert old_ping_result['dataRead'] < new_ping_result['dataRead']
        assert old_ping_result_remote['dataRead'] < new_ping_result_remote['dataRead']

        if not skip_verify_north_interface:
            assert old_ping_result['dataSent'] < new_ping_result['dataSent']
            assert old_ping_result_remote['dataSent'] < new_ping_result_remote['dataSent']
            _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                           remote_south_asset_name)

    def test_north_C_service_with_filter_reconfig(self, setup_local, setup_remote, read_data_from_pi_web_api,
                                                       remote_ip, add_filter,
                                                       skip_verify_north_interface, fledge_url, wait_time, retries,
                                                       pi_host,
                                                       pi_admin, pi_passwd, pi_db):
        """ Test C plugin as a North service by reconfiguring filter.
            setup_local: Fixture to reset, add and configure plugins on local machine
            setup_remote: Fixture to reset, add and configure plugins on remote machine
            add_filter: Adds and configures a filter
            read_data_from_pi_web_api: Fixture to read data from PI web API
            skip_verify_north_interface: Flag for assertion of data using PI web API
            Assertions:
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/filter"""

        # Wait until south and north services are created and some data is loaded
        time.sleep(wait_time)

        fledge_url_remote = "{}:8081".format(remote_ip)

        # Add filter in disbled mode
        filter_cfg_scale = {"enable": "true"}
        add_filter("scale", None, filter_name, filter_cfg_scale, fledge_url, local_north_service_name,
                   installation_type='package')
        verify_filter_added(fledge_url, filter_name)

        # Enable the filter  
        data = {"factor": "50"}
        put_url = "/fledge/category/{}_{}".format(local_north_service_name, filter_name)
        resp = utils.put_request(fledge_url, urllib.parse.quote(put_url), data)
        assert "50.0" == resp['factor']['value']

        old_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        old_ping_result_remote = verify_ping(fledge_url_remote, skip_verify_north_interface, wait_time, retries)
        # Wait for read and sent readings to increase
        time.sleep(wait_time)
        new_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        new_ping_result_remote = verify_ping(fledge_url_remote, skip_verify_north_interface, wait_time, retries)

        # Verifies whether Read and Sent readings are increasing
        assert old_ping_result['dataRead'] < new_ping_result['dataRead']
        assert old_ping_result_remote['dataRead'] < new_ping_result_remote['dataRead']

        if not skip_verify_north_interface:
            assert old_ping_result['dataSent'] < new_ping_result['dataSent']
            assert old_ping_result_remote['dataSent'] < new_ping_result_remote['dataSent']
            _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                           remote_south_asset_name)

    def test_north_C_service_with_delete_add_filter(self, setup_local, setup_remote, read_data_from_pi_web_api,
                                                         remote_ip, add_filter,
                                                         skip_verify_north_interface, fledge_url, wait_time, retries,
                                                         pi_host,
                                                         pi_admin, pi_passwd, pi_db):
        """ Test C plugin as a North service by deleting and re-adding filter on it.
            setup_local: Fixture to reset, add and configure plugins on local machine
            setup_remote: Fixture to reset, add and configure plugins on remote machine
            add_filter: Adds and configures a filter
            read_data_from_pi_web_api: Fixture to read data from PI web API
            skip_verify_north_interface: Flag for assertion of data using PI web API
            Assertions:
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/filter"""

        # Wait until south and north services are created and some data is loaded
        time.sleep(wait_time)

        fledge_url_remote = "{}:8081".format(remote_ip)

        # Add filter in enabled mode
        filter_cfg_scale = {"enable": "true"}
        add_filter("scale", None, filter_name, filter_cfg_scale, fledge_url, local_north_service_name,
                   installation_type='package')
        verify_filter_added(fledge_url, filter_name)

        # Delete the filter
        data = {"pipeline": []}
        put_url = "/fledge/filter/{}/pipeline?allow_duplicates=true&append_filter=false" \
            .format(local_north_service_name)
        utils.put_request(fledge_url, urllib.parse.quote(put_url, safe='?,=,&,/'), data)

        delete_url = "/fledge/filter/{}".format(filter_name)
        resp = utils.delete_request(fledge_url, urllib.parse.quote(delete_url))
        assert "Filter {} deleted successfully".format(filter_name) == resp['result']

        # Re-add filter in enabled mode
        filter_cfg_scale = {"enable": "true"}
        add_filter("scale", None, filter_name, filter_cfg_scale, fledge_url, local_north_service_name,
                   installation_type='package')
        verify_filter_added(fledge_url, filter_name)

        old_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        old_ping_result_remote = verify_ping(fledge_url_remote, skip_verify_north_interface, wait_time, retries)
        # Wait for read and sent readings to increase
        time.sleep(wait_time)
        new_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        new_ping_result_remote = verify_ping(fledge_url_remote, skip_verify_north_interface, wait_time, retries)

        # Verifies whether Read and Sent readings are increasing
        assert old_ping_result['dataRead'] < new_ping_result['dataRead']
        assert old_ping_result_remote['dataRead'] < new_ping_result_remote['dataRead']

        if not skip_verify_north_interface:
            assert old_ping_result['dataSent'] < new_ping_result['dataSent']
            assert old_ping_result_remote['dataSent'] < new_ping_result_remote['dataSent']
            _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                           remote_south_asset_name)

    def test_north_C_service_with_filter_reorder(self, setup_local, setup_remote, read_data_from_pi_web_api,
                                                      remote_ip, add_filter,
                                                      skip_verify_north_interface, fledge_url, wait_time, retries,
                                                      pi_host,
                                                      pi_admin, pi_passwd, pi_db):
        """ Test C plugin as a North service by deleting and re-adding filter on it.
            setup_local: Fixture to reset, add and configure plugins on local machine
            setup_remote: Fixture to reset, add and configure plugins on remote machine
            add_filter: Adds and configures a filter
            read_data_from_pi_web_api: Fixture to read data from PI web API
            skip_verify_north_interface: Flag for assertion of data using PI web API
            Assertions:
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/filter"""

        # Wait until south and north services are created and some data is loaded
        time.sleep(wait_time)

        fledge_url_remote = "{}:8081".format(remote_ip)

        # Add first filter in enabled mode
        filter_cfg_scale = {"enable": "true"}
        add_filter("scale", None, filter_name, filter_cfg_scale, fledge_url, local_north_service_name,
                   installation_type='package')
        verify_filter_added(fledge_url, filter_name)

        # Add second filter in enabled mode
        filter2_name = "MetadataFilter #1"
        filter2_cfg = {"enable": "true"}
        add_filter("scale", None, filter2_name, filter2_cfg, fledge_url, local_north_service_name,
                   installation_type='package')
        verify_filter_added(fledge_url, filter2_name)

        # Verify the filter pipeline order
        get_url = "/fledge/filter/{}/pipeline".format(local_north_service_name)
        resp = utils.get_request(fledge_url, urllib.parse.quote(get_url))
        assert filter_name == resp['result']['pipeline'][0]
        assert filter2_name == resp['result']['pipeline'][1]

        data = {"pipeline": ["{}".format(filter2_name), "{}".format(filter_name)]}
        put_url = "/fledge/filter/{}/pipeline?allow_duplicates=true&append_filter=false" \
            .format(local_north_service_name)
        utils.put_request(fledge_url, urllib.parse.quote(put_url, safe='?,=,&,/'), data)

        # Verify the filter pipeline order after reordering
        get_url = "/fledge/filter/{}/pipeline".format(local_north_service_name)
        resp = utils.get_request(fledge_url, urllib.parse.quote(get_url))
        assert filter2_name == resp['result']['pipeline'][0]
        assert filter_name == resp['result']['pipeline'][1]

        old_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        old_ping_result_remote = verify_ping(fledge_url_remote, skip_verify_north_interface, wait_time, retries)
        # Wait for read and sent readings to increase
        time.sleep(wait_time)
        new_ping_result = verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        new_ping_result_remote = verify_ping(fledge_url_remote, skip_verify_north_interface, wait_time, retries)

        # Verifies whether Read and Sent readings are increasing
        assert old_ping_result['dataRead'] < new_ping_result['dataRead']
        assert old_ping_result_remote['dataRead'] < new_ping_result_remote['dataRead']

        if not skip_verify_north_interface:
            assert old_ping_result['dataSent'] < new_ping_result['dataSent']
            assert old_ping_result_remote['dataSent'] < new_ping_result_remote['dataSent']
            _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                           remote_south_asset_name)
