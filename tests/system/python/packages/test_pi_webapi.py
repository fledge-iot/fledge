# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test sending data to PI using Web API

"""

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2019 Dianomic Systems Inc"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

import subprocess
import http.client
import json
import pytest
import os
import time
import utils


TEMPLATE_NAME = "template.json"
ASSET = "FOGL-2964-e2e-CoAP"
DATAPOINT = "sensor"
DATAPOINT_VALUE = 20


def get_ping_status(fledge_url):
    _connection = http.client.HTTPConnection(fledge_url)
    _connection.request("GET", '/fledge/ping')
    r = _connection.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    return jdoc


def get_statistics_map(fledge_url):
    _connection = http.client.HTTPConnection(fledge_url)
    _connection.request("GET", '/fledge/statistics')
    r = _connection.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    return utils.serialize_stats_map(jdoc)


def get_asset_tracking_details(fledge_url, event=None):
    _connection = http.client.HTTPConnection(fledge_url)
    uri = '/fledge/track'
    if event:
        uri += '?event={}'.format(event)
    _connection.request("GET", uri)
    r = _connection.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    return jdoc


def _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries, asset_name):
    retry_count = 0
    data_from_pi = None

    af_hierarchy_level = "fledge/room1/machine1"
    af_hierarchy_level_list = af_hierarchy_level.split("/")
    type_id = 1
    recorded_datapoint = "{}measurement_{}".format(type_id, asset_name)
    # Name of asset in the PI server
    PI_ASSET_NAME = "{}-type{}".format(asset_name, type_id)

    while (data_from_pi is None or data_from_pi == []) and retry_count < retries:
        data_from_pi = read_data_from_pi_web_api(pi_host, pi_admin, pi_passwd, pi_db, af_hierarchy_level_list, PI_ASSET_NAME, {recorded_datapoint})
        retry_count += 1
        time.sleep(wait_time*2)

    if data_from_pi is None or retry_count == retries:
        assert False, "Failed to read data from PI"

    assert data_from_pi[recorded_datapoint][-1] == DATAPOINT_VALUE


@pytest.fixture
def start_south_north(clean_setup_fledge_packages, add_south, start_north_task_omf_web_api, remove_data_file,
                      fledge_url, pi_host, pi_port, pi_admin, pi_passwd, asset_name=ASSET):
    """ This fixture
        clean_setup_fledge_packages: purge the fledge* packages and install latest for given repo url
        add_south: Fixture that adds a south service with given configuration
        start_north_task_omf_web_api: Fixture that starts PI north task
        remove_data_file: Fixture that remove data file created during the tests """

    # Define the template file for fogbench
    fogbench_template_path = os.path.join(
        os.path.expandvars('${FLEDGE_ROOT}'), 'data/{}'.format(TEMPLATE_NAME))
    with open(fogbench_template_path, "w") as f:
        f.write(
            '[{"name": "%s", "sensor_values": '
            '[{"name": "%s", "type": "number", "min": %d, "max": %d, "precision": 0}]}]' % (
                asset_name, DATAPOINT, DATAPOINT_VALUE, DATAPOINT_VALUE))

    south_plugin = "coap"
    # south_branch does not matter as these are archives.fledge-iot.org version install
    add_south(south_plugin, None, fledge_url, service_name="CoAP FOGL-2964", installation_type='package')
    start_north_task_omf_web_api(fledge_url, pi_host, pi_port, pi_user=pi_admin, pi_pwd=pi_passwd)

    yield start_south_north

    # Cleanup code that runs after the caller test is over
    remove_data_file(fogbench_template_path)


class TestPackagesCoAP_PI_WebAPI:

    def test_end_to_end(self, start_south_north, read_data_from_pi_web_api, fledge_url, pi_host, pi_admin, pi_passwd, pi_db,
                        wait_time, retries, skip_verify_north_interface, asset_name=ASSET):
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

        conn = http.client.HTTPConnection(fledge_url)
        subprocess.run(["cd $FLEDGE_ROOT/extras/python; python3 -m fogbench -t ../../data/{}; cd -".format(TEMPLATE_NAME)],
                       shell=True, check=True)

        time.sleep(wait_time)

        ping_response = get_ping_status(fledge_url)
        assert 1 == ping_response["dataRead"]

        retry_count = 1
        sent = 0
        if not skip_verify_north_interface:
            while retries > retry_count:
                sent = ping_response["dataSent"]
                if sent == 1:
                    break
                else:
                    time.sleep(wait_time)

                retry_count += 1
                ping_response = get_ping_status(fledge_url)

            assert 1 == sent, "Failed to send data via PI Web API using Basic auth"

        actual_stats_map = get_statistics_map(fledge_url)
        assert 1 == actual_stats_map[asset_name.upper()]
        assert 1 == actual_stats_map['READINGS']
        if not skip_verify_north_interface:
            assert 1 == actual_stats_map['Readings Sent']
            assert 1 == actual_stats_map['NorthReadingsToPI_WebAPI']

        conn.request("GET", '/fledge/asset')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        retval = json.loads(r)
        assert len(retval) == 1
        assert asset_name == retval[0]["assetCode"]
        assert 1 == retval[0]["count"]

        conn.request("GET", '/fledge/asset/{}'.format(asset_name))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        retval = json.loads(r)
        assert {DATAPOINT: DATAPOINT_VALUE} == retval[0]["reading"]

        if not skip_verify_north_interface:
            egress_tracking_details = get_asset_tracking_details(fledge_url, "Egress")
            assert len(egress_tracking_details["track"]), "Failed to track Egress event"
            tracked_item = egress_tracking_details["track"][0]
            assert "NorthReadingsToPI_WebAPI" == tracked_item["service"]
            assert asset_name == tracked_item["asset"]
            assert "OMF" == tracked_item["plugin"]

            _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries, asset_name)
