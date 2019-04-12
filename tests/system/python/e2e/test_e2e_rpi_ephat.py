# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test end to end flow with:
        Ingress: ePhat south plugin
        Egress: PI Server (C) plugin
"""

import platform
import http.client
import json
import time
import pytest
import utils
from urllib.parse import quote
from collections import Counter


__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


SOUTH_PLUGIN = "envirophat"
SVC_NAME = "Room-1"
ASSET_PREFIX = "envirophat/"  # default for envirophat South plugin
ASSET_NAME = "weather"
SENSOR_READ_KEY = "temperature"

TASK_NAME = "North v2 PI"


@pytest.mark.skipif(platform.platform().find("arm") == -1, reason="RPi only (ePhat) test")
# RPi Linux-4.14.98-v7+-armv7l-with-debian-9.8
class TestE2eRPiEphatEgress:

    # def test_Rpi(self):
    #     assert -1 != platform.platform().find("arm"), "ePhat tests are expected to be run on RPi only!"

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
    def start_south_north(self, reset_and_start_foglamp, add_south, south_branch,
                          remove_data_file, remove_directories, enable_schedule, foglamp_url,
                          start_north_pi_server_c, pi_host, pi_port, pi_token, wait_time):
        """ This fixture clones given south & filter plugin repo, and starts south and PI north C instance with filter

        """

        add_south(SOUTH_PLUGIN, south_branch, foglamp_url, service_name=SVC_NAME)

        start_north_pi_server_c(foglamp_url, pi_host, pi_port, pi_token, taskname=TASK_NAME, start_task=False)

        # let the readings ingress
        time.sleep(wait_time)

        enable_schedule(foglamp_url, TASK_NAME)

        yield self.start_south_north

        remove_directories("/tmp/foglamp-south-{}".format(SOUTH_PLUGIN))

    def test_end_to_end(self, start_south_north, read_data_from_pi, foglamp_url, pi_host, pi_admin,
                        pi_passwd, pi_db, wait_time, retries, skip_verify_north_interface):

        self._verify_ping_and_statistics(foglamp_url)

        self._verify_ingest(foglamp_url)

        # if not skip_verify_north_interface:
        #     self._verify_egress(read_data_from_pi, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries)

    def _verify_ping_and_statistics(self, foglamp_url):
        ping_response = self.get_ping_status(foglamp_url)
        assert ping_response["dataRead"]
        # assert ping_response["dataSent"]

        actual_stats_map = self.get_statistics_map(foglamp_url)
        key_asset_name_with_prefix = "{}{}".format(ASSET_PREFIX.upper(), ASSET_NAME.upper())
        assert actual_stats_map[key_asset_name_with_prefix]
        assert actual_stats_map['READINGS']
        # assert actual_stats_map[TASK_NAME]
        # assert actual_stats_map['Readings Sent']

    def _verify_ingest(self, foglamp_url):
        asset_name_with_prefix = "{}{}".format(ASSET_PREFIX, ASSET_NAME)
        conn = http.client.HTTPConnection(foglamp_url)

        conn.request("GET", '/foglamp/asset')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No asset found"
        actual_assets = [i["assetCode"] for i in jdoc]
        assert asset_name_with_prefix in actual_assets
        assert jdoc[0]["count"]
        expected_assets = Counter(["envirophat/magnetometer", "envirophat/rgb", "envirophat/accelerometer", "envirophat/weather"])
        assert Counter(actual_assets) == expected_assets

        # foglamp/asset/envirophat%2Fweather
        conn.request("GET", '/foglamp/asset/{}'.format(quote(asset_name_with_prefix, safe='')))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No asset found"
        assert jdoc[0]["reading"][SENSOR_READ_KEY]

        weather_sensors = ["temperature", "altitude", "pressure"]
        for s in weather_sensors:
            conn.request("GET", '/foglamp/asset/{}/{}'.format(quote(asset_name_with_prefix, safe=''), s))
            r = conn.getresponse()
            assert 200 == r.status
            r = r.read().decode()
            jdoc = json.loads(r)
            assert len(jdoc), "No asset found"

        # verify summary (avg|min|max)
        # foglamp/asset/envirophat%2Fweather/temperature/summary

    # def _verify_egress(self, read_data_from_pi, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries):
    #     retry_count = 0
    #     data_from_pi = None
    #     while (data_from_pi is None or data_from_pi == []) and retry_count < retries:
    #         asset_name_with_prefix = "{}{}".format(ASSET_PREFIX, ASSET_NAME)
    #         data_from_pi = read_data_from_pi(pi_host, pi_admin, pi_passwd, pi_db, asset_name_with_prefix, {READ_KEY})
    #         retry_count += 1
    #         time.sleep(wait_time * 2)
    #
    #     if data_from_pi is None or retry_count == retries:
    #         assert False, "Failed to read data from PI"
    #
    #     assert SENSOR_READ_KEY in data_from_pi
    #     assert isinstance(data_from_pi[SENSOR_READ_KEY], list)
    #     for n in data_from_pi[SENSOR_READ_KEY]]:
    #         assert round(n, 1) > 0.0
