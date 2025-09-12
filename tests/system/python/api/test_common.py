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
from conftest import restart_and_wait_for_fledge

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

SEMANTIC_VERSIONING_REGEX = "^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)$"


def get_machine_detail():
    host_name = socket.gethostname()
    # all addresses for the host
    all_ip_addresses_cmd_res = subprocess.run(['hostname', '-I'], stdout=subprocess.PIPE)
    ip_addresses = all_ip_addresses_cmd_res.stdout.decode('utf-8').replace("\n", "").strip().split(" ")
    return host_name, ip_addresses


class TestCommon:

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

        jdoc = restart_and_wait_for_fledge(fledge_url, wait_time)
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

        jdoc = restart_and_wait_for_fledge(fledge_url, wait_time)
        assert 'Unauthorized' == jdoc['message']

    def test_restart(self):
        assert True, "Already verified in test_ping_when_auth_mandatory_allow_ping_true"

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

        from contextlib import closing
        max_retries = 5
        for attempt in range(max_retries):
            try:
                with closing(http.client.HTTPConnection(fledge_url)) as connection:
                    connection.request("GET", "/fledge/ping")
            except (ConnectionRefusedError, socket.error) as ex:
                break
            finally:
                time.sleep(wait_time * 8)
        else:
            raise AssertionError("Fledge did not shut down after maximum retries.")

        stat = subprocess.run(["$FLEDGE_ROOT/scripts/fledge status"], shell=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        assert "Fledge not running." == stat.stderr.decode("utf-8").replace("\n", "").strip()
