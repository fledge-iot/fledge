# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test end to end flow with:
        Ingress: HTTP south plugin
        Egress: PI Server (C) plugin & scale-set filter plugin
"""

import os
import subprocess
import http.client
import json
import time
import pytest
import utils


__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


SOUTH_PLUGIN = "http_south"
SVC_NAME = "Room #1"
ASSET_PREFIX = "http-"  # default for HTTP South plugin
ASSET_NAME = "e1"

TASK_NAME = "North v2 PI"

FILTER_PLUGIN = "scale-set"
EGRESS_FILTER_NAME = "SS #1"

READ_KEY = "temperature"
SENSOR_VALUE = 21

# scale(set) factor
SCALE = 9/5
OFFSET = 32
OUTPUT = (SENSOR_VALUE * SCALE) + OFFSET


class TestE2ePiEgressWithScalesetFilter:

    def get_ping_status(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/ping')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        return jdoc

    def get_statistics_map(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/statistics')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        return utils.serialize_stats_map(jdoc)


    @pytest.fixture
    def start_south_north_with_filter(self, reset_and_start_fledge, add_south, south_branch,
                                      remove_data_file, remove_directories, enable_schedule,
                                      fledge_url, add_filter, filter_branch, filter_name,
                                      start_north_pi_server_c, pi_host, pi_port, pi_token):
        """ This fixture clones given south & filter plugin repo, and starts south and PI north C instance with filter

        """
        fogbench_template_path = os.path.join(
            os.path.expandvars('${FLEDGE_ROOT}'), 'data/template.json')
        with open(fogbench_template_path, "w") as f:
            f.write(
                '[{"name": "%s", "sensor_values": '
                '[{"name": "%s", "type": "number", "min": %d, "max": %d, "precision": 0}]}]' % (
                    ASSET_NAME, READ_KEY, SENSOR_VALUE, SENSOR_VALUE))

        add_south(SOUTH_PLUGIN, south_branch, fledge_url, service_name=SVC_NAME)

        start_north_pi_server_c(fledge_url, pi_host, pi_port, pi_token, taskname=TASK_NAME, start_task=False)

        filter_cfg = {"enable": "true",
                      "factors": {"factors": [
                          {
                              "asset": "{}{}".format(ASSET_PREFIX, ASSET_NAME),
                              "datapoint": READ_KEY,
                              "scale": SCALE,
                              "offset": OFFSET
                          }]}
                      }

        add_filter(FILTER_PLUGIN, filter_branch, EGRESS_FILTER_NAME, filter_cfg, fledge_url, TASK_NAME)
        enable_schedule(fledge_url, TASK_NAME)

        yield self.start_south_north_with_filter

        remove_data_file(fogbench_template_path)
        remove_directories("/tmp/fledge-south-{}".format(ASSET_NAME.lower()))
        remove_directories("/tmp/fledge-filter-{}".format(FILTER_PLUGIN))

    def test_end_to_end(self, start_south_north_with_filter, read_data_from_pi, fledge_url, pi_host, pi_admin,
                        pi_passwd, pi_db, wait_time, retries, skip_verify_north_interface):

        subprocess.run(["cd $FLEDGE_ROOT/extras/python; python3 -m fogbench -t ../../data/template.json -p http; cd -"]
                       , shell=True, check=True)
        # let the readings ingress
        time.sleep(wait_time * 2)

        self._verify_ping_and_statistics(fledge_url, count=1, skip_verify_north_interface=skip_verify_north_interface)

        self._verify_ingest(fledge_url, SENSOR_VALUE, read_count=1)

        if not skip_verify_north_interface:
            self._verify_egress(read_data_from_pi, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries)

        tracking_details = utils.get_asset_tracking_details(fledge_url, "Ingest")
        assert len(tracking_details["track"]), "Failed to track Ingest event"
        tracked_item = tracking_details["track"][0]
        assert SVC_NAME == tracked_item["service"]
        assert "http-e1" == tracked_item["asset"]
        assert "http_south" == tracked_item["plugin"]

        tracking_details = utils.get_asset_tracking_details(fledge_url, "Filter")
        assert len(tracking_details["track"]), "Failed to track Filter event"
        tracked_item = tracking_details["track"][0]
        assert TASK_NAME == tracked_item["service"]
        assert "http-e1" == tracked_item["asset"]
        assert "SS #1" == tracked_item["plugin"]

        if not skip_verify_north_interface:
            egress_tracking_details = utils.get_asset_tracking_details(fledge_url,"Egress")
            assert len(egress_tracking_details["track"]), "Failed to track Egress event"
            tracked_item = egress_tracking_details["track"][0]
            assert TASK_NAME == tracked_item["service"]
            assert "http-e1" == tracked_item["asset"]
            assert "OMF" == tracked_item["plugin"]

    def _verify_ping_and_statistics(self, fledge_url, count, skip_verify_north_interface=False):
        ping_response = self.get_ping_status(fledge_url)
        assert count == ping_response["dataRead"]
        if not skip_verify_north_interface:
            assert count == ping_response["dataSent"]

        actual_stats_map = self.get_statistics_map(fledge_url)
        key_asset_name_with_prefix = "{}{}".format(ASSET_PREFIX.upper(), ASSET_NAME.upper())
        assert count == actual_stats_map[key_asset_name_with_prefix]
        assert count == actual_stats_map['READINGS']

        if not skip_verify_north_interface:
            assert count == actual_stats_map['Readings Sent']
            assert count == actual_stats_map[TASK_NAME]

    def _verify_ingest(self, fledge_url, value, read_count):
        asset_name_with_prefix = "{}{}".format(ASSET_PREFIX, ASSET_NAME)
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/asset')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No asset found"
        assert asset_name_with_prefix == jdoc[0]["assetCode"]
        assert read_count == jdoc[0]["count"]

        conn.request("GET", '/fledge/asset/{}'.format(asset_name_with_prefix))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No asset found"
        assert value == jdoc[0]["reading"][READ_KEY]

    def _verify_egress(self, read_data_from_pi, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries):
        retry_count = 0
        data_from_pi = None
        while (data_from_pi is None or data_from_pi == []) and retry_count < retries:
            asset_name_with_prefix = "{}{}".format(ASSET_PREFIX, ASSET_NAME)
            data_from_pi = read_data_from_pi(pi_host, pi_admin, pi_passwd, pi_db, asset_name_with_prefix, {READ_KEY})
            retry_count += 1
            time.sleep(wait_time * 2)

        if data_from_pi is None or retry_count == retries:
            assert False, "Failed to read data from PI"

        assert READ_KEY in data_from_pi
        assert isinstance(data_from_pi[READ_KEY], list)
        assert round(OUTPUT, 1) in [round(n, 1) for n in data_from_pi[READ_KEY]]
