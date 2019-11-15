# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" System tests that obtain the set of available packages for the current platform
    It then installs each of those plugin packages via REST API endpoints
"""
import os
import subprocess
import http.client
import json
import pytest
import py

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2019 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

available_pkg = []
counter = 4
"""  By default 4 plugins are installed i.e. all north
"""


@pytest.fixture
def reset_packages():
    try:
        subprocess.run(["$FOGLAMP_ROOT/tests/system/python/scripts/package/remove"], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "remove package script failed"


@pytest.fixture
def setup_package(package_build_version):
    try:
        subprocess.run(["$FOGLAMP_ROOT/tests/system/python/scripts/package/setup {}".format(package_build_version)],
                       shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "setup package script failed"


def load_data_from_json():
    _dir = os.path.dirname(os.path.realpath(__file__))
    file_path = py.path.local(_dir).join('/').join('data/package_list.json')
    with open(str(file_path)) as data_file:
        json_data = json.load(data_file)
    return json_data


class TestPackages:

    def test_reset_and_setup(self, reset_packages, setup_package):
        # TODO: Remove this workaround
        #  Use better setup & teardown methods
        pass

    def test_ping(self, foglamp_url):
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("GET", '/foglamp/ping')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert 1 < jdoc['uptime']
        assert isinstance(jdoc['uptime'], int)
        assert 0 == jdoc['dataRead']
        assert 0 == jdoc['dataSent']
        assert 0 == jdoc['dataPurged']
        assert 'FogLAMP' == jdoc['serviceName']
        assert 'green' == jdoc['health']
        assert jdoc['authenticationOptional'] is True
        assert jdoc['safeMode'] is False

    def test_available_plugin_packages(self, foglamp_url):
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("GET", '/foglamp/plugins/available')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        global available_pkg
        plugins = available_pkg = jdoc['plugins']
        assert len(plugins), "No plugin found"
        assert 'link' in jdoc
        assert 'foglamp-filter-python35' in plugins
        assert 'foglamp-north-http-north' in plugins
        assert 'foglamp-north-kafka' in plugins
        assert 'foglamp-notify-python35' in plugins
        assert 'foglamp-rule-outofbound' in plugins
        assert 'foglamp-south-modbus' in plugins
        assert 'foglamp-south-playback' in plugins

    def test_available_service_packages(self, foglamp_url):
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("GET", '/foglamp/service/available')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert 1 == len(jdoc['services'])
        assert 'foglamp-service-notification' == jdoc['services'][0]
        assert 'link' in jdoc

    def test_install_service_package(self, foglamp_url):
        conn = http.client.HTTPConnection(foglamp_url)
        data = {"format": "repository", "name": "foglamp-service-notification"}
        conn.request("POST", '/foglamp/service?action=install', json.dumps(data))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 'message' in jdoc
        assert 'link' in jdoc
        assert '{} is successfully installed'.format(data['name']) == jdoc['message']

        # verify service installed
        conn.request("GET", '/foglamp/service/installed')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert 3 == len(jdoc['services'])
        assert 'notification' in jdoc['services']

    # FIXME: when package_build_list do not call parameterized test
    @pytest.mark.parametrize("pkg_name", available_pkg)
    def test_install_plugin_package(self, foglamp_url, pkg_name, package_build_source_list, package_build_list):
        # FIXME: FOGL-3276 Remove once we have dedicated RPi with sensehat device attached
        #  otherwise its discovery fails

        if 'foglamp-south-sensehat' in available_pkg:
            available_pkg.remove('foglamp-south-sensehat')

        # When "package_build_source_list" is true then it will install all available packages
        # Otherwise install from list as we defined in JSON file
        if package_build_source_list.lower() == 'true':
            self._verify_and_install_package(foglamp_url, pkg_name)
        else:
            json_data = load_data_from_json()
            # If 'all' in 'package_build_list' then it will iterate each key in JSON file
            if 'all' in package_build_list:
                package_build_list = ",".join(json_data.keys())
            my_list = package_build_list.split(",")

            for pkg_list_cat in my_list:
                for k, pkg_list_name in json_data[pkg_list_cat][0].items():
                    for pkg_name in pkg_list_name:
                        full_pkg_name = 'foglamp-{}-{}'.format(k, pkg_name)
                        if full_pkg_name in available_pkg:
                            self._verify_and_install_package(foglamp_url, full_pkg_name)
                        else:
                            print("{} not found in available package list".format(full_pkg_name))

    def _verify_and_install_package(self, foglamp_url, pkg_name):
        print("Installing ", pkg_name)
        global counter
        conn = http.client.HTTPConnection(foglamp_url)
        data = {"format": "repository", "name": pkg_name}
        conn.request("POST", '/foglamp/plugins', json.dumps(data))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert '{} is successfully installed'.format(pkg_name) == jdoc['message']
        assert 'link' in jdoc
        # Special case: On flirax8 package installation this installs modbus package too as it depends upon
        # available package list always in alphabetically sorted order
        if pkg_name == 'foglamp-south-flirax8':
            available_pkg.remove('foglamp-south-modbus')
            counter += 1
        counter += 1
        conn.request("GET", '/foglamp/plugins/installed')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        print("Discovery counter value is: - ", counter, jdoc['plugins'])
        assert counter == len(jdoc['plugins'])
