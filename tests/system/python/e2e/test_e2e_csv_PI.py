# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test system/python/test_e2e_csv_PI.py

"""
import os
import http.client
import json
import time
import pytest
from collections import Counter
import utils

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


CSV_NAME = "sample.csv"
CSV_HEADERS = "ivalue,fvalue,svalue"
CSV_DATA = [{'ivalue': 1, 'fvalue': 1.1, 'svalue': 'abc'},
            {'ivalue': 0, 'fvalue': 0.0, 'svalue': 'def'},
            {'ivalue': -1, 'fvalue': -1.1, 'svalue': 'ghi'}]

NORTH_TASK_NAME = "NorthReadingsTo_PI"

_data_str = {}


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


@pytest.fixture
def start_south_north(reset_and_start_fledge, add_south, start_north_pi_server_c, remove_data_file,
                      remove_directories, south_branch, fledge_url, pi_host, pi_port, pi_token,
                      asset_name="end_to_end_csv"):
    """ This fixture clone a south repo and starts both south and north instance
        reset_and_start_fledge: Fixture that resets and starts fledge, no explicit invocation, called at start
        add_south: Fixture that starts any south service with given configuration
        start_north_pi_server_c: Fixture that starts PI north task
        remove_data_file: Fixture that remove data file created during the tests
        remove_directories: Fixture that remove directories created during the tests"""

    # Define configuration of fledge south playback service
    south_config = {"assetName": {"value": "{}".format(asset_name)}, "csvFilename": {"value": "{}".format(CSV_NAME)},
                    "ingestMode": {"value": "batch"}}

    # Define the CSV data and create expected lists to be verified later
    csv_file_path = os.path.join(os.path.expandvars('${FLEDGE_ROOT}'), 'data/{}'.format(CSV_NAME))
    f = open(csv_file_path, "w")
    f.write(CSV_HEADERS)
    _heads = CSV_HEADERS.split(",")
    for c_data in CSV_DATA:
        temp_data = []
        for _head in _heads:
            temp_data.append(str(c_data[_head]))
        row = ','.join(temp_data)
        f.write("\n{}".format(row))
    f.close()

    # Prepare list of values for each header
    for _head in _heads:
        tmp_list = []
        for c_data in CSV_DATA:
            tmp_list.append(c_data[_head])
        _data_str[_head] = tmp_list

    south_plugin = "playback"
    add_south(south_plugin, south_branch, fledge_url, config=south_config)
    start_north_pi_server_c(fledge_url, pi_host, pi_port, pi_token)

    yield start_south_north

    # Cleanup code that runs after the caller test is over
    remove_data_file(csv_file_path)
    remove_directories("/tmp/fledge-south-{}".format(south_plugin))


def _verify_egress(read_data_from_pi, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries, asset_name):
    retry_count = 0
    data_from_pi = None
    while (data_from_pi is None or data_from_pi == []) and retry_count < retries:
        data_from_pi = read_data_from_pi(pi_host, pi_admin, pi_passwd, pi_db, asset_name,
                                         CSV_HEADERS.split(","))
        retry_count += 1
        time.sleep(wait_time*2)

    if data_from_pi is None or retry_count == retries:
        assert False, "Failed to read data from PI"

    for _head in CSV_HEADERS.split(","):
        assert Counter(data_from_pi[_head][-len(CSV_DATA):]) == Counter(_data_str[_head])


class TestE2E_CSV_PI:
    def test_e2e_csv_pi(self, start_south_north, read_data_from_pi, fledge_url, pi_host, pi_admin, pi_passwd, pi_db,
                        wait_time, retries, skip_verify_north_interface, asset_name="end_to_end_csv"):
        """ Test that data is inserted in Fledge and sent to PI
            start_south_north: Fixture that starts Fledge with south and north instance
            read_data_from_pi: Fixture to read data from PI
            skip_verify_north_interface: Flag for assertion of data from Pi web API
            Assertions:
                on endpoint GET /fledge/asset
                on endpoint GET /fledge/asset/<asset_name>
                data received from PI is same as data sent"""

        conn = http.client.HTTPConnection(fledge_url)
        time.sleep(wait_time)

        ping_response = get_ping_status(fledge_url)
        assert len(CSV_DATA) == ping_response["dataRead"]
        if not skip_verify_north_interface:
            assert len(CSV_DATA) == ping_response["dataSent"]

        actual_stats_map = get_statistics_map(fledge_url)
        assert len(CSV_DATA) == actual_stats_map[asset_name.upper()]
        assert len(CSV_DATA) == actual_stats_map['READINGS']
        if not skip_verify_north_interface:
            assert len(CSV_DATA) == actual_stats_map['Readings Sent']
            assert len(CSV_DATA) == actual_stats_map['NorthReadingsToPI']

        conn.request("GET", '/fledge/asset')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        retval = json.loads(r)
        assert len(retval) == 1
        assert asset_name == retval[0]["assetCode"]
        assert len(CSV_DATA) == retval[0]["count"]

        for _head in CSV_HEADERS.split(","):
            conn.request("GET", '/fledge/asset/{}/{}'.format(asset_name, _head))
            r = conn.getresponse()
            assert 200 == r.status
            r = r.read().decode()
            retval = json.loads(r)
            _actual_read_list = []
            for _el in retval:
                _actual_read_list.append(_el[_head])
            assert Counter(_actual_read_list) == Counter(_data_str[_head])

        if not skip_verify_north_interface:
            _verify_egress(read_data_from_pi, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries, asset_name)

        tracking_details = utils.get_asset_tracking_details(fledge_url, "Ingest")
        assert len(tracking_details["track"]), "Failed to track Ingest event"
        tracked_item = tracking_details["track"][0]
        assert "play" == tracked_item["service"]
        assert asset_name == tracked_item["asset"]
        assert "playback" == tracked_item["plugin"]

        if not skip_verify_north_interface:
            egress_tracking_details = utils.get_asset_tracking_details(fledge_url,"Egress")
            assert len(egress_tracking_details["track"]), "Failed to track Egress event"
            tracked_item = egress_tracking_details["track"][0]
            assert "NorthReadingsToPI" == tracked_item["service"]
            assert asset_name == tracked_item["asset"]
            assert "OMF" == tracked_item["plugin"]
