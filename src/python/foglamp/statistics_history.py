#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Statistics history task fetch information from the statistics table, compute delta and
stores the delta value (statistics.value - statistics.previous_value) in the statistics_history table
"""

import sys
from datetime import datetime

from foglamp.storage.payload_builder import PayloadBuilder
from foglamp.storage.storage import Storage

from foglamp import logger
from foglamp.parser import ArgumentParserError, Parser


__author__ = "Ori Shadmon, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSI Soft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_storage = None


def _stats_keys() -> list:
    """ Generates a list of distinct keys from statistics table

    Returns:
        list of distinct keys
    """
    payload = PayloadBuilder().SELECT().DISTINCT(["key"]).payload()
    results = _storage.query_tbl_with_payload('statistics', payload)

    key_list = [r['key'] for r in results['rows']]
    return key_list


def _insert_into_stats_history(key='', value=0, history_ts=None):
    """ INSERT values in statistics_history

    Args:
        key: corresponding stats_key_value 
        value: delta between `value` and `prev_val`
        history_ts: timestamp with timezone
    Returns:
        Return the number of rows inserted. Since each process inserts only 1 row, the expected count should always 
        be 1. 
    """
    date_to_str = history_ts.strftime("%Y-%m-%d %H:%M:%S.%f")
    payload = PayloadBuilder().INSERT(key=key, value=value, history_ts=date_to_str).payload()
    _storage.insert_into_tbl("statistics_history", payload)


def _update_previous_value(key='', value=0):
    """ UPDATE previous_value of column to have the same value as snapshot

    Query: 
        UPDATE statistics_history SET previous_value = value WHERE key = key
    Args:
        key: Key which previous_value gets update 
        value: value at snapshot
    """
    payload = PayloadBuilder().SET(previous_value=value).WHERE(["key", "=", key]).payload()
    _storage.update_tbl("statistics", payload)


def _select_from_statistics(key='') -> dict:
    """ SELECT * from statistics for the statistics_history WHERE key = key

    Args:
        key: The row name update is executed against (WHERE condition)

    Returns:
        row as dict
    """
    payload = PayloadBuilder().WHERE(["key", "=", key]).payload()
    result = _storage.query_tbl_with_payload("statistics", payload)
    return result


def _main():
    """ SELECT against the  statistics table, to get a snapshot of the data at that moment.

    Based on the snapshot:
        1. INSERT the delta between `value` and `previous_value` into  statistics_history
        2. UPDATE the previous_value in statistics table to be equal to statistics.value at snapshot 
    """

    stats_key_value_list = _stats_keys()
    current_time = datetime.now()

    for key in stats_key_value_list:
        stats = _select_from_statistics(key=key)
        value = stats["rows"][0]["value"]
        previous_value = stats["rows"][0]["previous_value"]
        delta = value - previous_value
        _insert_into_stats_history(key=key, value=delta, history_ts=current_time)
        _update_previous_value(key=key, value=value)


if __name__ == '__main__':
    _logger = logger.setup("Statistics History")

    try:
        core_mgt_port = Parser.get('--port')
        core_mgt_address = Parser.get('--address')
    except ArgumentParserError:
        _logger.exception('Unable to parse command line argument')
        sys.exit(1)

    if core_mgt_port is None:
        _logger.warning("Required argument '--port' is missing")
    elif core_mgt_address is None:
        _logger.warning("Required argument '--address' is missing")
    else:
        _storage = Storage(core_mgt_address, core_mgt_port)
        _main()

# TODO: FOGL-484 Move below commented code to tests/ and use storage instead of SQLAlchemy
# """Testing of statistics_history
# """
# import random
#
#
# def update_statistics_table():
#     """
#     Update statistics.value with a value that's 1 to 10 numbers larger
#     """
#     stats_key_value_list = _stats_keys()
#     for key in stats_key_value_list:
#         val = random.randint(1,10)
#         stmt = sqlalchemy.select([_STATS_TABLE.c.value]).where(_STATS_TABLE.c.key == key)
#         result = __query_execution(stmt)
#         result = int(result.fetchall()[0][0])+val
#         stmt = _STATS_TABLE.update().values(value=result).where(_STATS_TABLE.c.key == key)
#         __query_execution(stmt)
#
#
# def test_assert_previous_value_equals_value():
#     """Assert that previous_value = value"""
#     result_set = {}
#     stats_key_value_list = _stats_keys()
#     for key in stats_key_value_list:
#         stmt = sqlalchemy.select([_STATS_TABLE.c.value,
#                                   _STATS_TABLE.c.previous_value]).where(_STATS_TABLE.c.key == key)
#         result = __query_execution(stmt).fetchall()
#         result_set[result[0][0]] = result[0][1]
#
#     if (key == result_set[key] for key in sorted(result_set.keys())):
#         return "SUCCESS"
#     return "FAIL"
#
#
# def test_assert_previous_value_less_than_value():
#     """Assert that previous_value < value"""
#     result_set = {}
#     stats_key_value_list = _stats_keys()
#     for key in stats_key_value_list:
#         stmt = sqlalchemy.select([_STATS_TABLE.c.value,
#                                   _STATS_TABLE.c.previous_value]).where(_STATS_TABLE.c.key == key)
#         result = __query_execution(stmt).fetchall()
#         result_set[result[0][0]] = result[0][1]
#
#     if (key > result_set[key] for key in sorted(result_set.keys())):
#         return "SUCCESS"
#     return "FAIL"
#
#
# def stats_history_table_value():
#     delta = {}
#     stats_key_value_list = _stats_keys()
#     for key_value in stats_key_value_list:
#         stmt = sqlalchemy.select([_STATS_HISTORY_TABLE.c.value]).select_from(_STATS_HISTORY_TABLE).where(
#             _STATS_HISTORY_TABLE.c.key == key_value)
#         result = __query_execution(stmt).fetchall()
#         delta[key_value] = result[0][0]
#     return delta
#
# def test_main():
#     """Test verification main"""
#     delta1 = stats_history_table_value()
#     stats_history_main()
#     print('TEST A: Verify previous_value = value - ' + test_assert_previous_value_equals_value())
#     update_statistics_table()
#     print('TEST B: Verify previous_value < value - ' + test_assert_previous_value_less_than_value())
#     stats_history_main()
#     delta2 = stats_history_table_value()
#     for key in sorted(delta1.keys()):
#         if delta1[key] != delta2[key]:
#             print(key+": Stat History Updated - SUCCESS")
#         else:
#             print(key + ": Stat History Updated - FAIL")
