# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test REST API endpoints with different user types """

import http.client
import json
import time
import pytest


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2022 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

TOKEN = None
VIEW_USERNAME = "view"
VIEW_PWD = "V!3w@1"
DATA_VIEW_USERNAME = "dataview"
DATA_VIEW_PWD = "DV!3w$"
CONTROL_USERNAME = "control"
CONTROL_PWD = "C0ntrol!"


@pytest.fixture
def change_to_auth_mandatory(fledge_url, wait_time):
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


def test_setup(reset_and_start_fledge, change_to_auth_mandatory, fledge_url, wait_time):
    time.sleep(wait_time * 3)
    conn = http.client.HTTPConnection(fledge_url)
    # Admin login
    conn.request("POST", "/fledge/login", json.dumps({"username": "admin", "password": "fledge"}))
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    assert "Logged in successfully." == jdoc['message']
    assert "token" in jdoc
    assert jdoc['admin']
    admin_token = jdoc["token"]
    # Create view user
    view_payload = {"username": VIEW_USERNAME, "password": VIEW_PWD, "role_id": 3, "real_name": "View",
                    "description": "Only to view the configuration"}
    conn.request("POST", "/fledge/admin/user", body=json.dumps(view_payload), headers={"authorization": admin_token})
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    assert "{} user has been created successfully.".format(VIEW_USERNAME) == jdoc["message"]
    # Create Data view user
    data_view_payload = {"username": DATA_VIEW_USERNAME, "password": DATA_VIEW_PWD, "role_id": 4,
                         "real_name": "DataView", "description": "Only read the data in buffer"}
    conn.request("POST", "/fledge/admin/user", body=json.dumps(data_view_payload),
                 headers={"authorization": admin_token})
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    assert "{} user has been created successfully.".format(DATA_VIEW_USERNAME) == jdoc["message"]
    # Create Control user
    control_payload = {"username": CONTROL_USERNAME, "password": CONTROL_PWD, "role_id": 5, "real_name": "Control",
                       "description": "Same as editor can do and also have access for control scripts and pipelines"}
    conn.request("POST", "/fledge/admin/user", body=json.dumps(control_payload), headers={"authorization": admin_token})
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    assert "{} user has been created successfully.".format(CONTROL_USERNAME) == jdoc["message"]


class TestAPIEndpointsWithViewUserType:
    def test_login(self, fledge_url, wait_time):
        time.sleep(wait_time * 2)
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/login", json.dumps({"username": VIEW_USERNAME, "password": VIEW_PWD}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "Logged in successfully." == jdoc['message']
        assert "token" in jdoc
        assert not jdoc['admin']
        global TOKEN
        TOKEN = jdoc["token"]

    @pytest.mark.parametrize(("method", "route_path", "http_status_code"), [
        # common
        ("GET", "/fledge/ping", 200), ("PUT", "/fledge/shutdown", 403), ("PUT", "/fledge/restart", 403),
        # health
        ("GET", "/fledge/health/storage", 200), ("GET", "/fledge/health/logging", 200),
        # user & roles
        ("GET", "/fledge/user", 200), ("PUT", "/fledge/user", 500), ("PUT", "/fledge/user/1/password", 403),
        ("PUT", "/fledge/user/3/password", 500), ("GET", "/fledge/user/role", 200),
        # auth
        ("POST", "/fledge/login", 403), ("PUT", "/fledge/31/logout", 401),
        ("GET", "/fledge/auth/ott", 200),
        # admin
        ("POST", "/fledge/admin/user", 403), ("DELETE", "/fledge/admin/3/delete", 403), ("PUT", "/fledge/admin/3", 403),
        ("PUT", "/fledge/admin/3/enable", 403), ("PUT", "/fledge/admin/3/reset", 403),
        # category
        ("GET", "/fledge/category", 200), ("POST", "/fledge/category", 403), ("GET", "/fledge/category/General", 200),
        ("PUT", "/fledge/category/General", 403), ("DELETE", "/fledge/category/General", 403),
        ("POST", "/fledge/category/General/children", 403), ("GET", "/fledge/category/General/children", 200),
        ("DELETE", "/fledge/category/General/children/Advanced", 403),
        ("DELETE", "/fledge/category/General/parent", 403),
        ("GET", "/fledge/category/rest_api/allowPing", 200), ("PUT", "/fledge/category/rest_api/allowPing", 403),
        ("DELETE", "/fledge/category/rest_api/allowPing/value", 403),
        ("POST", "/fledge/category/rest_api/allowPing/upload", 403),
        # schedule processes & schedules
        ("GET", "/fledge/schedule/process", 200), ("POST", "/fledge/schedule/process", 403),
        ("GET", "/fledge/schedule/process/purge", 200),
        ("GET", "/fledge/schedule", 200), ("POST", "/fledge/schedule", 403), ("GET", "/fledge/schedule/type", 200),
        ("GET", "/fledge/schedule/2176eb68-7303-11e7-8cf7-a6006ad3dba0", 200),
        ("PUT", "/fledge/schedule/2176eb68-7303-11e7-8cf7-a6006ad3dba0/enable", 403),
        ("PUT", "/fledge/schedule/2176eb68-7303-11e7-8cf7-a6006ad3dba0/disable", 403),
        ("PUT", "/fledge/schedule/enable", 403), ("PUT", "/fledge/schedule/disable", 403),
        ("POST", "/fledge/schedule/start/2176eb68-7303-11e7-8cf7-a6006ad3dba0", 403),
        ("PUT", "/fledge/schedule/2176eb68-7303-11e7-8cf7-a6006ad3dba0", 403),
        ("DELETE", "/fledge/schedule/2176eb68-7303-11e7-8cf7-a6006ad3dba0", 403),
        # tasks
        ("GET", "/fledge/task", 200), ("GET", "/fledge/task/state", 200), ("GET", "/fledge/task/latest", 200),
        ("GET", "/fledge/task/123", 404), ("PUT", "/fledge/task/123/cancel", 403),
        ("POST", "/fledge/scheduled/task", 403), ("DELETE", "/fledge/scheduled/task/blah", 403),
        # service
        ("POST", "/fledge/service", 403), ("GET", "/fledge/service", 200), ("DELETE", "/fledge/service/blah", 403),
        # ("GET", "/fledge/service/available", 200), -- checked manually and commented out only to avoid apt-update
        ("GET", "/fledge/service/installed", 200),
        ("PUT", "/fledge/service/Southbound/blah/update", 403), ("POST", "/fledge/service/blah/otp", 403),
        # south & north
        ("GET", "/fledge/south", 200), ("GET", "/fledge/north", 200),
        # asset browse
        ("GET", "/fledge/asset", 200), ("GET", "/fledge/asset/sinusoid", 200),
        ("GET", "/fledge/asset/sinusoid/latest", 200),
        ("GET", "/fledge/asset/sinusoid/summary", 404), ("GET", "/fledge/asset/sinusoid/sinusoid", 200),
        ("GET", "/fledge/asset/sinusoid/sinusoid/summary", 404), ("GET", "/fledge/asset/sinusoid/sinusoid/series", 200),
        ("GET", "/fledge/asset/sinusoid/bucket/1", 200), ("GET", "/fledge/asset/sinusoid/sinusoid/bucket/1", 200),
        ("GET", "/fledge/structure/asset", 200), ("DELETE", "/fledge/asset", 403),
        ("DELETE", "/fledge/asset/sinusoid", 403),
        # asset tracker
        ("GET", "/fledge/track", 200), ("GET", "/fledge/track/storage/assets", 200),
        ("PUT", "/fledge/track/service/foo/asset/bar/event/Ingest", 403),
        # statistics
        ("GET", "/fledge/statistics", 200), ("GET", "/fledge/statistics/history", 200),
        ("GET", "/fledge/statistics/rate?periods=1&statistics=FOO", 200),
        # audit trail
        ("POST", "/fledge/audit", 403), ("GET", "/fledge/audit", 200), ("GET", "/fledge/audit/logcode", 200),
        ("GET", "/fledge/audit/severity", 200),
        # backup & restore
        ("GET", "/fledge/backup", 200), ("POST", "/fledge/backup", 403), ("POST", "/fledge/backup/upload", 403),
        ("GET", "/fledge/backup/status", 200), ("GET", "/fledge/backup/123", 404),
        ("DELETE", "/fledge/backup/123", 403), ("GET", "/fledge/backup/123/download", 404),
        ("PUT", "/fledge/backup/123/restore", 403),
        # package update
        # ("GET", "/fledge/update", 200), -- checked manually and commented out only to avoid apt-update run
        ("PUT", "/fledge/update", 403),
        # certs store
        ("GET", "/fledge/certificate", 200), ("POST", "/fledge/certificate", 403),
        ("DELETE", "/fledge/certificate/user", 403),
        # support bundle
        ("GET", "/fledge/support", 200), ("GET", "/fledge/support/foo", 400), ("POST", "/fledge/support", 403),
        # syslogs & package logs
        ("GET", "/fledge/syslog", 200), ("GET", "/fledge/package/log", 200), ("GET", "/fledge/package/log/foo", 400),
        ("GET", "/fledge/package/install/status", 404),
        # plugins
        ("GET", "/fledge/plugins/installed", 200),
        # ("GET", "/fledge/plugins/available", 200), -- checked manually and commented out only to avoid apt-update
        ("POST", "/fledge/plugins", 403), ("PUT", "/fledge/plugins/south/sinusoid/update", 403),
        ("DELETE", "/fledge/plugins/south/sinusoid", 403), ("GET", "/fledge/service/foo/persist", 404),
        ("GET", "/fledge/service/foo/plugin/omf/data", 404), ("POST", "/fledge/service/foo/plugin/omf/data", 403),
        ("DELETE", "/fledge/service/foo/plugin/omf/data", 403),
        # filters
        ("POST", "/fledge/filter", 403), ("PUT", "/fledge/filter/foo/pipeline", 403),
        ("GET", "/fledge/filter/foo/pipeline", 404), ("GET", "/fledge/filter/bar", 404), ("GET", "/fledge/filter", 200),
        ("DELETE", "/fledge/filter/foo/pipeline", 403), ("DELETE", "/fledge/filter/bar", 403),
        # snapshots
        ("GET", "/fledge/snapshot/plugins", 403), ("POST", "/fledge/snapshot/plugins", 403),
        ("PUT", "/fledge/snapshot/plugins/1", 403), ("DELETE", "/fledge/snapshot/plugins/1", 403),
        ("GET", "/fledge/snapshot/category", 403), ("POST", "/fledge/snapshot/category", 403),
        ("PUT", "/fledge/snapshot/category/1", 403), ("DELETE", "/fledge/snapshot/category/1", 403),
        ("GET", "/fledge/snapshot/schedule", 403), ("POST", "/fledge/snapshot/schedule", 403),
        ("PUT", "/fledge/snapshot/schedule/1", 403), ("DELETE", "/fledge/snapshot/schedule/1", 403),
        # repository
        ("POST", "/fledge/repository", 403),
        # ACL
        ("POST", "/fledge/ACL", 403), ("GET", "/fledge/ACL", 200), ("GET", "/fledge/ACL/foo", 404),
        ("PUT", "/fledge/ACL/foo", 403), ("DELETE", "/fledge/ACL/foo", 403), ("PUT", "/fledge/service/foo/ACL", 403),
        ("DELETE", "/fledge/service/foo/ACL", 403),
        # control script
        ("POST", "/fledge/control/script", 403), ("GET", "/fledge/control/script", 200),
        ("GET", "/fledge/control/script/foo", 404), ("PUT", "/fledge/control/script/foo", 403),
        ("DELETE", "/fledge/control/script/foo", 403), ("POST", "/fledge/control/script/foo/schedule", 403),
        # control pipeline
        ("POST", "/fledge/control/pipeline", 403), ("GET", "/fledge/control/lookup", 200),
        ("GET", "/fledge/control/pipeline", 200), ("GET", "/fledge/control/pipeline/1", 404),
        ("PUT", "/fledge/control/pipeline/1", 403), ("DELETE", "/fledge/control/pipeline/1", 403),
        # python packages
        ("GET", "/fledge/python/packages", 200), ("POST", "/fledge/python/package", 403),
        # notification
        ("GET", "/fledge/notification", 200), ("GET", "/fledge/notification/plugin", 404),
        ("GET", "/fledge/notification/type", 200), ("GET", "/fledge/notification/N1", 400),
        ("POST", "/fledge/notification", 403), ("PUT", "/fledge/notification/N1", 403),
        ("DELETE", "/fledge/notification/N1", 403), ("GET", "/fledge/notification/N1/delivery", 404),
        ("POST", "/fledge/notification/N1/delivery", 403), ("GET", "/fledge/notification/N1/delivery/C1", 404),
        ("DELETE", "/fledge/notification/N1/delivery/C1", 403),
        # alerts
        ("GET", "/fledge/alert", 200), ("DELETE", "/fledge/alert", 403), ("DELETE", "/fledge/alert/blah", 403)
    ])
    def test_endpoints(self, fledge_url, method, route_path, http_status_code, storage_plugin):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request(method, route_path, headers={"authorization": TOKEN})
        r = conn.getresponse()
        assert http_status_code == r.status
        r.read().decode()

    def test_logout_me(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", '/fledge/logout', headers={"authorization": TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert jdoc['logout']


class TestAPIEndpointsWithDataViewUserType:
    def test_login(self, fledge_url, wait_time):
        time.sleep(wait_time * 2)
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/login", json.dumps({"username": DATA_VIEW_USERNAME, "password": DATA_VIEW_PWD}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "Logged in successfully." == jdoc['message']
        assert "token" in jdoc
        assert not jdoc['admin']
        global TOKEN
        TOKEN = jdoc["token"]

    @pytest.mark.parametrize(("method", "route_path", "http_status_code"), [
        # common
        ("GET", "/fledge/ping", 200), ("PUT", "/fledge/shutdown", 403), ("PUT", "/fledge/restart", 403),
        # health
        ("GET", "/fledge/health/storage", 403), ("GET", "/fledge/health/logging", 403),
        # user & roles
        ("GET", "/fledge/user", 403), ("PUT", "/fledge/user", 500), ("PUT", "/fledge/user/1/password", 403),
        ("PUT", "/fledge/user/4/password", 500), ("GET", "/fledge/user/role", 200),
        # auth
        ("POST", "/fledge/login", 403), ("PUT", "/fledge/31/logout", 401),
        ("GET", "/fledge/auth/ott", 403),
        # admin
        ("POST", "/fledge/admin/user", 403), ("DELETE", "/fledge/admin/3/delete", 403), ("PUT", "/fledge/admin/3", 403),
        ("PUT", "/fledge/admin/3/enable", 403), ("PUT", "/fledge/admin/3/reset", 403),
        # category
        ("GET", "/fledge/category", 403), ("POST", "/fledge/category", 403), ("GET", "/fledge/category/General", 403),
        ("PUT", "/fledge/category/General", 403), ("DELETE", "/fledge/category/General", 403),
        ("POST", "/fledge/category/General/children", 403), ("GET", "/fledge/category/General/children", 403),
        ("DELETE", "/fledge/category/General/children/Advanced", 403),
        ("DELETE", "/fledge/category/General/parent", 403),
        ("GET", "/fledge/category/rest_api/allowPing", 403), ("PUT", "/fledge/category/rest_api/allowPing", 403),
        ("DELETE", "/fledge/category/rest_api/allowPing/value", 403),
        ("POST", "/fledge/category/rest_api/allowPing/upload", 403),
        # schedule processes & schedules
        ("GET", "/fledge/schedule/process", 403), ("POST", "/fledge/schedule/process", 403),
        ("GET", "/fledge/schedule/process/purge", 403),
        ("GET", "/fledge/schedule", 403), ("POST", "/fledge/schedule", 403), ("GET", "/fledge/schedule/type", 403),
        ("GET", "/fledge/schedule/2176eb68-7303-11e7-8cf7-a6006ad3dba0", 403),
        ("PUT", "/fledge/schedule/2176eb68-7303-11e7-8cf7-a6006ad3dba0/enable", 403),
        ("PUT", "/fledge/schedule/2176eb68-7303-11e7-8cf7-a6006ad3dba0/disable", 403),
        ("PUT", "/fledge/schedule/enable", 403), ("PUT", "/fledge/schedule/disable", 403),
        ("POST", "/fledge/schedule/start/2176eb68-7303-11e7-8cf7-a6006ad3dba0", 403),
        ("PUT", "/fledge/schedule/2176eb68-7303-11e7-8cf7-a6006ad3dba0", 403),
        ("DELETE", "/fledge/schedule/2176eb68-7303-11e7-8cf7-a6006ad3dba0", 403),
        # tasks
        ("GET", "/fledge/task", 403), ("GET", "/fledge/task/state", 403), ("GET", "/fledge/task/latest", 403),
        ("GET", "/fledge/task/123", 403), ("PUT", "/fledge/task/123/cancel", 403),
        ("POST", "/fledge/scheduled/task", 403), ("DELETE", "/fledge/scheduled/task/blah", 403),
        # service
        ("POST", "/fledge/service", 403), ("GET", "/fledge/service", 200), ("DELETE", "/fledge/service/blah", 403),
        ("GET", "/fledge/service/available", 403), ("GET", "/fledge/service/installed", 403),
        ("PUT", "/fledge/service/Southbound/blah/update", 403), ("POST", "/fledge/service/blah/otp", 403),
        # south & north
        ("GET", "/fledge/south", 403), ("GET", "/fledge/north", 403),
        # asset browse
        ("GET", "/fledge/asset", 200), ("GET", "/fledge/asset/sinusoid", 200),
        ("GET", "/fledge/asset/sinusoid/latest", 200),
        ("GET", "/fledge/asset/sinusoid/summary", 404), ("GET", "/fledge/asset/sinusoid/sinusoid", 200),
        ("GET", "/fledge/asset/sinusoid/sinusoid/summary", 404), ("GET", "/fledge/asset/sinusoid/sinusoid/series", 200),
        ("GET", "/fledge/asset/sinusoid/bucket/1", 200), ("GET", "/fledge/asset/sinusoid/sinusoid/bucket/1", 200),
        ("GET", "/fledge/structure/asset", 403), ("DELETE", "/fledge/asset", 403),
        ("DELETE", "/fledge/asset/sinusoid", 403),
        # asset tracker
        ("GET", "/fledge/track", 403), ("GET", "/fledge/track/storage/assets", 403),
        ("PUT", "/fledge/track/service/foo/asset/bar/event/Ingest", 403),
        # statistics
        ("GET", "/fledge/statistics", 200), ("GET", "/fledge/statistics/history", 200),
        ("GET", "/fledge/statistics/rate?periods=1&statistics=FOO", 200),
        # audit trail
        ("POST", "/fledge/audit", 403), ("GET", "/fledge/audit", 403), ("GET", "/fledge/audit/logcode", 403),
        ("GET", "/fledge/audit/severity", 403),
        # backup & restore
        ("GET", "/fledge/backup", 403), ("POST", "/fledge/backup", 403), ("POST", "/fledge/backup/upload", 403),
        ("GET", "/fledge/backup/status", 403), ("GET", "/fledge/backup/123", 403),
        ("DELETE", "/fledge/backup/123", 403), ("GET", "/fledge/backup/123/download", 403),
        ("PUT", "/fledge/backup/123/restore", 403),
        # package update
        # ("GET", "/fledge/update", 200), -- checked manually and commented out only to avoid apt-update
        ("PUT", "/fledge/update", 403),
        # certs store
        ("GET", "/fledge/certificate", 403), ("POST", "/fledge/certificate", 403),
        ("DELETE", "/fledge/certificate/user", 403),
        # support bundle
        ("GET", "/fledge/support", 403), ("GET", "/fledge/support/foo", 403), ("POST", "/fledge/support", 403),
        # syslogs & package logs
        ("GET", "/fledge/syslog", 403), ("GET", "/fledge/package/log", 403), ("GET", "/fledge/package/log/foo", 403),
        ("GET", "/fledge/package/install/status", 403),
        # plugins
        ("GET", "/fledge/plugins/installed", 403), ("GET", "/fledge/plugins/available", 403),
        ("POST", "/fledge/plugins", 403), ("PUT", "/fledge/plugins/south/sinusoid/update", 403),
        ("DELETE", "/fledge/plugins/south/sinusoid", 403), ("GET", "/fledge/service/foo/persist", 403),
        ("GET", "/fledge/service/foo/plugin/omf/data", 403), ("POST", "/fledge/service/foo/plugin/omf/data", 403),
        ("DELETE", "/fledge/service/foo/plugin/omf/data", 403),
        # filters
        ("POST", "/fledge/filter", 403), ("PUT", "/fledge/filter/foo/pipeline", 403),
        ("GET", "/fledge/filter/foo/pipeline", 403), ("GET", "/fledge/filter/bar", 403), ("GET", "/fledge/filter", 403),
        ("DELETE", "/fledge/filter/foo/pipeline", 403), ("DELETE", "/fledge/filter/bar", 403),
        # snapshots
        ("GET", "/fledge/snapshot/plugins", 403), ("POST", "/fledge/snapshot/plugins", 403),
        ("PUT", "/fledge/snapshot/plugins/1", 403), ("DELETE", "/fledge/snapshot/plugins/1", 403),
        ("GET", "/fledge/snapshot/category", 403), ("POST", "/fledge/snapshot/category", 403),
        ("PUT", "/fledge/snapshot/category/1", 403), ("DELETE", "/fledge/snapshot/category/1", 403),
        ("GET", "/fledge/snapshot/schedule", 403), ("POST", "/fledge/snapshot/schedule", 403),
        ("PUT", "/fledge/snapshot/schedule/1", 403), ("DELETE", "/fledge/snapshot/schedule/1", 403),
        # repository
        ("POST", "/fledge/repository", 403),
        # ACL
        ("POST", "/fledge/ACL", 403), ("GET", "/fledge/ACL", 403), ("GET", "/fledge/ACL/foo", 403),
        ("PUT", "/fledge/ACL/foo", 403), ("DELETE", "/fledge/ACL/foo", 403), ("PUT", "/fledge/service/foo/ACL", 403),
        ("DELETE", "/fledge/service/foo/ACL", 403),
        # control script
        ("POST", "/fledge/control/script", 403), ("GET", "/fledge/control/script", 403),
        ("GET", "/fledge/control/script/foo", 403), ("PUT", "/fledge/control/script/foo", 403),
        ("DELETE", "/fledge/control/script/foo", 403), ("POST", "/fledge/control/script/foo/schedule", 403),
        # control pipeline
        ("POST", "/fledge/control/pipeline", 403), ("GET", "/fledge/control/lookup", 403),
        ("GET", "/fledge/control/pipeline", 403), ("GET", "/fledge/control/pipeline/1", 403),
        ("PUT", "/fledge/control/pipeline/1", 403), ("DELETE", "/fledge/control/pipeline/1", 403),
        # python packages
        ("GET", "/fledge/python/packages", 403), ("POST", "/fledge/python/package", 403),
        # notification
        ("GET", "/fledge/notification", 403), ("GET", "/fledge/notification/plugin", 403),
        ("GET", "/fledge/notification/type", 403), ("GET", "/fledge/notification/N1", 403),
        ("POST", "/fledge/notification", 403), ("PUT", "/fledge/notification/N1", 403),
        ("DELETE", "/fledge/notification/N1", 403), ("GET", "/fledge/notification/N1/delivery", 403),
        ("POST", "/fledge/notification/N1/delivery", 403), ("GET", "/fledge/notification/N1/delivery/C1", 403),
        ("DELETE", "/fledge/notification/N1/delivery/C1", 403),
        # alerts
        ("GET", "/fledge/alert", 403), ("DELETE", "/fledge/alert", 403), ("DELETE", "/fledge/alert/blah", 403)
    ])
    def test_endpoints(self, fledge_url, method, route_path, http_status_code, storage_plugin):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request(method, route_path, headers={"authorization": TOKEN})
        r = conn.getresponse()
        assert http_status_code == r.status
        r.read().decode()

    def test_logout_me(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", '/fledge/logout', headers={"authorization": TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert jdoc['logout']


class TestAPIEndpointsWithControlUserType:
    def test_login(self, fledge_url, wait_time):
        time.sleep(wait_time * 2)
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", "/fledge/login", json.dumps({"username": CONTROL_USERNAME, "password": CONTROL_PWD}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "Logged in successfully." == jdoc['message']
        assert "token" in jdoc
        assert not jdoc['admin']
        global TOKEN
        TOKEN = jdoc["token"]

    @pytest.mark.parametrize(("method", "route_path", "http_status_code"), [
        # common
        ("GET", "/fledge/ping", 200),  # ("PUT", "/fledge/shutdown", 200), ("PUT", "/fledge/restart", 200),
        # health
        ("GET", "/fledge/health/storage", 200), ("GET", "/fledge/health/logging", 200),
        # user & roles
        ("GET", "/fledge/user", 200), ("PUT", "/fledge/user", 500), ("PUT", "/fledge/user/1/password", 500),
        ("PUT", "/fledge/user/3/password", 500), ("GET", "/fledge/user/role", 200),
        # auth
        ("POST", "/fledge/login", 500), ("PUT", "/fledge/31/logout", 401),
        ("GET", "/fledge/auth/ott", 200),
        # admin
        ("POST", "/fledge/admin/user", 403), ("DELETE", "/fledge/admin/3/delete", 403), ("PUT", "/fledge/admin/3", 403),
        ("PUT", "/fledge/admin/3/enable", 403), ("PUT", "/fledge/admin/3/reset", 403),
        # category
        ("GET", "/fledge/category", 200), ("POST", "/fledge/category", 400), ("GET", "/fledge/category/General", 200),
        ("PUT", "/fledge/category/General", 400), ("DELETE", "/fledge/category/General", 400),
        ("POST", "/fledge/category/General/children", 500), ("GET", "/fledge/category/General/children", 200),
        ("DELETE", "/fledge/category/General/children/Advanced", 200),
        ("DELETE", "/fledge/category/General/parent", 200),
        ("GET", "/fledge/category/rest_api/allowPing", 200), ("PUT", "/fledge/category/rest_api/allowPing", 500),
        ("DELETE", "/fledge/category/rest_api/allowPing/value", 200),
        ("POST", "/fledge/category/rest_api/allowPing/upload", 400),
        # schedule processes & schedules
        ("GET", "/fledge/schedule/process", 200), ("POST", "/fledge/schedule/process", 500),
        ("GET", "/fledge/schedule/process/purge", 200),
        ("GET", "/fledge/schedule", 200), ("POST", "/fledge/schedule", 400), ("GET", "/fledge/schedule/type", 200),
        ("GET", "/fledge/schedule/2176eb68-7303-11e7-8cf7-a6006ad3dba0", 200),
        ("PUT", "/fledge/schedule/2176eb68-7303-11e7-8cf7-a6006ad3dba0/enable", 200),
        ("PUT", "/fledge/schedule/2176eb68-7303-11e7-8cf7-a6006ad3dba0/disable", 200),
        ("PUT", "/fledge/schedule/enable", 404), ("PUT", "/fledge/schedule/disable", 404),
        ("POST", "/fledge/schedule/start/2176eb68-7303-11e7-8cf7-a6006ad3dba0", 200),
        ("PUT", "/fledge/schedule/2176eb68-7303-11e7-8cf7-a6006ad3dba0", 400),
        ("DELETE", "/fledge/schedule/d1631422-9ec6-11e7-abc4-cec278b6b50a", 200),
        # tasks
        ("GET", "/fledge/task", 200), ("GET", "/fledge/task/state", 200), ("GET", "/fledge/task/latest", 200),
        ("GET", "/fledge/task/123", 404), ("PUT", "/fledge/task/123/cancel", 404),
        ("POST", "/fledge/scheduled/task", 400), ("DELETE", "/fledge/scheduled/task/blah", 404),
        # service
        ("POST", "/fledge/service", 400), ("GET", "/fledge/service", 200), ("DELETE", "/fledge/service/blah", 404),
        # ("GET", "/fledge/service/available", 200), -- checked manually and commented out only to avoid apt-update
        ("GET", "/fledge/service/installed", 200),
        ("PUT", "/fledge/service/Southbound/blah/update", 400), ("POST", "/fledge/service/blah/otp", 403),
        # south & north
        ("GET", "/fledge/south", 200), ("GET", "/fledge/north", 200),
        # asset browse
        ("GET", "/fledge/asset", 200), ("GET", "/fledge/asset/sinusoid", 200),
        ("GET", "/fledge/asset/sinusoid/latest", 200),
        ("GET", "/fledge/asset/sinusoid/summary", 404), ("GET", "/fledge/asset/sinusoid/sinusoid", 200),
        ("GET", "/fledge/asset/sinusoid/sinusoid/summary", 404), ("GET", "/fledge/asset/sinusoid/sinusoid/series", 200),
        ("GET", "/fledge/asset/sinusoid/bucket/1", 200), ("GET", "/fledge/asset/sinusoid/sinusoid/bucket/1", 200),
        ("GET", "/fledge/structure/asset", 200), ("DELETE", "/fledge/asset", 200),
        ("DELETE", "/fledge/asset/sinusoid", 200),
        # asset tracker
        ("GET", "/fledge/track", 200), ("GET", "/fledge/track/storage/assets", 200),
        ("PUT", "/fledge/track/service/foo/asset/bar/event/Ingest", 404),
        # statistics
        ("GET", "/fledge/statistics", 200), ("GET", "/fledge/statistics/history", 200),
        ("GET", "/fledge/statistics/rate?periods=1&statistics=FOO", 200),
        # audit trail
        ("POST", "/fledge/audit", 500), ("GET", "/fledge/audit", 200), ("GET", "/fledge/audit/logcode", 200),
        ("GET", "/fledge/audit/severity", 200),
        # backup & restore
        ("GET", "/fledge/backup", 200),  # ("POST", "/fledge/backup", 200), -- checked manually
        ("POST", "/fledge/backup/upload", 500),
        ("GET", "/fledge/backup/status", 200), ("GET", "/fledge/backup/123", 404),
        ("DELETE", "/fledge/backup/123", 404), ("GET", "/fledge/backup/123/download", 404),
        ("PUT", "/fledge/backup/123/restore", 200),
        # package update
        # ("GET", "/fledge/update", 200), -- checked manually and commented out only to avoid apt-update run
        # ("PUT", "/fledge/update", 200), -- checked manually
        # certs store
        ("GET", "/fledge/certificate", 200), ("POST", "/fledge/certificate", 400),
        ("DELETE", "/fledge/certificate/user", 403),
        # support bundle
        ("GET", "/fledge/support", 200), ("GET", "/fledge/support/foo", 400),
        # ("POST", "/fledge/support", 200), - checked manually
        # syslogs & package logs
        ("GET", "/fledge/syslog", 200), ("GET", "/fledge/package/log", 200), ("GET", "/fledge/package/log/foo", 400),
        ("GET", "/fledge/package/install/status", 404),
        # plugins
        ("GET", "/fledge/plugins/installed", 200),
        # ("GET", "/fledge/plugins/available", 200), -- checked manually and commented out only to avoid apt operations
        # ("PUT", "/fledge/plugins/south/sinusoid/update", 200),
        # ("DELETE", "/fledge/plugins/south/sinusoid", 404),
        ("POST", "/fledge/plugins", 400), ("GET", "/fledge/service/foo/persist", 404),
        ("GET", "/fledge/service/foo/plugin/omf/data", 404), ("POST", "/fledge/service/foo/plugin/omf/data", 404),
        ("DELETE", "/fledge/service/foo/plugin/omf/data", 404),
        # filters
        ("POST", "/fledge/filter", 404), ("PUT", "/fledge/filter/foo/pipeline", 404),
        ("GET", "/fledge/filter/foo/pipeline", 404), ("GET", "/fledge/filter/bar", 404), ("GET", "/fledge/filter", 200),
        ("DELETE", "/fledge/filter/foo/pipeline", 500), ("DELETE", "/fledge/filter/bar", 404),
        # snapshots
        ("GET", "/fledge/snapshot/plugins", 403), ("POST", "/fledge/snapshot/plugins", 403),
        ("PUT", "/fledge/snapshot/plugins/1", 403), ("DELETE", "/fledge/snapshot/plugins/1", 403),
        ("GET", "/fledge/snapshot/category", 403), ("POST", "/fledge/snapshot/category", 403),
        ("PUT", "/fledge/snapshot/category/1", 403), ("DELETE", "/fledge/snapshot/category/1", 403),
        ("GET", "/fledge/snapshot/schedule", 403), ("POST", "/fledge/snapshot/schedule", 403),
        ("PUT", "/fledge/snapshot/schedule/1", 403), ("DELETE", "/fledge/snapshot/schedule/1", 403),
        # repository
        ("POST", "/fledge/repository", 400),
        # ACL
        ("POST", "/fledge/ACL", 403), ("GET", "/fledge/ACL", 200), ("GET", "/fledge/ACL/foo", 404),
        ("PUT", "/fledge/ACL/foo", 403), ("DELETE", "/fledge/ACL/foo", 403), ("PUT", "/fledge/service/foo/ACL", 403),
        ("DELETE", "/fledge/service/foo/ACL", 403),
        # control script
        ("POST", "/fledge/control/script", 400), ("GET", "/fledge/control/script", 200),
        ("GET", "/fledge/control/script/foo", 404), ("PUT", "/fledge/control/script/foo", 400),
        ("DELETE", "/fledge/control/script/foo", 404), ("POST", "/fledge/control/script/foo/schedule", 404),
        # control pipeline
        ("POST", "/fledge/control/pipeline", 400), ("GET", "/fledge/control/lookup", 200),
        ("GET", "/fledge/control/pipeline", 200), ("GET", "/fledge/control/pipeline/1", 404),
        ("PUT", "/fledge/control/pipeline/1", 404), ("DELETE", "/fledge/control/pipeline/1", 404),
        # python packages
        ("GET", "/fledge/python/packages", 200), ("POST", "/fledge/python/package", 500),
        # notification
        ("GET", "/fledge/notification", 200), ("GET", "/fledge/notification/plugin", 404),
        ("GET", "/fledge/notification/type", 200), ("GET", "/fledge/notification/N1", 400),
        ("POST", "/fledge/notification", 404), ("PUT", "/fledge/notification/N1", 404),
        ("DELETE", "/fledge/notification/N1", 404), ("GET", "/fledge/notification/N1/delivery", 404),
        ("POST", "/fledge/notification/N1/delivery", 400), ("GET", "/fledge/notification/N1/delivery/C1", 404),
        ("DELETE", "/fledge/notification/N1/delivery/C1", 404),
        # alerts
        ("GET", "/fledge/alert", 200), ("DELETE", "/fledge/alert", 200), ("DELETE", "/fledge/alert/blah", 404)
    ])
    def test_endpoints(self, fledge_url, method, route_path, http_status_code, storage_plugin):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request(method, route_path, headers={"authorization": TOKEN})
        r = conn.getresponse()
        assert http_status_code == r.status
        r.read().decode()

    def test_logout_me(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", '/fledge/logout', headers={"authorization": TOKEN})
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert jdoc['logout']
