# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Configuration system/python/conftest.py

"""
import subprocess
import os
import fnmatch
import http.client
import json
import base64
import ssl
import shutil
import pytest

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.fixture
def reset_and_start_foglamp():
    """Fixture that kills foglamp, reset database and starts foglamp again"""
    assert os.environ.get('FOGLAMP_ROOT') is not None
    subprocess.run(["$FOGLAMP_ROOT/scripts/foglamp kill"], shell=True, check=True)
    subprocess.run(["echo YES | $FOGLAMP_ROOT/scripts/foglamp reset"], shell=True, check=True)
    subprocess.run(["$FOGLAMP_ROOT/scripts/foglamp start"], shell=True)
    stat = subprocess.run(["$FOGLAMP_ROOT/scripts/foglamp status"], shell=True, stdout=subprocess.PIPE)
    assert "FogLAMP not running." not in stat.stdout.decode("utf-8")


def find(pattern, path):
    result = None
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result = os.path.join(root, name)
    return result


@pytest.fixture
def remove_data_file():
    """Fixture that removes any file from a given path"""
    def _remove_data_file(file_path=None):
        if os.path.exists(file_path):
            os.remove(file_path)
    return _remove_data_file


@pytest.fixture
def remove_directories():
    """Fixture that recursively removes any file and directories from a given path"""
    def _remove_directories(dir_path=None):
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path, ignore_errors=True)
    return _remove_directories


@pytest.fixture
def start_south():
    def _start_foglamp_south(south_plugin, south_branch, foglamp_url, service_name="play", config=None, use_pip_cache=True):
        """Start south service"""
        _config = config if config is not None else {}
        data = {"name": "{}".format(service_name), "type": "South", "plugin": "{}".format(south_plugin),
                "enabled": "true", "config": _config}

        conn = http.client.HTTPConnection(foglamp_url)
        try:
            subprocess.run(["$FOGLAMP_ROOT/tests/system/python/scripts/install_python_plugin {} south {} {}"
                           .format(south_branch, south_plugin, use_pip_cache)], shell=True, check=True)
        except subprocess.CalledProcessError:
            assert False, "{} plugin installation failed".format(south_plugin)

        # Create south service
        conn.request("POST", '/foglamp/service', json.dumps(data))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        retval = json.loads(r)
        assert service_name == retval["name"]
    return _start_foglamp_south


@pytest.fixture
def start_north_pi_v2():
    def _start_north_pi_server_c(foglamp_url, pi_host, pi_port, north_plugin, pi_token,
                                   taskname="North_Readings_to_PI"):
        """Start north task"""
        conn = http.client.HTTPConnection(foglamp_url)
        data = {"name": taskname,
                "plugin": "{}".format(north_plugin),
                "type": "north",
                "schedule_type": 3,
                "schedule_day": 0,
                "schedule_time": 0,
                "schedule_repeat": 30,
                "schedule_enabled": "true",
                "config": {"producerToken": {"value": pi_token},
                           "URL": {"value": "https://{}:{}/ingress/messages".format(pi_host, pi_port)}
                           }
                }
        conn.request("POST", '/foglamp/scheduled/task', json.dumps(data))
        r = conn.getresponse()
        assert 200 == r.status
        retval = r.read().decode()
        return retval
    return _start_north_pi_server_c

start_north_pi_server_c = start_north_pi_v2


@pytest.fixture
def read_data_from_pi():
    def _read_data_from_pi(host, admin, password, pi_database, asset, sensor):
        """ This method reads data from pi web api """

        # List of pi databases
        dbs = None
        # PI logical grouping of attributes and child elements
        elements = None
        # List of elements
        url_elements_list = None
        # Element's recorded data url
        url_recorded_data = None
        # Resources in the PI Web API are addressed by WebID, parameter used for deletion of element
        web_id = None

        username_password = "{}:{}".format(admin, password)
        username_password_b64 = base64.b64encode(username_password.encode('ascii')).decode("ascii")
        headers = {'Authorization': 'Basic %s' % username_password_b64}

        try:
            conn = http.client.HTTPSConnection(host, context=ssl._create_unverified_context())
            conn.request("GET", '/piwebapi/assetservers', headers=headers)
            res = conn.getresponse()
            r = json.loads(res.read().decode())
            dbs = r["Items"][0]["Links"]["Databases"]

            if dbs is not None:
                conn.request("GET", dbs, headers=headers)
                res = conn.getresponse()
                r = json.loads(res.read().decode())
                for el in r["Items"]:
                    if el["Name"] == pi_database:
                        elements = el["Links"]["Elements"]

            if elements is not None:
                conn.request("GET", elements, headers=headers)
                res = conn.getresponse()
                r = json.loads(res.read().decode())
                url_elements_list = r["Items"][0]["Links"]["Elements"]

            if url_elements_list is not None:
                conn.request("GET", url_elements_list, headers=headers)
                res = conn.getresponse()
                r = json.loads(res.read().decode())
                items = r["Items"]
                for el in items:
                    if el["Name"] == asset:
                        url_recorded_data = el["Links"]["RecordedData"]
                        web_id = el["WebId"]

            _data_pi = {}
            if url_recorded_data is not None:
                conn.request("GET", url_recorded_data, headers=headers)
                res = conn.getresponse()
                r = json.loads(res.read().decode())
                _items = r["Items"]
                for el in _items:
                    _recoded_value_list = []
                    for _head in sensor:
                        if el["Name"] == _head:
                            elx = el["Items"]
                            for _el in elx:
                                _recoded_value_list.append(_el["Value"])
                            _data_pi[_head] = _recoded_value_list
                conn.request("DELETE", '/piwebapi/elements/{}'.format(web_id), headers=headers)
                res = conn.getresponse()
                res.read()
                return _data_pi
        except (KeyError, IndexError, Exception):
            return None
    return _read_data_from_pi


def pytest_addoption(parser):
    parser.addoption("--south-branch", action="store", default="develop",
                     help="south branch name")
    parser.addoption("--north-branch", action="store", default="develop",
                     help="north branch name")
    parser.addoption("--foglamp-url", action="store", default="localhost:8081",
                     help="FogLAMP client api url")
    parser.addoption("--use-pip-cache", action="store", default=False,
                     help="use pip cache is requirement is available")
    # PI Config
    parser.addoption("--pi-host", action="store", default="pi-server",
                     help="PI Server Host Name/IP")
    parser.addoption("--pi-port", action="store", default="5460", type=int,
                     help="PI Server Port")
    parser.addoption("--pi-db", action="store", default="pi-server-db",
                     help="PI Server database")
    parser.addoption("--pi-admin", action="store", default="pi-server-uid",
                     help="PI Server user login")
    parser.addoption("--pi-passwd", action="store", default="pi-server-pwd",
                     help="PI Server user login password")
    parser.addoption("--pi-token", action="store", default="omf_north_0001",
                     help="OMF Producer Token")

    # OCS Config
    parser.addoption("--ocs-tenant", action="store", default="ocs_tenant_id",
                     help="Tenant id of OCS")
    parser.addoption("--ocs-client-id", action="store", default="ocs_client_id",
                     help="Client id of OCS account")
    parser.addoption("--ocs-client-secret", action="store", default="ocs_client_secret",
                     help="Client Secret of OCS account")
    parser.addoption("--ocs-namespace", action="store", default="ocs_namespace_0001",
                     help="OCS namespace where the information are stored")
    parser.addoption("--ocs-token", action="store", default="ocs_north_0001",
                     help="Token of OCS account")

    parser.addoption("--south-plugin", action="store", default="playback",
                     help="Name of the South Plugin")
    parser.addoption("--south-service-name", action="store", default="play",
                     help="Name of the South Service")
    parser.addoption("--north-plugin", action="store", default="PI_Server_V2",
                     help="Name of the North Plugin")
    parser.addoption("--asset-name", action="store", default="systemtest",
                     help="Name of asset")
    parser.addoption("--wait-time", action="store", default=5, type=int,
                     help="Generic wait time between processes to run")
    parser.addoption("--retries", action="store", default=3, type=int,
                     help="Number of tries to make to fetch data from PI web api")

    # Kafka Config
    parser.addoption("--kafka-host", action="store", default="localhost",
                     help="Kafka Server Host Name/IP")
    parser.addoption("--kafka-port", action="store", default="9092", type=int,
                     help="Kafka Server Port")
    parser.addoption("--kafka-topic", action="store", default="FogLAMP", help="Kafka topic")
    parser.addoption("--kafka-rest-port", action="store", default="8082", help="Kafka Rest Proxy Port")


@pytest.fixture
def south_branch(request):
    return request.config.getoption("--south-branch")


@pytest.fixture
def north_branch(request):
    return request.config.getoption("--north-branch")


@pytest.fixture
def foglamp_url(request):
    return request.config.getoption("--foglamp-url")


@pytest.fixture
def use_pip_cache(request):
    return request.config.getoption("--use-pip-cache")


@pytest.fixture
def wait_time(request):
    return request.config.getoption("--wait-time")


@pytest.fixture
def retries(request):
    return request.config.getoption("--retries")


@pytest.fixture
def pi_host(request):
    return request.config.getoption("--pi-host")


@pytest.fixture
def pi_port(request):
    return request.config.getoption("--pi-port")


@pytest.fixture
def pi_db(request):
    return request.config.getoption("--pi-db")


@pytest.fixture
def pi_admin(request):
    return request.config.getoption("--pi-admin")


@pytest.fixture
def pi_passwd(request):
    return request.config.getoption("--pi-passwd")


@pytest.fixture
def pi_token(request):
    return request.config.getoption("--pi-token")


@pytest.fixture
def ocs_tenant(request):
    return request.config.getoption("--ocs-tenant")


@pytest.fixture
def ocs_client_id(request):
    return request.config.getoption("--ocs-client-id")


@pytest.fixture
def ocs_client_secret(request):
    return request.config.getoption("--ocs-client-secret")


@pytest.fixture
def ocs_namespace(request):
    return request.config.getoption("--ocs-namespace")


@pytest.fixture
def ocs_token(request):
    return request.config.getoption("--ocs-token")


@pytest.fixture
def south_plugin(request):
    return request.config.getoption("--south-plugin")


@pytest.fixture
def south_service_name(request):
    return request.config.getoption("--south-service-name")


@pytest.fixture
def north_plugin(request):
    return request.config.getoption("--north-plugin")


@pytest.fixture
def asset_name(request):
    return request.config.getoption("--asset-name")


@pytest.fixture
def kafka_host(request):
    return request.config.getoption("--kafka-host")


@pytest.fixture
def kafka_port(request):
    return request.config.getoption("--kafka-port")


@pytest.fixture
def kafka_topic(request):
    return request.config.getoption("--kafka-topic")


@pytest.fixture
def kafka_rest_port(request):
    return request.config.getoption("--kafka-rest-port")


def pytest_itemcollected(item):
    par = item.parent.obj
    node = item.obj
    pref = par.__doc__.strip() if par.__doc__ else par.__class__.__name__
    suf = node.__doc__.strip() if node.__doc__ else node.__name__
    if pref or suf:
        item._nodeid = ' '.join((pref, suf))
