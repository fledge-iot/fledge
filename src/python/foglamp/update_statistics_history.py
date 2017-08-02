#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""
The following piece of code takes the information found in the statistics table, and stores it's delta value 
(statistics.value - statistics.prev_val) inside the statistics_history table. To complete this, SQLAlchemy will be 
used to execute SELECT statements against statistics, and INSERT against the statistics_history table.  
"""
import sqlalchemy
import sqlalchemy.dialects
from datetime import datetime

__author__ = "Ori Shadmon"
__copyright__ = "Copyright (c) 2017 OSI Soft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


# Set variables for connecting to database
_CONNECTION_STRING = "postgres:///foglamp"

# Deceleration of tables in SQLAlchemy format
_STATS_TABLE = sqlalchemy.Table('statistics', sqlalchemy.MetaData(),
                                sqlalchemy.Column('key', sqlalchemy.CHAR(10), primary_key=True),
                                sqlalchemy.Column('description', sqlalchemy.VARCHAR('255'), default=''),
                                sqlalchemy.Column('value', sqlalchemy.BIGINT, default=0),
                                sqlalchemy.Column('previous_value', sqlalchemy.BIGINT, default=0),
                                sqlalchemy.Column('ts', sqlalchemy.TIMESTAMP(6),
                                                  default=sqlalchemy.func.current_timestamp()))

"""Description of each column 
key - Corresponding statistics.key value, so that there is awareness of what the history is of
history_ts - the newest timestamp in statistics for that key 
value - delta value between `value` and `prev_val` of statistics
            The point is to know how many actions happened during the X time
ts - current timestamp 
"""
_STATS_HISTORY_TABLE = sqlalchemy.Table('statistics_history', sqlalchemy.MetaData(),
                                        sqlalchemy.Column('key', sqlalchemy.CHAR(10)),
                                        sqlalchemy.Column('history_ts', sqlalchemy.TIMESTAMP(6),
                                                          default=sqlalchemy.func.current_timestamp()),
                                        sqlalchemy.Column('value', sqlalchemy.BIGINT, default=0),
                                        sqlalchemy.Column('ts', sqlalchemy.TIMESTAMP(6),
                                                          default=sqlalchemy.func.current_timestamp())
                                        )


def __query_execution(stmt=""):
    """
    Execute query and return result
    Args:
        stmt: Query being executed

    Returns:
        Result of the query 
    """
    
    engine = sqlalchemy.create_engine(_CONNECTION_STRING,  pool_size=20, max_overflow=0)
    conn = engine.connect()
    result = conn.execute(stmt)

    return result


def _list_stats_keys() -> list:
    """
    generate a list of distinct keys from statistics table 
    Returns:
        list of distinct keys
    """
    key_list = []
    stmt = sqlalchemy.select([_STATS_TABLE.c.key.distinct()]).select_from(_STATS_TABLE)
    result = __query_execution(stmt)

    result = result.fetchall()
    for i in range(len(result)):
        key_list.append(str(result[i][0]).strip())

    return key_list


def _insert_into_stats_history(key='', value=0, history_ts=None):
    """
    INSERT values in statistics_history
    Args:
        key: corresponding stats_key_value 
        value: delta between `value` and `prev_val`
    Returns:
        Return the number of rows inserted. Since each process inserts only 1 row, the expected count should always 
        be 1. 
    """
    stmt = _STATS_HISTORY_TABLE.insert().values(key=key, value=value, history_ts=history_ts)
    __query_execution(stmt)


def _update_previous_value(key='', value=0):
    """
    Update previous_value of column to have the same value as snapshot
    Query: 
        UPDATE statistics_history SET previous_value = value WHERE key = key
    Args:
        key: Key which previous_value gets update 
        value: value at snapshot
    """
    stmt = _STATS_TABLE.update().values(previous_value=value).where(_STATS_TABLE.c.key == key)
    __query_execution(stmt)


def _select_from_statistics(key='') -> dict:
    """
    SELECT data from statistics for the statistics_history table
    Args:
        key: The row name update is executed against (WHERE condition)

    Returns:

    """
    stmt = sqlalchemy.select([_STATS_TABLE.c.value, _STATS_TABLE.c.previous_value]).where(_STATS_TABLE.c.key == key)
    result = __query_execution(stmt)
    return result.fetchall()


def stats_history_main():
    """
    1. SELECT against the  statistics table, to get a snapshot of the data at that moment. 
    Based on the snapshot: 
        1. INSERT the delta between `value` and `previous_value` into  statistics_history
        2. UPDATE the previous_value in statistics table to be equal to statistics.value at snapshot 
    """

    # List of distinct statistics.keys values
    stats_key_value_list = _list_stats_keys()
    current_time = datetime.now()
    for key in stats_key_value_list:
        stats_select_result = _select_from_statistics(key=key)
        value = int(stats_select_result[0][0])
        previous_value = int(stats_select_result[0][1])
        _insert_into_stats_history(key=key, value=value-previous_value, history_ts=current_time)
        _update_previous_value(key=key, value=value)

if __name__ == '__main__':
    stats_history_main()

# """Testing of statistics_history
# """
# import random
#
#
# def update_statistics_table():
#     """
#     Update statistics.value with a value that's 1 to 10 numbers larger
#     """
#     stats_key_value_list = _list_stats_keys()
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
#     stats_key_value_list = _list_stats_keys()
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
#     stats_key_value_list = _list_stats_keys()
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
#     stats_key_value_list = _list_stats_keys()
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


