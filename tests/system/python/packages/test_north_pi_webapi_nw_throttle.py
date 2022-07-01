# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test sending data to PI using Web API under a distorted network.

"""

__author__ = "Deepanshu Yadav"
__copyright__ = "Copyright (c) 2022 Dianomic Systems Inc"
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

from network_impairment import distort_network, reset_network

ASSET = "Sine-FOGL-6333"
DATAPOINT = "sinusoid"
NORTH_INSTANCE_NAME = "NorthReadingsToPI_WebAPI"
SOUTH_SERVICE_NAME = "Sinusoid-FOGL-6333"
# This  gives the path of directory where fledge is cloned. test_file < packages < python < system < tests < ROOT
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
SCRIPTS_DIR_ROOT = "{}/tests/system/python/scripts/package/".format(PROJECT_ROOT)
DATA_DIR_ROOT = "{}/tests/system/python/packages/data/".format(PROJECT_ROOT)


@pytest.fixture
def reset_fledge(wait_time):
    try:
        subprocess.run(["cd {} && ./reset"
                       .format(SCRIPTS_DIR_ROOT)], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "reset package script failed!"


@pytest.fixture
def install_netem(wait_time):
    try:
        subprocess.run(["sudo apt install net-tools iproute2"], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "Could not install netem "


def verify_ping(fledge_url, north_catch_up_time):
    get_url = "/fledge/ping"
    ping_result = utils.get_request(fledge_url, get_url)
    assert "dataRead" in ping_result
    assert "dataSent" in ping_result
    assert 0 < ping_result['dataRead'], "South data NOT seen in ping header"

    assert ping_result['dataRead'] == ping_result['dataSent'], "Could not send all" \
                                                               " the data even after " \
                                                               "waiting {} " \
                                                               "seconds.".format(north_catch_up_time)


def change_category(fledge_url, cat_name, config_item, value):
    """
    Changes the value of configuration item in the given category.
    Args:
        fledge_url: The url of the Fledge API.
        cat_name: The category name.
        config_item: The configuration item to be changed.
        value: The new value of configuration item.
    Returns: returns the value of changed category or raises error.
    """
    conn = http.client.HTTPConnection(fledge_url)
    body = {"value": str(value)}
    json_data = json.dumps(body)
    conn.request("PUT", '/fledge/category/{}/{}'.format(cat_name, config_item), json_data)
    r = conn.getresponse()
    # assert 200 == r.status, 'Could not change config item'
    print(r.status)
    r = r.read().decode()
    conn.close()
    retval = json.loads(r)
    print(retval)


def _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries, asset_name):
    retry_count = 0
    data_from_pi = None

    af_hierarchy_level = "fledge/room1/machine1"
    af_hierarchy_level_list = af_hierarchy_level.split("/")
    type_id = 1
    dp_name = 'id_datapoint'
    recorded_datapoint = "{}measurement_{}.{}".format(type_id, asset_name, dp_name)

    # Name of asset in the PI server
    PI_ASSET_NAME = "{}-type{}".format(asset_name, type_id)

    while (data_from_pi is None or data_from_pi == []) and retry_count < retries:
        data_from_pi = read_data_from_pi_web_api(pi_host, pi_admin, pi_passwd, pi_db, af_hierarchy_level_list,
                                                 PI_ASSET_NAME, {recorded_datapoint})
        retry_count += 1
        time.sleep(wait_time * 2)

    if data_from_pi is None or retry_count == retries:
        assert False, "Failed to read data from PI"

    return data_from_pi


@pytest.fixture
def start_south_north(add_south, start_north_task_omf_web_api, add_filter, remove_data_file,
                      fledge_url, pi_host, pi_port, pi_admin, pi_passwd,
                      start_north_omf_as_a_service, start_north_as_service,
                      enable_schedule, asset_name=ASSET):
    """ This fixture starts the sinusoid plugin and north pi web api plugin. Also puts a filter
        to insert reading id as a datapoint when we send the data to north.
        clean_setup_fledge_packages: purge the fledge* packages and install latest for given repo url
        add_south: Fixture that adds a south service with given configuration
        start_north_task_omf_web_api: Fixture that starts PI north task
        remove_data_file: Fixture that remove data file created during the tests """

    south_plugin = "sinusoid"
    # south_branch does not matter as these are archives.fledge-iot.org version install
    _config = {"assetName": {"value": ASSET}}
    add_south(south_plugin, None, fledge_url, config=_config,
              service_name=SOUTH_SERVICE_NAME, installation_type='package')
    if not start_north_as_service:
        start_north_task_omf_web_api(fledge_url, pi_host, pi_port, pi_user=pi_admin, pi_pwd=pi_passwd,
                                     start_task=False, taskname=NORTH_INSTANCE_NAME)
    else:
        start_north_omf_as_a_service(fledge_url, pi_host, pi_port, pi_user=pi_admin, pi_pwd=pi_passwd,
                                     start=False, service_name=NORTH_INSTANCE_NAME)

    add_filter("python35", None, "py35", {}, fledge_url, None, installation_type='package',
               only_installation=True)

    data = {"name": "py35", "plugin": "python35", "filter_config": {"enable": "true"}}
    utils.post_request(fledge_url, "/fledge/filter", data)

    data = {"pipeline": ["py35"]}
    put_url = "/fledge/filter/{}/pipeline?allow_duplicates=true&append_filter=true" \
        .format(NORTH_INSTANCE_NAME)
    utils.put_request(fledge_url, urllib.parse.quote(put_url, safe='?,=,&,/'), data)

    url = fledge_url + urllib.parse.quote('/fledge/category/{}_py35/script/upload'
                                          .format(NORTH_INSTANCE_NAME))
    script_path = 'script=@{}/set_id.py'.format(DATA_DIR_ROOT)
    upload_script = "curl -sX POST '{}' -F '{}'".format(url, script_path)
    exit_code = os.system(upload_script)
    assert 0 == exit_code

    enable_schedule(fledge_url, NORTH_INSTANCE_NAME)
    time.sleep(3)
    yield start_south_north


def turn_off_compression_for_pi_point(host, admin, password, asset_name, data_point_name):
    username_password = "{}:{}".format(admin, password)
    username_password_b64 = base64.b64encode(username_password.encode('ascii')).decode("ascii")
    headers = {'Authorization': 'Basic %s' % username_password_b64}
    try:
        conn = http.client.HTTPSConnection(host, context=ssl._create_unverified_context())
        conn.request("GET", '/piwebapi/dataservers', headers=headers)
        res = conn.getresponse()
        r = json.loads(res.read().decode())
        points = r["Items"][0]["Links"]["Points"]
    except Exception:
        print("Could not request data server of PI")

    name_to_search = asset_name + '.' + data_point_name
    for single_point in points['Items']:

        if name_to_search in single_point['Name']:
            web_id = single_point['WebId']
            pi_point_name = single_point["Name"]
            attr_name = 'compressing'
            conn.request("PUT", '/piwebapi/points/{}/attributes/{}'.format(web_id, attr_name),
                         "0", headers=headers)
            r = conn.getresponse()
            assert r.status == 204, "Could not update the compression" \
                                    " for the pi point {}.".format(pi_point_name)

            print("Turned off compression for the PI point".format(pi_point_name))

    print("Could not find {} in all PI points".format(name_to_search))


class TestPackagesSinusoid_PI_WebAPI:

    def test_omf_in_impaired_network(self, clean_setup_fledge_packages, reset_fledge,
                                     install_netem, start_south_north, read_data_from_pi_web_api,
                                     fledge_url, pi_host, pi_admin, pi_passwd, pi_db,
                                     wait_time, retries, skip_verify_north_interface,
                                     south_service_wait_time, north_catch_up_time, pi_port,
                                     throttled_network_config, disable_schedule,
                                     enable_schedule, asset_name=ASSET):
        """ Test that checks data is inserted in Fledge and sent to PI under an impaired network.
            start_south_north: Fixture that add south and north instance
            read_data_from_pi: Fixture to read data from PI
            skip_verify_north_interface: Flag for assertion of data using PI web API
            Assertions:
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/statistics
                on endpoint GET /fledge/asset
                on endpoint GET /fledge/asset/<asset_name>
                data received from PI is same as data sent
        """

        duration = south_service_wait_time + north_catch_up_time

        try:
            interface_for_impairment = throttled_network_config['interface']
        except KeyError:
            raise Exception("Interface not given for network impairment.")
        try:
            packet_delay = int(throttled_network_config['packet_delay'])
        except KeyError:
            packet_delay = None
        try:
            rate_limit = int(throttled_network_config['rate_limit'])
        except KeyError:
            rate_limit = None
        if not rate_limit and not packet_delay:
            raise Exception("None of packet delay or rate limit given, "
                            "cannot apply network impairment.")
        # Insert some readings before turning off compression.
        time.sleep(3)
        disable_schedule(fledge_url, SOUTH_SERVICE_NAME)

        # Turn off south service
        time.sleep(5)

        # Note down the total readings ingested

        # switch off Compression
        dp_name = 'id_datapoint'
        turn_off_compression_for_pi_point(pi_host, pi_admin, pi_passwd, ASSET, dp_name)

        # Restart the south service
        enable_schedule(fledge_url, SOUTH_SERVICE_NAME)

        # Wait for the south service to start.
        time.sleep(3)

        # Now we can distort the network.
        distort_network(interface=interface_for_impairment, traffic="outbound",
                        latency=packet_delay,
                        rate_limit=rate_limit, ip=pi_host, port=pi_port, duration=duration)

        # allow the south service to run for sometime
        time.sleep(5)
        change_category(fledge_url, SOUTH_SERVICE_NAME + "Advanced", "readingsPerSec", 3000)

        # Wait for south service to accumulate some readings
        time.sleep(south_service_wait_time)

        # now shutdown the south service
        disable_schedule(fledge_url, SOUTH_SERVICE_NAME)

        # Wait for north task or service to send these accumulated readings.
        time.sleep(north_catch_up_time)

        # clear up all the distortions on this network.
        reset_network(interface=interface_for_impairment)
        verify_ping(fledge_url, north_catch_up_time)


        # verify the bulk data from PI.

        verify_data_north = False
        if verify_data_north:
            data_pi = _verify_egress(read_data_from_pi_web_api, pi_host,
                                     pi_admin, pi_passwd, pi_db, wait_time, retries,
                                     asset_name)
