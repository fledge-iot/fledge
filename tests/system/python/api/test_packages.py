# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" System tests that obtain the set of available packages for the current platform
    It then installs each of those plugin packages via REST API endpoints
"""

import subprocess
import http.client
import json
import pytest


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2019 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.fixture
def reset_plugins():
    try:
        subprocess.run(["$FOGLAMP_ROOT/tests/system/lab/remove"], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "reset plugin script failed"


@pytest.fixture
def setup_package(build_version):
    try:
        subprocess.run(["$FOGLAMP_ROOT/tests/system/python/scripts/setup_package {}".format(build_version)], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "setup package script failed"


class TestPackages:

    def test_reset_and_setup(self, reset_plugins, setup_package):
        # TODO: Remove this workaround
        # Use better setup & teardown methods
        pass

    def test_available_plugin_packages(self, foglamp_url):
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("GET", '/foglamp/plugins/available')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert 56 == len(jdoc['plugins'])
        assert 'link' in jdoc

    def test_install_plugin_package(self, foglamp_url):
        pass

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
        pass
