# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test authentication REST API """

import http.client
import json
import time
import pytest


__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

TOKEN = None

# TODO: Cover scenario when auth is optional and negative scenarios


@pytest.fixture
def change_to_auth_mandatory(reset_and_start_foglamp, foglamp_url, wait_time):
        # Wait for foglamp server to start
        time.sleep(wait_time)
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("PUT", '/foglamp/category/rest_api', json.dumps({"authentication": "mandatory"}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "mandatory" == jdoc['authentication']['value']

        conn.request("PUT", '/foglamp/restart', json.dumps({}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "FogLAMP restart has been scheduled." == jdoc['message']


class TestAuthenticationAPI:
        def test_login_username_regular_user(self, change_to_auth_mandatory, foglamp_url, wait_time):
                time.sleep(wait_time * 2)
                conn = http.client.HTTPConnection(foglamp_url)
                conn.request("POST", "/foglamp/login", json.dumps({"username": "user", "password": "foglamp"}))
                r = conn.getresponse()
                assert 200 == r.status
                r = r.read().decode()
                jdoc = json.loads(r)
                assert "Logged in successfully" == jdoc['message']
                assert "token" in jdoc
                assert not jdoc['admin']
                global TOKEN
                TOKEN = jdoc["token"]

        def test_logout_me(self, foglamp_url):
                conn = http.client.HTTPConnection(foglamp_url)
                print(TOKEN)
                conn.request("PUT", '/foglamp/logout', headers={"authorization": TOKEN})
                r = conn.getresponse()
                assert 200 == r.status
                r = r.read().decode()
                jdoc = json.loads(r)
                assert jdoc['logout']


