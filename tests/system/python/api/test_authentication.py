# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test authentication REST API """

import os
import subprocess
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
def change_to_auth_mandatory(reset_and_start_fledge, fledge_url, wait_time):
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


class TestAuthenticationAPI:
    def test_login_username_regular_user(self, change_to_auth_mandatory, fledge_url, wait_time):
        time.sleep(wait_time * 2)
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/login", json.dumps({"username": "user", "password": "fledge"}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "Logged in successfully" == jdoc['message']
        assert "token" in jdoc
        assert not jdoc['admin']
        global TOKEN
        TOKEN = jdoc["token"]

    def test_logout_me(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", '/fledge/logout', headers={"authorization": TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert jdoc['logout']

    def test_login_username_admin(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/login", json.dumps({"username": "admin", "password": "fledge"}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "Logged in successfully" == jdoc['message']
        assert "token" in jdoc
        assert jdoc['admin']
        global TOKEN
        TOKEN = jdoc["token"]

    @pytest.mark.parametrize(("query", "expected_values"), [
        ('', {'users': [{'userId': 1, 'roleId': 1, 'userName': 'admin', 'accessMethod': 'any', 'realName': 'Admin user',
                         'description': 'admin user'},
                        {'userId': 2, 'roleId': 2, 'userName': 'user', 'accessMethod': 'any', 'realName': 'Normal user',
                         'description': 'normal user'}]}),
        ('?id=2', {'userId': 2, 'roleId': 2, 'userName': 'user', 'accessMethod': 'any', 'realName': 'Normal user',
                   'description': 'normal user'}),
        ('?username=admin',
         {'userId': 1, 'roleId': 1, 'userName': 'admin', 'accessMethod': 'any', 'realName': 'Admin user',
          'description': 'admin user'}),
        ('?id=1&username=admin',
         {'userId': 1, 'roleId': 1, 'userName': 'admin', 'accessMethod': 'any', 'realName': 'Admin user',
          'description': 'admin user'})
    ])
    def test_get_users(self, fledge_url, query, expected_values):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", "/fledge/user{}".format(query), headers={"authorization": TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert expected_values == jdoc

    def test_get_roles(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", "/fledge/user/role", headers={"authorization": TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'roles': [{'description': 'All CRUD privileges', 'id': 1, 'name': 'admin'},
                          {'description': 'All CRUD operations and self profile management',
                           'id': 2, 'name': 'user'}]} == jdoc

    @pytest.mark.parametrize(("form_data", "expected_values"), [
        ({"username": "any1", "password": "User@123", "real_name": "AJ", "description": "Nerd user"},
         {'user': {'userName': 'any1', 'userId': 3, 'roleId': 2, 'accessMethod': 'any', 'realName': 'AJ',
                   'description': 'Nerd user'}, 'message': 'any1 user has been created successfully'}),
        ({"username": "admin1", "password": "F0gl@mp!", "role_id": 1},
         {'user': {'userName': 'admin1', 'userId': 4, 'roleId': 1, 'accessMethod': 'any', 'realName': '',
                   'description': ''}, 'message': 'admin1 user has been created successfully'}),
        ({"username": "bogus", "password": "Fl3dG$", "role_id": 2},
         {'user': {'userName': 'bogus', 'userId': 5, 'roleId': 2, 'accessMethod': 'any', 'realName': '',
                   'description': ''}, 'message': 'bogus user has been created successfully'})
    ])
    def test_create_user(self, fledge_url, form_data, expected_values):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/admin/user", body=json.dumps(form_data), headers={"authorization": TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert expected_values == jdoc

    def test_update_password(self, fledge_url):
        uid = 3
        payload = {"current_password": "User@123", "new_password": "F0gl@mp1"}
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", "/fledge/user/{}/password".format(uid), body=json.dumps(payload),
                     headers={"authorization": TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': 'Password has been updated successfully for user id:<{}>'.format(uid)} == jdoc

    def test_update_user(self, fledge_url):
        uid = 5
        conn = http.client.HTTPConnection(fledge_url)
        payload = {"real_name": "Test Real", "description": "Test Desc"}
        conn.request("PUT", "/fledge/user/{}".format(uid), body=json.dumps(payload), headers={"authorization": TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 'user_info' in jdoc
        assert uid == jdoc["user_info"]["id"]
        assert payload["real_name"] == jdoc["user_info"]["real_name"]
        assert payload["description"] == jdoc["user_info"]["description"]

    def test_enable_user(self, fledge_url):
        uid = 5
        # Fetch users list
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", "/fledge/user", headers={"authorization": TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        user_list = [u['userId'] for u in jdoc['users']]
        assert uid in user_list

        # Disable user
        payload = {"enabled": "false"}
        conn.request("PUT", "/fledge/admin/{}/enabled".format(uid), body=json.dumps(payload),
                     headers={"authorization": TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': 'User with id:<{}> has been disabled successfully'.format(uid)} == jdoc

        # Fetch users list again and check disabled user does not exist in the response
        conn.request("GET", "/fledge/user", headers={"authorization": TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        user_list = [u['userId'] for u in jdoc['users']]
        assert uid not in user_list

    def test_reset_user(self, fledge_url):
        uid = 3
        payload = {"role_id": 1, "password": "F0gl@mp!"}
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", "/fledge/admin/{}/reset".format(uid), body=json.dumps(payload),
                     headers={"authorization": TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': 'User with id:<{}> has been updated successfully'.format(uid)} == jdoc

    def test_delete_user(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("DELETE", "/fledge/admin/4/delete", headers={"authorization": TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': "User has been deleted successfully"} == jdoc

    def test_logout_all(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", '/fledge/1/logout', headers={"authorization": TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert jdoc['logout']

    def test_admin_actions_reg_user(self, fledge_url):
        """Test that regular user is not able to perform any actions that only an admin can"""
        # Login with regular user
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/login", json.dumps({"username": "user", "password": "fledge"}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert not jdoc['admin']
        _token = jdoc["token"]

        # Create User
        conn.request("POST", "/fledge/admin/user", body=json.dumps({"username": "other", "password": "User@123"}),
                     headers={"authorization": _token})
        r = conn.getresponse()
        assert 403 == r.status
        r = r.read().decode()
        assert "403: Forbidden" == r

        # Reset User
        conn.request("PUT", "/fledge/admin/2/reset", body=json.dumps({"role_id": 1, "password": "F0gl@p!"}),
                     headers={"authorization": _token})
        r = conn.getresponse()
        assert 403 == r.status
        r = r.read().decode()
        assert "403: Forbidden" == r

        # Delete User
        conn.request("DELETE", "/fledge/admin/2/delete", headers={"authorization": _token})
        r = conn.getresponse()
        assert 403 == r.status
        r = r.read().decode()
        assert "403: Forbidden" == r

    def test_login_with_user_certificate(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        cert_file_path = os.path.join(os.path.expandvars('${FLEDGE_ROOT}'), 'data/etc/certs/user.cert')
        with open(cert_file_path, 'r') as f:
            conn.request("POST", "/fledge/login", body=f)
            r = conn.getresponse()
            assert 200 == r.status
            r = r.read().decode()
            jdoc = json.loads(r)
            assert "Logged in successfully" == jdoc['message']
            assert "token" in jdoc
            assert not jdoc['admin']

    def test_login_with_admin_certificate(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        cert_file_path = os.path.join(os.path.expandvars('${FLEDGE_ROOT}'), 'data/etc/certs/admin.cert')
        with open(cert_file_path, 'r') as f:
            conn.request("POST", "/fledge/login", body=f)
            r = conn.getresponse()
            assert 200 == r.status
            r = r.read().decode()
            jdoc = json.loads(r)
            assert "Logged in successfully" == jdoc['message']
            assert "token" in jdoc
            assert jdoc['admin']

    def test_login_with_custom_certificate(self, fledge_url, remove_data_file):
        # Create a custom certificate and sign
        subprocess.run(["openssl genrsa -out custom.key 1024 2> /dev/null"], shell=True)
        subprocess.run(["openssl req -new -key custom.key -out custom.csr -subj '/C=IN/CN=user' 2> /dev/null"],
                       shell=True)
        subprocess.run(["openssl x509 -req -days 1 -in custom.csr "
                        "-CA $FLEDGE_ROOT/data/etc/certs/ca.cert -CAkey $FLEDGE_ROOT/data/etc/certs/ca.key "
                        "-set_serial 01 -out custom.cert 2> /dev/null"], shell=True)

        # Login with custom certificate
        conn = http.client.HTTPConnection(fledge_url)
        cert_file_path = 'custom.cert'
        with open(cert_file_path, 'r') as f:
            conn.request("POST", "/fledge/login", body=f)
            r = conn.getresponse()
            assert 200 == r.status
            r = r.read().decode()
            jdoc = json.loads(r)
            assert "Logged in successfully" == jdoc['message']
            assert "token" in jdoc
            assert not jdoc['admin']

        # Delete Certificates and keys created
        remove_data_file('custom.key')
        remove_data_file('custom.csr')
        remove_data_file('custom.cert')
