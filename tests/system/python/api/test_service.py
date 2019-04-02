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
from urllib.parse import quote
import pytest
import plugin_and_service

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


SVC_NAME_1 = 'Random Walk #1'
SVC_NAME_2 = 'HTTP-SOUTH'
SVC_NAME_3 = '1 Bench'
SVC_NAME_4 = 'Rand 1 #3'
SVC_NAME_5 = 'randomwalk'
PLUGIN_FILTER = 'metadata'
FILTER_NAME = 'meta'


@pytest.fixture
def install_plugins():
    plugin_and_service.install('south', plugin='randomwalk')
    plugin_and_service.install('south', plugin='http')
    plugin_and_service.install('south', plugin='benchmark', plugin_lang='C')
    plugin_and_service.install('south', plugin='random', plugin_lang='C')
    # TODO: FOGL-2662 C-async plugin - Once done add 1 more plugin
    # plugin_and_service.install('south', plugin='?', plugin_lang='C')


def get_service(foglamp_url, path):
    conn = http.client.HTTPConnection(foglamp_url)
    conn.request("GET", path)
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    return jdoc


class TestService:

    def test_cleanup_and_setup(self, reset_and_start_foglamp, install_plugins):
        # TODO: FOGL-2669 Remove this workaround
        # Use better setup & teardown methods
        pass

    def test_default_service(self, foglamp_url):
        jdoc = get_service(foglamp_url, '/foglamp/service')
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

    @pytest.mark.parametrize("plugin, svc_name, display_svc_name, config, enabled, svc_count", [
        ("randomwalk", SVC_NAME_1, SVC_NAME_1, None, True, 3),
        ("http_south", SVC_NAME_2, SVC_NAME_1, None, False, 3),
        ("Benchmark", SVC_NAME_3, SVC_NAME_3, None, True, 4),
        ("Random", SVC_NAME_4, SVC_NAME_3, None, False, 4)
    ])
    def test_add_service(self, foglamp_url, wait_time, plugin, svc_name, display_svc_name, config, enabled, svc_count):
        jdoc = plugin_and_service.add_south_service(plugin, foglamp_url, svc_name, config, enabled)
        assert svc_name == jdoc['name']
        assert UUID(jdoc['id'], version=4)

        time.sleep(wait_time)
        jdoc = get_service(foglamp_url, '/foglamp/service')
        assert len(jdoc), "No data found"
        assert svc_count == len(jdoc['services'])
        southbound_svc = jdoc['services'][svc_count - 1]
        assert isinstance(southbound_svc['management_port'], int)
        assert southbound_svc['service_port'] is None
        assert display_svc_name == southbound_svc['name']
        assert 'running' == southbound_svc['status']
        assert 'Southbound' == southbound_svc['type']
        assert 'localhost' == southbound_svc['address']
        assert 'http' == southbound_svc['protocol']

    def test_add_service_with_config(self, foglamp_url, wait_time):
        # add service with config param
        data = {"name": SVC_NAME_5,
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
        assert SVC_NAME_5 == jdoc['name']
        assert UUID(jdoc['id'], version=4)

        # verify config is correctly saved
        conn.request("GET", '/foglamp/category/{}'.format(SVC_NAME_5))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert data['config']['assetName']['value'] == jdoc['assetName']['value']
        assert data['config']['maxValue']['value'] == jdoc['maxValue']['value']

        time.sleep(wait_time)
        jdoc = get_service(foglamp_url, '/foglamp/service')
        assert len(jdoc), "No data found"
        assert 5 == len(jdoc['services'])
        assert SVC_NAME_5 == jdoc['services'][4]['name']

    @pytest.mark.parametrize("svc_name, status, svc_count", [
        ("FogLAMP Storage", 404, 2),
        ("FogLAMP Core", 404, 2),
        (SVC_NAME_1, 200, 4),
        (SVC_NAME_2, 200, 4),
        (SVC_NAME_3, 200, 3)
    ])
    def test_delete_service(self, svc_name, status, svc_count, foglamp_url, wait_time):
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("DELETE", '/foglamp/service/{}'.format(quote(svc_name)))
        r = conn.getresponse()
        assert status == r.status
        # FIXME: FOGL-2668
        if status == 404:
            assert '{} service does not exist.'.format(svc_name) == r.reason
        else:
            r = r.read().decode()
            jdoc = json.loads(r)
            assert 'Service {} deleted successfully.'.format(svc_name) == jdoc['result']

            time.sleep(wait_time)
            jdoc = get_service(foglamp_url, '/foglamp/service')
            assert len(jdoc), "No data found"
            assert svc_count == len(jdoc['services'])
            services = [name['name'] for name in jdoc['services']]
            assert svc_name not in services

    def test_service_with_enable_schedule(self, foglamp_url, wait_time, enable_schedule):
        enable_schedule(foglamp_url, SVC_NAME_4)

        time.sleep(wait_time)
        jdoc = get_service(foglamp_url, '/foglamp/service')
        assert len(jdoc), "No data found"
        assert 4 == len(jdoc['services'])
        assert SVC_NAME_4 == jdoc['services'][3]['name']

    def test_service_with_disable_schedule(self, foglamp_url, wait_time, disable_schedule):
        disable_schedule(foglamp_url, SVC_NAME_4)

        time.sleep(wait_time)
        jdoc = get_service(foglamp_url, '/foglamp/service')
        assert len(jdoc), "No data found"
        assert 4 == len(jdoc['services'])
        assert SVC_NAME_4 == jdoc['services'][3]['name']
        assert 'shutdown' == jdoc['services'][3]['status']

    def test_service_on_restart(self, foglamp_url, wait_time):
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("PUT", '/foglamp/restart')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert 'FogLAMP restart has been scheduled.' == jdoc['message']

        time.sleep(wait_time * 3)
        jdoc = get_service(foglamp_url, '/foglamp/service')
        assert len(jdoc), "No data found"
        assert 3 == len(jdoc['services'])
        services = [name['name'] for name in jdoc['services']]
        assert SVC_NAME_4 not in services

    def test_delete_service_with_filters(self, foglamp_url, wait_time, add_filter, filter_branch, enable_schedule):
        # add filter
        add_filter(PLUGIN_FILTER, filter_branch, FILTER_NAME, {"enable": "true"}, foglamp_url, SVC_NAME_5)

        # delete service
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("DELETE", '/foglamp/service/{}'.format(SVC_NAME_5))
        r = conn.getresponse()
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 'Service {} deleted successfully.'.format(SVC_NAME_5) == jdoc['result']

        # verify service does not exist
        time.sleep(wait_time)
        jdoc = get_service(foglamp_url, '/foglamp/service')
        assert len(jdoc), "No data found"
        assert 2 == len(jdoc['services'])
        services = [name['name'] for name in jdoc['services']]
        assert SVC_NAME_5 not in services

        # filter linked with SVC_NAME_4
        data = {"pipeline": [FILTER_NAME]}
        conn.request("PUT", '/foglamp/filter/{}/pipeline?allow_duplicates=true&append_filter=true'
                     .format(quote(SVC_NAME_4)), json.dumps(data))
        r = conn.getresponse()
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "Filter pipeline {{'pipeline': ['{}']}} updated successfully".format(FILTER_NAME) == jdoc['result']

        # enable SVC_NAME_4 schedule
        enable_schedule(foglamp_url, SVC_NAME_4)

        # verify SVC_NAME_4 exist
        time.sleep(wait_time)
        jdoc = get_service(foglamp_url, '/foglamp/service')
        assert len(jdoc), "No data found"
        assert 3 == len(jdoc['services'])
        assert SVC_NAME_4 == jdoc['services'][2]['name']

        # delete SVC_NAME_4
        conn.request("DELETE", '/foglamp/service/{}'.format(quote(SVC_NAME_4)))
        r = conn.getresponse()
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 'Service {} deleted successfully.'.format(SVC_NAME_4) == jdoc['result']

        # verify SVC_NAME_4 does not exist anymore
        time.sleep(wait_time)
        jdoc = get_service(foglamp_url, '/foglamp/service')
        assert len(jdoc), "No data found"
        assert 2 == len(jdoc['services'])
        services = [name['name'] for name in jdoc['services']]
        assert SVC_NAME_4 not in services

    def test_notification_service(self):
        assert 1, "Already verified in test_e2e_notification_service_with_plugins.py"
