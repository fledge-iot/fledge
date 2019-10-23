# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge.readthedocs.io/
# FLEDGE_END

"""Utility methods"""


def serialize_stats_map(jdoc):
    actual_stats_map = {}
    for itm in jdoc:
        actual_stats_map[itm['key']] = itm['value']
    return actual_stats_map
