# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import http.client
import json

"""Utility methods"""


def serialize_stats_map(jdoc):
    actual_stats_map = {}
    for itm in jdoc:
        actual_stats_map[itm['key']] = itm['value']
    return actual_stats_map


def get_asset_tracking_details(fledge_url, event=None):
    _connection = http.client.HTTPConnection(fledge_url)
    uri = '/fledge/track'
    if event:
        uri += '?event={}'.format(event)
    _connection.request("GET", uri)
    r = _connection.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    return jdoc


def post_request(fledge_url, post_url, payload):
    conn = http.client.HTTPConnection(fledge_url)
    conn.request("POST", post_url, json.dumps(payload))
    res = conn.getresponse()
    assert 200 == res.status, "ERROR! POST {} request failed".format(post_url)
    res = res.read().decode()
    r = json.loads(res)
    return r


def get_request(fledge_url, get_url):
    con = http.client.HTTPConnection(fledge_url)
    con.request("GET", get_url)
    res = con.getresponse()
    assert 200 == res.status, "ERROR! GET {} request failed".format(get_url)
    r = json.loads(res.read().decode())
    return r


def put_request(fledge_url, put_url, payload = None):
    conn = http.client.HTTPConnection(fledge_url)
    conn.request("PUT", put_url, json.dumps(payload))
    res = conn.getresponse()
    assert 200 == res.status, "ERROR! PUT {} request failed".format(put_url)
    r = json.loads(res.read().decode())
    return r


def delete_request(fledge_url, delete_url):
    con = http.client.HTTPConnection(fledge_url)
    con.request("DELETE", delete_url)
    res = con.getresponse()
    assert 200 == res.status, "ERROR! GET {} request failed".format(delete_url)
    r = json.loads(res.read().decode())
    return r