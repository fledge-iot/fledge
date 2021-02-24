# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test system/python/e2e/test_e2e_modbus_c_pi.py

"""

import http.client
import json
import time
import socket
import pytest
import utils


__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

SOUTH_PLUGIN = "modbus-c"
PLUGIN_NAME = "ModbusC"
SVC_NAME = "modbus-c"
ASSET_NAME = "A15"


class TestE2EModbusCPI:
    def check_connect(self, modbus_host, modbus_port):
        s = socket.socket()
        print("Connecting... Modbus simulator on {}:{}".format(modbus_host, modbus_port))
        result = s.connect_ex((modbus_host, modbus_port))
        if result != 0:
            print("Socket connection failed!!")
            pytest.skip("Test requires a running simulator, please run before starting the test!!")

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
    def start_south_north(self, reset_and_start_fledge, add_south, remove_directories, south_branch, fledge_url,
                          start_north_pi_server_c, pi_host, pi_port, pi_token, modbus_host, modbus_port):
        """ This fixture clone a south and north repo and starts both south and north instance

            reset_and_start_fledge: Fixture that resets and starts fledge, no explicit invocation, called at start
            add_south: Fixture that adds a south service with given configuration with enabled or disabled mode
            remove_directories: Fixture that remove directories created during the tests
        """

        cfg = {"protocol": {"value": "TCP"}, "address": {"value": modbus_host},
               "port": {"value": "{}".format(modbus_port)},
               "map": {"value": {"values": [
                   {"slave": 1, "scale": 1, "offset": 0, "register": 1, "assetName": ASSET_NAME, "name": "front right"},
                   {"slave": 1, "scale": 1, "offset": 0, "register": 2, "assetName": ASSET_NAME, "name": "rear right"},
                   {"slave": 1, "scale": 1, "offset": 0, "register": 3, "assetName": ASSET_NAME, "name": "front left"},
                   {"slave": 1, "scale": 1, "offset": 0, "register": 4, "assetName": ASSET_NAME, "name": "rear left"}
               ]}}
               }

        add_south(SOUTH_PLUGIN, south_branch, fledge_url, service_name=SVC_NAME, config=cfg,
                  plugin_lang="C", start_service=False, plugin_discovery_name=PLUGIN_NAME)

        start_north_pi_server_c(fledge_url, pi_host, pi_port, pi_token)

        yield self.start_south_north

        remove_directories("/tmp/fledge-south-{}".format(SOUTH_PLUGIN.lower()))

    def test_end_to_end(self, start_south_north, enable_schedule, disable_schedule, fledge_url, read_data_from_pi,
                        pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries, skip_verify_north_interface,
                        modbus_host, modbus_port):
        """ Test that data is inserted in Fledge using modbus-c south plugin and sent to PI
            start_south_north: Fixture that starts Fledge with south service and north instance
            skip_verify_north_interface: Flag for assertion of data from Pi web API
            Assertions:
                on endpoint GET /fledge/asset
                on endpoint GET /fledge/asset/<asset_name> with applied data processing filter value
                data received from PI is same as data sent"""

        # self.check_connect(modbus_host, modbus_port)
        """ $ docker logs --follow modbus-device
            start listening at: port:502
            start listening at: port:503
            Quit the loop: Connection reset by peer // on check_connect
        """
        enable_schedule(fledge_url, SVC_NAME)
        time.sleep(wait_time * 2)

        ping_response = self.get_ping_status(fledge_url)
        assert 0 < ping_response["dataRead"]
        if not skip_verify_north_interface:
            assert 0 < ping_response["dataSent"]

        actual_stats_map = self.get_statistics_map(fledge_url)
        assert 0 < actual_stats_map[ASSET_NAME.upper()]
        assert 0 < actual_stats_map['READINGS']
        if not skip_verify_north_interface:
            assert 0 < actual_stats_map['Readings Sent']
            assert 0 < actual_stats_map['NorthReadingsToPI']

        conn = http.client.HTTPConnection(fledge_url)
        self._verify_ingest(conn)

        # disable schedule to stop the service and sending data
        disable_schedule(fledge_url, SVC_NAME)
        if not skip_verify_north_interface:
            self._verify_egress(read_data_from_pi, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries)

        tracking_details = utils.get_asset_tracking_details(fledge_url, "Ingest")
        assert len(tracking_details["track"]), "Failed to track Ingest event"
        tracked_item = tracking_details["track"][0]
        assert SVC_NAME == tracked_item["service"]
        assert ASSET_NAME == tracked_item["asset"]
        assert PLUGIN_NAME == tracked_item["plugin"]

        if not skip_verify_north_interface:
            egress_tracking_details = utils.get_asset_tracking_details(fledge_url, "Egress")
            assert len(egress_tracking_details["track"]), "Failed to track Egress event"
            tracked_item = egress_tracking_details["track"][0]
            assert "NorthReadingsToPI" == tracked_item["service"]
            assert ASSET_NAME == tracked_item["asset"]
            assert "OMF" == tracked_item["plugin"]

    def _verify_ingest(self, conn):
        conn.request("GET", '/fledge/asset')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 1 == len(jdoc)
        assert ASSET_NAME == jdoc[0]["assetCode"]
        assert 0 < jdoc[0]["count"]

        conn.request("GET", '/fledge/asset/{}'.format(ASSET_NAME))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 0 < len(jdoc)

        read = jdoc[0]["reading"]
        assert 11 == read["front right"]
        assert 12 == read["rear right"]
        assert 13 == read["front left"]
        assert 14 == read["rear left"]

    def _verify_egress(self, read_data_from_pi, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries):
        retry_count = 0
        data_from_pi = None
        while (data_from_pi is None or data_from_pi == []) and retry_count < retries:
            data_from_pi = read_data_from_pi(pi_host, pi_admin, pi_passwd, pi_db, ASSET_NAME,
                                             {"front right", "rear right", "front left", "rear left"})
            retry_count += 1
            time.sleep(wait_time * 2)

        if data_from_pi is None or retry_count == retries:
            assert False, "Failed to read data from PI"

        assert len(data_from_pi)
        assert "front right" in data_from_pi
        assert "rear right" in data_from_pi
        assert "front left" in data_from_pi
        assert "rear left" in data_from_pi

        assert isinstance(data_from_pi["front right"], list)
        assert isinstance(data_from_pi["rear right"], list)
        assert isinstance(data_from_pi["front left"], list)
        assert isinstance(data_from_pi["front left"], list)

        assert 11 == data_from_pi["front right"][-1]
        assert 12 == data_from_pi["rear right"][-1]
        assert 13 == data_from_pi["front left"][-1]
        assert 14 == data_from_pi["rear left"][-1]
