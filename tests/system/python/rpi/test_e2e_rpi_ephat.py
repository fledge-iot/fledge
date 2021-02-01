# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test end to end flow with:
        Ingress: ePhat south plugin
        Egress: PI Server (C) plugin
"""

import os
import http.client
import json
import time
import pytest
import utils
from urllib.parse import quote
from collections import Counter


__author__ = "Praveen Garg, Vaibhav Singhal"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


SOUTH_PLUGIN = "envirophat"
SVC_NAME = "Room-1"

ASSET_PREFIX = "e_"  # default for envirophat South plugin

ASSET_NAME_W = "weather"
SENSOR_READ_KEY_W = {"temperature", "altitude", "pressure"}

ASSET_NAME_M = "magnetometer"
SENSOR_READ_KEY_M = {"x", "y", "z"}

ASSET_NAME_A = "accelerometer"
SENSOR_READ_KEY_A = {"x", "y", "z"}

ASSET_NAME_C = "rgb"
SENSOR_READ_KEY_C = {"r", "g", "b"}

TASK_NAME = "North v2 PI"


@pytest.mark.skipif('raspberrypi' != os.uname()[1] and 'raspizero' != os.uname()[1], reason="RPi only (ePhat) test")
# sysname='Linux', nodename='raspberrypi', release='4.14.98+', version='#1200 ', machine='armv6l'
class TestE2eRPiEphatEgress:

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
    def start_south_north(self, reset_and_start_fledge, add_south, south_branch, disable_schedule,
                          remove_data_file, skip_verify_north_interface, remove_directories, enable_schedule,
                          fledge_url, start_north_pi_server_c, pi_host, pi_port, pi_token, wait_time):
        """ This fixture clones given south & filter plugin repo, and starts south and PI north C instance

        """

        add_south(SOUTH_PLUGIN, south_branch, fledge_url, service_name=SVC_NAME)

        if not skip_verify_north_interface:
            start_north_pi_server_c(fledge_url, pi_host, pi_port, pi_token, taskname=TASK_NAME, start_task=False)

        # let the readings ingress
        time.sleep(wait_time)
        disable_schedule(fledge_url, SVC_NAME)

        if not skip_verify_north_interface:
            enable_schedule(fledge_url, TASK_NAME)

        yield self.start_south_north

        remove_directories("/tmp/fledge-south-{}".format(SOUTH_PLUGIN))

    def test_end_to_end(self, start_south_north, read_data_from_pi, fledge_url, pi_host, pi_admin,
                        pi_passwd, pi_db, wait_time, retries, skip_verify_north_interface):

        # let the readings egress
        time.sleep(wait_time * 2)
        self._verify_ping_and_statistics(fledge_url, skip_verify_north_interface)

        self._verify_ingest(fledge_url)

        if not skip_verify_north_interface:
            self._verify_egress(read_data_from_pi, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries)

    def _verify_ping_and_statistics(self, fledge_url, skip_verify_north_interface):
        ping_response = self.get_ping_status(fledge_url)
        assert ping_response["dataRead"]
        if not skip_verify_north_interface:
            assert ping_response["dataSent"]

        actual_stats_map = self.get_statistics_map(fledge_url)
        assert actual_stats_map["{}{}".format(ASSET_PREFIX.upper(), ASSET_NAME_W.upper())]
        assert actual_stats_map["{}{}".format(ASSET_PREFIX.upper(), ASSET_NAME_M.upper())]
        assert actual_stats_map["{}{}".format(ASSET_PREFIX.upper(), ASSET_NAME_A.upper())]
        assert actual_stats_map["{}{}".format(ASSET_PREFIX.upper(), ASSET_NAME_C.upper())]
        assert actual_stats_map['READINGS']
        if not skip_verify_north_interface:
            assert actual_stats_map[TASK_NAME]
            assert actual_stats_map['Readings Sent']

    def _verify_ingest(self, fledge_url):
        asset_name_with_prefix_w = "{}{}".format(ASSET_PREFIX, ASSET_NAME_W)
        asset_name_with_prefix_m = "{}{}".format(ASSET_PREFIX, ASSET_NAME_M)
        asset_name_with_prefix_a = "{}{}".format(ASSET_PREFIX, ASSET_NAME_A)
        asset_name_with_prefix_c = "{}{}".format(ASSET_PREFIX, ASSET_NAME_C)
        conn = http.client.HTTPConnection(fledge_url)

        conn.request("GET", '/fledge/asset')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No asset found"
        actual_assets = [i["assetCode"] for i in jdoc]
        assert asset_name_with_prefix_w in actual_assets
        assert asset_name_with_prefix_m in actual_assets
        assert asset_name_with_prefix_a in actual_assets
        assert asset_name_with_prefix_c in actual_assets
        assert jdoc[0]["count"]
        expected_assets = Counter([asset_name_with_prefix_w, asset_name_with_prefix_m,
                                   asset_name_with_prefix_a, asset_name_with_prefix_c])
        assert Counter(actual_assets) == expected_assets

        # fledge/asset/envirophat%2Fweather
        conn.request("GET", '/fledge/asset/{}'.format(quote(asset_name_with_prefix_w, safe='')))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc_asset = json.loads(r)

        for _sensor in SENSOR_READ_KEY_W:
            assert len(jdoc_asset), "No data found for asset '{}'".format(asset_name_with_prefix_w)
            assert jdoc_asset[0]["reading"][_sensor] is not None
            conn.request("GET", '/fledge/asset/{}/{}'.format(quote(asset_name_with_prefix_w, safe=''), _sensor))
            r = conn.getresponse()
            assert 200 == r.status
            r = r.read().decode()
            jdoc = json.loads(r)
            assert len(jdoc), "No data found for asset '{}' and datapoint '{}'".format(asset_name_with_prefix_w, _sensor)

        # fledge/asset/envirophat%2Fmagnetometer
        conn.request("GET", '/fledge/asset/{}'.format(quote(asset_name_with_prefix_m, safe='')))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc_asset = json.loads(r)

        for _sensor in SENSOR_READ_KEY_M:
            assert len(jdoc_asset), "No data found for asset '{}'".format(asset_name_with_prefix_m)
            assert jdoc_asset[0]["reading"][_sensor] is not None
            conn.request("GET", '/fledge/asset/{}/{}'.format(quote(asset_name_with_prefix_m, safe=''), _sensor))
            r = conn.getresponse()
            assert 200 == r.status
            r = r.read().decode()
            jdoc = json.loads(r)
            assert len(jdoc), "No data found for asset '{}' and datapoint '{}'".format(asset_name_with_prefix_m,
                                                                                       _sensor)

        # fledge/asset/envirophat%2Faccelerometer
        conn.request("GET", '/fledge/asset/{}'.format(quote(asset_name_with_prefix_a, safe='')))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc_asset = json.loads(r)

        for _sensor in SENSOR_READ_KEY_A:
            assert len(jdoc_asset), "No data found for asset '{}'".format(asset_name_with_prefix_a)
            assert jdoc_asset[0]["reading"][_sensor] is not None
            conn.request("GET", '/fledge/asset/{}/{}'.format(quote(asset_name_with_prefix_a, safe=''), _sensor))
            r = conn.getresponse()
            assert 200 == r.status
            r = r.read().decode()
            jdoc = json.loads(r)
            assert len(jdoc), "No data found for asset '{}' and datapoint '{}'".format(asset_name_with_prefix_a,
                                                                                       _sensor)
        # fledge/asset/envirophat%2Frgb
        conn.request("GET", '/fledge/asset/{}'.format(quote(asset_name_with_prefix_c, safe='')))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc_asset = json.loads(r)

        for _sensor in SENSOR_READ_KEY_C:
            assert len(jdoc_asset), "No data found for asset '{}'".format(asset_name_with_prefix_c)
            assert jdoc_asset[0]["reading"][_sensor] is not None
            conn.request("GET", '/fledge/asset/{}/{}'.format(quote(asset_name_with_prefix_c, safe=''), _sensor))
            r = conn.getresponse()
            assert 200 == r.status
            r = r.read().decode()
            jdoc = json.loads(r)
            assert len(jdoc), "No data found for asset '{}' and datapoint '{}'".format(asset_name_with_prefix_c,
                                                                                       _sensor)

    def _verify_egress(self, read_data_from_pi, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries):
        retry_count = 0

        data_from_pi_w = None
        data_from_pi_m = None
        data_from_pi_a = None
        data_from_pi_c = None

        asset_name_with_prefix_w = "{}{}".format(ASSET_PREFIX, ASSET_NAME_W)
        asset_name_with_prefix_a = "{}{}".format(ASSET_PREFIX, ASSET_NAME_A)
        asset_name_with_prefix_m = "{}{}".format(ASSET_PREFIX, ASSET_NAME_M)
        asset_name_with_prefix_c = "{}{}".format(ASSET_PREFIX, ASSET_NAME_C)

        while (data_from_pi_w is None or data_from_pi_w == []) and retry_count < retries:
            data_from_pi_w = read_data_from_pi(pi_host, pi_admin, pi_passwd, pi_db, asset_name_with_prefix_w,
                                               SENSOR_READ_KEY_W)

            data_from_pi_m = read_data_from_pi(pi_host, pi_admin, pi_passwd, pi_db, asset_name_with_prefix_m,
                                               SENSOR_READ_KEY_M)

            data_from_pi_a = read_data_from_pi(pi_host, pi_admin, pi_passwd, pi_db, asset_name_with_prefix_a,
                                               SENSOR_READ_KEY_A)

            data_from_pi_c = read_data_from_pi(pi_host, pi_admin, pi_passwd, pi_db, asset_name_with_prefix_c,
                                               SENSOR_READ_KEY_C)

            retry_count += 1
            time.sleep(wait_time * 2)

        if data_from_pi_w is None or data_from_pi_m is None or data_from_pi_a is None or data_from_pi_c is None\
                or retry_count == retries:
            assert False, "Failed to read data from PI"

        print("Data read from PI System:\nWeather={}\nMagnetometer={}\nAccelerometer={}\nrgbColor={}\n".format(
            data_from_pi_w, data_from_pi_m, data_from_pi_a, data_from_pi_c))

        for w in SENSOR_READ_KEY_W:
            assert w in data_from_pi_w
            abs_sum_w = sum([abs(n) for n in data_from_pi_w[w]])
            print("Weather (sum of {} absolute values), Sensor={}".format(len(data_from_pi_w[w]), w), abs_sum_w)
            assert abs_sum_w, "Sum of weather sensor absolute values is 0"

        for a in SENSOR_READ_KEY_A:
            assert a in data_from_pi_a
            abs_sum_a = sum([abs(n) for n in data_from_pi_a[a]])
            print("Accelerometer (sum of {} absolute values, Sensor={}".format(len(data_from_pi_a[a]), a), abs_sum_a)
            assert abs_sum_a, "Sum of accelerometer sensor absolute values is 0"

        for m in SENSOR_READ_KEY_M:
            assert m in data_from_pi_m
            abs_sum_m = sum([abs(n) for n in data_from_pi_m[m]])
            print("Magnetometer (sum of {} absolute values), Sensor={}".format(len(data_from_pi_m[m]), m), abs_sum_m)
            assert abs_sum_m, "Sum of magnetometer sensor absolute values is 0"

        for c in SENSOR_READ_KEY_C:
            assert c in data_from_pi_c
            abs_sum_c = sum([abs(n) for n in data_from_pi_c[c]])
            print("RGB colors (sum of {} absolute values), Sensor={}".format(len(data_from_pi_c[c]), c), abs_sum_c)
            assert abs_sum_c, "Sum of rgb sensors absolute values is 0"
