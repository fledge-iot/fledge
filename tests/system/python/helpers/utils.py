# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Utility methods"""


def serialize_stats_map(jdoc):
    actual_stats_map = {}
    for itm in jdoc:
        actual_stats_map[itm['key']] = itm['value']
    return actual_stats_map
