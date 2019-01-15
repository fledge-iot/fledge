# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Configuration system/python/conftest.py

"""
import subprocess
import os
import http.client
import json
import pytest

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2018 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.fixture
def reset_and_start_foglamp():
    assert os.environ.get('FOGLAMP_ROOT') is not None
    subprocess.run(["$FOGLAMP_ROOT/scripts/foglamp kill"], shell=True, check=True)
    subprocess.run(["echo YES | $FOGLAMP_ROOT/scripts/foglamp reset"], shell=True, check=True)
    subprocess.run(["$FOGLAMP_ROOT/scripts/foglamp start"], shell=True)
    stat = subprocess.run(["$FOGLAMP_ROOT/scripts/foglamp status"], shell=True, stdout=subprocess.PIPE)
    assert "FogLAMP not running." not in stat.stdout.decode("utf-8")


@pytest.fixture
def start_south():
    def _start_foglamp_south(south_plugin, foglamp_url, config=None):
        """Start south service"""
        _config = config if config is not None else {}
        data = {"name": "play", "type": "South", "plugin": "{}".format(south_plugin), "enabled": "true",
                "config": _config}

        conn = http.client.HTTPConnection(foglamp_url)
        subprocess.run(["rm -rf /tmp/foglamp-south-{}".format(south_plugin)], shell=True, check=True)
        subprocess.run(["rm -rf $FOGLAMP_ROOT/python/foglamp/plugins/south/foglamp-south-{}".format(south_plugin)],
                       shell=True, check=True)
        subprocess.run(["git clone https://github.com/foglamp/foglamp-south-{}.git /tmp/foglamp-south-{}".
                       format(south_plugin, south_plugin)], shell=True, check=True)
        subprocess.run(["cp -r /tmp/foglamp-south-{}/python/foglamp/plugins/south/* "
                        "$FOGLAMP_ROOT/python/foglamp/plugins/south/".format(south_plugin)], shell=True, check=True)

        conn.request("POST", '/foglamp/service', json.dumps(data))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        retval = json.loads(r)
        assert "play" == retval["name"]
    return _start_foglamp_south


@pytest.fixture
def start_north():
    def _start_foglamp_north_pi_v2(foglamp_url, pi_host, pi_port, north_plugin, pi_token,
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
    return _start_foglamp_north_pi_v2


def pytest_addoption(parser):
    parser.addoption("--foglamp_url", action="store", default="localhost:8081",
                     help="foglmap client api url")
    parser.addoption("--pi_host", action="store", default="pi-server",
                     help="PI Server Host Name/IP")
    parser.addoption("--pi_port", action="store", default="5460",
                     help="PI Server PORT")
    parser.addoption("--pi_db", action="store", default="pi-server-db",
                     help="PI Server database")
    parser.addoption("--pi_admin", action="store", default="pi-server-uid",
                     help="PI Server user login")
    parser.addoption("--pi_passwd", action="store", default="pi-server-pwd",
                     help="PI Server user login password")
    parser.addoption("--pi_token", action="store", default="omf_north_0001",
                     help="OMF Producer Token")
    parser.addoption("--south_plugin", action="store", default="playback",
                     help="Name of the South Plugin")
    parser.addoption("--north_plugin", action="store", default="PI_Server_V2",
                     help="Name of the North Plugin")
    parser.addoption("--asset_name", action="store", default="systemtest",
                     help="Name of asset")
    parser.addoption("--wait_time", action="store", default=5,
                     help="Time to wait between retries")
    parser.addoption("--retries", action="store", default=3,
                     help="Number of tries to make to fetch data")


@pytest.fixture
def foglamp_url(request):
    return request.config.getoption("--foglamp_url")


@pytest.fixture
def wait_time(request):
    return request.config.getoption("--wait_time")


@pytest.fixture
def retries(request):
    return request.config.getoption("--retries")


@pytest.fixture
def pi_host(request):
    return request.config.getoption("--pi_host")


@pytest.fixture
def pi_port(request):
    return request.config.getoption("--pi_port")


@pytest.fixture
def pi_db(request):
    return request.config.getoption("--pi_db")


@pytest.fixture
def pi_admin(request):
    return request.config.getoption("--pi_admin")


@pytest.fixture
def pi_passwd(request):
    return request.config.getoption("--pi_passwd")


@pytest.fixture
def pi_token(request):
    return request.config.getoption("--pi_token")


@pytest.fixture
def south_plugin(request):
    return request.config.getoption("--south_plugin")


@pytest.fixture
def north_plugin(request):
    return request.config.getoption("--north_plugin")


@pytest.fixture
def asset_name(request):
    return request.config.getoption("--asset_name")

