import http.client
import json
import pytest

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2024 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


""" Control Pipeline API tests """

CP_1 = "CP #1"
CP_2 = "CP-mine"
payload1 = {"name": CP_1, "enabled": True, "execution": "shared", "source": {"type": 1},
            "destination": {"type": 1}}
payload2 = {"name": CP_2, "enabled": False, "execution": "shared", "source": {"type": 3},
            "destination": {"type": 5}}

def verify_audit_details(conn, name, source):
    conn.request("GET", '/fledge/audit?source={}'.format(source))
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    assert len(jdoc), "No audit record entry found!"
    assert 'audit' in jdoc
    if source.endswith("CH"):
        assert 'pipeline' in jdoc['audit'][0]['details']
        assert name == jdoc['audit'][0]['details']['pipeline']['name']
        assert 'old_pipeline' in jdoc['audit'][0]['details']
        assert name == jdoc['audit'][0]['details']['old_pipeline']['name']
    else:
        assert name == jdoc['audit'][0]['details']['name']
    assert 'INFORMATION' == jdoc['audit'][0]['severity']
    assert source == jdoc['audit'][0]['source']


def verify_details(conn, data, cpid):
    conn.request("GET", '/fledge/control/pipeline/{}'.format(cpid))
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc_pipeline = json.loads(r)
    assert len(jdoc_pipeline), "Failed to fetch details of pipeline having ID: {}".format(cpid)

    if jdoc_pipeline['name'] == CP_1:
        assert 1 == jdoc_pipeline['id']
        assert data['name'] == jdoc_pipeline['name']
        assert "Any" == jdoc_pipeline['source']['type']
        assert "" == jdoc_pipeline['source']['name']
        assert "Any" == jdoc_pipeline['destination']['type']
        assert "" == jdoc_pipeline['destination']['name']
        assert data['enabled'] == jdoc_pipeline['enabled']
        assert data['execution'] == jdoc_pipeline['execution']
        assert [] == jdoc_pipeline['filters']
    elif jdoc_pipeline['name'] == CP_2:
        assert 2 == jdoc_pipeline['id']
        assert data['name'] == jdoc_pipeline['name']
        assert "API" == jdoc_pipeline['source']['type']
        assert "anonymous" == jdoc_pipeline['source']['name']
        assert "Broadcast" == jdoc_pipeline['destination']['type']
        assert "" == jdoc_pipeline['destination']['name']
        assert data['enabled'] == jdoc_pipeline['enabled']
        assert data['execution'] == jdoc_pipeline['execution']
        assert [] == jdoc_pipeline['filters']


def _get_all(url):
    conn = http.client.HTTPConnection(url)
    conn.request("GET", '/fledge/control/pipeline')
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    assert len(jdoc), "No pipelines found!"
    assert 'pipelines' in jdoc
    return jdoc['pipelines']


class TestPipeline:
    def test_empty_get_all(self, fledge_url, reset_and_start_fledge):
        pipelines = _get_all(fledge_url)
        assert [] == pipelines

    @pytest.mark.parametrize("payload", [payload1, payload2])
    def test_create(self, fledge_url, payload):
        name = payload['name']
        conn = http.client.HTTPConnection(fledge_url)
        conn.request('POST', '/fledge/control/pipeline', body=json.dumps(payload))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "Failed to create {} pipeline!".format(name)
        verify_details(conn, payload, jdoc['id'])
        verify_audit_details(conn, name, 'CTPAD')

    def test_get_all(self, fledge_url):
        pipelines = _get_all(fledge_url)
        assert 2 == len(pipelines)

    def test_get_by_name(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        verify_details(conn, payload1, 1)

    @pytest.mark.parametrize("cpid, name, data, payload", [
        (1, CP_1, payload1, {"enabled": False}),
        (2, CP_2, payload2, {"execution": "exclusive", "enabled": True})
    ])
    def test_update(self, fledge_url, cpid, name, data, payload):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request('PUT', '/fledge/control/pipeline/{}'.format(cpid), body=json.dumps(payload))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 'message' in jdoc
        assert 'Control Pipeline with ID:<{}> has been updated successfully.'.format(cpid) == jdoc['message']
        modified_data = data.copy()
        for k, v in payload.items():
            modified_data[k] = v
        verify_details(conn, modified_data, cpid)
        verify_audit_details(conn, name, 'CTPCH')

    @pytest.mark.parametrize("cpid, name, count", [(1, CP_1, 1), (2, CP_2, 0)])
    def test_delete(self, fledge_url, cpid, name, count):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("DELETE", '/fledge/control/pipeline/{}'.format(cpid))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "Pipeline with ID:<{}> not found!".format(cpid)
        assert 'message' in jdoc
        assert 'Control Pipeline with ID:<{}> has been deleted successfully.'.format(cpid) == jdoc['message']
        verify_audit_details(conn, name, 'CTPDL')
        jdoc = _get_all(fledge_url)
        assert count == len(jdoc)

