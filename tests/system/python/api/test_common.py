# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test Common (ping, shutdown, restart) REST API """

import re
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

SEMANTIC_VERSIONING_REGEX = "^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)$"


@pytest.fixture
def get_machine_detail():
    host_name = socket.gethostname()
    # all addresses for the host
    all_ip_addresses_cmd_res = subprocess.run(['hostname', '-I'], stdout=subprocess.PIPE)
    ip_addresses = all_ip_addresses_cmd_res.stdout.decode('utf-8').replace("\n", "").strip().split(" ")
    return host_name, ip_addresses


class TestCommon:

    def do_restart(self, fledge_url, wait_time, retries):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", '/fledge/restart')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert 'Fledge restart has been scheduled.' == jdoc['message']

        time.sleep(wait_time*2)
        tried = 2
        ping_status = None
        while ping_status is None and tried < retries:
            ping_status = self.get_ping(fledge_url)            
            tried += 1
            time.sleep(wait_time)
        if ping_status is None:
            assert False, "Failed to restart in {}s.".format(wait_time * retries)
        return ping_status

    def get_ping(self, fledge_url):
        try:
            conn = http.client.HTTPConnection(fledge_url)
            conn.request("GET", '/fledge/ping')
            r = conn.getresponse()
        except:            
            r = None
        return r

    def test_ping_default(self, reset_and_start_fledge, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/ping')
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
        assert 'Fledge' == jdoc['serviceName']
        assert host_name == jdoc['hostName']
        assert ip_addresses == jdoc['ipAddresses']
        assert 'green' == jdoc['health']
        assert jdoc['authenticationOptional'] is True
        assert jdoc['safeMode'] is False
        assert re.match(SEMANTIC_VERSIONING_REGEX, jdoc['version']) is not None
        assert jdoc['alerts'] == 0

    def test_ping_when_auth_mandatory_allow_ping_true(self, fledge_url, wait_time, retries):
        conn = http.client.HTTPConnection(fledge_url)
        payload = {"allowPing": "true", "authentication": "mandatory"}
        conn.request("PUT", '/fledge/category/rest_api', body=json.dumps(payload))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"

        ping_status = self.do_restart(fledge_url, wait_time, retries*2)        
        
        assert 200 == ping_status.status
        r = ping_status.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert 1 < jdoc['uptime']
        assert isinstance(jdoc['uptime'], int)

    def test_ping_when_auth_mandatory_allow_ping_false(self, reset_and_start_fledge, fledge_url, wait_time, retries):
        # reset_and_start_fledge fixture needed to get default settings back
        conn = http.client.HTTPConnection(fledge_url)
        payload = {"allowPing": "false", "authentication": "mandatory"}
        conn.request("PUT", '/fledge/category/rest_api', body=json.dumps(payload))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"

        ping_status = self.do_restart(fledge_url, wait_time, retries*2)        
        
        assert 401 == ping_status.status
        assert 'Unauthorized' == ping_status.reason

    def test_restart(self):
        assert 1, "Already verified in test_ping_when_auth_mandatory_allow_ping_true"

    def test_shutdown(self, reset_and_start_fledge, fledge_url, wait_time):
        # reset_and_start_fledge fixture needed to get default settings back
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", '/fledge/shutdown')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert 'Fledge shutdown has been scheduled. Wait for few seconds for process cleanup.' == jdoc['message']

        time.sleep(wait_time * 2)
        stat = subprocess.run(["$FLEDGE_ROOT/scripts/fledge status"], shell=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        assert "Fledge not running." == stat.stderr.decode("utf-8").replace("\n", "").strip()
