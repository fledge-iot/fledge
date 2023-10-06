import http.client
import json
import pytest
from urllib.parse import quote
from collections import OrderedDict

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2023 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


""" Control Flow Entrypoint API tests """

EP_1 = "EP #1"
EP_2 = "EP-1"
EP_3 = "EP #_2"
payload1 = {"name": EP_1, "type": "write", "description": "Entry Point 1", "operation_name": "",
            "destination": "broadcast", "constants": {"c1": "100"}, "variables": {"v1": "100"}, "anonymous": False,
            "allow": []}
payload2 = {"name": EP_2, "type": "operation", "description": "Operation 1", "operation_name": "distance",
            "destination": "broadcast", "anonymous": False, "allow": []}
payload3 = {"name": EP_3, "type": "operation", "description": "Operation 2", "operation_name": "distance",
            "destination": "broadcast", "constants": {"c1": "100"}, "variables": {"v1": "1200"}, "anonymous": True,
            "allow": ["admin", "user"]}

# TODO: add more tests
"""
    a) authentication based
    b) update request by installing external service
"""


class TestEntrypoint:
    def test_empty_get_all(self, fledge_url, reset_and_start_fledge):
        jdoc = self._get_all(fledge_url)
        assert [] == jdoc

    @pytest.mark.parametrize("payload", [payload1, payload2, payload3])
    def test_create(self, fledge_url, payload):
        ep_name = payload['name']
        conn = http.client.HTTPConnection(fledge_url)
        conn.request('POST', '/fledge/control/manage', body=json.dumps(payload))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "Failed to create {} entrypoint!".format(ep_name)
        assert 'message' in jdoc
        assert '{} control entrypoint has been created successfully.'.format(ep_name) == jdoc['message']
        self.verify_details(conn, payload)
        self.verify_audit_details(conn, ep_name, 'CTEAD')

    def test_get_all(self, fledge_url):
        jdoc = self._get_all(fledge_url)
        assert 3 == len(jdoc)
        assert ['name', 'description', 'permitted'] == list(jdoc[0].keys())

    def test_get_by_name(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/control/manage/{}'.format(quote(EP_1)))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "{} entrypoint found!".format(EP_1)
        assert payload1 == jdoc
        assert 'permitted' in jdoc

    @pytest.mark.parametrize("name, payload, old_info", [
        (EP_1, {"anonymous": True}, {"anonymous": False}),
        (EP_2, {"description": "Updated", "type": "operation", "operation_name": "focus", "allow": ["user"]},
         {"description": "Operation 1", "type": "operation", "operation_name": "distance", "allow": []}),
        (EP_3, {"constants": {"c1": "123", "c2": "100"}, "variables": {"v1": "900"}},
         {"constants": {"c1": "100"}, "variables": {"v1": "1200"}})
    ])
    def test_update(self, fledge_url, name, payload, old_info):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request('PUT', '/fledge/control/manage/{}'.format(quote(name)), body=json.dumps(payload))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 'message' in jdoc
        assert '{} control entrypoint has been updated successfully.'.format(name) == jdoc['message']

        source = 'CTECH'
        conn.request("GET", '/fledge/audit?source={}'.format(source))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 'audit' in jdoc
        assert len(jdoc['audit'])
        audit = jdoc['audit'][0]
        assert 'INFORMATION' == audit['severity']
        assert source == audit['source']
        assert 'details' in audit
        assert 'entrypoint' in audit['details']
        assert 'old_entrypoint' in audit['details']
        audit_old = audit['details']['old_entrypoint']
        audit_new = audit['details']['entrypoint']
        assert name == audit_new['name']
        assert name == audit_old['name']

        conn.request("GET", '/fledge/control/manage/{}'.format(quote(name)))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "{} entrypoint found!".format(name)
        assert name == jdoc['name']
        if name == EP_1:
            assert old_info['anonymous'] == audit_old['anonymous']
            assert payload['anonymous'] == audit_new['anonymous']
            assert payload['anonymous'] == jdoc['anonymous']
        elif name == EP_2:
            assert old_info['description'] == audit_old['description']
            assert payload['description'] == audit_new['description']
            assert old_info['type'] == audit_old['type']
            assert payload['type'] == audit_new['type']
            assert old_info['operation_name'] == audit_old['operation_name']
            assert payload['operation_name'] == audit_new['operation_name']
            assert old_info['allow'] == audit_old['allow']
            assert payload['allow'] == audit_new['allow']
            assert payload['description'] == jdoc['description']
            assert payload['type'] == jdoc['type']
            assert payload['operation_name'] == jdoc['operation_name']
            assert payload['allow'] == jdoc['allow']
        elif name == EP_3:
            assert old_info['constants']['c1'] == audit_old['constants']['c1']
            assert 'c2' not in audit_old['constants']
            assert payload['constants']['c1'] == audit_new['constants']['c1']
            assert payload['constants']['c2'] == audit_new['constants']['c2']
            assert old_info['variables']['v1'] == audit_old['variables']['v1']
            assert payload['variables']['v1'] == audit_new['variables']['v1']
            assert payload['constants']['c1'] == jdoc['constants']['c1']
            assert payload['constants']['c2'] == jdoc['constants']['c2']
            assert payload['variables']['v1'] == jdoc['variables']['v1']
        else:
            # Add more scenarios
            pass

    @pytest.mark.parametrize("name, count", [(EP_1, 2), (EP_2, 1), (EP_3, 0)])
    def test_delete(self, fledge_url, name, count):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("DELETE", '/fledge/control/manage/{}'.format(quote(name)))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "{} entrypoint found!".format(name)
        assert 'message' in jdoc
        assert '{} control entrypoint has been deleted successfully.'.format(name) == jdoc['message']
        self.verify_audit_details(conn, name, 'CTEDL')
        jdoc = self._get_all(fledge_url)
        assert count == len(jdoc)

    def verify_audit_details(self, conn, ep_name, source):
        conn.request("GET", '/fledge/audit?source={}'.format(source))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No audit record entry found!"
        assert 'audit' in jdoc
        assert ep_name == jdoc['audit'][0]['details']['name']
        assert 'INFORMATION' == jdoc['audit'][0]['severity']
        assert source == jdoc['audit'][0]['source']

    def verify_details(self, conn, data):
        name = data['name']
        conn.request("GET", '/fledge/control/manage/{}'.format(quote(name)))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "{} entrypoint found!".format(name)
        data['permitted'] = True
        if 'constants' not in data:
            data['constants'] = {}
        if 'variables' not in data:
            data['variables'] = {}

        d1 = OrderedDict(sorted(data.items()))
        d2 = OrderedDict(sorted(jdoc.items()))
        assert d1 == d2
    
    def _get_all(self, url):
        conn = http.client.HTTPConnection(url)
        conn.request("GET", '/fledge/control/manage')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No entrypoint found!"
        assert 'controls' in jdoc
        return jdoc['controls']
