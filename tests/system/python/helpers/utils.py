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
