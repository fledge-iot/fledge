"""
Description: Based on FOGL-200 (https://docs.google.com/document/d/1GdMTerNq_-XQuAY0FJNQm09nbYQSjZudKJhY8x5Dq8c/edit) 
    the purge process is suppose to remove data based on either a user_id, or an X amount of time back depending on
    whether or not the configuration (config.json) requires to retain data that has not been sent to the Pi System.
    
    Given that the code is dependent on configuration files, sending data to Pi, and connecting to the database, 
    I have "hard-coded" those dependencies with the use of extra methods, and files. This includes things like: 
    get_nth_id which updates the config file with a 'random' last ID that was sent to Pi, and the main which also 
    as a scheduler process. 
    
     Specifically the purge process (purge_process_function) does the following: 
     - Based on the configuration file (retainUnsent) it either removes by the lastID 
        (in which case retainUnsent is True), or by age (timestamp)
     - Calculate vital information regarding the purge, and record it in the logs file
      
Based on the way things are currently being done, both the logs file (logs.json), and configurations file (config.json)
will be replaced either database tables, or some other kind of file. 
"""
import datetime
import json
import random
import sqlalchemy
import sqlalchemy.dialects.postgresql
import sys
import time


__author__ = "Ori Shadmon"
__copyright__ = "Copyright (c) 2017 OSI Soft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


# Set variables for connecting to database
_user = "foglamp"
_db_user = "foglamp"
_host = "192.168.0.182"
_db = "foglamp"

# Create Connection
_ENGINE = sqlalchemy.create_engine('postgres://%s:%s@%s/%s' % (_db_user, _user, _host, _db),  pool_size=20,
                                      max_overflow=0)
_CONN = _ENGINE.connect()

# Important files
config_file = 'config.json'
other_config = "other_config.json"

# Will be replaced once FOGL-212 work is done
with open(config_file, 'r') as conf:
    _CONFIG = json.load(conf)


with open(other_config, 'r') as conf:
    _LAST_ID = json.load(conf)['lastID']

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
                                  sqlalchemy.Column('total_unsent_rows', sqlalchemy.INTEGER, default=0),
                                  sqlalchemy.Column('total_unsent_rows_removed', sqlalchemy.INTEGER, default=0),
                                  sqlalchemy.Column('total_failed_to_remove', sqlalchemy.INTEGER, default=0))

"""Methods that support the purge process. For the most part, theses methods would be replaced by either a scheduler,  
a database API interface,  and/or proper configuration methodology. 
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
        return datetime.timedelta(hours=int(set_time))
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
    print(stmt)

    _CONN.execute(stmt)
    _CONN.execute("commit")


def set_id():
    stmt = sqlalchemy.select([_LOGGING_TABLE.c.id]).select_from(_LOGGING_TABLE).order_by(_LOGGING_TABLE.c.id.desc()).limit(1)
    result = execute_command_with_return_value(stmt)
    if not result:
        return 1
    return int(result[0][0])+1

def get_nth_id() -> None:
    """Update the config file to have row ID somewhere within the oldest 100 rows.
    
    This method would potentially be replaced by the communication with the Pi System which will be
    aware of what was the last ID sent to the Pi System. 
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


"""The actual purge process 
"""


def purge_process_function(table_name) -> None:
    """The actual process read the configuration file, and based off the information in it does the following:
    1. Gets previous information found in log file
    2. Based on the configurations, call the DELETE command to purge the data
    3. Calculate relevant information kept in logs
    4. Based on the configuration calculates how long to wait until next purge, and returns that

    Args:
        table_name (SQLAlchemy.Table): The name of the table queries run against
    Returns:
        Amount of time until next purge process
    """


    start_time = datetime.datetime.fromtimestamp(time.time())

    age_timestamp = datetime.datetime.strftime(start_time - convert_timestamp(
        set_time=_CONFIG['age']['value_item_entry']), '%Y-%m-%d %H:%M:%S.%f')
    start_time = start_time.strftime('%Y-%m-%d %H:%M:%S')

    # Number of rows exist at the point of calling purge
    total_count_query = sqlalchemy.select([sqlalchemy.func.count()]).select_from(table_name).where(
        table_name.c.ts < start_time)
    total_count_before = execute_command_with_return_value(total_count_query)
    total_count_before = int(total_count_before[0][0])

    # Number of unsent rows
    number_sent_rows_query = sqlalchemy.select([sqlalchemy.func.count()]).select_from(table_name).where(
        table_name.c.ts < start_time).where(table_name.c.id > _LAST_ID)

    unsent_rows_before = execute_command_with_return_value(number_sent_rows_query)
    unsent_rows_before = int(unsent_rows_before[0][0])

    """Time purge process starts
    If unsent data is retained, then the WHERE condition is against the last sent ID
    """

    if _CONFIG['retainUnsent']['value_item_entry'] is True:
        delete_query = sqlalchemy.delete(table_name).where(table_name.c.id <= _LAST_ID).where(
            table_name.c.ts < start_time)
        execute_command_without_return_value(delete_query)

        # Number of rows that were expected to get removed, but weren't
        failed_removal_query = sqlalchemy.select([sqlalchemy.func.count()]).select_from(
            table_name).where(table_name.c.id <= _LAST_ID).where(
            table_name.c.ts < start_time)
        failed_removal_count = execute_command_with_return_value(failed_removal_query)
        failed_removal_count = int(failed_removal_count[0][0])

    # If unsent data is not retained, then the WHERE condition is against the age
    else:
        row_id = execute_command_with_return_value(sqlalchemy.select([table_name.c.id]).select_from(
            table_name).where(table_name.c.ts <= age_timestamp).order_by(table_name.c.id.desc()).limit(1))
        row_id = row_id[0][0]

        delete_query = sqlalchemy.delete(table_name).where(table_name.c.id <= row_id).where(
            table_name.c.ts < start_time)
        execute_command_without_return_value(delete_query)

        # Number of rows that were expected to get removed, but weren't
        failed_removal_query = sqlalchemy.select([sqlalchemy.func.count()]).select_from(
            table_name).where(table_name.c.id <= _LAST_ID).where(
            table_name.c.ts < start_time)
        failed_removal_count = execute_command_with_return_value(failed_removal_query)
        failed_removal_count = int(failed_removal_count[0][0])

    total_count_after = execute_command_with_return_value(sqlalchemy.select(
        [sqlalchemy.func.count()]).select_from(table_name).where(table_name.c.ts < start_time))
    total_count_after = int(total_count_after[0][0])
    total_rows_removed = total_count_before - total_count_after

    if total_rows_removed <= 0:
        total_rows_removed = 0

    # Number of unsent rows removed
    unsent_rows_after = execute_command_with_return_value(number_sent_rows_query)
    unsent_rows_after = int(unsent_rows_after[0][0])

    unsent_rows_removed = unsent_rows_before - unsent_rows_after
    if unsent_rows_removed < 0:
        unsent_rows_removed = 0
    # Time  purge process finished
    end_time = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')

    inst_stmt = _LOGGING_TABLE.insert().values(id=set_id(), table_name=table_name.name, start_time=start_time, end_time=end_time,
                                               total_rows_removed = total_rows_removed,
                                               total_unsent_rows_removed = unsent_rows_removed,
                                               total_unsent_rows = unsent_rows_before,
                                               total_failed_to_remove = failed_removal_count)

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

