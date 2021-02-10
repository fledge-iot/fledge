# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test system/python/e2e/test_e2e_modbus_c_rtu_pi.py

"""

import http.client
import json
import time
import pytest
import serial
import utils


__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

SOUTH_PLUGIN = "modbus-c"
PLUGIN_NAME = "ModbusC"
SVC_NAME = "modbus-c"
ASSET_NAME_1 = "adam4015"
ASSET_NAME_2 = "adam4017"


class TestE2EModbusC_RTU_PI:
    def check_connect(self, modbus_serial_port, modbus_baudrate):
        print("Checking serial port {} at baudrate {}.....".format(modbus_serial_port, modbus_baudrate))
        try:
            ser = serial.Serial(modbus_serial_port, modbus_baudrate, timeout=1)
        except:
            print("Socket connection failed!!")
            pytest.skip("Test requires a connected serial port!!")

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
    def start_south_north(self, reset_and_start_fledge, add_south, skip_verify_north_interface, remove_directories,
                          south_branch, fledge_url, start_north_pi_server_c, pi_host, pi_port, pi_token,
                          modbus_serial_port, modbus_baudrate):
        """ This fixture clone a south and north repo and starts both south and north instance

            reset_and_start_fledge: Fixture that resets and starts fledge, no explicit invocation, called at start
            add_south: Fixture that adds a south service with given configuration with enabled or disabled mode
            remove_directories: Fixture that remove directories created during the tests
        """
        self.check_connect(modbus_serial_port, modbus_baudrate)
        cfg = {"protocol": {"value": "RTU"}, "asset": {"value": "modbus"},
               "device": {"value": modbus_serial_port}, "baud": {"value": modbus_baudrate},
               "map": {"value": {"values": [
                   {"offset": -1.1, "assetName": "adam4017", "slave": 2, "name": "dwyer_temperature", "register": 0,
                    "scale": 0.00178},
                   {"offset": 0, "assetName": "adam4017", "slave": 2, "name": "dwyer_humidity", "register": 1,
                    "scale": 0.00152},
                   {"offset": -50, "assetName": "adam4015", "slave": 3, "name": "pt100_0", "register": 0,
                    "scale": 0.00305},
                   {"offset": -50, "assetName": "adam4015", "slave": 3, "name": "pt100_1", "register": 1,
                    "scale": 0.00305}
               ]}}
               }

        add_south(SOUTH_PLUGIN, south_branch, fledge_url, service_name=SVC_NAME, config=cfg,
                  plugin_lang="C", start_service=False, plugin_discovery_name=PLUGIN_NAME)

        if not skip_verify_north_interface:
            start_north_pi_server_c(fledge_url, pi_host, pi_port, pi_token)

        yield self.start_south_north

        remove_directories("/tmp/fledge-south-{}".format(SOUTH_PLUGIN.lower()))

    def test_end_to_end(self, start_south_north, enable_schedule, disable_schedule, fledge_url, read_data_from_pi, pi_host, pi_admin,
                        pi_passwd, pi_db, wait_time, retries, skip_verify_north_interface):
        """ Test that data is inserted in Fledge using modbus-c south plugin and sent to PI
            start_south_north: Fixture that starts Fledge with south service and north instance
            skip_verify_north_interface: Flag for assertion of data from Pi web API
            Assertions:
                on endpoint GET /fledge/asset
                on endpoint GET /fledge/asset/<asset_name> with applied data processing filter value
                data received from PI is same as data sent"""

        enable_schedule(fledge_url, SVC_NAME)
        time.sleep(wait_time * 2)

        ping_response = self.get_ping_status(fledge_url)
        assert 0 < ping_response["dataRead"]

        actual_stats_map = self.get_statistics_map(fledge_url)
        assert 0 < actual_stats_map[ASSET_NAME_1.upper()]
        assert 0 < actual_stats_map[ASSET_NAME_2.upper()]

        assert 0 < actual_stats_map['READINGS']

        conn = http.client.HTTPConnection(fledge_url)
        self._verify_ingest(conn)

        # disable schedule to stop the service and sending data
        disable_schedule(fledge_url, SVC_NAME)
        if not skip_verify_north_interface:
            assert 0 < ping_response["dataSent"]
            assert 0 < actual_stats_map['NorthReadingsToPI']
            assert 0 < actual_stats_map['Readings Sent']
            self._verify_egress(read_data_from_pi, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                                ASSET_NAME_1, {"pt100_1", "pt100_0"})
            self._verify_egress(read_data_from_pi, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                                ASSET_NAME_2, {"dwyer_temperature", "dwyer_humidity"})

    def _verify_ingest(self, conn):
        conn.request("GET", '/fledge/asset')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 2 == len(jdoc)
        assert [ASSET_NAME_1, ASSET_NAME_2] == [jdoc[0]["assetCode"], jdoc[1]["assetCode"]]
        assert 0 < jdoc[0]["count"]
        assert 0 < jdoc[1]["count"]

        conn.request("GET", '/fledge/asset/{}'.format(ASSET_NAME_1))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 0 < len(jdoc)

        read = jdoc[0]["reading"]
        assert read["pt100_1"] is not None
        assert read["pt100_0"] is not None

        conn.request("GET", '/fledge/asset/{}'.format(ASSET_NAME_2))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 0 < len(jdoc)

        read = jdoc[0]["reading"]
        assert read["dwyer_temperature"] is not None
        assert read["dwyer_humidity"] is not None

    def _verify_egress(self, read_data_from_pi, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries, asset,
                       datapoints):

        retry_count = 0
        data_from_pi = None
        while (data_from_pi is None or data_from_pi == []) and retry_count < retries:
            data_from_pi = read_data_from_pi(pi_host, pi_admin, pi_passwd, pi_db, asset, datapoints)
            retry_count += 1
            time.sleep(wait_time * 2)

        if data_from_pi is None or retry_count == retries:
            assert False, "Failed to read data from PI"

        assert len(data_from_pi)
        for itm in datapoints:
            assert itm in data_from_pi
            assert isinstance(data_from_pi[itm], list)
