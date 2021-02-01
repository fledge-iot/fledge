# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test end to end flow with:
        Playback south plugin
        FFT Filter on playback south plugin and Threshold on PI north
        PI Server (C) plugin
"""


import http.client
import os
import json
import time
import pytest
import utils
import subprocess

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2019 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


SVC_NAME = "playfilter"
CSV_NAME = "wind-data.csv"
CSV_HEADERS = "10 Min Std Dev,10 Min Sampled Avg"

NORTH_TASK_NAME = "NorthReadingsTo_PI"

ASSET = "e2e_fft_threshold"


class TestE2eFilterFFTThreshold:
    def get_ping_status(self, fledge_url):
        _connection = http.client.HTTPConnection(fledge_url)
        _connection.request("GET", '/fledge/ping')
        r = _connection.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        return jdoc

    def get_statistics_map(self, fledge_url):
        _connection = http.client.HTTPConnection(fledge_url)
        _connection.request("GET", '/fledge/statistics')
        r = _connection.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        return utils.serialize_stats_map(jdoc)


    @pytest.fixture
    def start_south_north(self, reset_and_start_fledge, add_south, enable_schedule, remove_directories,
                          remove_data_file, south_branch, fledge_url, add_filter, filter_branch,
                          start_north_pi_server_c, pi_host, pi_port, pi_token, asset_name=ASSET):
        """ This fixture clone a south and north repo and starts both south and north instance

            reset_and_start_fledge: Fixture that resets and starts fledge, no explicit invocation, called at start
            add_south: Fixture that adds a south service with given configuration with enabled or disabled mode
            remove_directories: Fixture that remove directories created during the tests
            remove_data_file: Fixture that remove data file created during the tests
        """

        # Define configuration of Fledge playback service
        south_config = {"assetName": {"value": "{}".format(asset_name)},
                        "csvFilename": {"value": "{}".format(CSV_NAME)},
                        "fieldNames": {"value": "10 Min Std Dev"},
                        "ingestMode": {"value": "batch"}}

        csv_dest = os.path.join(os.path.expandvars('${FLEDGE_ROOT}'), 'data/{}'.format(CSV_NAME))
        csv_src_file = os.path.join(os.path.expandvars('${FLEDGE_ROOT}'), 'tests/system/python/data/{}'.format(CSV_NAME))

        cmd = 'cp {} {}'.format(csv_src_file, csv_dest)
        status = subprocess.call(cmd, shell=True)
        if status != 0:
            if status < 0:
                print("Killed by signal", status)
            else:
                print("copy command failed with return code - ", status)

        south_plugin = "playback"
        add_south(south_plugin, south_branch, fledge_url, service_name=SVC_NAME,
                  config=south_config, start_service=False)

        filter_cfg_fft = {"asset": ASSET, "lowPass": "10", "highPass": "30", "enable": "true"}
        add_filter("fft", filter_branch, "FFT Filter", filter_cfg_fft, fledge_url, SVC_NAME)

        # Since playback plugin reads all csv data at once, we cant keep it in enable mode before filter add
        # enable service when all filters all applied
        enable_schedule(fledge_url, SVC_NAME)

        start_north_pi_server_c(fledge_url, pi_host, pi_port, pi_token, taskname=NORTH_TASK_NAME,
                                start_task=False)

        # Add threshold filter at north side
        filter_cfg_threshold = {"expression": "Band00 > 30", "enable": "true"}
        # TODO: Apply a better expression with AND / OR with data points e.g. OR Band01 > 19
        add_filter("threshold", filter_branch, "fltr_threshold", filter_cfg_threshold, fledge_url, NORTH_TASK_NAME)
        enable_schedule(fledge_url, NORTH_TASK_NAME)

        yield self.start_south_north

        remove_directories("/tmp/fledge-south-{}".format(south_plugin))
        filters = ["fft", "threshold"]
        for fltr in filters:
            remove_directories("/tmp/fledge-filter-{}".format(fltr))

        remove_data_file(csv_dest)

    def test_end_to_end(self, start_south_north, disable_schedule, fledge_url, read_data_from_pi, pi_host, pi_admin,
                        pi_passwd, pi_db, wait_time, retries, skip_verify_north_interface):
        """ Test that data is inserted in Fledge using playback south plugin &
            FFT filter, and sent to PI after passing through threshold filter
            start_south_north: Fixture that starts Fledge with south service, add filter and north instance
            skip_verify_north_interface: Flag for assertion of data from Pi web API
            Assertions:
                on endpoint GET /fledge/asset
                on endpoint GET /fledge/asset/<asset_name> with applied data processing filter value
                data received from PI is same as data sent"""

        time.sleep(wait_time)
        conn = http.client.HTTPConnection(fledge_url)

        self._verify_ingest(conn)

        # disable schedule to stop the service and sending data
        disable_schedule(fledge_url, SVC_NAME)

        ping_response = self.get_ping_status(fledge_url)
        assert 6 == ping_response["dataRead"]
        if not skip_verify_north_interface:
            assert 1 == ping_response["dataSent"]

        actual_stats_map = self.get_statistics_map(fledge_url)
        assert 6 == actual_stats_map[ASSET.upper() + " FFT"]
        assert 6 == actual_stats_map['READINGS']
        if not skip_verify_north_interface:
            assert 1 == actual_stats_map['Readings Sent']
            assert 1 == actual_stats_map[NORTH_TASK_NAME]

        if not skip_verify_north_interface:
            self._verify_egress(read_data_from_pi, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries)

        tracking_details = utils.get_asset_tracking_details(fledge_url, "Ingest")
        assert len(tracking_details["track"]), "Failed to track Ingest event"
        tracked_item = tracking_details["track"][0]
        assert SVC_NAME == tracked_item["service"]
        assert "e2e_fft_threshold FFT" == tracked_item["asset"]
        assert "playback" == tracked_item["plugin"]

        # TODO: FOGL:3440,FOGL:3441 Add asset tracker entry for fft and threshold filters
        # tracking_details = self.get_asset_tracking_details(fledge_url, "Filter")
        # assert len(tracking_details["track"]), "Failed to track Ingest event"
        # tracked_item = tracking_details["track"][0]
        # assert "playfilter" == tracked_item["service"]
        # assert "e2e_fft_threshold FFT" == tracked_item["asset"]
        # assert "FFT Filter" == tracked_item["plugin"]

        if not skip_verify_north_interface:
            egress_tracking_details = utils.get_asset_tracking_details(fledge_url,"Egress")
            assert len(egress_tracking_details["track"]), "Failed to track Egress event"
            tracked_item = egress_tracking_details["track"][0]
            assert NORTH_TASK_NAME == tracked_item["service"]
            assert "e2e_fft_threshold FFT" == tracked_item["asset"]
            assert "OMF" == tracked_item["plugin"]


    def _verify_ingest(self, conn):
        conn.request("GET", '/fledge/asset')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc)

        assert ASSET + " FFT" == jdoc[0]["assetCode"]
        assert 0 < jdoc[0]["count"]

        conn.request("GET", '/fledge/asset/{}'.format(ASSET + "%20FFT"))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 0 < len(jdoc)
        # print(jdoc)
        read = jdoc[0]["reading"]
        assert read["Band00"]
        assert read["Band01"]
        assert read["Band02"]

    def _verify_egress(self, read_data_from_pi, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries):
        retry_count = 0
        data_from_pi = None
        while (data_from_pi is None or data_from_pi == []) and retry_count < retries:
            data_from_pi = read_data_from_pi(pi_host, pi_admin, pi_passwd, pi_db,
                                             ASSET + " FFT", {"Band00"})
            retry_count += 1
            time.sleep(wait_time * 2)

        if data_from_pi is None or retry_count == retries:
            assert False, "Failed to read data from PI"

        assert 30 < data_from_pi["Band00"][-1]
