# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test add service using poll and async plugins for both python & C version REST API """

import subprocess
import http.client
import json
import time
from uuid import UUID
from collections import Counter
import pytest
import plugin_and_service


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


SVC_NAME_1 = 'Random Walk #1'
SVC_NAME_2 = 'HTTP-SOUTH'
SVC_NAME_3 = 'Bench'
SVC_NAME_4 = 'randomwalk'


@pytest.fixture
def install_plugins():
    plugin_and_service.install('south', plugin='randomwalk')
    plugin_and_service.install('south', plugin='http')
    plugin_and_service.install('south', plugin='benchmark', plugin_lang='C')
    # TODO: FOGL-2662 C-async plugin - Once done add 1 more plugin
    # plugin_and_service.install('south', plugin='?', plugin_lang='C')


class TestService:

    def test_cleanup_and_setup(self, reset_and_start_foglamp, install_plugins):
        # TODO: Remove this workaround
        # Use better setup & teardown methods
        pass

    def test_default_service(self, foglamp_url):
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("GET", '/foglamp/service')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        # Only storage and core service is expected by default
        assert 2 == len(jdoc['services'])
        keys = {'address', 'service_port', 'type', 'status', 'name', 'management_port', 'protocol'}
        assert Counter(keys) == Counter(jdoc['services'][0].keys())

        storage_svc = jdoc['services'][0]
        assert isinstance(storage_svc['service_port'], int)
        assert isinstance(storage_svc['management_port'], int)
        assert 'running' == storage_svc['status']
        assert 'Storage' == storage_svc['type']
        assert 'localhost' == storage_svc['address']
        assert 'FogLAMP Storage' == storage_svc['name']
        assert 'http' == storage_svc['protocol']

        core_svc = jdoc['services'][1]
        assert isinstance(core_svc['management_port'], int)
        assert 8081 == core_svc['service_port']
        assert 'running' == core_svc['status']
        assert 'Core' == core_svc['type']
        assert '0.0.0.0' == core_svc['address']
        assert 'FogLAMP Core' == core_svc['name']
        assert 'http' == core_svc['protocol']

    @pytest.mark.parametrize("plugin, svc_name, config, enabled, svc_count", [
        ("randomwalk", SVC_NAME_1, None, True, 3),
        ("http_south", SVC_NAME_2, None, False, 3),
        ("Benchmark", SVC_NAME_3, None, True, 4)
    ])
    def test_add_service(self, foglamp_url, wait_time, plugin, svc_name, config, enabled, svc_count):
        jdoc = plugin_and_service.add_south(plugin, foglamp_url, svc_name, config, enabled)
        assert svc_name == jdoc['name']
        assert UUID(jdoc['id'], version=4)

        time.sleep(wait_time)
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("GET", '/foglamp/service')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert svc_count == len(jdoc['services'])
        southbound_svc = jdoc['services'][svc_count - 1]
        assert isinstance(southbound_svc['management_port'], int)
        assert southbound_svc['service_port'] is None
        assert svc_name if enabled else SVC_NAME_1 == southbound_svc['name']
        assert 'running' == southbound_svc['status']
        assert 'Southbound' == southbound_svc['type']
        assert 'localhost' == southbound_svc['address']
        assert 'http' == southbound_svc['protocol']

    def test_add_service_with_config(self, foglamp_url):
        data = {"name": SVC_NAME_4,
                "type": "South",
                "plugin": 'randomwalk',
                "config": {"maxValue": {"value": "20"}, "assetName": {"value": "Random"}},
                "enabled": True
                }
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("POST", '/foglamp/service', json.dumps(data))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert SVC_NAME_4 == jdoc['name']
        assert UUID(jdoc['id'], version=4)

        conn.request("GET", '/foglamp/category/{}'.format(SVC_NAME_4))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert data['config']['assetName']['value'] == jdoc['assetName']['value']
        assert data['config']['maxValue']['value'] == jdoc['maxValue']['value']

    @pytest.mark.parametrize("encoded_svc_name, svc_name, status, svc_count", [
        ("FogLAMP%20Storage", "FogLAMP Storage", 404, 2),
        ("FogLAMP%20Core", "FogLAMP Core", 404, 2),
        ("Random%20Walk%20%231", SVC_NAME_1, 200, 4),
        ("HTTP-SOUTH", SVC_NAME_2, 200, 4),
        (SVC_NAME_3, SVC_NAME_3, 200, 3)
    ])
    def test_delete_service(self, encoded_svc_name, svc_name, status, svc_count, foglamp_url, wait_time):
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("DELETE", '/foglamp/service/{}'.format(encoded_svc_name))
        r = conn.getresponse()
        assert status == r.status
        if status == 404:
            assert '{} service does not exist.'.format(svc_name) == r.reason
        else:
            r = r.read().decode()
            jdoc = json.loads(r)
            assert 'Service {} deleted successfully.'.format(svc_name) == jdoc['result']

            time.sleep(wait_time)
            conn.request("GET", '/foglamp/service')
            r = conn.getresponse()
            assert 200 == r.status
            r = r.read().decode()
            jdoc = json.loads(r)
            assert len(jdoc), "No data found"
            assert svc_count == len(jdoc['services'])
            services = [name['name'] for name in jdoc['services']]
            assert svc_name not in services

    def test_notification_service(self):
        assert 1, "Already verified in test_e2e_notification_service_with_plugins.py"
