import http.client
import json
import pytest

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2024 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

""" User Alerts API tests """


def verify_alert_in_ping(url, alert_count):
    conn = http.client.HTTPConnection(url)
    conn.request("GET", '/fledge/ping')
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    assert len(jdoc), "No Ping data found."
    assert jdoc['alerts'] == alert_count


def create_alert(url, payload):
    svc_conn = http.client.HTTPConnection(url)
    svc_conn.request("GET", '/fledge/service?type=Core')
    resp = svc_conn.getresponse()
    assert 200 == resp.status
    resp = resp.read().decode()
    svc_jdoc = json.loads(resp)

    svc_details = svc_jdoc["services"][0]
    url = "{}:{}".format(svc_details['address'], svc_details['management_port'])
    conn = http.client.HTTPConnection(url)
    conn.request('POST', '/fledge/alert', body=json.dumps(payload))
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    assert len(jdoc), "Failed to create alert!"
    return jdoc

class TestAlerts:

    def test_get_default_alerts(self, fledge_url, reset_and_start_fledge):
        verify_alert_in_ping(fledge_url, alert_count=0)

        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/alert')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No alerts found."
        assert 'alerts' in jdoc
        assert jdoc['alerts'] == []

    def test_no_delete_alert(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("DELETE", '/fledge/alert')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 'message' in jdoc
        assert {"message": "Nothing to delete."} == jdoc

    def test_bad_delete_alert_by_key(self, fledge_url):
        key = "blah"
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("DELETE", '/fledge/alert/{}'.format(key))
        r = conn.getresponse()
        assert 404 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 'message' in jdoc
        assert {"message": "{} alert not found.".format(key)} == jdoc

    @pytest.mark.parametrize("payload, count", [
        ({"key": "updates", "urgency": "normal", "message": "Fledge new version is available."}, 1),
        ({"key": "updates", "urgency": "normal", "message": "Fledge new version is available."}, 1)
    ])
    def test_create_alert(self, fledge_url, payload, count):
        jdoc = create_alert(fledge_url, payload)
        assert 'alert' in jdoc
        alert_jdoc = jdoc['alert']
        payload['urgency'] = 'Normal'
        assert payload == alert_jdoc

        verify_alert_in_ping(fledge_url, alert_count=count)

    def test_get_all_alerts(self, fledge_url):
        verify_alert_in_ping(fledge_url, alert_count=1)

        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/alert')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No alerts found."
        assert 'alerts' in jdoc
        assert 1 == len(jdoc['alerts'])
        alert_jdoc = jdoc['alerts'][0]
        assert 'key' in alert_jdoc
        assert 'updates' == alert_jdoc['key']
        assert 'message' in alert_jdoc
        assert 'Fledge new version is available.' == alert_jdoc['message']
        assert 'urgency' in alert_jdoc
        assert 'Normal' == alert_jdoc['urgency']
        assert 'timestamp' in alert_jdoc

    def test_delete_alert_by_key(self, fledge_url):
        payload = {"key": "Sine", "message": "The service has restarted 4 times", "urgency": "critical"}
        jdoc = create_alert(fledge_url, payload)
        assert 'alert' in jdoc
        alert_jdoc = jdoc['alert']
        payload['urgency'] = 'Critical'
        assert payload == alert_jdoc

        verify_alert_in_ping(fledge_url, alert_count=2)

        conn = http.client.HTTPConnection(fledge_url)
        conn.request("DELETE", '/fledge/alert/{}'.format(payload['key']))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 'message' in jdoc
        assert {'message': '{} alert is deleted.'.format(payload['key'])} == jdoc

        verify_alert_in_ping(fledge_url, alert_count=1)

    def test_delete_alert(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("DELETE", '/fledge/alert')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 'message' in jdoc
        assert {'message': 'Delete all alerts.'} == jdoc

        verify_alert_in_ping(fledge_url, alert_count=0)
