"""
Description: Based on FOGL-200 (https://docs.google.com/document/d/1GdMTerNq_-XQuAY0FJNQm09nbYQSjZudKJhY8x5Dq8c/edit) 
    the purge process is suppose to remove data based on either a user_id, or an X amount of time back depending on
    whether or not the configuration (config.json) reuqires to retain data that has not been sent to the Pi System.
    
    Given that the code is dependent on configuration files, sending data to Pi, and connecting to the database, 
    I have "hard-coded" those dependencies with the use of extra methods, and files. This includes things like: 
    get_nth_id which updates the config file with a 'random' last ID that was sent to Pi, and the main which also 
    as a scheduler process. 
    
     Specifically the purge process (purge_process_function) does the following: 
     - Based on the configuration file (retainUnsent) it either removes by the lastID 
        (in which case retainUnsent is True), or by age (timestamp)
     - Calculate vital information regarding the purge, and record it in the logs file
      
Based on the way things are currently being done, both the logs file (logs.json), and configurations file (config.json)
will be replaced either databse tables, or some other kind of file. 
"""
import datetime
import json
import os
import random
import sqlalchemy
import sqlalchemy.dialects.postgresql
import sys
import time


__author__ = "Ori Shadmon"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "2"


# Set variables for connecting to database
user = "foglamp"
db_user = "foglamp"
host = "127.0.0.1"
db = "foglamp"

# Create Connection
engine = sqlalchemy.create_engine('postgres://%s:%s@%s/%s' % (db_user, user, host, db),  pool_size=20,  max_overflow=0)
conn = engine.connect()

# Important files
config_file = 'config.json'
logs_file = 'logs.json'


# Table purge against
readings_table = sqlalchemy.Table('readings', sqlalchemy.MetaData(), 
      sqlalchemy.Column('id', sqlalchemy.BIGINT, primary_key=True),
      sqlalchemy.Column('asset_code', sqlalchemy.VARCHAR(50)),
      sqlalchemy.Column('read_key', sqlalchemy.dialects.postgresql.UUID,
                        default='00000000-0000-0000-0000-000000000000'),
      sqlalchemy.Column('reading', sqlalchemy.dialects.postgresql.JSON, default='{}'),
      sqlalchemy.Column('user_ts', sqlalchemy.TIMESTAMP(6), default=time.strftime('%Y-%m-%d %H:%M:%S',
                        time.localtime(time.time()))),
      sqlalchemy.Column('ts', sqlalchemy.TIMESTAMP(6),  default=time.strftime('%Y-%m-%d %H:%M:%S',
                        time.localtime(time.time()))))


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
    if set_time.isdigit():
        return datetime.timedelta(minutes=int(set_time))
    time_dict = {}
    tmp = 0

    for value in set_time.split(" "):
        if value.isdigit() is True:
            tmp = int(value)
        else:
            time_dict[value] = tmp

    sec = datetime.timedelta(seconds=0)
    min = datetime.timedelta(minutes=0)
    hr = datetime.timedelta(hours=0)
    day = datetime.timedelta(days=0)

    for key in time_dict.keys():
        if 'sec' in key:
            sec = datetime.timedelta(seconds=time_dict[key])
        elif 'min' in key:
            min = datetime.timedelta(minutes=time_dict[key])
        elif ('hr' in key) or ('hour' in key):
            hr = datetime.timedelta(hours=time_dict[key])
        elif ('day' in key) or ('dy' in key):
            day = datetime.timedelta(days=time_dict[key])
    return sec+min+hr+day


def convert_sleep(set_time: str) -> int:
    """Convert "wait" in config file to seconds in order to know how long to wait until next purge process. 
        This method would potentially be replaced by the scheduler 
    Args:
        set_time (str): A string of "values" specified in the config to declare how long to wait till next purge

    Returns:
        integer (of seconds) based on wait in config 
    """
    if set_time.isdigit():
        return int(set_time)
    time_dict = {}
    tmp = 0
    for value in set_time.split(" "):
        if value.isdigit() is True:
            tmp = int(value)
        else:
            time_dict[value] = tmp
    sec = 0
    min = 0
    hr = 0
    dy = 0
    for key in time_dict:
        if "sec" in key:
            sec = time_dict[key]
        elif "min" in key:
            min = 60 * time_dict[key]
        elif ("hour" in key) or ("hr" in key):
            hr = 60 * 60 * time_dict[key]
        elif ("day" in key) or ("dy" in key):
            dy = 60 * 60 * 24 * time_dict[key]
        else:
            print("Error: Invalid Value(s) in config file")
            sys.exit()
    return sec+min+hr+dy


def get_count(stmt: str) -> int:
    """Immititate connection  to psql that returns result.
    
    Since all queries return either an ID (integer) or COUNT (integer) the expected 
    return value is also an integer. 
    
    Args:
        stmt (str): generated SQL query   
    Returns:
        Integer value result of SQL query
    """
    try:
        query_result = conn.execute(stmt)
    except conn.Error as e:
        print(e)
        sys.exit()
    else:
        return int(query_result.fetchall()[0][0])


def execute_delete(stmt: str) -> None:
    """Imitate connection to Postgres and execute DELETE query
    Args:
        stmt (str): DELETE stmt 
    Returns: 
        The method doesn't return anything
    """

    try:
        conn.execute(stmt)
    except conn.Error as e:
        print(e)
        sys.exit()
    else:
        conn.execute("commit")


def get_nth_id() -> None:
    """Update the config file to have row ID somewhere within the oldest 100 rows.
    
    This method would potentially be replaced by the communication with the Pi System which will be
    aware of what was the last ID sent to the Pi System. 
    Returns: 
        Method doesn't return anything
    """
    rand = random.randint(1, 100)

    stmt = "SELECT id FROM (SELECT id FROM readings ORDER BY id ASC LIMIT %s)t ORDER BY id DESC LIMIT 1"
    row_id = get_count(stmt % rand)

    with open(config_file, 'r') as conf:
        config_info = json.load(conf)

    config_info["lastID"] = row_id
    open(config_file, 'w').close()
    with open(config_file, 'r+') as conf:
        conf.write(json.dumps(config_info))

"""The actual purge process 
"""


def purge_process_function(tableName,  config_file,  logs_file) -> int:
    """The actual process read the configuration file, and based off the information in it does the following:
    1. Gets previous information found in log file
    2. Based on the configurations, call the DELETE command to purge the data
    3. Calculate relevant information kept in logs
    4. Based on the configuration calculates how long to wait until next purge, and returns that
    
    Args: 
        tableName (sqlalchemy.Table): The name of the table queries run against
        config_file (file): Name of file containing configuration 
        logs_file (file): Name of file containing the logs
    Returns: 
        Amount of time until next purge process
    """

    # Reload config (JSON File) - age,  enabled,  wait,  pi_date
    with open(config_file, 'r') as conf:
        config = json.load(conf)

    data = {}
    purgeStatus = {}

    if os.path.getsize(logs_file) > 0:
        with open(logs_file,  'r') as f:
            data = json.load(f)


    if config['enabled'] is True:  # meaning that config info is authorizing the purge
        age_timestamp = datetime.datetime.strftime(datetime.datetime.now() - convert_timestamp(set_time=config['age']),
                                                   '%Y-%m-%d %H:%M:%S.%f')
        with open(config_file) as json_data:
            last_connection_id = json.load(json_data)['lastID']

        # Time purge process starts
        purgeStatus['startTime'] = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')

        # Number of rows exist at the point of calling purge
        totalCountBefore = get_count(sqlalchemy.select([sqlalchemy.func.count()]).select_from(tableName).where(tableName.c.ts < purgeStatus['startTime']))

        # Number of unsent rows
        unsentRowsQuery = sqlalchemy.select([sqlalchemy.func.count()]).select_from(tableName).where(tableName.c.id > last_connection_id).where(tableName.c.ts <= age_timestamp).where(tableName.c.ts < purgeStatus['startTime'])
        unsentRowsBefore = get_count(unsentRowsQuery)
        # If unsent data is retained, then the WHERE condition is against the last sent ID
        if config['retainUnsent'] is True:
            deleteQuery = sqlalchemy.delete(tableName).where(tableName.c.id <= last_connection_id).where(tableName.c.ts < purgeStatus['startTime'])
            execute_delete(deleteQuery)

            # Number of rows that were expected to get removed, but weren't
            purgeStatus['failedRemovals'] = get_count(sqlalchemy.select([sqlalchemy.func.count()]).select_from(tableName).where(tableName.c.id <= last_connection_id).where(tableName.c.ts < purgeStatus['startTime']))
        # If unsent data is not retained, then the WHERE condition is against the age
        else:
            id = get_count(sqlalchemy.select([tableName.c.id]).select_from(tableName).where(tableName.c.ts <= age_timestamp).order_by(tableName.c.id.desc()).limit(1))

            deleteQuery = sqlalchemy.delete(tableName).where(tableName.c.id <= id).where(tableName.c.ts < purgeStatus['startTime'])
            execute_delete(deleteQuery)

            # Number of rows that were expected to get removed, but weren't
            purgeStatus['failedRemovals'] = get_count(sqlalchemy.select([sqlalchemy.func.count()]).select_from(tableName).where(tableName.c.ts <= age_timestamp).where(tableName.c.ts < purgeStatus['startTime']))

        totalCountAfter = get_count(sqlalchemy.select([sqlalchemy.func.count()]).select_from(tableName).where(tableName.c.ts < purgeStatus['startTime']))
        purgeStatus['rowsRemoved'] = totalCountBefore - totalCountAfter

        # Number of unsent rows removed
        purgeStatus['unsentRowsRemoved'] = unsentRowsBefore - get_count(unsentRowsQuery)
        # Time  purge process finished
        purgeStatus['complete'] = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')


        # The purgeStatus dictionary is stored into a dictionary containing all other purge runs,  where the key is
        #   the `start` timestamp.
        data[purgeStatus['startTime']] = purgeStatus

    # Write to file
    f = open(logs_file, 'w')
    f.write(json.dumps(data))
    f.close()

    return convert_sleep(config['wait'])

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

    open(logs_file,  'w').close()

    while True:
        get_nth_id()
        wait = purge(tableName=readings_table, config_file=config_file,  logs_file=logs_file)
        time.sleep(wait)

