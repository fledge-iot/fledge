#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END
"""
Description: Based on FOGL-200 (https://docs.google.com/document/d/1GdMTerNq_-XQuAY0FJNQm09nbYQSjZudKJhY8x5Dq8c/edit) 
    the purge process is suppose to remove data based on either a user_id, or an X amount of time back depending on
    whether or not the configuration (config.json) requires to retain data that has not been sent to a  historian.
    
    As of now, all dependencies, with the exception of the database layer have been settled, and being used. These are
    -> configurations 
    -> retrieval of last ID sent to the Historian
     
     As for the database layer, the code currently uses SQLAlchemy, but can easily be switched out to use some other 
    tool to communicate with the database. 
    
     Once the purge process is called by the scheduler, it does the following: 
     1. Connects to the database 
     2. Retrieve information from the Configuration, and last ID sent to the historian
     3. Calculates how many rows are in the database to this point (using "NOW()") 
     4. Either DELETE rows based off age, or lastID (as well as "NOW()")
     5. Calculate necessary information regarding the purge process 
        -> total_rows_removed
        -> total_unsent_rows
        -> total_rows_remaining
        -> total_failed_to_remove
     6. INSERT information into log table 
     
     There currently isn't a formal confirmation that the purge process has succeeded, HOWEVER if 
     total_failed_to_remove > 0 then it is safe to assume that that there was an error with INSERTS, and if 
     total_failed_to_remove > total_rows_removed then PURGE completely failed. 
"""

import asyncio
import datetime
import random
import sqlalchemy
import sqlalchemy.dialects.postgresql
import time
from foglamp import configuration_manager
from foglamp import statistics

"""Script information and connection to the Database
"""
__author__ = "Ori Shadmon"
__copyright__ = "Copyright (c) 2017 OSI Soft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# Create Connection
__CONNECTION_STRING = "postgres:///foglamp"

_DEFAULT_PURGE_CONFIG = {
    "age": {
        "description": "Age of data to be retained, all data that is older than this value will be removed," +
                       "unless retained. (in Hours)",
        "type": "integer",
        "default": "72"
    },
    "retainUnsent": {
        "description": "Retain data that has not been sent to any historian yet.",
        "type": "boolean",
        "default": "False"
    }
}
_CONFIG_CATEGORY_NAME = 'PURGE_READ'
_CONFIG_CATEGORY_DESCRIPTION = 'Purge the readings table'


"""Utilized tables 
"""
# Table purge against
# The pruge process utilizes only either id or ts respectively
_READING_TABLE = sqlalchemy.Table('readings', sqlalchemy.MetaData(),
                                  sqlalchemy.Column('id', sqlalchemy.BIGINT, primary_key=True),
                                  sqlalchemy.Column('asset_code', sqlalchemy.VARCHAR(50)),
                                  sqlalchemy.Column('read_key', sqlalchemy.dialects.postgresql.UUID,
                                                    default='00000000-0000-0000-0000-000000000000'),
                                  sqlalchemy.Column('reading', sqlalchemy.dialects.postgresql.JSON, default='{}'),
                                  sqlalchemy.Column('user_ts', sqlalchemy.TIMESTAMP(6),
                                                    default=sqlalchemy.func.current_timestamp()),
                                  sqlalchemy.Column('ts', sqlalchemy.TIMESTAMP(6),
                                                    default=sqlalchemy.func.current_timestamp()))


"""log table column information
id - the row id
code - process being logged 
level - Whether or not process succeeded (0 Success | 1 Failure | 2 Warning | 4 Info)
log - values being logged 
ts - current timestamp 
"""
# For 'ts' need need to have "onupdate=sqlalchemy.func.current_timestamp()" otherwise code returns sqlalchemy.exc.IntegrityError 
_LOG_TABLE = sqlalchemy.Table('log', sqlalchemy.MetaData(),
                                        sqlalchemy.Column('id', sqlalchemy.BIGINT, primary_key=True, autoincrement=True),
                                        sqlalchemy.Column('code', sqlalchemy.CHAR(5), default='PURGE'),
                                        sqlalchemy.Column('level', sqlalchemy.SMALLINT, default=0),
                                        sqlalchemy.Column('log', sqlalchemy.dialects.postgresql.JSONB, default={}),
                                        sqlalchemy.Column('ts', sqlalchemy.TIMESTAMP(6),
                                                          default=sqlalchemy.func.current_timestamp(),
                                                          onupdate=sqlalchemy.func.current_timestamp()))


"""Methods that support the purge process.  
"""


def get_nth_id() -> int:
    """Update the config file to have row ID somewhere within the oldest 100 rows.
    This method would potentially be replaced by a mechanism that is aware what was the last value sent to the
     historian.
    Returns:
        Method doesn't return anything
    """
    rand = random.randint(1, 100)
    stmt = "SELECT id FROM (SELECT id FROM readings ORDER BY id ASC LIMIT %s)t ORDER BY id DESC LIMIT 1"
    row_id = execute_command(stmt % rand).fetchall()
    try:
        return int(row_id[0][0])
    except IndexError:
        return 1


def convert_timestamp(set_time: str) -> datetime.timedelta:
    """Convert "age" in config file to timedelta. If only an integer is specified,  then 
        the code assumes that it is already in minutes (ie age:1 means wait 1 minute) 
    Args:
        set_time (str): Newest amount of  time back to delete
    Returns:
        converted set_time to datetime.timedelta value
    """
    if type(set_time) is int or set_time.isdigit():
        return datetime.timedelta(minutes=int(set_time))
    time_dict = {}
    tmp = 0

    for value in set_time.split(" "):
        if value.isdigit() is True:
            tmp = int(value)
        else:
            time_dict[value] = tmp

    time_in_sec = datetime.timedelta(seconds=0)
    time_in_min = datetime.timedelta(minutes=0)
    time_in_hr = datetime.timedelta(hours=0)
    time_in_day = datetime.timedelta(days=0)

    for key in time_dict.keys():
        if 'sec' in key:
            time_in_sec = datetime.timedelta(seconds=time_dict[key])
        elif 'min' in key:
            time_in_min = datetime.timedelta(minutes=time_dict[key])
        elif ('hr' in key) or ('hour' in key):
            time_in_hr = datetime.timedelta(hours=time_dict[key])
        elif ('day' in key) or ('dy' in key):
            time_in_day = datetime.timedelta(days=time_dict[key])
    return time_in_sec+time_in_min+time_in_hr+time_in_day


def execute_command(stmt: str):
    """Imitate connection to postgres that returns result.    
    Args:
        stmt (str): generated SQL query   
    Returns:
        Returns result set 
    """
    engine = sqlalchemy.create_engine(__CONNECTION_STRING, pool_size=20, max_overflow=0)
    conn = engine.connect()
    query_result = conn.execute(stmt)
    return query_result


"""The actual purge process 
"""


def purge(config) -> (int, int):
    """The actual process read the configuration file, and based off the information in it does the following:
    1. Gets previous information found in log file
    2. Based on the configurations, call the DELETE command to purge the data
    3. Calculate relevant information kept in logs
    4. Based on the configuration calculates how long to wait until next purge, and returns that 
         
    Returns:
        The number of rows that have been purged
    """
    last_id = get_nth_id()
    table_name = _READING_TABLE  # This could be replaced with any table that would need to be purged.

    start_time = datetime.datetime.fromtimestamp(time.time())

    age_timestamp = datetime.datetime.strftime(start_time - convert_timestamp(
        set_time=config['age']['value']), '%Y-%m-%d %H:%M:%S.%f')
    start_time = start_time.strftime('%Y-%m-%d %H:%M:%S')

    # Number of unsent rows
    number_sent_rows_query = sqlalchemy.select([sqlalchemy.func.count()]).select_from(table_name).where(
        table_name.c.ts <= start_time).where(table_name.c.id > last_id)

    unsent_rows_before = execute_command(number_sent_rows_query).fetchall()
    unsent_rows_before = int(unsent_rows_before[0][0])

    """Time purge process starts
    If unsent data is retained, then the WHERE condition is against the last sent ID
    """

    if config['retainUnsent']['value'] == 'True':
        count_query = sqlalchemy.select([sqlalchemy.func.count()]).select_from(table_name).where(
            table_name.c.id <= last_id).where(table_name.c.ts <= start_time)
        total_count_before = execute_command(count_query).fetchall()
        total_count_before = int(total_count_before[0][0])

        delete_query = sqlalchemy.delete(table_name).where(table_name.c.id <= last_id).where(
            table_name.c.ts <= start_time)

        execute_command(delete_query)

        # Number of rows that were expected to get removed, but weren't
        failed_removal_query = sqlalchemy.select([sqlalchemy.func.count()]).select_from(
            table_name).where(table_name.c.id <= last_id).where(
            table_name.c.ts <= start_time)

        failed_removal_count = execute_command(failed_removal_query).fetchall()
        failed_removal_count = int(failed_removal_count[0][0])
        total_rows_removed = total_count_before - failed_removal_count

    # If unsent data is not retained, then the WHERE condition is against the age
    else:
        count_query = sqlalchemy.select([sqlalchemy.func.count()]).select_from(table_name).where(
            table_name.c.ts <= age_timestamp).where(table_name.c.ts <= start_time)
        total_count_before = execute_command(count_query).fetchall()
        total_count_before = int(total_count_before[0][0])

        delete_query = sqlalchemy.delete(table_name).where(table_name.c.ts <= age_timestamp).where(
            table_name.c.ts < start_time)
        execute_command(delete_query)

        # Number of rows that were expected to get removed, but weren't
        failed_removal_query = sqlalchemy.select([sqlalchemy.func.count()]).select_from(
            table_name).where(table_name.c.ts <= age_timestamp).where(
            table_name.c.ts <= start_time)
        failed_removal_count = execute_command(failed_removal_query).fetchall()
        failed_removal_count = int(failed_removal_count[0][0])
        total_rows_removed = total_count_before - failed_removal_count

    # Total number of rows that remain under start_time
    total_count = sqlalchemy.select([sqlalchemy.func.count()]).select_from(table_name).where(
        table_name.c.ts < start_time)
    total_count_after = execute_command(total_count).fetchall()
    total_count_after = int(total_count_after[0][0])

    # Time  purge process finished
    end_time = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')

    """Levels:
    -> 0 - No issues  (success) 
    -> 1 - Rows failed to get removed (failure) 
    -> 2 - (warnings)
    --> less than 10% of original data remain in database  
    --> unsent data was purged 
    """
    level = 0
    unsent_count = execute_command(number_sent_rows_query).fetchall()
    if failed_removal_count > 0:
        level = 1
    elif (int(unsent_count[0][0]) < unsent_rows_before) or (total_count_after <= int(total_count_before * 0.1)):
        level = 2

    """Column information
    start_time - time that purge process began
    end_time - time that purge process ended
    total_rows_removed - number of rows removed 
    total_unsent_rows - total number of unsent rows under start_time 
    total_failed_to_remove - total number of rows that failed to remove (this is the confirmation whether  purge 
                                                                            succeeded or not.) 
    """
    unsent_rows_removed = unsent_rows_before-int(unsent_count[0][0]) 
    if unsent_rows_removed < 0: 
        unsent_rows_removed = 0
    purge_set = {'start_time': start_time, 'end_time': end_time, 'rows_removed': total_rows_removed,
                 'rows_remaining': total_count_after, 'unsent_rows_removed': unsent_rows_removed,
                 'total_failed_to_remove': failed_removal_count}

    insert_into_log(level=level, log=purge_set)
    return total_rows_removed, unsent_rows_removed


def insert_into_log(level=0, log=None):
    """INSERT into log table values"""
    stmt = _LOG_TABLE.insert().values(code='PURGE', level=level, log=log)
    execute_command(stmt)


def purge_main():
    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(configuration_manager.create_category(_CONFIG_CATEGORY_NAME, _DEFAULT_PURGE_CONFIG,
                                                                        _CONFIG_CATEGORY_DESCRIPTION))

    config = event_loop.run_until_complete(configuration_manager.get_category_all_items(_CONFIG_CATEGORY_NAME))
    total_purged, unsent_purged = purge(config)

    event_loop.run_until_complete(statistics.update_statistics_value('PURGED', total_purged))
    event_loop.run_until_complete(statistics.update_statistics_value('UNSNPURGED', unsent_purged))

if __name__ == '__main__':
    purge_main()


"""Testing
"""


# def insert_into_readings():
#     """
#     Insert rows into table
#     """
#     stmt = "SELECT MAX(id) FROM readings;"
#     reading_table_id = execute_command(stmt).fetchall()
#     if reading_table_id[0][0] is None:
#         reading_table_id = 1
#     else:
#         reading_table_id = int(reading_table_id[0][0])+1
#     for i in range(1000):
#         stmt = "INSERT INTO readings(id, asset_code) VALUES (%s, '%s')" % (reading_table_id, reading_table_id)
#         # stmt = _READING_TABLE.insert().values(id=reading_table_id, asset_code='', )
#         print(stmt)
#         execute_command(stmt)
#         reading_table_id = reading_table_id+1
#
#
# def select_count_from_readings():
#     """
#     Get count of readings table
#     """
#     stmt = sqlalchemy.select([sqlalchemy.func.count()]).select_from(_READING_TABLE)
#     result = execute_command(stmt).fetchall()
#     return int(result[0][0])
#
#
# def check_log_count():
#     stmt = sqlalchemy.select([sqlalchemy.func.count()]).select_from(_LOG_TABLE)
#     result = execute_command(stmt).fetchall()
#     return int(result[0][0])
#
#
# def check_statistics_purge_values():
#     stmt = "SELECT value FROM statistics WHERE key = 'PURGED'"
#     purge_count = execute_command(stmt).fetchall()
#     stmt = "SELECT value FROM statistics WHERE key = 'UNSNPURGED'"
#     unsent = execute_command(stmt).fetchall()
#     return int(purge_count[0][0]), int(unsent[0][0])
#
#
# def purge_by_id():
#     """
#     Test purge by row ID
#     :return:
#     """
#     event_loop = asyncio.get_event_loop()
#     event_loop.run_until_complete(configuration_manager.set_category_item_value_entry(_CONFIG_CATEGORY_NAME,
#                                                                                       'retainUnsent', "True"))
#
#     insert_into_readings()
#     count1 = select_count_from_readings()
#     log1 = check_log_count()
#     purge1, unsent1 = check_statistics_purge_values()
#     purge_main()
#     count2 = select_count_from_readings()
#     log2 = check_log_count()
#     purge2, unsent2 = check_statistics_purge_values()
#
#     if count1 > count2:
#         print("Test Purge - Success")
#     else:
#         print("Test Purge - Fail")
#
#     if log1 < log2:
#         print("Test Log Update - Success")
#     else:
#         print("Test Log Update - Fail")
#
#     if purge1 < purge2 and unsent1 < unsent2:
#         print("Test Statistics Update - Success")
#     else:
#         print("Test Statistics Update - Fail")
#
#
# def purge_by_age():
#     """Purge by age"""
#     event_loop = asyncio.get_event_loop()
#     event_loop.run_until_complete(configuration_manager.set_category_item_value_entry(_CONFIG_CATEGORY_NAME,
#                                                                                       'retainUnsent', "False"))
#     event_loop.run_until_complete(configuration_manager.set_category_item_value_entry(_CONFIG_CATEGORY_NAME,
#                                                                                       'age', "0"))
#
#     insert_into_readings()
#     count1 = select_count_from_readings()
#     log1 = check_log_count()
#     purge1, unsent1 = check_statistics_purge_values()
#     purge_main()
#     count2 = select_count_from_readings()
#     log2 = check_log_count()
#     purge2, unsent2 = check_statistics_purge_values()
#
#     if count1 > count2:
#         print("Test Purge - Success")
#     else:
#         print("Test Purge - Fail")
#
#     if log1 < log2:
#         print("Test Log Update - Success")
#     else:
#         print("Test Log Update - Fail")
#
#     if purge1 < purge2 and unsent1 < unsent2:
#         print("Test Statistics Update - Success")
#     else:
#         print("Test Statistics Update - Fail")
#
#
# if __name__ == '__main__':
#     purge_by_id()
#     purge_by_age()
