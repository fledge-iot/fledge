# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test Common (ping, shutdown, restart) REST API """

import socket
import subprocess
import http.client
import time
import json
import pytest


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.fixture
def get_machine_detail():
    host_name = socket.gethostname()
    # all addresses for the host
    all_ip_addresses_cmd_res = subprocess.run(['hostname', '-I'], stdout=subprocess.PIPE)
    ip_addresses = all_ip_addresses_cmd_res.stdout.decode('utf-8').replace("\n", "").strip().split(" ")
    return host_name, ip_addresses


class TestCommon:

    def test_ping_default(self, reset_and_start_foglamp, foglamp_url):
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("GET", '/foglamp/ping')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        host_name, ip_addresses = get_machine_detail()
        assert 1 < jdoc['uptime']
        assert isinstance(jdoc['uptime'], int)
        assert 0 == jdoc['dataRead']
        assert 0 == jdoc['dataSent']
        assert 0 == jdoc['dataPurged']
        assert 'FogLAMP' == jdoc['serviceName']
        assert host_name == jdoc['hostName']
        assert ip_addresses == jdoc['ipAddresses']
        assert 'green' == jdoc['health']
        assert jdoc['authenticationOptional'] is True
        assert jdoc['safeMode'] is False

    @pytest.mark.skip(reason='Not Implemented yet')
    def test_ping_when_auth_mandatory(self):
        # TODO: Its a bit tricky to automate user input on shell when foglamp start
        pass

    def test_restart(self, foglamp_url, wait_time):
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("PUT", '/foglamp/restart')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert 'FogLAMP restart has been scheduled.' == jdoc['message']

        time.sleep(wait_time * 2)
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("GET", '/foglamp/ping')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert 1 < jdoc['uptime']
        assert isinstance(jdoc['uptime'], int)

    def test_shutdown(self, foglamp_url, wait_time):
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("PUT", '/foglamp/shutdown')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert 'FogLAMP shutdown has been scheduled. Wait for few seconds for process cleanup.' == jdoc['message']

        time.sleep(wait_time * 2)
        stat = subprocess.run(["$FOGLAMP_ROOT/scripts/foglamp status"], shell=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        assert "FogLAMP not running." == stat.stderr.decode("utf-8").replace("\n", "").strip()
