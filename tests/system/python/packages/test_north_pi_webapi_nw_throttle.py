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
import csv

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
              service_name=SOUTH_SERVICE_NAME, installation_type='package', start_service=False)
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
    enable_schedule(fledge_url, SOUTH_SERVICE_NAME)
    time.sleep(1)
    yield start_south_north


def get_total_readings(fledge_url):
    """
    Fetches the reading for an asset
    Args:
        fledge_url: The url of fledge . By default localhost:8081
    Returns: The first element in the list of json strings. (A dictionary)
    """

    conn = http.client.HTTPConnection(fledge_url)
    conn.request("GET", '/fledge/asset')
    r = conn.getresponse()
    assert 200 == r.status, "Could not get total readings from fledge"
    r = r.read().decode()
    jdoc = json.loads(r)
    return jdoc[0]['count']


def get_bulk_data_from_pi(host, admin, password, asset_name, data_point_name):
    """Used for getting bulk data < 100000 from PI."""
    username_password = "{}:{}".format(admin, password)
    username_password_b64 = base64.b64encode(username_password.encode('ascii')).decode("ascii")
    headers = {'Authorization': 'Basic %s' % username_password_b64}
    try:
        conn = http.client.HTTPSConnection(host, context=ssl._create_unverified_context())
        conn.request("GET", '/piwebapi/dataservers', headers=headers)
        res = conn.getresponse()
        r = json.loads(res.read().decode())
        points_url = r["Items"][0]["Links"]["Points"]
    except Exception:
        assert False, "Could not request data server of PI"

    try:
        conn.request("GET", points_url, headers=headers)
        res = conn.getresponse()
        points = json.loads(res.read().decode())
    except Exception:
        assert False, "Could not get Points data."

    name_to_search = asset_name + '.' + data_point_name
    for single_point in points['Items']:

        if name_to_search in single_point["Name"]:
            web_id = single_point["WebId"]
            pi_point_name = single_point["Name"]
            url = single_point["Links"]["RecordedData"]
            full_url = url + '?startTime=*-1d&endTime=*&maxCount=100000'
            try:
                conn.request("GET", full_url, headers=headers)
                res = conn.getresponse()
                r = json.loads(res.read().decode())
            except Exception:
                assert False, "Could not get Required data from PI"

            required_values = []
            # ignoring first value as it is not needed.
            for full_value in r["Items"][1:]:
                required_values.append(full_value['Value'])

            assert required_values != [], "Could not get required values for PI point."

            # The last reading will come from API if we wait for a few moments.
            # So not required to insert the last reading.
            # url_for_last_value = single_point["Links"]["EndValue"]
            # conn.request("GET", url_for_last_value, headers=headers)
            # res = conn.getresponse()
            # r = json.loads(res.read().decode())
            # assert "Value" in r, "Could not fetch the last reading from PI."
            # required_values.append(r["Value"])

            conn.close()
            return required_values

    assert False, "Could not find {} in all PI points".format(name_to_search)


def delete_pi_point(host, admin, password, asset_name, data_point_name):
    """Deletes a given pi point fromPI."""
    username_password = "{}:{}".format(admin, password)

    username_password_b64 = base64.b64encode(username_password.encode('ascii')).decode("ascii")
    headers = {'Authorization': 'Basic %s' % username_password_b64, 'Content-Type': 'application/json'}

    try:
        web_id, pi_point_name = search_for_pi_point(host, admin, password, asset_name, data_point_name)
        if not web_id:
            assert False, "Could not search PI Point {}".format(data_point_name)

        conn = http.client.HTTPSConnection(host, context=ssl._create_unverified_context())
        conn.request("DELETE", "/piwebapi/points/{}".format(web_id), headers=headers)
        r = conn.getresponse()
        assert r.status == 204, "Could not delete" \
                                " the pi point {}.".format(pi_point_name)

        conn.close()

    except Exception as er:
        print("Could not turn off compression for pi point {} due to {}".format(data_point_name, er))
        assert False, "Could not turn off compression for pi point {} due to {}".format(data_point_name, er)


def search_for_pi_point(host, admin, password, asset_name, data_point_name):
    """Searches for a pi point in PI return its web_id and its full name in PI."""
    username_password = "{}:{}".format(admin, password)

    username_password_b64 = base64.b64encode(username_password.encode('ascii')).decode("ascii")
    headers = {'Authorization': 'Basic %s' % username_password_b64, 'Content-Type': 'application/json'}
    try:
        conn = http.client.HTTPSConnection(host, context=ssl._create_unverified_context())
        conn.request("GET", '/piwebapi/dataservers', headers=headers)
        res = conn.getresponse()
        r = json.loads(res.read().decode())
        points_url = r["Items"][0]["Links"]["Points"]
    except Exception:
        assert False, "Could not request data server of PI"

    try:
        conn.request("GET", points_url, headers=headers)
        res = conn.getresponse()
        points = json.loads(res.read().decode())
    except Exception:
        assert False, "Could not get Points data."

    name_to_search = asset_name + '.' + data_point_name
    for single_point in points['Items']:

        if name_to_search in single_point['Name']:
            web_id = single_point['WebId']
            pi_point_name = single_point["Name"]
            conn.close()
            return web_id, pi_point_name

    return None, None


def turn_off_compression_for_pi_point(host, admin, password, asset_name, data_point_name):
    """Turns off compression for a given point in PI."""
    username_password = "{}:{}".format(admin, password)

    username_password_b64 = base64.b64encode(username_password.encode('ascii')).decode("ascii")
    headers = {'Authorization': 'Basic %s' % username_password_b64, 'Content-Type': 'application/json'}
    try:
        web_id, pi_point_name = search_for_pi_point(host, admin, password, asset_name, data_point_name)
        if not web_id:
            assert False, "Could not search PI Point {}".format(data_point_name)

        conn = http.client.HTTPSConnection(host, context=ssl._create_unverified_context())
        attr_name = 'compressing'
        conn.request("PUT", '/piwebapi/points/{}/attributes/{}'.format(web_id, attr_name),
                     body="0", headers=headers)
        r = conn.getresponse()
        conn.close()
        assert r.status == 204, "Could not update the compression" \
                                " for the PI Point {}.".format(pi_point_name)
    except Exception as er:
        print("Could not turn off compression for pi point {} due to {}".format(data_point_name, er))
        assert False, "Could not turn off compression for pi point {} due to {}".format(data_point_name, er)

    print("Turned off compression for the PI Point {} ".format(pi_point_name))
    return


def get_readings_within_range(fledge_url, asset_name, limit, offset, order='desc'):
    """
    Takes a subset of readings from the database.
    Args:
        fledge_url: The url of fledge . By default localhost:8081
        asset_name: The name of asset
        limit: The number of readings to select.
        offset: The index from which the readings have to be selected.
        order: The order of readings to be fetched from database. (desc / asc)
    Returns:
        JSON string containing the subset of readings.
    """
    conn = http.client.HTTPConnection(fledge_url)
    conn.request("GET", '/fledge/asset/{}?limit={}&skip={}&order={}'.format(asset_name, limit, offset, order))
    r = conn.getresponse()
    assert 200 == r.status, "Could not get readings for the asset {} ".format(asset_name)
    r = r.read().decode()
    jdoc = json.loads(r)
    return


def delete_element_hierarchy(host, admin, password, pi_database, af_hierarchy_list):
    """ This method deletes the given hierarchy list form PI."""
    # List of pi databases
    dbs = None
    # PI logical grouping of attributes and child elements
    elements = None
    # List of elements
    url_elements_list = None
    # Element's recorded data url
    url_recorded_data = None
    # Resources in the PI Web API are addressed by WebID, parameter used for deletion of element
    web_id = None
    # List of elements
    url_elements_data_list = None

    username_password = "{}:{}".format(admin, password)
    username_password_b64 = base64.b64encode(username_password.encode('ascii')).decode("ascii")
    headers = {'Authorization': 'Basic %s' % username_password_b64}

    try:
        conn = http.client.HTTPSConnection(host, context=ssl._create_unverified_context())
        conn.request("GET", '/piwebapi/assetservers', headers=headers)
        res = conn.getresponse()
        r = json.loads(res.read().decode())
        dbs = r["Items"][0]["Links"]["Databases"]

        if dbs is not None:
            conn.request("GET", dbs, headers=headers)
            res = conn.getresponse()
            r = json.loads(res.read().decode())
            for el in r["Items"]:
                if el["Name"] == pi_database:
                    url_elements_list = el["Links"]["Elements"]

        af_level_count = 0
        for level in af_hierarchy_list[:-1]:
            if url_elements_list is not None:
                conn.request("GET", url_elements_list, headers=headers)
                res = conn.getresponse()
                r = json.loads(res.read().decode())
                for el in r["Items"]:
                    if el["Name"] == af_hierarchy_list[af_level_count]:
                        url_elements_list = el["Links"]["Elements"]
                        if af_level_count == 0:
                            web_id_root = el["WebId"]
                        af_level_count = af_level_count + 1

        conn.request("DELETE", '/piwebapi/elements/{}'.format(web_id_root), headers=headers)
        r = conn.getresponse()
        assert r.status == 204, "Could not delete element hierarchy of {}".format(af_hierarchy_list)
        conn.close()

    except Exception as er:
        print("Could not delete hierarchy of {} due to {}".format(af_hierarchy_list, er))
        assert False, "Could not delete hierarchy of {} due to {}".format(af_hierarchy_list, er)


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
        time.sleep(2)
        # Turn off south service
        disable_schedule(fledge_url, SOUTH_SERVICE_NAME)
        time.sleep(5)
        # switch off Compression
        dp_name = 'id_datapoint'
        turn_off_compression_for_pi_point(pi_host, pi_admin, pi_passwd, ASSET, dp_name)

        # allow the newly applied compression setting to be saved.
        time.sleep(2)

        # Restart the south service
        enable_schedule(fledge_url, SOUTH_SERVICE_NAME)

        # Wait for the south service to start and ingest a few readings.
        time.sleep(10)
        # Increase the ingest rate.
        # Note down the total readings ingested
        initial_readings = int(get_total_readings(fledge_url))

        print("Initial readings ingested {} \n".format(initial_readings))
        change_category(fledge_url, SOUTH_SERVICE_NAME + "Advanced", "readingsPerSec", 3000)

        # Now we can distort the network.
        distort_network(interface=interface_for_impairment, traffic="outbound",
                        latency=packet_delay,
                        rate_limit=rate_limit, ip=pi_host, port=pi_port, duration=duration)

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
        data_from_pi = get_bulk_data_from_pi(pi_host, pi_admin, pi_passwd, ASSET, dp_name)

        af_hierarchy_level = "fledge/room1/machine1"
        af_hierarchy_level_list = af_hierarchy_level.split("/")
        delete_element_hierarchy(pi_host, pi_admin, pi_passwd, pi_db, af_hierarchy_level_list)
        delete_pi_point(pi_host, pi_admin, pi_passwd, ASSET, dp_name)
        delete_pi_point(pi_host, pi_admin, pi_passwd, ASSET, 'sinusoid')

        assert len(data_from_pi) > 0, "Could not fetch fetch data from PI."
        data_from_pi = [int(d) for d in data_from_pi]
        # opening the csv file in 'w+' mode
        file_csv = open('readings_from_PI.csv', 'w+', newline='')

        # writing the data into the file
        with file_csv:
            write = csv.writer(file_csv)
            for d in data_from_pi:
                write.writerow([d])

        total_readings = int(get_total_readings(fledge_url))
        print("Total readings from Fledge {}\n".format(total_readings))
        discontinuities = [data_from_pi[i] for i in range(len(data_from_pi)-1) if data_from_pi[i+1] != data_from_pi[i]+1]
        print(sorted(discontinuities))
