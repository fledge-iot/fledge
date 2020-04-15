# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge.readthedocs.io/
# FLEDGE_END

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
counter = 3
errors = []
"""  By default 3 plugins are pre-installed i.e. all north
"""


@pytest.fixture
def reset_packages():
    try:
        subprocess.run(["$FLEDGE_ROOT/tests/system/python/scripts/package/remove"], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "remove package script failed"


@pytest.fixture
def setup_package(package_build_version):
    try:
        subprocess.run(["$FLEDGE_ROOT/tests/system/python/scripts/package/setup {}".format(package_build_version)],
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

    def test_ping(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/ping')
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
        assert 'Fledge' == jdoc['serviceName']
        assert 'green' == jdoc['health']
        assert jdoc['authenticationOptional'] is True
        assert jdoc['safeMode'] is False

    def test_available_plugin_packages(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/plugins/available')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        global available_pkg
        plugins = available_pkg = jdoc['plugins']
        assert len(plugins), "No plugin found"
        assert 'link' in jdoc
        assert 'fledge-filter-python35' in plugins
        assert 'fledge-north-http-north' in plugins
        assert 'fledge-north-kafka' in plugins
        assert 'fledge-notify-python35' in plugins
        assert 'fledge-rule-outofbound' in plugins
        assert 'fledge-south-modbus' in plugins
        assert 'fledge-south-playback' in plugins

    def test_available_service_packages(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/service/available')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert 1 == len(jdoc['services'])
        assert 'fledge-service-notification' == jdoc['services'][0]
        assert 'link' in jdoc

    def test_install_service_package(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        data = {"format": "repository", "name": "fledge-service-notification"}
        conn.request("POST", '/fledge/service?action=install', json.dumps(data))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 'message' in jdoc
        assert 'link' in jdoc
        assert '{} is successfully installed'.format(data['name']) == jdoc['message']

        # verify service installed
        conn.request("GET", '/fledge/service/installed')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert 3 == len(jdoc['services'])
        assert 'notification' in jdoc['services']

    def test_install_plugin_package(self, fledge_url, package_build_source_list, package_build_list):
        # FIXME: FOGL-3276 Remove once we have dedicated RPi with sensehat device attached
        #  otherwise its discovery fails

        if 'fledge-south-sensehat' in available_pkg:
            available_pkg.remove('fledge-south-sensehat')

        # When "package_build_source_list" is true then it will install all available packages
        # Otherwise install from list as we defined in JSON file
        if package_build_source_list.lower() == 'true':
            for pkg_name in available_pkg:
                self._verify_and_install_package(fledge_url, pkg_name)
            assert not errors, "Package errors have occurred: \n {}".format("\n".join(errors))
        else:
            json_data = load_data_from_json()
            # If 'all' in 'package_build_list' then it will iterate each key in JSON file
            if 'all' in package_build_list:
                package_build_list = ",".join(json_data.keys())
            my_list = package_build_list.split(",")

            for pkg_list_cat in my_list:
                for k, pkg_list_name in json_data[pkg_list_cat][0].items():
                    for pkg_name in pkg_list_name:
                        full_pkg_name = 'fledge-{}-{}'.format(k, pkg_name)
                        if full_pkg_name in available_pkg:
                            self._verify_and_install_package(fledge_url, full_pkg_name)
                        else:
                            print("{} not found in available package list".format(full_pkg_name))
            assert not errors, "Package errors have occurred: \n {}".format("\n".join(errors))

    def _verify_and_install_package(self, fledge_url, pkg_name):
        print("Installing %s package" % pkg_name)
        global counter
        global errors
        conn = http.client.HTTPConnection(fledge_url)
        data = {"format": "repository", "name": pkg_name}
        conn.request("POST", '/fledge/plugins', json.dumps(data))
        r = conn.getresponse()
        # assert 200 == r.status
        if r.status != 200:
            print("POST Install plugin failed due to %s while attempting %s" % (r.reason, pkg_name))
            errors.append("POST Install plugin failed due to {} while attempting {}".format(r.reason, pkg_name))
            return
        r = r.read().decode()
        jdoc = json.loads(r)
        assert '{} is successfully installed'.format(pkg_name) == jdoc['message']
        assert 'link' in jdoc
        # Special case: On flirax8 package installation this installs modbus package too as it depends upon
        # available package list always in alphabetically sorted order
        if pkg_name == 'fledge-south-flirax8':
            available_pkg.remove('fledge-south-modbus')
            counter += 1
        counter += 1
        conn.request("GET", '/fledge/plugins/installed')
        r = conn.getresponse()
        # assert 200 == r.status
        if r.status != 200:
            print("GET Plugins installed failed due to %s while attempting %s" % (r.reason, pkg_name))
            errors.append("GET Plugins installed failed due to {} while attempting {}".format(r.reason, pkg_name))
            counter -= 1
            return
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        # assert counter == len(jdoc['plugins'])
        if counter != len(jdoc['plugins']):
            print("Error in discovery of %s package" % pkg_name)
            errors.append("{} package discovery failed".format(pkg_name))
            counter -= 1
