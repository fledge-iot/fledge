# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test end to end flow with:
        Playback south plugin
        Delta, RMS, Rate, Scale, Asset & Metadata filter plugins
        PI Server (C) plugin
"""


import http.client
import os
import json
import time
import pytest
import utils


__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


SVC_NAME = "playfilter"
CSV_NAME = "sample.csv"
CSV_HEADERS = "ivalue"
CSV_DATA = "10,20,21,40"

NORTH_TASK_NAME = "NorthReadingsTo_PI"


class TestE2eCsvMultiFltrPi:
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
                          start_north_pi_server_c, pi_host, pi_port, pi_token, asset_name="e2e_csv_filter_pi"):
        """ This fixture clone a south and north repo and starts both south and north instance

            reset_and_start_fledge: Fixture that resets and starts fledge, no explicit invocation, called at start
            add_south: Fixture that adds a south service with given configuration with enabled or disabled mode
            remove_directories: Fixture that remove directories created during the tests
            remove_data_file: Fixture that remove data file created during the tests
        """

        # Define configuration of fledge south playback service
        south_config = {"assetName": {"value": "{}".format(asset_name)},
                        "csvFilename": {"value": "{}".format(CSV_NAME)},
                        "ingestMode": {"value": "batch"}}

        # Define the CSV data and create expected lists to be verified later
        csv_file_path = os.path.join(os.path.expandvars('${FLEDGE_ROOT}'), 'data/{}'.format(CSV_NAME))
        with open(csv_file_path, 'w') as f:
            f.write(CSV_HEADERS)
            for _items in CSV_DATA.split(","):
                f.write("\n{}".format(_items))

        south_plugin = "playback"
        add_south(south_plugin, south_branch, fledge_url, service_name=SVC_NAME,
                  config=south_config, start_service=False)

        filter_cfg_scale = {"enable": "true"}
        # I/P 10, 20, 21, 40 -> O/P 1000, 2000, 2100, 4000
        add_filter("scale", filter_branch, "fscale", filter_cfg_scale, fledge_url, SVC_NAME)

        # I/P asset_name : e2e_csv_filter_pi > O/P e2e_filters
        filter_cfg_asset = {"config": {"rules": [{"new_asset_name": "e2e_filters",
                                                  "action": "rename",
                                                  "asset_name": asset_name}]},
                            "enable": "true"}
        add_filter("asset", filter_branch, "fasset", filter_cfg_asset, fledge_url, SVC_NAME)

        # I/P 1000, 2000, 2100, 4000 -> O/P 2000, 2100, 4000
        filter_cfg_rate = {"trigger": "ivalue > 1200", "untrigger": "ivalue < 1100", "preTrigger": "0", "enable": "true"}
        add_filter("rate", filter_branch, "frate", filter_cfg_rate, fledge_url, SVC_NAME)

        # I/P 1000, 2000, 2100, 4000 -> O/P 2000, 4000
        # Delta in 1st pair (2000-1000) = 1000 (> 20% of 1000) so 2000 is output
        # Delta in second pair (2100-2000) = 100 (<20% of 2000) so 2100 not in output
        # Delta in third pair (4000-2100) = 1900 (>20% of 2100) so 4000 in output
        filter_cfg_delta = {"tolerance": "20", "enable": "true"}
        add_filter("delta", filter_branch, "fdelta", filter_cfg_delta , fledge_url, SVC_NAME)

        # I/P 2000, 4000 -> O/P rms=3162.2776601684, rms_peak=2000
        filter_cfg_rms = {"assetName": "%a_RMS", "samples": "2", "peak": "true", "enable": "true"}
        add_filter("rms", filter_branch, "frms", filter_cfg_rms, fledge_url, SVC_NAME)

        filter_cfg_meta = {"enable": "true"}
        add_filter("metadata", filter_branch, "fmeta", filter_cfg_meta, fledge_url, SVC_NAME)

        # Since playback plugin reads all csv data at once, we cant keep it in enable mode before filter add
        # enable service when all filters all applied
        enable_schedule(fledge_url, SVC_NAME)

        start_north_pi_server_c(fledge_url, pi_host, pi_port, pi_token)

        yield self.start_south_north

        remove_directories("/tmp/fledge-south-{}".format(south_plugin))
        filters = ["scale", "asset", "rate", "delta", "rms", "metadata"]
        for fltr in filters:
            remove_directories("/tmp/fledge-filter-{}".format(fltr))

        remove_data_file(csv_file_path)

    def test_end_to_end(self, start_south_north, disable_schedule, fledge_url, read_data_from_pi, pi_host, pi_admin,
                        pi_passwd, pi_db, wait_time, retries, skip_verify_north_interface):
        """ Test that data is inserted in Fledge using playback south plugin &
            Delta, RMS, Rate, Scale, Asset & Metadata filters, and sent to PI
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
        assert 1 == ping_response["dataRead"]
        if not skip_verify_north_interface:
            assert 1 == ping_response["dataSent"]

        actual_stats_map = self.get_statistics_map(fledge_url)
        assert 1 == actual_stats_map["e2e_filters_RMS".upper()]
        assert 1 == actual_stats_map['READINGS']
        if not skip_verify_north_interface:
            assert 1 == actual_stats_map['Readings Sent']
            assert 1 == actual_stats_map['NorthReadingsToPI']

        if not skip_verify_north_interface:
            self._verify_egress(read_data_from_pi, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries)

        tracking_details = utils.get_asset_tracking_details(fledge_url, "Ingest")
        assert len(tracking_details["track"]), "Failed to track Ingest event"
        tracked_item = tracking_details["track"][0]
        assert SVC_NAME == tracked_item["service"]
        assert "e2e_filters_RMS" == tracked_item["asset"]
        assert "playback" == tracked_item["plugin"]

        tracking_details = utils.get_asset_tracking_details(fledge_url, "Filter")
        assert len(tracking_details["track"]), "Failed to track Filter event"
        tracked_item = tracking_details["track"][0]
        assert SVC_NAME == tracked_item["service"]
        assert "e2e_csv_filter_pi" == tracked_item["asset"]
        assert "fscale" == tracked_item["plugin"]

        tracked_item = tracking_details["track"][1]
        assert SVC_NAME == tracked_item["service"]
        assert "e2e_csv_filter_pi" == tracked_item["asset"]
        assert "fasset" == tracked_item["plugin"]

        tracked_item = tracking_details["track"][2]
        assert SVC_NAME == tracked_item["service"]
        assert "e2e_filters" == tracked_item["asset"]
        assert "fasset" == tracked_item["plugin"]

        tracked_item = tracking_details["track"][3]
        assert SVC_NAME == tracked_item["service"]
        assert "e2e_filters" == tracked_item["asset"]
        assert "frate" == tracked_item["plugin"]

        tracked_item = tracking_details["track"][4]
        assert SVC_NAME == tracked_item["service"]
        assert "e2e_filters" == tracked_item["asset"]
        assert "fdelta" == tracked_item["plugin"]

        tracked_item = tracking_details["track"][5]
        assert SVC_NAME == tracked_item["service"]
        assert "e2e_filters_RMS" == tracked_item["asset"]
        assert "frms" == tracked_item["plugin"]

        tracked_item = tracking_details["track"][6]
        assert SVC_NAME == tracked_item["service"]
        assert "e2e_filters_RMS" == tracked_item["asset"]
        assert "fmeta" == tracked_item["plugin"]

        if not skip_verify_north_interface:
            egress_tracking_details = utils.get_asset_tracking_details(fledge_url,"Egress")
            assert len(egress_tracking_details["track"]), "Failed to track Egress event"
            tracked_item = egress_tracking_details["track"][0]
            assert "NorthReadingsToPI" == tracked_item["service"]
            assert "e2e_filters_RMS" == tracked_item["asset"]
            assert "OMF" == tracked_item["plugin"]

    def _verify_ingest(self, conn):

        conn.request("GET", '/fledge/asset')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 1 == len(jdoc)
        assert "e2e_filters_RMS" == jdoc[0]["assetCode"]
        assert 0 < jdoc[0]["count"]

        conn.request("GET", '/fledge/asset/{}'.format("e2e_filters_RMS"))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 0 < len(jdoc)

        read = jdoc[0]["reading"]
        assert 2000.0 == read["ivaluepeak"]
        assert 3162.2776601684 == read["ivalue"]
        assert "value" == read["name"]

    def _verify_egress(self, read_data_from_pi, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries):

        retry_count = 0
        data_from_pi = None
        while (data_from_pi is None or data_from_pi == []) and retry_count < retries:
            data_from_pi = read_data_from_pi(pi_host, pi_admin, pi_passwd, pi_db,
                                             "e2e_filters_RMS", {"ivalue", "ivaluepeak", "name"})
            retry_count += 1
            time.sleep(wait_time * 2)

        if data_from_pi is None or retry_count == retries:
            assert False, "Failed to read data from PI"

        assert 3162.2776601684 == data_from_pi["ivalue"][-1]
        assert 2000 == data_from_pi["ivaluepeak"][-1]
        assert "value" == data_from_pi["name"][-1]
