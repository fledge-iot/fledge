# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test end to end flow with:
        Expression south plugin
        Metadata filter plugin
        PI Server (C) plugin
"""


import http.client
import json
import time
import pytest


__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


SOUTH_PLUGIN = "Expression"
SOUTH_PLUGIN_LANGUAGE = "C"

SVC_NAME = "Expr #1"
ASSET_NAME = "Expression"


class TestE2eExprPi:

    @pytest.fixture
    def start_south_north(self, reset_and_start_foglamp, add_south, enable_schedule, remove_directories,
                          south_branch, foglamp_url, add_filter, filter_branch, filter_name,
                          start_north_pi_server_c, pi_host, pi_port, pi_token):
        """ This fixture clone a south and north repo and starts both south and north instance

            reset_and_start_foglamp: Fixture that resets and starts foglamp, no explicit invocation, called at start
            add_south: Fixture that adds a south service with given configuration with enabled or disabled mode
            remove_directories: Fixture that remove directories created during the tests
        """

        cfg = {"expression": {"value": "tan(x)"}, "minimumX": {"value": "45"}, "maximumX": {"value": "45"},
               "stepX": {"value": "0"}}

        add_south(SOUTH_PLUGIN, south_branch, foglamp_url, service_name=SVC_NAME, config=cfg,
                  plugin_lang=SOUTH_PLUGIN_LANGUAGE, start_service=True)

        filter_cfg = {"enable": "true"}
        filter_plugin = "metadata"
        add_filter(filter_plugin, filter_branch, filter_name, filter_cfg, foglamp_url, SVC_NAME)

        # enable_schedule(foglamp_url, SVC_NAME)

        start_north_pi_server_c(foglamp_url, pi_host, pi_port, pi_token)

        yield self.start_south_north

        remove_directories("/tmp/foglamp-south-{}".format(SOUTH_PLUGIN.lower()))
        remove_directories("/tmp/foglamp-filter-{}".format(filter_plugin))

    def test_end_to_end(self, start_south_north, disable_schedule, foglamp_url, read_data_from_pi, pi_host, pi_admin,
                        pi_passwd, pi_db, wait_time, retries):
        """ Test that data is inserted in FogLAMP using expression south plugin & metadata filter, and sent to PI
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
        assert ASSET_NAME == jdoc[0]["assetCode"]
        assert 0 < jdoc[0]["count"]

        conn.request("GET", '/foglamp/asset/{}'.format(ASSET_NAME))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 0 < len(jdoc)

        read = jdoc[0]["reading"]
        # FOGL-2438 values like tan(45) = 1.61977519054386 gets truncated to 1.6197751905 with ingest
        assert 1.6197751905 == read["Expression"]
        # verify filter is applied and we have {name: value} pair added by metadata filter
        assert "value" == read["name"]

    def _verify_egress(self, read_data_from_pi, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries):

        retry_count = 0
        data_from_pi = None
        while (data_from_pi is None or data_from_pi == []) and retry_count < retries:
            data_from_pi = read_data_from_pi(pi_host, pi_admin, pi_passwd, pi_db, ASSET_NAME, {"Expression", "name"})
            retry_count += 1
            time.sleep(wait_time * 2)

        if data_from_pi is None or retry_count == retries:
            assert False, "Failed to read data from PI"

        assert len(data_from_pi)
        assert "name" in data_from_pi
        assert "Expression" in data_from_pi
        assert isinstance(data_from_pi["name"], list)
        assert isinstance(data_from_pi["Expression"], list)
        assert "value" in data_from_pi["name"]
        # FOGL-2438 values like tan(45) = 1.61977519054386 gets truncated to 1.6197751905 with ingest
        assert 1.6197751905 in data_from_pi["Expression"]
