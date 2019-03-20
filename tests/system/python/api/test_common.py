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

    def do_restart(self, foglamp_url):
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("PUT", '/foglamp/restart')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert 'FogLAMP restart has been scheduled.' == jdoc['message']

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

    def test_ping_when_auth_mandatory_allow_ping_true(self, foglamp_url, wait_time):
        conn = http.client.HTTPConnection(foglamp_url)
        payload = {"allowPing": "true", "authentication": "mandatory"}
        conn.request("PUT", '/foglamp/category/rest_api', body=json.dumps(payload))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"

        self.do_restart(foglamp_url)

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

    def test_ping_when_auth_mandatory_allow_ping_false(self, reset_and_start_foglamp, foglamp_url, wait_time):
        # reset_and_start_foglamp fixture needed to get default settings back
        conn = http.client.HTTPConnection(foglamp_url)
        payload = {"allowPing": "false", "authentication": "mandatory"}
        conn.request("PUT", '/foglamp/category/rest_api', body=json.dumps(payload))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"

        self.do_restart(foglamp_url)

        time.sleep(wait_time * 2)
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("GET", '/foglamp/ping')
        r = conn.getresponse()
        assert 403 == r.status
        assert 'Forbidden' == r.reason

    def test_restart(self):
        assert 1, "Already verified in test_ping_when_auth_mandatory_allow_ping_true"

    def test_shutdown(self, reset_and_start_foglamp, foglamp_url, wait_time):
        # reset_and_start_foglamp fixture needed to get default settings back
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
