# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import http.client
import json
import time
import pytest


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2024 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

TOKEN = None

def update_policy(fledge_url, policy):
    conn = http.client.HTTPConnection(fledge_url)
    conn.request("PUT", '/fledge/category/password', json.dumps({"policy": policy}),
                 headers={"authorization": TOKEN})
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    assert policy == jdoc['policy']['value']

def test_setup(reset_and_start_fledge, fledge_url, wait_time):
    # Wait for fledge server to start
    time.sleep(wait_time)
    conn = http.client.HTTPConnection(fledge_url)
    conn.request("PUT", '/fledge/category/rest_api', json.dumps({"authentication": "mandatory"}))
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    assert "mandatory" == jdoc['authentication']['value']

    conn.request("PUT", '/fledge/restart', json.dumps({}))
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    assert "Fledge restart has been scheduled." == jdoc['message']

    time.sleep(wait_time * 3)
    conn = http.client.HTTPConnection(fledge_url)
    conn.request("POST", "/fledge/login", json.dumps({"username": "admin", "password": "fledge"}))
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    assert "Logged in successfully." == jdoc['message']
    assert "token" in jdoc
    global TOKEN
    TOKEN = jdoc["token"]

class TestAnyCharPolicy:

    def test_default_policy(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", "/fledge/category/password", headers={"authorization": TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 'Any characters' == jdoc['policy']['value']

    @pytest.mark.parametrize("payload", [
        {"username": "any1", "password": "User@123", "real_name": "AJ", "description": "Test user"},
        {"username": "dianomic", "password": "password", "real_name": "Dianomic", "description": "Dianomic user"},
        {"username": "nerd", "password": "PASSWORD", "real_name": "Nerd", "description": "Nerd user"}
    ])
    def test_create_user(self, fledge_url, payload):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/admin/user", body=json.dumps(payload),
                     headers={"authorization": TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert '{} user has been created successfully.'.format(payload['username']) == jdoc['message']

    def test_update_password(self, fledge_url):
        uid = 4
        payload = {"current_password": "password", "new_password": "0123456"}
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", "/fledge/user/{}/password".format(uid), body=json.dumps(payload),
                     headers={"authorization": TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': 'Password has been updated successfully for user ID:<{}>.'.format(uid)} == jdoc


class TestMixedCasePolicy:

    def test_setup(self, fledge_url):
        update_policy(fledge_url, "Mixed case Alphabetic")

    @pytest.mark.parametrize("payload", [
        {"username": "any2", "password": "Passw0rd", "real_name": "AJ", "description": "Any user"},
        {"username": "dianomic2", "password": "Password", "real_name": "Dianomic", "description": "Dianomic-2 user"},
        {"username": "nerd2", "password": "Pass!23", "real_name": "Nerd", "description": "Nerd-2 user"},
        {"username": "test2", "password": "Pass123", "real_name": "Nerd", "description": "Test-2 user"}
    ])
    def test_create_user(self, fledge_url, payload):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/admin/user", body=json.dumps(payload),
                     headers={"authorization": TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert '{} user has been created successfully.'.format(payload['username']) == jdoc['message']

    def test_update_password(self, fledge_url):
        uid = 6
        payload = {"current_password": "Passw0rd", "new_password": "13pAss1"}
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", "/fledge/user/{}/password".format(uid), body=json.dumps(payload),
                     headers={"authorization": TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': 'Password has been updated successfully for user ID:<{}>.'.format(uid)} == jdoc

class TestMixedAndNumericCasePolicy:

    def test_setup(self, fledge_url):
        update_policy(fledge_url, "Mixed case and numeric")

    @pytest.mark.parametrize("payload", [
        {"username": "any3", "password": "Passw0rd", "real_name": "AJ", "description": "Any User"},
        {"username": "dianomic3", "password": "paSSw0rd", "real_name": "Dianomic", "description": "Dianomic-3 user"},
        {"username": "nerd3", "password": "1ass0Rd", "real_name": "Nerd", "description": "Nerd-3 user"},
        {"username": "test3", "password": "PASSw0rD", "real_name": "Nerd", "description": "Test-3 user"}
    ])
    def test_create_user(self, fledge_url, payload):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/admin/user", body=json.dumps(payload),
                     headers={"authorization": TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert '{} user has been created successfully.'.format(payload['username']) == jdoc['message']

    def test_update_password(self, fledge_url):
        uid = 11
        payload = {"current_password": "paSSw0rd", "new_password": "13pAss1"}
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", "/fledge/user/{}/password".format(uid), body=json.dumps(payload),
                     headers={"authorization": TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': 'Password has been updated successfully for user ID:<{}>.'.format(uid)} == jdoc


class TestMixedAndNumericAndSpecialCasePolicy:

    def test_setup(self, fledge_url):
        update_policy(fledge_url, "Mixed case, numeric and special characters")

    @pytest.mark.parametrize("payload", [
        {"username": "any4", "password": "pAss@!1", "real_name": "AJ", "description": "user"},
        {"username": "dianomic4", "password": "s!@#$%G2", "real_name": "Dianomic", "description": "Dianomic-4 user"},
        {"username": "nerd4", "password": "A(swe1)", "real_name": "Nerd", "description": "Nerd-4 user"},
        {"username": "test4", "password": "Fl@3737", "real_name": "Nerd", "description": "Test-4 user"}
    ])
    def test_create_user(self, fledge_url, payload):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/admin/user", body=json.dumps(payload),
                     headers={"authorization": TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert '{} user has been created successfully.'.format(payload['username']) == jdoc['message']

    def test_update_password(self, fledge_url):
        uid = 17
        payload = {"current_password": "Fl@3737", "new_password": "pAss@!1"}
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", "/fledge/user/{}/password".format(uid), body=json.dumps(payload),
                     headers={"authorization": TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': 'Password has been updated successfully for user ID:<{}>.'.format(uid)} == jdoc

    def test_reset_user(self, fledge_url):
        uid = 17
        payload = {"password": "F0gl@mp!"}
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", "/fledge/admin/{}/reset".format(uid), body=json.dumps(payload),
                     headers={"authorization": TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': 'User with ID:<{}> has been updated successfully.'.format(uid)} == jdoc

