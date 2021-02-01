# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test add service using poll and async plugins for both python & C version REST API """

import os
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

SVC_NAME_5 = SVC_NAME_C_ASYNC = "Async 1"
SVC_NAME_6 = 'randomwalk'


PLUGIN_FILTER = 'metadata'
FILTER_NAME = 'meta'


@pytest.fixture
def install_plugins():
    plugin_and_service.install('south', plugin='randomwalk')
    plugin_and_service.install('south', plugin='http')
    plugin_and_service.install('south', plugin='benchmark', plugin_lang='C')
    plugin_and_service.install('south', plugin='random', plugin_lang='C')
    plugin_and_service.install('south', plugin='csv-async', plugin_lang='C')


def get_service(fledge_url, path):
    conn = http.client.HTTPConnection(fledge_url)
    conn.request("GET", path)
    res = conn.getresponse()
    r = res.read().decode()
    assert 200 == res.status
    jdoc = json.loads(r)
    return jdoc


class TestService:

    def test_cleanup_and_setup(self, reset_and_start_fledge, install_plugins):
        # TODO: FOGL-2669 Better setup & teardown fixtures
        pass

    def test_default_service(self, fledge_url):
        jdoc = get_service(fledge_url, '/fledge/service')
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
        assert 'Fledge Storage' == storage_svc['name']
        assert 'http' == storage_svc['protocol']

        core_svc = jdoc['services'][1]
        assert isinstance(core_svc['management_port'], int)
        assert 8081 == core_svc['service_port']
        assert 'running' == core_svc['status']
        assert 'Core' == core_svc['type']
        assert '0.0.0.0' == core_svc['address']
        assert 'Fledge Core' == core_svc['name']
        assert 'http' == core_svc['protocol']

    C_ASYNC_CONFIG = {"file": {"value": os.getenv("FLEDGE_ROOT", "") + '/tests/system/python/data/vibration.csv'}}

    @pytest.mark.parametrize("plugin, svc_name, display_svc_name, config, enabled, svc_count", [
        ("randomwalk", SVC_NAME_1, SVC_NAME_1, None, True, 3),
        ("http_south", SVC_NAME_2, SVC_NAME_1, None, False, 3),
        ("Benchmark", SVC_NAME_3, SVC_NAME_3, None, True, 4),
        ("Random", SVC_NAME_4, SVC_NAME_3, None, False, 4),
        ("CSV-Async", SVC_NAME_C_ASYNC, SVC_NAME_C_ASYNC, C_ASYNC_CONFIG, True, 5)
    ])
    def test_add_service(self, fledge_url, wait_time, plugin, svc_name, display_svc_name, config, enabled, svc_count):

        jdoc = plugin_and_service.add_south_service(plugin, fledge_url, svc_name, config, enabled)
        assert svc_name == jdoc['name']
        assert UUID(jdoc['id'], version=4)

        time.sleep(wait_time)
        jdoc = get_service(fledge_url, '/fledge/service')
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

    def test_add_service_with_config(self, fledge_url, wait_time):
        # add service with config param
        data = {"name": SVC_NAME_6,
                "type": "South",
                "plugin": 'randomwalk',
                "config": {"maxValue": {"value": "20"}, "assetName": {"value": "Random"}},
                "enabled": True
                }
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", '/fledge/service', json.dumps(data))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert SVC_NAME_6 == jdoc['name']
        assert UUID(jdoc['id'], version=4)

        # verify config is correctly saved
        conn.request("GET", '/fledge/category/{}'.format(SVC_NAME_6))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert data['config']['assetName']['value'] == jdoc['assetName']['value']
        assert data['config']['maxValue']['value'] == jdoc['maxValue']['value']

        time.sleep(wait_time)
        jdoc = get_service(fledge_url, '/fledge/service')
        assert len(jdoc), "No data found"
        assert 6 == len(jdoc['services'])
        assert SVC_NAME_6 == jdoc['services'][5]['name']

    @pytest.mark.parametrize("svc_name, status, svc_count", [
        ("Fledge Storage", 404, 2),
        ("Fledge Core", 404, 2),
        (SVC_NAME_1, 200, 5),
        (SVC_NAME_2, 200, 5),
        (SVC_NAME_3, 200, 4)
    ])
    def test_delete_service(self, svc_name, status, svc_count, fledge_url, wait_time):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("DELETE", '/fledge/service/{}'.format(quote(svc_name)))
        res = conn.getresponse()
        assert status == res.status

        if status == 404:
            # FIXME: FOGL-2668 expected 403 for Core and Storage
            assert '{} service does not exist.'.format(svc_name) == res.reason
        else:
            r = res.read().decode()
            jdoc = json.loads(r)
            assert 'Service {} deleted successfully.'.format(svc_name) == jdoc['result']

            time.sleep(wait_time)

            jdoc = get_service(fledge_url, '/fledge/service')
            assert len(jdoc), "No data found"
            assert svc_count == len(jdoc['services'])
            services = [s['name'] for s in jdoc['services']]
            assert svc_name not in services

            # no category (including its children) exists anymore for serviceName
            conn = http.client.HTTPConnection(fledge_url)
            conn.request("GET", '/fledge/category/{}'.format(quote(svc_name)))
            res = conn.getresponse()
            r = res.read().decode()
            assert 404 == res.status

            conn.request("GET", '/fledge/category/{}/children'.format(quote(svc_name)))
            res = conn.getresponse()
            r = res.read().decode()
            assert 404 == res.status

            # no schedule exists anymore for serviceName
            conn.request("GET", '/fledge/schedule')
            res = conn.getresponse()
            r = res.read().decode()
            jdoc = json.loads(r)
            assert svc_name not in [s['name'] for s in jdoc["schedules"]]

            # TODO: verify FOGL-2718 no category interest exists anymore for serviceId in InterestRegistry

    def test_service_with_enable_schedule(self, fledge_url, wait_time, enable_schedule):
        enable_schedule(fledge_url, SVC_NAME_4)

        time.sleep(wait_time)
        jdoc = get_service(fledge_url, '/fledge/service')
        assert len(jdoc), "No data found"
        assert 5 == len(jdoc['services'])
        assert SVC_NAME_4 in [s['name'] for s in jdoc['services']]

    def test_service_with_disable_schedule(self, fledge_url, wait_time, disable_schedule):
        disable_schedule(fledge_url, SVC_NAME_4)

        time.sleep(wait_time)
        jdoc = get_service(fledge_url, '/fledge/service')
        assert len(jdoc), "No data found"
        assert 5 == len(jdoc['services'])
        assert (SVC_NAME_4, 'shutdown') in [(s['name'], s['status']) for s in jdoc['services']]

    def test_service_on_restart(self, fledge_url, wait_time):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", '/fledge/restart')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert 'Fledge restart has been scheduled.' == jdoc['message']

        time.sleep(wait_time * 4)
        jdoc = get_service(fledge_url, '/fledge/service')
        assert len(jdoc), "No data found"
        assert 4 == len(jdoc['services'])
        services = [name['name'] for name in jdoc['services']]
        assert SVC_NAME_4 not in services

    def test_delete_service_with_filters(self, fledge_url, wait_time, add_filter, filter_branch, enable_schedule):
        # add filter
        add_filter(PLUGIN_FILTER, filter_branch, FILTER_NAME, {"enable": "true"}, fledge_url, SVC_NAME_6)

        # delete service
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("DELETE", '/fledge/service/{}'.format(SVC_NAME_6))
        r = conn.getresponse()
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 'Service {} deleted successfully.'.format(SVC_NAME_6) == jdoc['result']

        # verify service does not exist
        time.sleep(wait_time)
        jdoc = get_service(fledge_url, '/fledge/service')
        assert len(jdoc), "No data found"
        assert 3 == len(jdoc['services'])
        services = [name['name'] for name in jdoc['services']]
        assert SVC_NAME_6 not in services

        # filter linked with SVC_NAME_4
        data = {"pipeline": [FILTER_NAME]}
        conn.request("PUT", '/fledge/filter/{}/pipeline?allow_duplicates=true&append_filter=true'
                     .format(quote(SVC_NAME_4)), json.dumps(data))
        r = conn.getresponse()
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "Filter pipeline {{'pipeline': ['{}']}} updated successfully".format(FILTER_NAME) == jdoc['result']

        # enable SVC_NAME_4 schedule
        enable_schedule(fledge_url, SVC_NAME_4)

        # verify SVC_NAME_4 exist
        time.sleep(wait_time)
        jdoc = get_service(fledge_url, '/fledge/service')
        assert len(jdoc), "No data found"
        assert 4 == len(jdoc['services'])
        services = [s['name'] for s in jdoc['services']]
        assert SVC_NAME_4 in services

        # delete SVC_NAME_4
        conn.request("DELETE", '/fledge/service/{}'.format(quote(SVC_NAME_4)))
        r = conn.getresponse()
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 'Service {} deleted successfully.'.format(SVC_NAME_4) == jdoc['result']

        # verify SVC_NAME_4 does not exist anymore
        time.sleep(wait_time)
        jdoc = get_service(fledge_url, '/fledge/service')
        assert len(jdoc), "No data found"
        assert 3 == len(jdoc['services'])
        services = [s['name'] for s in jdoc['services']]
        assert SVC_NAME_4 not in services

    def test_notification_service(self):
        assert 1, "Already verified in test_e2e_notification_service_with_plugins.py"
