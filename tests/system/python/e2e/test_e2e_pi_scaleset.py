# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

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

READ_KEY = "temprature"
SENSOR_VALUE = 21

# scale(set) factor
SCALE = 9/5
OFFSET = 32
OUTPUT = (SENSOR_VALUE * SCALE) + OFFSET


class TestE2ePiEgressWithScalesetFilter:

    def get_ping_status(self, foglamp_url):
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("GET", '/foglamp/ping')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        return jdoc

    def get_statistics_map(self, foglamp_url):
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("GET", '/foglamp/statistics')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        return utils.serialize_stats_map(jdoc)

    @pytest.fixture
    def start_south_north_with_filter(self, reset_and_start_foglamp, add_south, south_branch,
                                      remove_data_file, remove_directories,
                                      foglamp_url, add_filter, filter_branch, filter_name,
                                      start_north_pi_server_c, pi_host, pi_port, pi_token):
        """ This fixture clones given south & filter plugin repo, and starts south and PI north C instance with filter

        """
        fogbench_template_path = os.path.join(
            os.path.expandvars('${FOGLAMP_ROOT}'), 'data/template.json')
        with open(fogbench_template_path, "w") as f:
            f.write(
                '[{"name": "%s", "sensor_values": '
                '[{"name": "%s", "type": "number", "min": %d, "max": %d, "precision": 0}]}]' % (
                    ASSET_NAME, READ_KEY, SENSOR_VALUE, SENSOR_VALUE))

        add_south(SOUTH_PLUGIN, south_branch, foglamp_url, service_name=SVC_NAME)

        start_north_pi_server_c(foglamp_url, pi_host, pi_port, pi_token, taskname=TASK_NAME)

        filter_cfg = {"enable": "true",
                      "factors": {"factors": [
                          {
                              "asset": "{}{}".format(ASSET_PREFIX, ASSET_NAME),
                              "datapoint": READ_KEY,
                              "scale": SCALE,
                              "offset": OFFSET
                          }]}
                      }

        add_filter(FILTER_PLUGIN, filter_branch, EGRESS_FILTER_NAME, filter_cfg, foglamp_url, TASK_NAME)

        yield self.start_south_north_with_filter

        remove_data_file(fogbench_template_path)
        remove_directories("/tmp/foglamp-south-{}".format(ASSET_NAME.lower()))
        remove_directories("/tmp/foglamp-filter-{}".format(FILTER_PLUGIN))

    def test_end_to_end(self, start_south_north_with_filter, read_data_from_pi, foglamp_url, pi_host, pi_admin,
                        pi_passwd, pi_db, wait_time, retries, skip_verify_north_interface,
                        disable_schedule, enable_schedule):

        subprocess.run(["cd $FOGLAMP_ROOT/extras/python; python3 -m fogbench -t ../../data/template.json -p http; cd -"]
                       , shell=True, check=True)
        # let the readings ingress
        time.sleep(wait_time)

        self._verify_ping_and_statistics(foglamp_url, count=1)

        self._verify_ingest(foglamp_url, SENSOR_VALUE, read_count=1)

        if not skip_verify_north_interface:
            self._verify_egress(read_data_from_pi, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries)

    def _verify_ping_and_statistics(self, foglamp_url, count):
        ping_response = self.get_ping_status(foglamp_url)
        assert count == ping_response["dataRead"]
        assert count == ping_response["dataSent"]

        actual_stats_map = self.get_statistics_map(foglamp_url)
        key_asset_name_with_prefix = "{}{}".format(ASSET_PREFIX.upper(), ASSET_NAME.upper())
        assert count == actual_stats_map[key_asset_name_with_prefix]
        assert count == actual_stats_map['READINGS']
        assert count == actual_stats_map[TASK_NAME]
        assert count == actual_stats_map['Readings Sent']

    def _verify_ingest(self, foglamp_url, value, read_count):
        asset_name_with_prefix = "{}{}".format(ASSET_PREFIX, ASSET_NAME)
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("GET", '/foglamp/asset')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No asset found"
        assert asset_name_with_prefix == jdoc[0]["assetCode"]
        assert read_count == jdoc[0]["count"]

        conn.request("GET", '/foglamp/asset/{}'.format(asset_name_with_prefix))
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
        assert OUTPUT in data_from_pi[READ_KEY]
