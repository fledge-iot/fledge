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


def get_last_id() -> int:
    """
    From foglamp.streams retrive the heighest last_object that corresponds to the newest readings table row id sent to Pi/OMF 
    Returns: 
        The newest `readings` table row id that was sent to Pi/OMF
    """
   stmt = "SELECT MAX(last_object) FROM foglamp.streams;" 
   return int(conn.execute(stmt).fetchall()[0][0]) 

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


def purge(config, table_name) -> (int, int):
    """Column information
    start_time - time that purge process began
    end_time - time that purge process ended
    -------------------------------------------
    total_rows_removed - number of rows removed 
        - DELETE stmt returns value
    ------------------------------------------
    unsent_rows_removed - number of rows that weren't sent to historian, but were removed
    failed_removal - number of rows that failed to remove
        - SELECT stmt of DELETE
    rows_remaining - total number of rows remain at screenshot 
        - total_row - total_rows_removed
    """
    start_time = time.strftime('%Y-%m-%d %H:%M:%S.%s', time.localtime(time.time()))

    unsent_rows_removed = 0 
    total_rows_removed = 0
    last_id = get_last_id()
    error_level = 0
    
    # Calculate current count and age_timestamp
    age_and_count_query = sqlalchemy.select([sqlalchemy.func.current_timestamp() - datetime.timedelta(hours=int(config['age']['value'])), 
        sqlalchemy.func.count()]).select_from(table_name)
    result = execute_command(age_and_count_query).fetchall()
    age_timestamp = result[0][0]
    total_count = result[0][1]

    # MAX possible ID to delete
    max_id_query = sqlalchemy.select([sqlalchemy.func.max(table_name.c.id)]).select_from(table_name).where(table_name.c.user_ts <= age_timestamp)
    max_id = execute_command(max_id_query).fetchall()[0][0]

    # if retainUnsent is True then delete by last_id,  else delete by age
    if config['retainUnsent']['value'] == "True":
        delete_query = sqlalchemy.delete(table_name).where(table_name.c.id <= last_id)
        total_rows_removed = execute_command(delete_query).rowcount
        failed_removal_query = sqlalchemy.select([sqlalchemy.func.count()]).select_from(table_name).where(table_name.c.id <= last_id) 
        failed_removal = execute_command(failed_removal_query).fetchall()[0][0]
    
    else: 
        delete_query = sqlalchemy.delete(table_name).where(table_name.c.user_ts <= age_timestamp)
        total_rows_removed = execute_command(delete_query).rowcount
        failed_removal_query = sqlalchemy.select([sqlalchemy.func.count()]).select_from(table_name).where(table_name.c.user_ts <= age_timestamp)
        failed_removal = execute_command(failed_removal_query).fetchall()[0][0]
        unsent_rows_removed = int(max_id) - last_id
        if unsent_rows_removed < 0: 
            unsent_rows_removed = 0
    
    # Rows remaining is based on the snapshot taking at the start of the process 
    rows_remaining = int(total_count) - int(total_rows_removed)

    """Error Levels: 
    - 0: No errors
    - 1: Rows failed to remove 
    - 2: Unsent rows were removed
    """ 
    if  failed_removal > 0: 
        error_level = 1
    elif unsent_rows_removed > 0: 
        error_level = 2

    end_time = time.strftime('%Y-%m-%d %H:%M:%S.%s', time.localtime(time.time()))

    insert_into_log(level=error_level, log={"start_time":start_time, "end_time": end_time, "rowsRemoved": total_rows_removed, "unsentRowsRemoved": 
        unsent_rows_removed, "failedRemovals": failed_removal, "rowsRemaining": rows_remaining})  

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
    total_purged, unsent_purged = purge(config, _READING_TABLE)

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
