# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import http.client
import json

"""Utility methods"""


def serialize_stats_map(jdoc):
    actual_stats_map = {}
    for itm in jdoc:
        actual_stats_map[itm['key']] = itm['value']
    return actual_stats_map

def get_asset_tracking_details(foglamp_url, event=None):
    _connection = http.client.HTTPConnection(foglamp_url)
    uri = '/foglamp/track'
    if event:
        uri += '?event={}'.format(event)
    _connection.request("GET", uri)
    r = _connection.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    return jdoc
