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
import sqlalchemy
import sqlalchemy.dialects.postgresql
import time
from foglamp import configuration_manager
from foglamp import statistics

"""Script information and connection to the Database"""
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


"""Utilized tables"""
# Table purge against
# The purge process utilizes only user_ts
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


# For 'ts' need need to have "onupdate=sqlalchemy.func.current_timestamp()" otherwise code returns
# sqlalchemy.exc.IntegrityError
_LOG_TABLE = sqlalchemy.Table('log', sqlalchemy.MetaData(),
                              sqlalchemy.Column('id', sqlalchemy.BIGINT, primary_key=True, autoincrement=True),
                              sqlalchemy.Column('code', sqlalchemy.CHAR(5), default='PURGE'),
                              sqlalchemy.Column('level', sqlalchemy.SMALLINT, default=0),
                              sqlalchemy.Column('log', sqlalchemy.dialects.postgresql.JSONB, default={}),
                              sqlalchemy.Column('ts', sqlalchemy.TIMESTAMP(6),
                                                default=sqlalchemy.func.current_timestamp(),
                                                onupdate=sqlalchemy.func.current_timestamp()))

# Subset of `streams` table in order to execute MAX(last_object) as part of sqlalchemy query
_STREAMS_TABLE = sqlalchemy.Table('streams', sqlalchemy.MetaData(),
                                  sqlalchemy.Column('id', sqlalchemy.INTEGER, primary_key=True, autoincrement=True),
                                  sqlalchemy.Column('last_object', sqlalchemy.BIGINT, default=0))

"""Methods that support the purge process."""


def execute_command(stmt):
    """"Imitate connection to postgres that returns result.
    Args:
        stmt (str): generated SQL query   
    Returns:
        Returns result set 
    """
    # Set connection to database
    engine = sqlalchemy.create_engine(__CONNECTION_STRING, pool_size=20, max_overflow=0)
    conn = engine.connect()
    # Execute query
    query_result = conn.execute(stmt)
    return query_result


def insert_into_log(level=0, log=None):
    """"INSERT into log table values"""
    stmt = _LOG_TABLE.insert().values(code='PURGE', level=level, log=log)
    execute_command(stmt)


def set_configuration():
    """"set the default configuration for purge
    :return:
        Configuration information that was set for purge process
    """
    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(configuration_manager.create_category(_CONFIG_CATEGORY_NAME, _DEFAULT_PURGE_CONFIG,
                                                                        _CONFIG_CATEGORY_DESCRIPTION))
    return event_loop.run_until_complete(configuration_manager.get_category_all_items(_CONFIG_CATEGORY_NAME))

"""The actual purge process"""


def purge(config, table_name):
    """"Column information
    start_time - time that purge process began
    end_time - time that purge process ended
    -------------------------------------------
    total_rows_removed - number of rows removed 
        - DELETE stmt returns value
    ------------------------------------------
    unsent_rows_removed - number of rows that weren't sent to historian, but were removed
    failed_removal - number of rows that failed to remove
        - SELECT stmt of DELETE
    rows_remaining - total number of rows remain at screen shot
        - total_row - total_rows_removed
    """
    start_time = time.strftime('%Y-%m-%d %H:%M:%S.%s', time.localtime(time.time()))

    unsent_rows_removed = 0
    last_id = sqlalchemy.select([sqlalchemy.func.min(_STREAMS_TABLE.c.last_object)]).select_from(_STREAMS_TABLE)
    last_id = int(execute_command(last_id).fetchall()[0][0])

    # Calculate current count and age_timestamp
    age_and_count_query = sqlalchemy.select([sqlalchemy.func.current_timestamp() -
                                             datetime.timedelta(hours=int(config['age']['value'])),
    sqlalchemy.func.count()]).select_from(table_name)

    result = execute_command(age_and_count_query).fetchall()
    age_timestamp = result[0][0]    
    total_count = result[0][1]

    delete_query = sqlalchemy.delete(table_name).where(table_name.c.user_ts <= age_timestamp)
    failed_removal_query = sqlalchemy.select([sqlalchemy.func.count()]).select_from(table_name).where(
        table_name.c.user_ts <= age_timestamp)
    
    max_id_query = sqlalchemy.select([sqlalchemy.func.max(table_name.c.id)]).select_from(table_name).where(
        table_name.c.user_ts <= age_timestamp)
    max_id = execute_command(max_id_query).fetchall()[0][0]

    # If max_id is not an integer than it is assumed that no rows would be removed
    if max_id is None: 
        total_rows_removed = 0 
        unsent_rows_removed = 0 
        failed_removal = 0 
    # if retainUnsent is True then delete by both age_timestamp & last_id; else only by age_timestamp
    elif config['retainUnsent']['value'] == 'True':
        total_rows_removed = execute_command(delete_query.where(table_name.c.id <= last_id)).rowcount
        failed_removal = execute_command(failed_removal_query.where(table_name.c.id <= last_id)).fetchall()[0][0]
    else: 
        total_rows_removed = execute_command(delete_query).rowcount
        failed_removal = execute_command(failed_removal_query).fetchall()[0][0] 
        unsent_rows_removed = int(max_id) - int(last_id)

    if unsent_rows_removed < 0:
        unsent_rows_removed = 0 
           
    # Rows remaining is based on the snapshot taking at the start of the process 
    rows_remaining = int(total_count) - int(total_rows_removed)

    """Error Levels: 
    - 0: No errors
    - 1: Rows failed to remove 
    - 2: Unsent rows were removed
    """ 
    error_level = 0
    if failed_removal > 0:
        error_level = 1
    elif unsent_rows_removed > 0: 
        error_level = 2

    end_time = time.strftime('%Y-%m-%d %H:%M:%S.%s', time.localtime(time.time()))

    insert_into_log(level=error_level, log={"start_time": start_time, "end_time": end_time,
                                            "rowsRemoved": total_rows_removed, "unsentRowsRemoved": unsent_rows_removed,
                                            "failedRemovals": failed_removal, "rowsRemaining": rows_remaining})

    return total_rows_removed, unsent_rows_removed 


def purge_main():
    """"Execute the processes around and including purge."""
    config = set_configuration() 
    total_purged, unsent_purged = purge(config, _READING_TABLE)

    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(statistics.update_statistics_value('PURGED', total_purged))
    event_loop.run_until_complete(statistics.update_statistics_value('UNSNPURGED', unsent_purged))

if __name__ == '__main__':
    purge_main()

