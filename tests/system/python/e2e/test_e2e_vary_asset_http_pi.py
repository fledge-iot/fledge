# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test system/python/e2e/test_e2e_vary_asset_http_pi.py

"""

import http.client
import json
import time
from datetime import datetime, timezone
import uuid
import pytest
import utils


__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class TestE2EAssetHttpPI:
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


    def _verify_egress(self, read_data_from_pi, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries, asset_name,
                       sensor_data, sensor_data_2):
        retry_count = 0
        data_from_pi = None
        while (data_from_pi is None or data_from_pi == []) and retry_count < retries:
            data_from_pi = read_data_from_pi(pi_host, pi_admin, pi_passwd, pi_db, asset_name, {"a", "b", "a2", "b2"})
            retry_count += 1
            time.sleep(wait_time * 2)

        if data_from_pi is None or retry_count == retries:
            assert False, "Failed to read data from PI"

        assert data_from_pi["b"][-1] == 0.0
        assert data_from_pi["b"][-2] == 0.0
        assert data_from_pi["b"][-3] == sensor_data_2[0]["b"]
        assert data_from_pi["b"][-4] == sensor_data[2]["b"]
        assert data_from_pi["b"][-5] == sensor_data[1]["b"]
        assert data_from_pi["b"][-6] == 0.0

        assert data_from_pi["a"][-1] == sensor_data_2[2]["a"]
        assert data_from_pi["a"][-2] == 0.0
        assert data_from_pi["a"][-3] == 0.0
        assert data_from_pi["a"][-4] == 0.0
        assert data_from_pi["a"][-5] == sensor_data[1]["a"]
        assert data_from_pi["a"][-6] == sensor_data[0]["a"]

        assert data_from_pi["b2"][-1] == 0.0
        assert data_from_pi["b2"][-2] == sensor_data_2[1]["b2"]
        assert data_from_pi["b2"][-3] == 0.0
        assert data_from_pi["b2"][-4] == 0.0
        assert data_from_pi["b2"][-5] == 0.0
        assert data_from_pi["b2"][-6] == 0.0

        assert data_from_pi["a2"][-1] == 0.0
        assert data_from_pi["a2"][-2] == sensor_data_2[1]["a2"]
        assert data_from_pi["a2"][-3] == 0.0
        assert data_from_pi["a2"][-4] == 0.0
        assert data_from_pi["a2"][-5] == 0.0
        assert data_from_pi["a2"][-6] == 0.0

    @pytest.fixture
    def start_south_north(self, reset_and_start_fledge, add_south, start_north_pi_server_c, remove_directories,
                          south_branch, fledge_url, pi_host, pi_port, pi_token):
        """ This fixture clone a south repo and starts both south and north instance
            reset_and_start_fledge: Fixture that resets and starts fledge, no explicit invocation, called at start
            add_south: Fixture that adds a south service with given configuration
            start_north_pi_server_c: Fixture that starts PI north task
            remove_directories: Fixture that remove directories created during the tests"""

        south_plugin = "http"
        add_south("http_south", south_branch, fledge_url, config={"assetNamePrefix": {"value": ""}},
                  service_name="http_south")
        start_north_pi_server_c(fledge_url, pi_host, pi_port, pi_token)

        yield self.start_south_north

        # Cleanup code that runs after the caller test is over
        remove_directories("/tmp/fledge-south-{}".format(south_plugin))

    def test_end_to_end(self, start_south_north, read_data_from_pi, fledge_url, pi_host, pi_admin, pi_passwd, pi_db,
                        wait_time, retries, skip_verify_north_interface):
        """ Test that data is inserted in Fledge and sent to PI
            start_south_north: Fixture that starts Fledge with south and north instance
            read_data_from_pi: Fixture to read data from PI
            skip_verify_north_interface: Flag for assertion of data from Pi web API
            Assertions:
                on endpoint GET /fledge/asset
                on endpoint GET /fledge/asset/<asset_name>
                data received from PI is same as data sent"""

        # Allow http_south service to come up and register before sending data
        time.sleep(wait_time)
        conn = http.client.HTTPConnection(fledge_url)

        # Send data to fledge-south-http
        conn_http_south = http.client.HTTPConnection("localhost:6683")

        asset_name = "e2e_varying"
        # 2 list having mixed data simulating different sensors
        # (sensors coming up and down, sensors throwing int and float data)
        sensor_data = [{"a": 1}, {"a": 2, "b": 3}, {"b": 4}]
        sensor_data_2 = [{"b": 1.1}, {"a2": 2, "b2": 3}, {"a": 4.0}]
        for d in sensor_data + sensor_data_2:
            tm = str(datetime.now(timezone.utc).astimezone())
            data = [{"asset": "{}".format(asset_name), "timestamp": "{}".format(tm), "key": str(uuid.uuid4()),
                     "readings": d}]
            conn_http_south.request("POST", '/sensor-reading', json.dumps(data))
            r = conn_http_south.getresponse()
            assert 200 == r.status
            r = r.read().decode()
            jdoc = json.loads(r)
            assert {'result': 'success'} == jdoc

        # Allow some buffer so that data is ingested before retrieval
        time.sleep(wait_time)

        ping_response = self.get_ping_status(fledge_url)
        assert 6 == ping_response["dataRead"]
        if not skip_verify_north_interface:
            assert 6 == ping_response["dataSent"]

        actual_stats_map = self.get_statistics_map(fledge_url)
        assert 6 == actual_stats_map[asset_name.upper()]
        assert 6 == actual_stats_map['READINGS']
        if not skip_verify_north_interface:
            assert 6 == actual_stats_map['Readings Sent']
            assert 6 == actual_stats_map['NorthReadingsToPI']

        conn.request("GET", '/fledge/asset')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        retval = json.loads(r)
        assert len(retval) == 1
        assert asset_name == retval[0]["assetCode"]
        assert 6 == retval[0]["count"]

        conn.request("GET", '/fledge/asset/{}'.format(asset_name))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        retval = json.loads(r)

        assert sensor_data_2[2] == retval[0]["reading"]
        assert sensor_data_2[1] == retval[1]["reading"]
        assert sensor_data_2[0] == retval[2]["reading"]
        assert sensor_data[2] == retval[3]["reading"]
        assert sensor_data[1] == retval[4]["reading"]
        assert sensor_data[0] == retval[5]["reading"]

        if not skip_verify_north_interface:
            # Allow some buffer so that data is ingested in PI before fetching using PI Web API
            time.sleep(wait_time)
            self._verify_egress(read_data_from_pi, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries, asset_name,
                                sensor_data, sensor_data_2)

        tracking_details = utils.get_asset_tracking_details(fledge_url, "Ingest")
        assert len(tracking_details["track"]), "Failed to track Ingest event"
        tracked_item = tracking_details["track"][0]
        assert "http_south" == tracked_item["service"]
        assert asset_name == tracked_item["asset"]
        assert "http_south" == tracked_item["plugin"]

        if not skip_verify_north_interface:
            egress_tracking_details = utils.get_asset_tracking_details(fledge_url,"Egress")
            assert len(egress_tracking_details["track"]), "Failed to track Egress event"
            tracked_item = egress_tracking_details["track"][0]
            assert "NorthReadingsToPI" == tracked_item["service"]
            assert asset_name == tracked_item["asset"]
            assert "OMF" == tracked_item["plugin"]




