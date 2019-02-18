# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

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

    @pytest.fixture
    def start_south_north(self, reset_and_start_foglamp, add_south, enable_schedule, remove_directories,
                          remove_data_file, south_branch, foglamp_url, add_filter, filter_branch,
                          start_north_pi_server_c, pi_host, pi_port, pi_token, asset_name="e2e_csv_filter_pi"):
        """ This fixture clone a south and north repo and starts both south and north instance

            reset_and_start_foglamp: Fixture that resets and starts foglamp, no explicit invocation, called at start
            add_south: Fixture that adds a south service with given configuration with enabled or disabled mode
            remove_directories: Fixture that remove directories created during the tests
            remove_data_file: Fixture that remove data file created during the tests
        """

        # Define configuration of foglamp south playback service
        south_config = {"assetName": {"value": "{}".format(asset_name)},
                        "csvFilename": {"value": "{}".format(CSV_NAME)},
                        "ingestMode": {"value": "batch"}}

        # Define the CSV data and create expected lists to be verified later
        csv_file_path = os.path.join(os.path.expandvars('${FOGLAMP_ROOT}'), 'data/{}'.format(CSV_NAME))
        f = open(csv_file_path, "w")
        f.write(CSV_HEADERS)
        for _items in CSV_DATA.split(","):
            f.write("\n{}".format(_items))
        f.close()

        south_plugin = "playback"
        add_south(south_plugin, south_branch, foglamp_url, service_name=SVC_NAME,
                  config=south_config, start_service=False)

        filter_cfg = {"enable": "true"}
        # I/P 10, 20, 21, 40 -> O/P 1000, 2000, 2100, 4000
        add_filter("scale", filter_branch, "fscale", filter_cfg, foglamp_url, SVC_NAME)

        # I/P asset_name : e2e_csv_filter_pi > O/P e2e_filters
        filter_cfg_asset = {"config": {"rules": [{"new_asset_name": "e2e_filters",
                                                  "action": "rename",
                                                  "asset_name": asset_name}]},
                            "enable": "true"}
        add_filter("asset", filter_branch, "fasset", filter_cfg_asset, foglamp_url, SVC_NAME)

        # I/P 1000, 2000, 2100, 4000 -> O/P 2000, 2100, 4000
        filter_cfg_rate = {"trigger": "ivalue > 1200", "untrigger": "ivalue < 1100", "preTrigger": "0", "enable": "true"}
        add_filter("rate", filter_branch, "frate", filter_cfg_rate, foglamp_url, SVC_NAME)

        # I/P 1000, 2000, 2100, 40000 -> O/P 2000, 4000
        filter_cfg_delta = {"tolerance": "20", "enable": "true"}
        add_filter("delta", filter_branch, "fdelta", filter_cfg_delta , foglamp_url, SVC_NAME)

        # I/P 2000, 4000 -> O/P rms=3162.2776601684, rms_peak=2000
        filter_cfg_rms = {"assetName": "%a_RMS", "samples": "2", "peak": "true", "enable": "true"}
        add_filter("rms", filter_branch, "frms", filter_cfg_rms, foglamp_url, SVC_NAME)

        add_filter("metadata", filter_branch, "fmeta", filter_cfg, foglamp_url, SVC_NAME)

        # Since playback plugin reads all csv data at once, we cant keep it in enable mode before filter add
        # enable service when all filters all applied
        enable_schedule(foglamp_url, SVC_NAME)

        start_north_pi_server_c(foglamp_url, pi_host, pi_port, pi_token)

        yield self.start_south_north

        remove_directories("/tmp/foglamp-south-{}".format(south_plugin))
        remove_directories("/tmp/foglamp-filter-{}".format("scale"))
        remove_directories("/tmp/foglamp-filter-{}".format("asset"))
        remove_directories("/tmp/foglamp-filter-{}".format("rate"))
        remove_directories("/tmp/foglamp-filter-{}".format("delta"))
        remove_directories("/tmp/foglamp-filter-{}".format("rms"))
        remove_directories("/tmp/foglamp-filter-{}".format("metadata"))
        remove_data_file(csv_file_path)

    def test_end_to_end(self, start_south_north, disable_schedule, foglamp_url, read_data_from_pi, pi_host, pi_admin,
                        pi_passwd, pi_db, wait_time, retries):
        """ Test that data is inserted in FogLAMP using playback south plugin &
            Delta, RMS, Rate, Scale, Asset & Metadata filters, and sent to PI
            start_south_north: Fixture that starts FogLAMP with south service, add filter and north instance
            Assertions:
                on endpoint GET /foglamp/asset
                on endpoint GET /foglamp/asset/<asset_name> with applied data processing filter value
                data received from PI is same as data sent"""

        time.sleep(wait_time)
        conn = http.client.HTTPConnection(foglamp_url)
        self._verify_ingest(conn)

        # disable schedule to stop the service and sending data
        disable_schedule(foglamp_url, SVC_NAME)

        self._verify_egress(read_data_from_pi, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries)

    def _verify_ingest(self, conn):

        conn.request("GET", '/foglamp/asset')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 1 == len(jdoc)
        assert "e2e_filters_RMS" == jdoc[0]["assetCode"]
        assert 0 < jdoc[0]["count"]

        conn.request("GET", '/foglamp/asset/{}'.format("e2e_filters_RMS"))
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
