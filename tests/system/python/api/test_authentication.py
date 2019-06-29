# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test authentication REST API """

import os
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
                conn.request("PUT", '/foglamp/logout', headers={"authorization": TOKEN})
                r = conn.getresponse()
                assert 200 == r.status
                r = r.read().decode()
                jdoc = json.loads(r)
                assert jdoc['logout']

        def test_login_username_admin(self, foglamp_url):
                conn = http.client.HTTPConnection(foglamp_url)
                conn.request("POST", "/foglamp/login", json.dumps({"username": "admin", "password": "foglamp"}))
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
                ('', {'users': [{'userId': 1, 'roleId': 1, 'userName': 'admin'},
                                {'userId': 2, 'roleId': 2, 'userName': 'user'}]}),
                ('?id=2', {'userId': 2, 'roleId': 2, 'userName': 'user'}),
                ('?username=admin', {'userId': 1, 'roleId': 1, 'userName': 'admin'}),
                ('?id=1&username=admin', {'userId': 1, 'roleId': 1, 'userName': 'admin'}),
        ])
        def test_get_users(self, foglamp_url, query, expected_values):
                conn = http.client.HTTPConnection(foglamp_url)
                conn.request("GET", "/foglamp/user{}".format(query), headers={"authorization": TOKEN})
                r = conn.getresponse()
                assert 200 == r.status
                r = r.read().decode()
                jdoc = json.loads(r)
                assert expected_values == jdoc

        def test_get_roles(self, foglamp_url):
                conn = http.client.HTTPConnection(foglamp_url)
                conn.request("GET", "/foglamp/user/role", headers={"authorization": TOKEN})
                r = conn.getresponse()
                assert 200 == r.status
                r = r.read().decode()
                jdoc = json.loads(r)
                assert {'roles': [{'description': 'All CRUD privileges', 'id': 1, 'name': 'admin'},
                                  {'description': 'All CRUD operations and self profile management',
                                   'id': 2, 'name': 'user'}]} == jdoc

        @pytest.mark.parametrize(("form_data", "expected_values"), [
                ({"username": "any1", "password": "User@123"}, {'user': {'userName': 'any1', 'userId': 3, 'roleId': 2},
                                                                'message': 'User has been created successfully'}),
                ({"username": "admin1", "password": "F0gl@mp!", "role_id": 1},
                 {'user': {'userName': 'admin1', 'userId': 4, 'roleId': 1},
                  'message': 'User has been created successfully'}),
        ])
        def test_create_user(self, foglamp_url, form_data, expected_values):
                conn = http.client.HTTPConnection(foglamp_url)
                conn.request("POST", "/foglamp/admin/user", body=json.dumps(form_data),
                             headers={"authorization": TOKEN})
                r = conn.getresponse()
                assert 200 == r.status
                r = r.read().decode()
                jdoc = json.loads(r)
                assert expected_values == jdoc

        def test_update_password(self, foglamp_url):
                conn = http.client.HTTPConnection(foglamp_url)
                conn.request("PUT", "/foglamp/user/any1/password", body=json.dumps({"current_password": "User@123",
                                                                                    "new_password": "F0gl@mp1"}),
                             headers={"authorization": TOKEN})
                r = conn.getresponse()
                assert 200 == r.status
                r = r.read().decode()
                jdoc = json.loads(r)
                assert {'message': 'Password has been updated successfully for user id:<3>'} == jdoc

        def test_reset_user(self, foglamp_url):
                conn = http.client.HTTPConnection(foglamp_url)
                conn.request("PUT", "/foglamp/admin/3/reset", body=json.dumps({"role_id": 1, "password": "F0gl@mp!"}),
                             headers={"authorization": TOKEN})
                r = conn.getresponse()
                assert 200 == r.status
                r = r.read().decode()
                jdoc = json.loads(r)
                assert {'message': 'User with id:<3> has been updated successfully'} == jdoc

        def test_delete_user(self, foglamp_url):
                conn = http.client.HTTPConnection(foglamp_url)
                conn.request("DELETE", "/foglamp/admin/4/delete", headers={"authorization": TOKEN})
                r = conn.getresponse()
                assert 200 == r.status
                r = r.read().decode()
                jdoc = json.loads(r)
                assert {'message': "User has been deleted successfully"} == jdoc

        def test_logout_all(self, foglamp_url):
                conn = http.client.HTTPConnection(foglamp_url)
                conn.request("PUT", '/foglamp/1/logout', headers={"authorization": TOKEN})
                r = conn.getresponse()
                assert 200 == r.status
                r = r.read().decode()
                jdoc = json.loads(r)
                assert jdoc['logout']

        def test_admin_actions_reg_user(self, foglamp_url):
                """Test that regular user is not able to perform any actions that only an admin can"""
                # Login with regular user
                conn = http.client.HTTPConnection(foglamp_url)
                conn.request("POST", "/foglamp/login", json.dumps({"username": "user", "password": "foglamp"}))
                r = conn.getresponse()
                assert 200 == r.status
                r = r.read().decode()
                jdoc = json.loads(r)
                assert not jdoc['admin']
                _token = jdoc["token"]

                # Create User
                conn.request("POST", "/foglamp/admin/user", body=json.dumps({"username": "other", "password": "User@123"}),
                             headers={"authorization": _token})
                r = conn.getresponse()
                assert 403 == r.status
                r = r.read().decode()
                assert "403: Forbidden" == r

                # Reset User
                conn.request("PUT", "/foglamp/admin/2/reset", body=json.dumps({"role_id": 1, "password": "F0gl@p!"}),
                             headers={"authorization": _token})
                r = conn.getresponse()
                assert 403 == r.status
                r = r.read().decode()
                assert "403: Forbidden" == r

                # Delete User
                conn.request("DELETE", "/foglamp/admin/2/delete", headers={"authorization": _token})
                r = conn.getresponse()
                assert 403 == r.status
                r = r.read().decode()
                assert "403: Forbidden" == r

        def test_login_with_certificate(self, foglamp_url):
                conn = http.client.HTTPConnection(foglamp_url)
                cert_file_path = os.path.join(os.path.expandvars('${FOGLAMP_ROOT}'), 'data/etc/certs/user.cert')
                with open(cert_file_path, 'r') as f:
                        conn.request("POST", "/foglamp/login", body=f)
                        r = conn.getresponse()
                        assert 200 == r.status
                        r = r.read().decode()
                        jdoc = json.loads(r)
                        assert "Logged in successfully" == jdoc['message']
                        assert "token" in jdoc
                        assert not jdoc['admin']
