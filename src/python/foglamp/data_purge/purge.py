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
import datetime
import json
import random
import sqlalchemy
import sqlalchemy.dialects.postgresql
import time

"""Script information and connection to the Database
"""
__author__ = "Ori Shadmon"
__copyright__ = "Copyright (c) 2017 OSI Soft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


# Set variables for connecting to database
_db_type = "postgres"
_user = "foglamp"
_db_user = "foglamp"
_host = "192.168.0.182"
_db = "foglamp"

# Create Connection
_ENGINE = sqlalchemy.create_engine('%s://%s:%s@%s/%s' % (_db_type, _db_user, _user, _host, _db),  pool_size=20,
                                   max_overflow=0)
_CONN = _ENGINE.connect()

"""Temporary methods and variables that exist until the script utilizes other components. In specific: 
-> configuration API 
-> Last ID sent to the historian
"""
# Important files
config_file = 'config.json'
other_config = "other_config.json"

# Will be replaced once FOGL-212 work is done
with open(config_file, 'r') as conf:
    _CONFIG = json.load(conf)

# Will be replaced by the last ID sent to the Historian
with open(other_config, 'r') as conf:
    _LAST_ID = json.load(conf)['lastID']


def get_nth_id() -> None:
    """Update the config file to have row ID somewhere within the oldest 100 rows.

    This method would potentially be replaced by a mechanism that is aware what was the last value sent to the
     historian.
    Returns: 
        Method doesn't return anything
    """
    rand = random.randint(1, 100)

    stmt = "SELECT id FROM (SELECT id FROM readings ORDER BY id ASC LIMIT %s)t ORDER BY id DESC LIMIT 1"
    row_id = execute_command_with_return_value(stmt % rand)
    row_id = int(row_id[0][0])

    with open(other_config, 'r') as conf:
        config_info = json.load(conf)

    config_info["lastID"] = row_id
    open(other_config, 'w').close()
    with open(other_config, 'r+') as conf:
        conf.write(json.dumps(config_info))


"""Utilized tables 
"""
# Table purge against
_READING_TABLE = sqlalchemy.Table('readings', sqlalchemy.MetaData(),
                                  sqlalchemy.Column('id', sqlalchemy.BIGINT, primary_key=True),
                                  sqlalchemy.Column('asset_code', sqlalchemy.VARCHAR(50)),
                                  sqlalchemy.Column('read_key', sqlalchemy.dialects.postgresql.UUID,
                                                    default='00000000-0000-0000-0000-000000000000'),
                                  sqlalchemy.Column('reading', sqlalchemy.dialects.postgresql.JSON, default='{}'),
                                  sqlalchemy.Column('user_ts', sqlalchemy.TIMESTAMP(6),
                                                    default=time.strftime('%Y-%m-%d %H:%M:%S',
                                                                          time.localtime(time.time()))),
                                  sqlalchemy.Column('ts', sqlalchemy.TIMESTAMP(6),
                                                    default=time.strftime('%Y-%m-%d %H:%M:%S',
                                                                          time.localtime(time.time()))))


"""logging table is instead of the log. After much thought, in addition to the discussed information the table also 
includes the following: 
    -> table to specify which table has been purged, since the process could occur in multiple tables 
    -> total_unsent_rows specifies the total number of unsent rows that existed within range prior to the purge. 
    based off that, and unsent_rows_removed one can calculate how many (unsent rows) remain.
"""
_LOGGING_TABLE = sqlalchemy.Table('purge_logging', sqlalchemy.MetaData(),
                                  sqlalchemy.Column('id', sqlalchemy.BIGINT, primary_key=True, autoincrement=True),
                                  sqlalchemy.Column('table_name', sqlalchemy.VARCHAR(255), default=_READING_TABLE.name,
                                                    primary_key=True),
                                  sqlalchemy.Column('start_time', sqlalchemy.VARCHAR(255),
                                                    default=sqlalchemy.func.current_timestamp),
                                  sqlalchemy.Column('end_time', sqlalchemy.VARCHAR(255),
                                                    default=sqlalchemy.func.current_timestamp),
                                  sqlalchemy.Column('total_rows_removed', sqlalchemy.INTEGER, default=0),
                                  sqlalchemy.Column('total_rows_remaining', sqlalchemy.INTEGER, default=0),
                                  sqlalchemy.Column('total_unsent_rows', sqlalchemy.INTEGER, default=0),

                                  sqlalchemy.Column('total_failed_to_remove', sqlalchemy.INTEGER, default=0))

"""Methods that support the purge process.  
"""


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


def execute_command_with_return_value(stmt: str) -> dict:
    """Imitate connection to postgres that returns result.    
    Args:
        stmt (str): generated SQL query   
    Returns:
        Returns result set 
    """
    query_result = _CONN.execute(stmt)
    return query_result.fetchall()


def execute_command_without_return_value(stmt: str) -> None:
    """Imitate connection to Postgres and a query that doesn't generate results
    Args:
        stmt (str): DELETE stmt 
    """
    _CONN.execute(stmt)
    _CONN.execute("commit")


def set_id() -> int:
    """
    Set the ID value for the next purge log table
    Returns:
        Next INT in purge logging table
    """
    stmt = sqlalchemy.select([_LOGGING_TABLE.c.id]).select_from(_LOGGING_TABLE).order_by(
        _LOGGING_TABLE.c.id.desc()).limit(1)
    result = execute_command_with_return_value(stmt)
    if not result:
        return 1
    return int(result[0][0])+1


"""The actual purge process 
"""


def purge_process_function(table_name) -> None:
    """The actual process read the configuration file, and based off the information in it does the following:
    1. Gets previous information found in log file
    2. Based on the configurations, call the DELETE command to purge the data
    3. Calculate relevant information kept in logs
    4. Based on the configuration calculates how long to wait until next purge, and returns that

    Args:
        table_name (SQLAlchemy.Table): The name of the table that will be purged. 
        The reason for this is because  purge process can occur on any of the tables. 
    Returns:
        Amount of time until next purge process
    """

    start_time = datetime.datetime.fromtimestamp(time.time())

    age_timestamp = datetime.datetime.strftime(start_time - convert_timestamp(
        set_time=_CONFIG['age']['value_item_entry']), '%Y-%m-%d %H:%M:%S.%f')
    start_time = start_time.strftime('%Y-%m-%d %H:%M:%S')

    # Number of unsent rows
    number_sent_rows_query = sqlalchemy.select([sqlalchemy.func.count()]).select_from(table_name).where(
        table_name.c.ts <= start_time).where(table_name.c.id > _LAST_ID)

    unsent_rows_before = execute_command_with_return_value(number_sent_rows_query)
    unsent_rows_before = int(unsent_rows_before[0][0])

    """Time purge process starts
    If unsent data is retained, then the WHERE condition is against the last sent ID
    """

    if _CONFIG['retainUnsent']['value_item_entry'] is True:
        count_query = sqlalchemy.select([sqlalchemy.func.count()]).select_from(table_name).where(
            table_name.c.id <= _LAST_ID).where(table_name.c.ts <= start_time)
        total_count_before = execute_command_with_return_value(count_query)
        total_count_before = int(total_count_before[0][0])

        delete_query = sqlalchemy.delete(table_name).where(table_name.c.id <= _LAST_ID).where(
            table_name.c.ts <= start_time)

        execute_command_without_return_value(delete_query)

        # Number of rows that were expected to get removed, but weren't
        failed_removal_query = sqlalchemy.select([sqlalchemy.func.count()]).select_from(
            table_name).where(table_name.c.id <= _LAST_ID).where(
            table_name.c.ts <= start_time)

        failed_removal_count = execute_command_with_return_value(failed_removal_query)
        failed_removal_count = int(failed_removal_count[0][0])
        total_rows_removed = total_count_before - failed_removal_count

    # If unsent data is not retained, then the WHERE condition is against the age
    else:
        count_query = sqlalchemy.select([sqlalchemy.func.count()]).select_from(table_name).where(
            table_name.c.ts <= age_timestamp).where(table_name.c.ts <= start_time)
        total_count_before = execute_command_with_return_value(count_query)
        total_count_before = int(total_count_before[0][0])

        delete_query = sqlalchemy.delete(table_name).where(table_name.c.ts <= age_timestamp).where(
            table_name.c.ts < start_time)
        execute_command_without_return_value(delete_query)

        # Number of rows that were expected to get removed, but weren't
        failed_removal_query = sqlalchemy.select([sqlalchemy.func.count()]).select_from(
            table_name).where(table_name.c.ts <= age_timestamp).where(
            table_name.c.ts <= start_time)
        failed_removal_count = execute_command_with_return_value(failed_removal_query)
        failed_removal_count = int(failed_removal_count[0][0])
        total_rows_removed = total_count_before - failed_removal_count

    # Total number of rows that remain under start_time
    total_count = sqlalchemy.select([sqlalchemy.func.count()]).select_from(table_name).where(
        table_name.c.ts < start_time)
    total_count_after = execute_command_with_return_value(total_count)
    total_count_after = int(total_count_after[0][0])

    # Time  purge process finished
    end_time = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')

    """Column information
    id - row id PK
    table_name - table that was purged PK
    start_time - time that purge process began
    end_time - time that purge process ended
    total_rows_removed - number of rows removed 
    total_unsent_rows - total number of unsent rows under start_time 
    total_failed_to_remove - total number of rows that failed to remove (this is the confirmation whether  purge 
                                                                            succeeded or not.) 
    """
    inst_stmt = _LOGGING_TABLE.insert().values(id=set_id(), table_name=table_name.name, start_time=start_time,
                                               end_time=end_time, total_rows_removed=total_rows_removed,
                                               total_rows_remaining=total_count_after,
                                               total_unsent_rows=unsent_rows_before,
                                               total_failed_to_remove=failed_removal_count)

    execute_command_without_return_value(inst_stmt)


"""
The main,  which would be replaced by the scheduler 
"""
if __name__ == '__main__':
    """The main / scheduler creates the logs.json file,  and executes the purge (returning how long to wait)
    till the next purge execution. Noticed that the purge process expects the table,  and config file. 
    This is because (theoretically) purge  would be executed on multiple tables,  where each table could 
    have its own configs. 
        
    As of now,  the example shows only 1 table,  but can be rewritten to show multiple tables without too much
    work. 
    """
    get_nth_id()
    purge_process_function(table_name=_READING_TABLE)

