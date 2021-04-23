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
from pathlib import Path
import ssl

__author__ = "Yash Tatkondawar"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

TEMPLATE_NAME = "template.json"
SENSOR_VALUE = 12.25
HTTP_SOUTH_SVC_NAME = "SOUTH_HTTP"
HTTP_SOUTH_SVC_NAME_1 = "SOUTH_HTTP_1"
ASSET_NAME = "auth"
PASSWORD_TOKEN = None
CERT_TOKEN = None
# This  gives the path of directory where fledge is cloned. test_file < packages < python < system < tests < ROOT
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
SCRIPTS_DIR_ROOT = "{}/tests/system/python/packages/data/".format(PROJECT_ROOT)
context = ssl._create_unverified_context()


def send_data_using_fogbench(wait_time):
    execute_fogbench = 'cd {}/extras/python ;python3 -m fogbench -t $FLEDGE_ROOT/data/tests/{} ' \
                       '-p http -O 10'.format(PROJECT_ROOT, TEMPLATE_NAME)
    exit_code = os.system(execute_fogbench)
    assert 0 == exit_code
    # Wait until data gets ingested
    time.sleep(wait_time)


def add_south_http(fledge_url, name, token, wait_time, tls_enabled):
    payload = {"name": name, "type": "south", "plugin": "http_south", "enabled": True}
    post_url = "/fledge/service"
    if tls_enabled:
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
    else:
        conn = http.client.HTTPConnection(fledge_url)
    conn.request("POST", post_url, json.dumps(payload), headers={"authorization": token})
    res = conn.getresponse()
    assert 200 == res.status, "ERROR! POST {} request failed".format(post_url)
    res = res.read().decode()
    r = json.loads(res)
    # Wait for service to get added
    time.sleep(wait_time * 2)
    return r


def generate_json_for_fogbench(asset_name):
    subprocess.run(["cd $FLEDGE_ROOT/data && mkdir -p tests"], shell=True, check=True)

    fogbench_template_path = os.path.join(
        os.path.expandvars('${FLEDGE_ROOT}'), 'data/tests/{}'.format(TEMPLATE_NAME))
    with open(fogbench_template_path, "w") as f:
        f.write(
            '[{"name": "%s", "sensor_values": '
            '[{"name": "sensor", "type": "number", "min": %f, "max": %f, "precision": 2}]}]' % (
                asset_name, SENSOR_VALUE, SENSOR_VALUE))


@pytest.fixture
def change_to_auth_mandatory_any(fledge_url, wait_time):
    conn = http.client.HTTPConnection(fledge_url)
    conn.request("PUT", '/fledge/category/rest_api', json.dumps({"authentication": "mandatory", "authMethod": "any"}))
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

    # Wait for fledge server to start
    time.sleep(wait_time * 2)


@pytest.fixture
def change_to_auth_mandatory_password(fledge_url, wait_time):
    conn = http.client.HTTPConnection(fledge_url)
    conn.request("PUT", '/fledge/category/rest_api',
                 json.dumps({"authentication": "mandatory", "authMethod": "password"}))
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

    # Wait for fledge server to start
    time.sleep(wait_time * 2)


@pytest.fixture
def change_to_auth_mandatory_certificate(fledge_url, wait_time):
    conn = http.client.HTTPConnection(fledge_url)
    conn.request("PUT", '/fledge/category/rest_api',
                 json.dumps({"authentication": "mandatory", "authMethod": "certificate"}))
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

    # Wait for fledge server to start
    time.sleep(wait_time * 2)


@pytest.fixture
def reset_fledge(wait_time):
    # TODO: Remove kill after resolution of FOGL-1499
    try:
        subprocess.run(["$FLEDGE_ROOT/bin/fledge kill"], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "kill command failed!"

    try:
        subprocess.run(["cd {}/tests/system/python/scripts/package && ./reset"
                       .format(PROJECT_ROOT)], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "reset package script failed!"

    # Wait for fledge server to start
    time.sleep(wait_time)


@pytest.fixture
def remove_and_add_fledge_pkgs(package_build_version):
    try:
        subprocess.run(["cd {}/tests/system/python/scripts/package && ./remove"
                       .format(PROJECT_ROOT)], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "remove package script failed!"

    try:
        subprocess.run(["cd {}/tests/system/python/scripts/package/ && ./setup {}"
                       .format(PROJECT_ROOT, package_build_version)], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "setup package script failed"

    try:
        subprocess.run(["sudo apt install -y fledge-south-http-south"], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "installation of http-south package failed"


@pytest.fixture
def enable_tls():
    def _enable_tls(fledge_url, wait_time, auth):
        conn = http.client.HTTPConnection(fledge_url)
        headers = None
        if auth == 'password':
            headers = {"authorization": PASSWORD_TOKEN}
        elif auth == 'certificate':
            headers = {"authorization": CERT_TOKEN}

        if headers is None:
            conn.request("PUT", '/fledge/category/rest_api', json.dumps({"enableHttp": "false"}))
        else:
            conn.request("PUT", '/fledge/category/rest_api', json.dumps({"enableHttp": "false"}),
                         headers=headers)
        r = conn.getresponse()
        assert 200 == r.status

        # FIXME: Remove this wait time
        time.sleep(wait_time)

        conn = http.client.HTTPConnection(fledge_url)
        if headers is None:
            conn.request("PUT", '/fledge/restart', json.dumps({}))
        else:
            conn.request("PUT", '/fledge/restart', json.dumps({}), headers=headers)
        r = conn.getresponse()
        assert 200 == r.status

        # Wait for fledge server to start
        time.sleep(wait_time * 2)

    return _enable_tls


@pytest.fixture
def generate_password_based_auth_token(asset_name, fledge_url):
    conn = http.client.HTTPConnection(fledge_url)
    conn.request("POST", "/fledge/login", json.dumps({"username": "user", "password": "fledge"}))
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    assert "Logged in successfully" == jdoc['message']
    assert not jdoc['admin']
    global PASSWORD_TOKEN
    PASSWORD_TOKEN = jdoc["token"]


@pytest.fixture
def generate_certificate_based_auth_token(asset_name, fledge_url):
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
        global CERT_TOKEN
        CERT_TOKEN = jdoc["token"]


class TestTLSDisabled:
    def test_on_default_port(self, remove_and_add_fledge_pkgs, reset_fledge, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", "/fledge/ping")
        r = conn.getresponse()
        jdoc = json.loads(r.read().decode())
        assert "uptime" in jdoc
        assert 0 < jdoc['uptime'], "Fledge not up."

    def test_on_custom_port(self, fledge_url, wait_time):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", '/fledge/category/rest_api', json.dumps({"httpPort": "8005"}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "httpPort" in jdoc
        assert '8005' == jdoc['httpPort']['value']

        # FIXME: Remove this wait time
        time.sleep(wait_time)

        conn.request("PUT", '/fledge/restart')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "Fledge restart has been scheduled." == jdoc['message']

        # Wait for fledge server to start
        time.sleep(wait_time * 2)

        conn = http.client.HTTPConnection("localhost", 8005)
        conn.request("GET", "/fledge/ping")
        r = conn.getresponse()
        jdoc = json.loads(r.read().decode())
        assert "dataRead" in jdoc
        assert "uptime" in jdoc
        assert 0 < jdoc['uptime'], "Fledge not up."

    def test_reset_to_default_port(self, fledge_url, wait_time):
        conn = http.client.HTTPConnection("localhost", 8005)
        conn.request("PUT", '/fledge/category/rest_api', json.dumps({"httpPort": "8081"}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "httpPort" in jdoc
        assert '8081' == jdoc['httpPort']['value']

        # FIXME: Remove this wait time
        time.sleep(wait_time)

        conn.request("PUT", '/fledge/restart', json.dumps({}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "Fledge restart has been scheduled." == jdoc['message']

        # Wait for fledge server to start
        time.sleep(wait_time * 2)

        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", "/fledge/ping")
        r = conn.getresponse()
        jdoc = json.loads(r.read().decode())
        assert "dataRead" in jdoc
        assert "uptime" in jdoc
        assert 0 < jdoc['uptime'], "Fledge not up."


class TestAuthAnyWithoutTLS:
    def test_login_regular_user_using_password(self, reset_fledge, change_to_auth_mandatory_any,
                                               fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/login", json.dumps({"username": "user", "password": "fledge"}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "Logged in successfully" == jdoc['message']
        assert not jdoc['admin']
        global PASSWORD_TOKEN
        PASSWORD_TOKEN = jdoc["token"]

    def test_logout_me_password_token(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", '/fledge/logout', headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert jdoc['logout']

    def test_login_with_invalid_credentials_regular_user_using_password(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/login", json.dumps({"username": "user", "password": "Fledge"}))
        r = conn.getresponse()
        assert 404 == r.status
        assert "Username or Password do not match" == r.reason

    def test_login_username_admin_using_password(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/login", json.dumps({"username": "admin", "password": "fledge"}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "Logged in successfully" == jdoc['message']
        assert "token" in jdoc
        assert jdoc['admin']
        global PASSWORD_TOKEN
        PASSWORD_TOKEN = jdoc["token"]

    def test_login_with_invalid_credentials_admin_using_password(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/login", json.dumps({"username": "admin", "password": "FLEDGE"}))
        r = conn.getresponse()
        assert 404 == r.status
        assert "Username or Password do not match" == r.reason

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
            global CERT_TOKEN
            CERT_TOKEN = jdoc["token"]

    def test_login_with_custom_certificate(self, fledge_url, remove_data_file):
        # Create a custom certificate and sign
        try:
            subprocess.run(["openssl genrsa -out custom.key 1024 2> /dev/null"], shell=True)
            subprocess.run(["openssl req -new -key custom.key -out custom.csr -subj '/C=IN/CN=user' 2> /dev/null"],
                           shell=True)
            subprocess.run(["openssl x509 -req -days 1 -in custom.csr "
                            "-CA $FLEDGE_ROOT/data/etc/certs/ca.cert -CAkey $FLEDGE_ROOT/data/etc/certs/ca.key "
                            "-set_serial 01 -out custom.cert 2> /dev/null"], shell=True)
        except subprocess.CalledProcessError:
            assert False, " Certificate creation failed!"

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

    def test_ping_with_allow_ping_true(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", "/fledge/ping")
        r = conn.getresponse()
        jdoc = json.loads(r.read().decode())
        assert "dataRead" in jdoc
        assert 0 == jdoc['dataRead'], "data NOT seen in ping header"

    def test_ingest_with_password_token(self, fledge_url, wait_time):
        add_south_http(fledge_url, HTTP_SOUTH_SVC_NAME, PASSWORD_TOKEN, wait_time, tls_enabled=False)

        generate_json_for_fogbench(ASSET_NAME)

        send_data_using_fogbench(wait_time)

        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", "/fledge/ping")
        r = conn.getresponse()
        jdoc = json.loads(r.read().decode())
        assert "dataRead" in jdoc
        assert 10 == jdoc['dataRead'], "data NOT seen in ping header"

    def test_ingest_with_certificate_token(self, fledge_url, wait_time):
        add_south_http(fledge_url, HTTP_SOUTH_SVC_NAME_1, CERT_TOKEN, wait_time, tls_enabled=False)

        generate_json_for_fogbench(ASSET_NAME)

        send_data_using_fogbench(wait_time)

        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", "/fledge/ping")
        r = conn.getresponse()
        jdoc = json.loads(r.read().decode())
        assert "dataRead" in jdoc
        assert 20 == jdoc['dataRead'], "data NOT seen in ping header"

    def test_ping_with_allow_ping_false_with_password_token(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/login", json.dumps({"username": "admin", "password": "fledge"}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "Logged in successfully" == jdoc['message']
        _token = jdoc["token"]

        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", '/fledge/category/rest_api', body=json.dumps({"allowPing": "false"}),
                     headers={"authorization": _token})
        r = conn.getresponse()
        assert 200 == r.status

        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", '/fledge/logout', headers={"authorization": _token})
        r = conn.getresponse()
        assert 200 == r.status

        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", "/fledge/ping")
        r = conn.getresponse()
        assert 401 == r.status
        assert "Unauthorized" == r.reason

    def test_ping_with_allow_ping_false_with_certificate_token(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        cert_file_path = os.path.join(os.path.expandvars('${FLEDGE_ROOT}'), 'data/etc/certs/admin.cert')
        with open(cert_file_path, 'r') as f:
            conn.request("POST", "/fledge/login", body=f)
            r = conn.getresponse()
            assert 200 == r.status
            r = r.read().decode()
            jdoc = json.loads(r)
            assert "Logged in successfully" == jdoc['message']
            _token = jdoc["token"]

        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", '/fledge/category/rest_api', json.dumps({"allowPing": "false"}),
                     headers={"authorization": _token})
        r = conn.getresponse()
        assert 200 == r.status

        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", '/fledge/logout', headers={"authorization": _token})
        r = conn.getresponse()
        assert 200 == r.status

        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", "/fledge/ping")
        r = conn.getresponse()
        assert 401 == r.status
        assert "Unauthorized" == r.reason

    @pytest.mark.parametrize(("query", "expected_values"), [
        ('', {'users': [{'userId': 1, 'roleId': 1, 'userName': 'admin'},
                        {'userId': 2, 'roleId': 2, 'userName': 'user'}]}),
        ('?id=2', {'userId': 2, 'roleId': 2, 'userName': 'user'}),
        ('?username=admin', {'userId': 1, 'roleId': 1, 'userName': 'admin'}),
        ('?id=1&username=admin', {'userId': 1, 'roleId': 1, 'userName': 'admin'}),
    ])
    def test_get_users_with_password_token(self, fledge_url, query, expected_values):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", "/fledge/user{}".format(query), headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert expected_values == jdoc

    @pytest.mark.parametrize(("query", "expected_values"), [
        ('', {'users': [{'userId': 1, 'roleId': 1, 'userName': 'admin'},
                        {'userId': 2, 'roleId': 2, 'userName': 'user'}]}),
        ('?id=2', {'userId': 2, 'roleId': 2, 'userName': 'user'}),
        ('?username=admin', {'userId': 1, 'roleId': 1, 'userName': 'admin'}),
        ('?id=1&username=admin', {'userId': 1, 'roleId': 1, 'userName': 'admin'}),
    ])
    def test_get_users_with_certificate_token(self, fledge_url, query, expected_values):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", "/fledge/user{}".format(query), headers={"authorization": CERT_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert expected_values == jdoc

    def test_get_roles_with_password_token(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", "/fledge/user/role", headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'roles': [{'description': 'All CRUD privileges', 'id': 1, 'name': 'admin'},
                          {'description': 'All CRUD operations and self profile management',
                           'id': 2, 'name': 'user'}]} == jdoc

    def test_get_roles_with_certificate_token(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", "/fledge/user/role", headers={"authorization": CERT_TOKEN})
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
    def test_create_user_with_password_token(self, fledge_url, form_data, expected_values):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/admin/user", body=json.dumps(form_data),
                     headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert expected_values == jdoc

    @pytest.mark.parametrize(("form_data", "expected_values"), [
        ({"username": "any2", "password": "User@123"}, {'user': {'userName': 'any2', 'userId': 5, 'roleId': 2},
                                                        'message': 'User has been created successfully'}),
        ({"username": "admin2", "password": "F0gl@mp!", "role_id": 1},
         {'user': {'userName': 'admin2', 'userId': 6, 'roleId': 1},
          'message': 'User has been created successfully'}),
    ])
    def test_create_user_with_certificate_token(self, fledge_url, form_data, expected_values):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/admin/user", body=json.dumps(form_data),
                     headers={"authorization": CERT_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert expected_values == jdoc

    @pytest.mark.parametrize(("form_data", "expected_values"), [
        ({"username": "any1", "password": "User@123"}, 'Logged in successfully'),
        ({"username": "admin1", "password": "F0gl@mp!"}, 'Logged in successfully'),
        ({"username": "any2", "password": "User@123"}, 'Logged in successfully'),
        ({"username": "admin2", "password": "F0gl@mp!"}, 'Logged in successfully')
    ])
    def test_login_of_newly_created_user(self, fledge_url, form_data, expected_values):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/login", body=json.dumps(form_data))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert expected_values == jdoc['message']

    def test_update_password_with_password_token(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", "/fledge/user/any1/password", body=json.dumps({"current_password": "User@123",
                                                                            "new_password": "F0gl@mp1"}),
                     headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': 'Password has been updated successfully for user id:<3>'} == jdoc

    def test_update_password_with_certificate_token(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", "/fledge/user/any2/password", body=json.dumps({"current_password": "User@123",
                                                                            "new_password": "F0gl@mp2"}),
                     headers={"authorization": CERT_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': 'Password has been updated successfully for user id:<5>'} == jdoc

    @pytest.mark.parametrize(("form_data", "expected_values"), [
        ({"username": "any1", "password": "F0gl@mp1"}, 'Logged in successfully'),
        ({"username": "any2", "password": "F0gl@mp2"}, 'Logged in successfully')
    ])
    def test_login_with_updated_password(self, fledge_url, form_data, expected_values):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/login", body=json.dumps(form_data))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert expected_values == jdoc['message']

    def test_reset_user_with_password_token(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", "/fledge/admin/3/reset", body=json.dumps({"role_id": 1, "password": "F0gl@mp!#1"}),
                     headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': 'User with id:<3> has been updated successfully'} == jdoc

    def test_reset_user_with_certificate_token(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", "/fledge/admin/5/reset", body=json.dumps({"role_id": 1, "password": "F0gl@mp!#2"}),
                     headers={"authorization": CERT_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': 'User with id:<5> has been updated successfully'} == jdoc

    @pytest.mark.parametrize(("form_data", "expected_values"), [
        ({"username": "any1", "password": "F0gl@mp!#1"}, 'Logged in successfully'),
        ({"username": "any2", "password": "F0gl@mp!#2"}, 'Logged in successfully')
    ])
    def test_login_with_resetted_password(self, fledge_url, form_data, expected_values):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/login", body=json.dumps(form_data))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert expected_values == jdoc['message']

    def test_delete_user_with_password_token(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("DELETE", "/fledge/admin/4/delete", headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': "User has been deleted successfully"} == jdoc

    def test_delete_user_with_certificate_token(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("DELETE", "/fledge/admin/6/delete", headers={"authorization": CERT_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': "User has been deleted successfully"} == jdoc

    @pytest.mark.parametrize(("form_data", "expected_values"), [
        ({"username": "admin1", "password": "F0gl@mp!"}, ""),
        ({"username": "admin2", "password": "F0gl@mp!"}, "")
    ])
    def test_login_of_deleted_user(self, fledge_url, form_data, expected_values):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/login", body=json.dumps(form_data))
        r = conn.getresponse()
        assert 404 == r.status
        assert "User does not exist" == r.reason

    def test_logout_all_with_password_token(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", '/fledge/1/logout', headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert jdoc['logout']

    def test_verify_logout(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/asset', headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 401 == r.status

    def test_admin_actions_forbidden_for_regular_user_with_pwd_token(self, fledge_url):
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
        conn.request("POST", "/fledge/admin/user", body=json.dumps({"username": "other",
                                                                     "password": "User@123"}),
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

    def test_admin_actions_forbidden_for_regular_user_with_cert_token(self, fledge_url):
        """Test that regular user is not able to perform any actions that only an admin can"""
        # Login with regular user
        conn = http.client.HTTPConnection(fledge_url)
        cert_file_path = os.path.join(os.path.expandvars('${FLEDGE_ROOT}'), 'data/etc/certs/user.cert')
        with open(cert_file_path, 'r') as f:
            conn.request("POST", "/fledge/login", body=f)
            r = conn.getresponse()
            assert 200 == r.status
            r = r.read().decode()
            jdoc = json.loads(r)
            assert not jdoc['admin']
            _token = jdoc["token"]

        # Create User
        conn.request("POST", "/fledge/admin/user", body=json.dumps({"username": "other",
                                                                     "password": "User@123"}),
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

    @pytest.mark.skip(reason="Currently this feature is not implemented.")
    def test_regular_user_access_to_admin_api_config(self, fledge_url):
        pass


class TestAuthPasswordWithoutTLS:
    def test_login_username_regular_user(self, reset_fledge, change_to_auth_mandatory_password,
                                         fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/login", json.dumps({"username": "user", "password": "fledge"}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "Logged in successfully" == jdoc['message']
        assert not jdoc['admin']
        global PASSWORD_TOKEN
        PASSWORD_TOKEN = jdoc["token"]

    def test_logout_me(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", '/fledge/logout', headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert jdoc['logout']

    def test_login_with_invalid_credentials_regular_user(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/login", json.dumps({"username": "user", "password": "Fledge"}))
        r = conn.getresponse()
        assert 404 == r.status
        assert "Username or Password do not match" == r.reason

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
        global PASSWORD_TOKEN
        PASSWORD_TOKEN = jdoc["token"]

    def test_login_with_invalid_credentials_admin(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/login", json.dumps({"username": "admin", "password": "FLEDGE"}))
        r = conn.getresponse()
        assert 404 == r.status
        assert "Username or Password do not match" == r.reason

    def test_login_with_admin_certificate(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        cert_file_path = os.path.join(os.path.expandvars('${FLEDGE_ROOT}'), 'data/etc/certs/admin.cert')
        with open(cert_file_path, 'r') as f:
            conn.request("POST", "/fledge/login", body=f)
            r = conn.getresponse()
            assert 400 == r.status
            assert "Use a valid username and password to login." == r.reason

    def test_ping_with_allow_ping_true(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", "/fledge/ping")
        r = conn.getresponse()
        jdoc = json.loads(r.read().decode())
        assert "dataRead" in jdoc
        assert 0 == jdoc['dataRead'], "data NOT seen in ping header"

    def test_ingest(self, fledge_url, wait_time):
        add_south_http(fledge_url, HTTP_SOUTH_SVC_NAME, PASSWORD_TOKEN, wait_time, tls_enabled=False)

        generate_json_for_fogbench(ASSET_NAME)

        send_data_using_fogbench(wait_time)

        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", "/fledge/ping")
        r = conn.getresponse()
        jdoc = json.loads(r.read().decode())
        assert "dataRead" in jdoc
        assert 10 == jdoc['dataRead'], "data NOT seen in ping header"

    def test_ping_with_allow_ping_false(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/login", json.dumps({"username": "admin", "password": "fledge"}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "Logged in successfully" == jdoc['message']
        _token = jdoc["token"]

        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", '/fledge/category/rest_api', body=json.dumps({"allowPing": "false"}),
                     headers={"authorization": _token})
        r = conn.getresponse()
        assert 200 == r.status

        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", '/fledge/logout', headers={"authorization": _token})
        r = conn.getresponse()
        assert 200 == r.status

        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", "/fledge/ping")
        r = conn.getresponse()
        assert 401 == r.status
        assert "Unauthorized" == r.reason

    @pytest.mark.parametrize(("query", "expected_values"), [
        ('', {'users': [{'userId': 1, 'roleId': 1, 'userName': 'admin'},
                        {'userId': 2, 'roleId': 2, 'userName': 'user'}]}),
        ('?id=2', {'userId': 2, 'roleId': 2, 'userName': 'user'}),
        ('?username=admin', {'userId': 1, 'roleId': 1, 'userName': 'admin'}),
        ('?id=1&username=admin', {'userId': 1, 'roleId': 1, 'userName': 'admin'}),
    ])
    def test_get_users(self, fledge_url, query, expected_values):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", "/fledge/user{}".format(query), headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert expected_values == jdoc

    def test_get_roles(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", "/fledge/user/role", headers={"authorization": PASSWORD_TOKEN})
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
    def test_create_user(self, fledge_url, form_data, expected_values):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/admin/user", body=json.dumps(form_data),
                     headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert expected_values == jdoc

    @pytest.mark.parametrize(("form_data", "expected_values"), [
        ({"username": "any1", "password": "User@123"}, 'Logged in successfully'),
        ({"username": "admin1", "password": "F0gl@mp!"}, 'Logged in successfully')
    ])
    def test_login_of_newly_created_user(self, fledge_url, form_data, expected_values):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/login", body=json.dumps(form_data))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert expected_values == jdoc['message']

    def test_update_password(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", "/fledge/user/any1/password", body=json.dumps({"current_password": "User@123",
                                                                            "new_password": "F0gl@mp1"}),
                     headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': 'Password has been updated successfully for user id:<3>'} == jdoc

    def test_login_with_updated_password(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/login", body=json.dumps({"username": "any1", "password": "F0gl@mp1"}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 'Logged in successfully' == jdoc['message']

    def test_reset_user(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", "/fledge/admin/3/reset", body=json.dumps({"role_id": 1, "password": "F0gl@mp!"}),
                     headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': 'User with id:<3> has been updated successfully'} == jdoc

    def test_login_with_resetted_password(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/login", body=json.dumps({"username": "any1", "password": "F0gl@mp!"}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 'Logged in successfully' == jdoc['message']

    def test_delete_user(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("DELETE", "/fledge/admin/4/delete", headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': "User has been deleted successfully"} == jdoc

    def test_login_of_deleted_user(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/login", body=json.dumps({"username": "admin1", "password": "F0gl@mp!"}))
        r = conn.getresponse()
        assert 404 == r.status
        assert "User does not exist" == r.reason

    def test_logout_all(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", '/fledge/1/logout', headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert jdoc['logout']

    def test_verify_logout(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/asset', headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 401 == r.status

    def test_admin_actions_forbidden_for_regular_user(self, fledge_url):
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
        conn.request("POST", "/fledge/admin/user", body=json.dumps({"username": "other",
                                                                     "password": "User@123"}),
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

    @pytest.mark.skip(reason="Currently this feature is not implemented.")
    def test_regular_user_access_to_admin_api_config(self, fledge_url):
        pass


class TestAuthCertificateWithoutTLS:
    def test_login_with_user_certificate(self, fledge_url, reset_fledge,
                                         change_to_auth_mandatory_certificate):
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
            global CERT_TOKEN
            CERT_TOKEN = jdoc["token"]

    def test_login_with_custom_certificate(self, fledge_url, remove_data_file):
        # Create a custom certificate and sign
        try:
            subprocess.run(["openssl genrsa -out custom.key 1024 2> /dev/null"], shell=True)
            subprocess.run(["openssl req -new -key custom.key -out custom.csr -subj '/C=IN/CN=user' 2> /dev/null"],
                           shell=True)
            subprocess.run(["openssl x509 -req -days 1 -in custom.csr "
                            "-CA $FLEDGE_ROOT/data/etc/certs/ca.cert -CAkey $FLEDGE_ROOT/data/etc/certs/ca.key "
                            "-set_serial 01 -out custom.cert 2> /dev/null"], shell=True)
        except subprocess.CalledProcessError:
            assert False, " Certificate creation failed!"

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

    def test_login_with_invalid_credentials(self, fledge_url, remove_data_file):
        try:
            subprocess.run(["echo 'Fledge certificate' > template.cert"], shell=True)
        except subprocess.CalledProcessError:
            assert False, " Certificate creation failed!"

        # Login with custom certificate
        conn = http.client.HTTPConnection(fledge_url)
        cert_file_path = 'template.cert'
        with open(cert_file_path, 'r') as f:
            conn.request("POST", "/fledge/login", body=f)
            r = conn.getresponse()
            assert 400 == r.status
            assert 'Use a valid certificate to login.' == r.reason

        # Delete Certificates and keys created
        remove_data_file('template.cert')

    def test_login_username_admin(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/login", json.dumps({"username": "admin", "password": "fledge"}))
        r = conn.getresponse()
        assert 400 == r.status
        assert "Use a valid certificate to login." == r.reason

    def test_ping_with_allow_ping_true(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", "/fledge/ping")
        r = conn.getresponse()
        jdoc = json.loads(r.read().decode())
        assert "dataRead" in jdoc
        assert 0 == jdoc['dataRead'], "data NOT seen in ping header"

    def test_ingest(self, fledge_url, wait_time):
        add_south_http(fledge_url, HTTP_SOUTH_SVC_NAME, CERT_TOKEN, wait_time, tls_enabled=False)

        generate_json_for_fogbench(ASSET_NAME)

        send_data_using_fogbench(wait_time)

        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", "/fledge/ping")
        r = conn.getresponse()
        jdoc = json.loads(r.read().decode())
        assert "dataRead" in jdoc
        assert 10 == jdoc['dataRead'], "data NOT seen in ping header"

    def test_ping_with_allow_ping_false(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        cert_file_path = os.path.join(os.path.expandvars('${FLEDGE_ROOT}'), 'data/etc/certs/admin.cert')
        with open(cert_file_path, 'r') as f:
            conn.request("POST", "/fledge/login", body=f)
            r = conn.getresponse()
            assert 200 == r.status
            r = r.read().decode()
            jdoc = json.loads(r)
            assert "Logged in successfully" == jdoc['message']
            _token = jdoc["token"]

        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", '/fledge/category/rest_api', json.dumps({"allowPing": "false"}),
                     headers={"authorization": _token})
        r = conn.getresponse()
        assert 200 == r.status

        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", '/fledge/logout', headers={"authorization": _token})
        r = conn.getresponse()
        assert 200 == r.status

        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", "/fledge/ping")
        r = conn.getresponse()
        assert 401 == r.status
        assert "Unauthorized" == r.reason

    @pytest.mark.parametrize(("query", "expected_values"), [
        ('', {'users': [{'userId': 1, 'roleId': 1, 'userName': 'admin'},
                        {'userId': 2, 'roleId': 2, 'userName': 'user'}]}),
        ('?id=2', {'userId': 2, 'roleId': 2, 'userName': 'user'}),
        ('?username=admin', {'userId': 1, 'roleId': 1, 'userName': 'admin'}),
        ('?id=1&username=admin', {'userId': 1, 'roleId': 1, 'userName': 'admin'}),
    ])
    def test_get_users(self, fledge_url, query, expected_values):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", "/fledge/user{}".format(query), headers={"authorization": CERT_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert expected_values == jdoc

    def test_get_roles(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", "/fledge/user/role", headers={"authorization": CERT_TOKEN})
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
    def test_create_user(self, fledge_url, form_data, expected_values):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/admin/user", body=json.dumps(form_data),
                     headers={"authorization": CERT_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert expected_values == jdoc

    def test_update_password(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", "/fledge/user/any1/password", body=json.dumps({"current_password": "User@123",
                                                                            "new_password": "F0gl@mp1"}),
                     headers={"authorization": CERT_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': 'Password has been updated successfully for user id:<3>'} == jdoc

    def test_reset_user(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", "/fledge/admin/3/reset", body=json.dumps({"role_id": 1, "password": "F0gl@mp!"}),
                     headers={"authorization": CERT_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': 'User with id:<3> has been updated successfully'} == jdoc

    def test_delete_user(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("DELETE", "/fledge/admin/4/delete", headers={"authorization": CERT_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': "User has been deleted successfully"} == jdoc

    def test_logout_all(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", '/fledge/1/logout', headers={"authorization": CERT_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert jdoc['logout']

    def test_verify_logout(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/asset', headers={"authorization": CERT_TOKEN})
        r = conn.getresponse()
        assert 401 == r.status

    def test_admin_actions_forbidden_for_regular_user(self, fledge_url):
        """Test that regular user is not able to perform any actions that only an admin can"""
        # Login with regular user
        conn = http.client.HTTPConnection(fledge_url)
        cert_file_path = os.path.join(os.path.expandvars('${FLEDGE_ROOT}'), 'data/etc/certs/user.cert')
        with open(cert_file_path, 'r') as f:
            conn.request("POST", "/fledge/login", body=f)
            r = conn.getresponse()
            assert 200 == r.status
            r = r.read().decode()
            jdoc = json.loads(r)
            assert not jdoc['admin']
            _token = jdoc["token"]

        # Create User
        conn.request("POST", "/fledge/admin/user", body=json.dumps({"username": "other",
                                                                     "password": "User@123"}),
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

    @pytest.mark.skip(reason="Currently this feature is not implemented.")
    def test_regular_user_access_to_admin_api_config(self, fledge_url):
        pass


class TestTLSEnabled:
    def test_on_default_port(self, reset_fledge, enable_tls, fledge_url, wait_time):
        enable_tls(fledge_url, wait_time, auth=None)
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("GET", "/fledge/ping")
        r = conn.getresponse()
        jdoc = json.loads(r.read().decode())
        assert "uptime" in jdoc
        assert 0 < jdoc['uptime'], "Fledge not up."

    def test_on_custom_port(self, wait_time):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("PUT", '/fledge/category/rest_api', json.dumps({"httpsPort": "2005"}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "httpsPort" in jdoc
        assert '2005' == jdoc['httpsPort']['value']

        # FIXME: Remove this wait time
        time.sleep(wait_time)

        conn.request("PUT", '/fledge/restart', json.dumps({}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "Fledge restart has been scheduled." == jdoc['message']

        time.sleep(wait_time * 2)

        conn = http.client.HTTPSConnection("localhost", 2005, context=context)
        conn.request("GET", "/fledge/ping")
        r = conn.getresponse()
        jdoc = json.loads(r.read().decode())
        assert "uptime" in jdoc
        assert 0 < jdoc['uptime'], "Fledge not up."


class TestAuthAnyWithTLS:
    def test_login_regular_user_using_password(self, reset_fledge, change_to_auth_mandatory_any,
                                               generate_password_based_auth_token, enable_tls,
                                               fledge_url, wait_time):
        auth = 'password'
        enable_tls(fledge_url, wait_time, auth)

        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("POST", "/fledge/login", json.dumps({"username": "user", "password": "fledge"}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "Logged in successfully" == jdoc['message']
        assert not jdoc['admin']
        global PASSWORD_TOKEN
        PASSWORD_TOKEN = jdoc["token"]

    def test_logout_me_password_token(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("PUT", '/fledge/logout', headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert jdoc['logout']

    def test_login_with_invalid_credentials_regular_user_using_password(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("POST", "/fledge/login", json.dumps({"username": "user", "password": "Fledge"}))
        r = conn.getresponse()
        assert 404 == r.status
        assert "Username or Password do not match" == r.reason

    def test_login_username_admin_using_password(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("POST", "/fledge/login", json.dumps({"username": "admin", "password": "fledge"}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "Logged in successfully" == jdoc['message']
        assert "token" in jdoc
        assert jdoc['admin']
        global PASSWORD_TOKEN
        PASSWORD_TOKEN = jdoc["token"]

    def test_login_with_invalid_credentials_admin_using_password(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("POST", "/fledge/login", json.dumps({"username": "admin", "password": "FLEDGE"}))
        r = conn.getresponse()
        assert 404 == r.status
        assert "Username or Password do not match" == r.reason

    def test_login_with_user_certificate(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
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

    def test_login_with_admin_certificate(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
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
            global CERT_TOKEN
            CERT_TOKEN = jdoc["token"]

    def test_login_with_custom_certificate(self, remove_data_file):
        # Create a custom certificate and sign
        try:
            subprocess.run(["openssl genrsa -out custom.key 1024 2> /dev/null"], shell=True)
            subprocess.run(["openssl req -new -key custom.key -out custom.csr -subj '/C=IN/CN=user' 2> /dev/null"],
                           shell=True)
            subprocess.run(["openssl x509 -req -days 1 -in custom.csr "
                            "-CA $FLEDGE_ROOT/data/etc/certs/ca.cert -CAkey $FLEDGE_ROOT/data/etc/certs/ca.key "
                            "-set_serial 01 -out custom.cert 2> /dev/null"], shell=True)
        except subprocess.CalledProcessError:
            assert False, " Certificate creation failed!"

        # Login with custom certificate
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
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

    def test_ping_with_allow_ping_true(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("GET", "/fledge/ping")
        r = conn.getresponse()
        jdoc = json.loads(r.read().decode())
        assert "dataRead" in jdoc
        assert 0 == jdoc['dataRead'], "data NOT seen in ping header"

    def test_ingest_with_password_token(self, fledge_url, wait_time):
        add_south_http(fledge_url, HTTP_SOUTH_SVC_NAME, PASSWORD_TOKEN, wait_time, tls_enabled=True)

        generate_json_for_fogbench(ASSET_NAME)

        send_data_using_fogbench(wait_time)

        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("GET", "/fledge/ping")
        r = conn.getresponse()
        jdoc = json.loads(r.read().decode())
        assert "dataRead" in jdoc
        assert 10 == jdoc['dataRead'], "data NOT seen in ping header"

    def test_ingest_with_certificate_token(self, fledge_url, wait_time):
        add_south_http(fledge_url, HTTP_SOUTH_SVC_NAME_1, CERT_TOKEN, wait_time, tls_enabled=True)

        generate_json_for_fogbench(ASSET_NAME)

        send_data_using_fogbench(wait_time)

        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("GET", "/fledge/ping")
        r = conn.getresponse()
        jdoc = json.loads(r.read().decode())
        assert "dataRead" in jdoc
        assert 20 == jdoc['dataRead'], "data NOT seen in ping header"

    def test_ping_with_allow_ping_false_with_password_token(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("POST", "/fledge/login", json.dumps({"username": "admin", "password": "fledge"}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "Logged in successfully" == jdoc['message']
        _token = jdoc["token"]

        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("PUT", '/fledge/category/rest_api', body=json.dumps({"allowPing": "false"}),
                     headers={"authorization": _token})
        r = conn.getresponse()
        assert 200 == r.status

        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("PUT", '/fledge/logout', headers={"authorization": _token})
        r = conn.getresponse()
        assert 200 == r.status

        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("GET", "/fledge/ping")
        r = conn.getresponse()
        assert 401 == r.status
        assert "Unauthorized" == r.reason

    def test_ping_with_allow_ping_false_with_certificate_token(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        cert_file_path = os.path.join(os.path.expandvars('${FLEDGE_ROOT}'), 'data/etc/certs/admin.cert')
        with open(cert_file_path, 'r') as f:
            conn.request("POST", "/fledge/login", body=f)
            r = conn.getresponse()
            assert 200 == r.status
            r = r.read().decode()
            jdoc = json.loads(r)
            assert "Logged in successfully" == jdoc['message']
            _token = jdoc["token"]

        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("PUT", '/fledge/category/rest_api', json.dumps({"allowPing": "false"}),
                     headers={"authorization": _token})
        r = conn.getresponse()
        assert 200 == r.status

        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("PUT", '/fledge/logout', headers={"authorization": _token})
        r = conn.getresponse()
        assert 200 == r.status

        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("GET", "/fledge/ping")
        r = conn.getresponse()
        assert 401 == r.status
        assert "Unauthorized" == r.reason

    @pytest.mark.parametrize(("query", "expected_values"), [
        ('', {'users': [{'userId': 1, 'roleId': 1, 'userName': 'admin'},
                        {'userId': 2, 'roleId': 2, 'userName': 'user'}]}),
        ('?id=2', {'userId': 2, 'roleId': 2, 'userName': 'user'}),
        ('?username=admin', {'userId': 1, 'roleId': 1, 'userName': 'admin'}),
        ('?id=1&username=admin', {'userId': 1, 'roleId': 1, 'userName': 'admin'}),
    ])
    def test_get_users_with_password_token(self, query, expected_values):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("GET", "/fledge/user{}".format(query), headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert expected_values == jdoc

    @pytest.mark.parametrize(("query", "expected_values"), [
        ('', {'users': [{'userId': 1, 'roleId': 1, 'userName': 'admin'},
                        {'userId': 2, 'roleId': 2, 'userName': 'user'}]}),
        ('?id=2', {'userId': 2, 'roleId': 2, 'userName': 'user'}),
        ('?username=admin', {'userId': 1, 'roleId': 1, 'userName': 'admin'}),
        ('?id=1&username=admin', {'userId': 1, 'roleId': 1, 'userName': 'admin'}),
    ])
    def test_get_users_with_certificate_token(self, query, expected_values):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("GET", "/fledge/user{}".format(query), headers={"authorization": CERT_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert expected_values == jdoc

    def test_get_roles_with_password_token(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("GET", "/fledge/user/role", headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'roles': [{'description': 'All CRUD privileges', 'id': 1, 'name': 'admin'},
                          {'description': 'All CRUD operations and self profile management',
                           'id': 2, 'name': 'user'}]} == jdoc

    def test_get_roles_with_certificate_token(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("GET", "/fledge/user/role", headers={"authorization": CERT_TOKEN})
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
    def test_create_user_with_password_token(self, form_data, expected_values):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("POST", "/fledge/admin/user", body=json.dumps(form_data),
                     headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert expected_values == jdoc

    @pytest.mark.parametrize(("form_data", "expected_values"), [
        ({"username": "any2", "password": "User@123"}, {'user': {'userName': 'any2', 'userId': 5, 'roleId': 2},
                                                        'message': 'User has been created successfully'}),
        ({"username": "admin2", "password": "F0gl@mp!", "role_id": 1},
         {'user': {'userName': 'admin2', 'userId': 6, 'roleId': 1},
          'message': 'User has been created successfully'}),
    ])
    def test_create_user_with_certificate_token(self, form_data, expected_values):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("POST", "/fledge/admin/user", body=json.dumps(form_data),
                     headers={"authorization": CERT_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert expected_values == jdoc

    @pytest.mark.parametrize(("form_data", "expected_values"), [
        ({"username": "any1", "password": "User@123"}, 'Logged in successfully'),
        ({"username": "admin1", "password": "F0gl@mp!"}, 'Logged in successfully'),
        ({"username": "any2", "password": "User@123"}, 'Logged in successfully'),
        ({"username": "admin2", "password": "F0gl@mp!"}, 'Logged in successfully')
    ])
    def test_login_of_newly_created_user(self, form_data, expected_values):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("POST", "/fledge/login", body=json.dumps(form_data))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert expected_values == jdoc['message']

    def test_update_password_with_password_token(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("PUT", "/fledge/user/any1/password", body=json.dumps({"current_password": "User@123",
                                                                            "new_password": "F0gl@mp1"}),
                     headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': 'Password has been updated successfully for user id:<3>'} == jdoc

    def test_update_password_with_certificate_token(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("PUT", "/fledge/user/any2/password", body=json.dumps({"current_password": "User@123",
                                                                            "new_password": "F0gl@mp2"}),
                     headers={"authorization": CERT_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': 'Password has been updated successfully for user id:<5>'} == jdoc

    @pytest.mark.parametrize(("form_data", "expected_values"), [
        ({"username": "any1", "password": "F0gl@mp1"}, 'Logged in successfully'),
        ({"username": "any2", "password": "F0gl@mp2"}, 'Logged in successfully')
    ])
    def test_login_with_updated_password(self, form_data, expected_values):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("POST", "/fledge/login", body=json.dumps(form_data))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert expected_values == jdoc['message']

    def test_reset_user_with_password_token(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("PUT", "/fledge/admin/3/reset", body=json.dumps({"role_id": 1, "password": "F0gl@mp!#1"}),
                     headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': 'User with id:<3> has been updated successfully'} == jdoc

    def test_reset_user_with_certificate_token(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("PUT", "/fledge/admin/5/reset", body=json.dumps({"role_id": 1, "password": "F0gl@mp!#2"}),
                     headers={"authorization": CERT_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': 'User with id:<5> has been updated successfully'} == jdoc

    @pytest.mark.parametrize(("form_data", "expected_values"), [
        ({"username": "any1", "password": "F0gl@mp!#1"}, 'Logged in successfully'),
        ({"username": "any2", "password": "F0gl@mp!#2"}, 'Logged in successfully')
    ])
    def test_login_with_resetted_password(self, form_data, expected_values):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("POST", "/fledge/login", body=json.dumps(form_data))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert expected_values == jdoc['message']

    def test_delete_user_with_password_token(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("DELETE", "/fledge/admin/4/delete", headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': "User has been deleted successfully"} == jdoc

    def test_delete_user_with_certificate_token(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("DELETE", "/fledge/admin/6/delete", headers={"authorization": CERT_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': "User has been deleted successfully"} == jdoc

    @pytest.mark.parametrize(("form_data", "expected_values"), [
        ({"username": "admin1", "password": "F0gl@mp!"}, ""),
        ({"username": "admin2", "password": "F0gl@mp!"}, "")
    ])
    def test_login_of_deleted_user(self, form_data, expected_values):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("POST", "/fledge/login", body=json.dumps(form_data))
        r = conn.getresponse()
        assert 404 == r.status
        assert "User does not exist" == r.reason

    def test_logout_all_with_password_token(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("PUT", '/fledge/1/logout', headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert jdoc['logout']

    def test_verify_logout(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("GET", '/fledge/asset', headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 401 == r.status

    def test_admin_actions_forbidden_for_regular_user_with_pwd_token(self):
        """Test that regular user is not able to perform any actions that only an admin can"""
        # Login with regular user
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("POST", "/fledge/login", json.dumps({"username": "user", "password": "fledge"}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert not jdoc['admin']
        _token = jdoc["token"]

        # Create User
        conn.request("POST", "/fledge/admin/user", body=json.dumps({"username": "other",
                                                                     "password": "User@123"}),
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

    def test_admin_actions_forbidden_for_regular_user_with_cert_token(self):
        """Test that regular user is not able to perform any actions that only an admin can"""
        # Login with regular user
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        cert_file_path = os.path.join(os.path.expandvars('${FLEDGE_ROOT}'), 'data/etc/certs/user.cert')
        with open(cert_file_path, 'r') as f:
            conn.request("POST", "/fledge/login", body=f)
            r = conn.getresponse()
            assert 200 == r.status
            r = r.read().decode()
            jdoc = json.loads(r)
            assert not jdoc['admin']
            _token = jdoc["token"]

        # Create User
        conn.request("POST", "/fledge/admin/user", body=json.dumps({"username": "other",
                                                                     "password": "User@123"}),
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

    @pytest.mark.skip(reason="Currently this function is not implemented.")
    def test_regular_user_access_to_admin_api_config(self, fledge_url):
        pass


class TestAuthPasswordWithTLS:
    def test_login_username_regular_user(self, reset_fledge, change_to_auth_mandatory_password,
                                         generate_password_based_auth_token, enable_tls, wait_time,
                                         fledge_url):
        auth = 'password'
        enable_tls(fledge_url, wait_time, auth)

        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("POST", "/fledge/login", json.dumps({"username": "user", "password": "fledge"}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "Logged in successfully" == jdoc['message']
        assert not jdoc['admin']
        global PASSWORD_TOKEN
        PASSWORD_TOKEN = jdoc["token"]

    def test_logout_me(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("PUT", '/fledge/logout', headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert jdoc['logout']

    def test_login_with_invalid_credentials_regular_user(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("POST", "/fledge/login", json.dumps({"username": "user", "password": "Fledge"}))
        r = conn.getresponse()
        assert 404 == r.status
        assert "Username or Password do not match" == r.reason

    def test_login_username_admin(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("POST", "/fledge/login", json.dumps({"username": "admin", "password": "fledge"}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "Logged in successfully" == jdoc['message']
        assert "token" in jdoc
        assert jdoc['admin']
        global PASSWORD_TOKEN
        PASSWORD_TOKEN = jdoc["token"]

    def test_login_with_invalid_credentials_admin(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("POST", "/fledge/login", json.dumps({"username": "admin", "password": "FLEDGE"}))
        r = conn.getresponse()
        assert 404 == r.status
        assert "Username or Password do not match" == r.reason

    def test_login_with_admin_certificate(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        cert_file_path = os.path.join(os.path.expandvars('${FLEDGE_ROOT}'), 'data/etc/certs/admin.cert')
        with open(cert_file_path, 'r') as f:
            conn.request("POST", "/fledge/login", body=f)
            r = conn.getresponse()
            assert 400 == r.status
            assert "Use a valid username and password to login." == r.reason

    def test_ping_with_allow_ping_true(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("GET", "/fledge/ping")
        r = conn.getresponse()
        jdoc = json.loads(r.read().decode())
        assert "dataRead" in jdoc
        assert 0 == jdoc['dataRead'], "data NOT seen in ping header"

    def test_ingest(self, fledge_url, wait_time):
        add_south_http(fledge_url, HTTP_SOUTH_SVC_NAME, PASSWORD_TOKEN, wait_time, tls_enabled=True)

        generate_json_for_fogbench(ASSET_NAME)

        send_data_using_fogbench(wait_time)

        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("GET", "/fledge/ping")
        r = conn.getresponse()
        jdoc = json.loads(r.read().decode())
        assert "dataRead" in jdoc
        assert 10 == jdoc['dataRead'], "data NOT seen in ping header"

    def test_ping_with_allow_ping_false(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("POST", "/fledge/login", json.dumps({"username": "admin", "password": "fledge"}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "Logged in successfully" == jdoc['message']
        _token = jdoc["token"]

        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("PUT", '/fledge/category/rest_api', body=json.dumps({"allowPing": "false"}),
                     headers={"authorization": _token})
        r = conn.getresponse()
        assert 200 == r.status

        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("PUT", '/fledge/logout', headers={"authorization": _token})
        r = conn.getresponse()
        assert 200 == r.status

        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("GET", "/fledge/ping")
        r = conn.getresponse()
        assert 401 == r.status
        assert "Unauthorized" == r.reason

    @pytest.mark.parametrize(("query", "expected_values"), [
        ('', {'users': [{'userId': 1, 'roleId': 1, 'userName': 'admin'},
                        {'userId': 2, 'roleId': 2, 'userName': 'user'}]}),
        ('?id=2', {'userId': 2, 'roleId': 2, 'userName': 'user'}),
        ('?username=admin', {'userId': 1, 'roleId': 1, 'userName': 'admin'}),
        ('?id=1&username=admin', {'userId': 1, 'roleId': 1, 'userName': 'admin'}),
    ])
    def test_get_users(self, query, expected_values):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("GET", "/fledge/user{}".format(query), headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert expected_values == jdoc

    def test_get_roles(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("GET", "/fledge/user/role", headers={"authorization": PASSWORD_TOKEN})
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
    def test_create_user(self, form_data, expected_values):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("POST", "/fledge/admin/user", body=json.dumps(form_data),
                     headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert expected_values == jdoc

    @pytest.mark.parametrize(("form_data", "expected_values"), [
        ({"username": "any1", "password": "User@123"}, 'Logged in successfully'),
        ({"username": "admin1", "password": "F0gl@mp!"}, 'Logged in successfully')
    ])
    def test_login_of_newly_created_user(self, form_data, expected_values):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("POST", "/fledge/login", body=json.dumps(form_data))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert expected_values == jdoc['message']

    def test_update_password(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("PUT", "/fledge/user/any1/password", body=json.dumps({"current_password": "User@123",
                                                                            "new_password": "F0gl@mp1"}),
                     headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': 'Password has been updated successfully for user id:<3>'} == jdoc

    def test_login_with_updated_password(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("POST", "/fledge/login", body=json.dumps({"username": "any1", "password": "F0gl@mp1"}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 'Logged in successfully' == jdoc['message']

    def test_reset_user(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("PUT", "/fledge/admin/3/reset", body=json.dumps({"role_id": 1, "password": "F0gl@mp!"}),
                     headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': 'User with id:<3> has been updated successfully'} == jdoc

    def test_login_with_resetted_password(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("POST", "/fledge/login", body=json.dumps({"username": "any1", "password": "F0gl@mp!"}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 'Logged in successfully' == jdoc['message']

    def test_delete_user(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("DELETE", "/fledge/admin/4/delete", headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': "User has been deleted successfully"} == jdoc

    def test_login_of_deleted_user(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("POST", "/fledge/login", body=json.dumps({"username": "admin1", "password": "F0gl@mp!"}))
        r = conn.getresponse()
        assert 404 == r.status
        assert "User does not exist" == r.reason

    def test_logout_all(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("PUT", '/fledge/1/logout', headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert jdoc['logout']

    def test_verify_logout(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("GET", '/fledge/asset', headers={"authorization": PASSWORD_TOKEN})
        r = conn.getresponse()
        assert 401 == r.status

    def test_admin_actions_forbidden_for_regular_user(self):
        """Test that regular user is not able to perform any actions that only an admin can"""
        # Login with regular user
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("POST", "/fledge/login", json.dumps({"username": "user", "password": "fledge"}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert not jdoc['admin']
        _token = jdoc["token"]

        # Create User
        conn.request("POST", "/fledge/admin/user", body=json.dumps({"username": "other",
                                                                     "password": "User@123"}),
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

    @pytest.mark.skip(reason="Currently this feature is not implemented.")
    def test_regular_user_access_to_admin_api_config(self, fledge_url):
        pass


class TestAuthCertificateWithTLS:
    def test_login_with_user_certificate(self, fledge_url, reset_fledge, change_to_auth_mandatory_certificate,
                                         generate_certificate_based_auth_token, enable_tls, wait_time):
        auth = 'certificate'
        enable_tls(fledge_url, wait_time, auth)

        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
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

    def test_login_with_admin_certificate(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
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
            global CERT_TOKEN
            CERT_TOKEN = jdoc["token"]

    def test_login_with_custom_certificate(self, remove_data_file):
        # Create a custom certificate and sign
        try:
            subprocess.run(["openssl genrsa -out custom.key 1024 2> /dev/null"], shell=True)
            subprocess.run(["openssl req -new -key custom.key -out custom.csr -subj '/C=IN/CN=user' 2> /dev/null"],
                           shell=True)
            subprocess.run(["openssl x509 -req -days 1 -in custom.csr "
                            "-CA $FLEDGE_ROOT/data/etc/certs/ca.cert -CAkey $FLEDGE_ROOT/data/etc/certs/ca.key "
                            "-set_serial 01 -out custom.cert 2> /dev/null"], shell=True)
        except subprocess.CalledProcessError:
            assert False, " Certificate creation failed!"

        # Login with custom certificate
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
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

    def test_login_with_invalid_credentials(self, remove_data_file):
        try:
            subprocess.run(["echo 'Fledge certificate' > template.cert"], shell=True)
        except subprocess.CalledProcessError:
            assert False, " Certificate creation failed!"

        # Login with custom certificate
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        cert_file_path = 'template.cert'
        with open(cert_file_path, 'r') as f:
            conn.request("POST", "/fledge/login", body=f)
            r = conn.getresponse()
            assert 400 == r.status
            assert 'Use a valid certificate to login.' == r.reason

        # Delete Certificates and keys created
        remove_data_file('template.cert')

    def test_login_username_admin(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("POST", "/fledge/login", json.dumps({"username": "admin", "password": "fledge"}))
        r = conn.getresponse()
        assert 400 == r.status
        assert "Use a valid certificate to login." == r.reason

    def test_ping_with_allow_ping_true(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("GET", "/fledge/ping")
        r = conn.getresponse()
        jdoc = json.loads(r.read().decode())
        assert "dataRead" in jdoc
        assert 0 == jdoc['dataRead'], "data NOT seen in ping header"

    def test_ingest(self, fledge_url, wait_time):
        add_south_http(fledge_url, HTTP_SOUTH_SVC_NAME, CERT_TOKEN, wait_time, tls_enabled=True)

        generate_json_for_fogbench(ASSET_NAME)

        send_data_using_fogbench(wait_time)

        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("GET", "/fledge/ping")
        r = conn.getresponse()
        jdoc = json.loads(r.read().decode())
        assert "dataRead" in jdoc
        assert 10 == jdoc['dataRead'], "data NOT seen in ping header"

    def test_ping_with_allow_ping_false(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        cert_file_path = os.path.join(os.path.expandvars('${FLEDGE_ROOT}'), 'data/etc/certs/admin.cert')
        with open(cert_file_path, 'r') as f:
            conn.request("POST", "/fledge/login", body=f)
            r = conn.getresponse()
            assert 200 == r.status
            r = r.read().decode()
            jdoc = json.loads(r)
            assert "Logged in successfully" == jdoc['message']
            _token = jdoc["token"]

        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("PUT", '/fledge/category/rest_api', json.dumps({"allowPing": "false"}),
                     headers={"authorization": _token})
        r = conn.getresponse()
        assert 200 == r.status

        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("PUT", '/fledge/logout', headers={"authorization": _token})
        r = conn.getresponse()
        assert 200 == r.status

        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("GET", "/fledge/ping")
        r = conn.getresponse()
        assert 401 == r.status
        assert "Unauthorized" == r.reason

    @pytest.mark.parametrize(("query", "expected_values"), [
        ('', {'users': [{'userId': 1, 'roleId': 1, 'userName': 'admin'},
                        {'userId': 2, 'roleId': 2, 'userName': 'user'}]}),
        ('?id=2', {'userId': 2, 'roleId': 2, 'userName': 'user'}),
        ('?username=admin', {'userId': 1, 'roleId': 1, 'userName': 'admin'}),
        ('?id=1&username=admin', {'userId': 1, 'roleId': 1, 'userName': 'admin'}),
    ])
    def test_get_users(self, query, expected_values):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("GET", "/fledge/user{}".format(query), headers={"authorization": CERT_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert expected_values == jdoc

    def test_get_roles(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("GET", "/fledge/user/role", headers={"authorization": CERT_TOKEN})
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
    def test_create_user(self, form_data, expected_values):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("POST", "/fledge/admin/user", body=json.dumps(form_data),
                     headers={"authorization": CERT_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert expected_values == jdoc

    def test_update_password(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("PUT", "/fledge/user/any1/password", body=json.dumps({"current_password": "User@123",
                                                                            "new_password": "F0gl@mp1"}),
                     headers={"authorization": CERT_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': 'Password has been updated successfully for user id:<3>'} == jdoc

    def test_reset_user(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("PUT", "/fledge/admin/3/reset", body=json.dumps({"role_id": 1, "password": "F0gl@mp!"}),
                     headers={"authorization": CERT_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': 'User with id:<3> has been updated successfully'} == jdoc

    def test_delete_user(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("DELETE", "/fledge/admin/4/delete", headers={"authorization": CERT_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert {'message': "User has been deleted successfully"} == jdoc

    def test_logout_all(self):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("PUT", '/fledge/1/logout', headers={"authorization": CERT_TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert jdoc['logout']

    def test_verify_logout(self, fledge_url):
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        conn.request("GET", '/fledge/asset', headers={"authorization": CERT_TOKEN})
        r = conn.getresponse()
        assert 401 == r.status

    def test_admin_actions_forbidden_for_regular_user(self):
        """Test that regular user is not able to perform any actions that only an admin can"""
        # Login with regular user
        conn = http.client.HTTPSConnection("localhost", 1995, context=context)
        cert_file_path = os.path.join(os.path.expandvars('${FLEDGE_ROOT}'), 'data/etc/certs/user.cert')
        with open(cert_file_path, 'r') as f:
            conn.request("POST", "/fledge/login", body=f)
            r = conn.getresponse()
            assert 200 == r.status
            r = r.read().decode()
            jdoc = json.loads(r)
            assert not jdoc['admin']
            _token = jdoc["token"]

        # Create User
        conn.request("POST", "/fledge/admin/user", body=json.dumps({"username": "other",
                                                                     "password": "User@123"}),
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

    @pytest.mark.skip(reason="Currently this feature is not implemented.")
    def test_regular_user_access_to_admin_api_config(self, fledge_url):
        pass
