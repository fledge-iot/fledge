"""
Date: June 2017
Description: The following piece of code is the written purge script,  with its main acting as a scheduler,  based on
    configurations. As of now,  all code is done using SQLAlchemy,  with JSON files storing both config,  and logged 
    information,  with the knowledge that once the actual scheduler and the database will be done,  then something else
    will be (potentially) used. 
"""
import datetime
import json
import os
import sqlalchemy
import sqlalchemy.dialects.postgresql
import sys
import time

# Set variables for connecting to database
user = "foglamp"
db_user = "foglamp"
host = "127.0.0.1"
db = "foglamp"

# Create Connection
engine = sqlalchemy.create_engine('postgres://%s:%s@%s/%s' % (db_user, user, host, db),  pool_size=20,  max_overflow=0)
conn = engine.connect()


# Important files
configFile = 'config.json'
logsFile = 'logs.json'

readings = sqlalchemy.Table('readings', sqlalchemy.MetaData(), 
      sqlalchemy.Column('id', sqlalchemy.BIGINT, primary_key=True),
      sqlalchemy.Column('asset_code', sqlalchemy.VARCHAR(50)),
      sqlalchemy.Column('read_key', sqlalchemy.dialects.postgresql.UUID,
                        default='00000000-0000-0000-0000-000000000000'),
      sqlalchemy.Column('reading', sqlalchemy.dialects.postgresql.JSON, default='{}'),
      sqlalchemy.Column('user_ts', sqlalchemy.TIMESTAMP(6), default=time.strftime('%Y-%m-%d %H:%M:%S',
                        time.localtime(time.time()))),
      sqlalchemy.Column('ts', sqlalchemy.TIMESTAMP(6),  default=time.strftime('%Y-%m-%d %H:%M:%S',
                        time.localtime(time.time()))))


"""
Methods that support the purge process. For the most part,  theses methods would be replaced by either a scheduler,  
Database tool,  and/or proper configuration methodology. 
"""


def convert_timestamp(set_time=None):
    """
    Convert "age" in config file to timedelta. If only an integer is specified,  then 
        the code assumes that it is already in minutes (ie age:1 means wait 1 minute) 
    Args:
        set_time: 
    Returns:
        timedelta based on age in config file
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


def convert_sleep(set_time=None):
    """
    Convert "wait time" in config file to seconds. If only an integer is specified,  then 
        the code assumes that it is already in seconds (ie wait:1 means wait 1 second) 
    Args:
        set_time: 

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


def get_count(stmt):
    """
    Imitate connection to Postgres and execute COUNT queries 
    Args:
        stmt: 
    Returns:
        COUNT value
    """
    try:
        result = conn.execute(stmt)
    except conn.Error as e:
        print(e)
        sys.exit()
    else:
        return int(result.fetchall()[0][0])


def execute_delete(stmt=None):
    """
    Imitate connection to Postgres and execute DELETE query
    Args:
        stmt: DELETE stmt 
    Returns:
        totalCount
        start
        end
    """

    try:
        conn.execute(stmt)
    except conn.Error as e:
        print(e)
        sys.exit()
    else:
        conn.execute("commit")

"""
The actual purge process 
"""


def purge(tableName=None,  configFile=None,  logsFile=None):
    """
    The actual purge process reads the configuration file,  and based off the information in it does the following: 
        1. Gets important COUNT information that will be stored in the database
        2. Call the DELETE command so that data will be purged
        3. Based on prior and post DELETE COUNTS,  calculate information to be logged 
        4. log information 
    Since the database layer is yet to be complete,  please consider the queries generated in this method as the basis
    for what the db layer needs to accomplish in order for purging to work. 
    Args:
        tableName
        configFile
        logsFile
    Returns:
        amount of time to wait until next execution (based on config.json)
    """

    # Reload config (JSON File) - age,  enabled,  wait,  pi_date
    with open(configFile, 'r') as conf:
        config = json.load(conf)

    data = {}
    purgeStatus = {}

    if os.path.getsize(logsFile) > 0:
        with open(logsFile,  'r') as f:
            data = json.load(f)

    if config['enabled'] is True:  # meaning that config info is authorizing the purge
        age_timestamp = datetime.datetime.strftime(datetime.datetime.now() - convert_timestamp(set_time=config['age']),
                                                   '%Y-%m-%d %H:%M:%S.%f')
        last_connection = datetime.datetime.strptime(config['lastConnection'],  '%Y-%m-%d %H:%M:%S')

        # Time that purge process begins (NOW) - the script will ignore everything after now for purging
        #   IE `start` will be executed as part of the WHERE condition(s) in all queries that fall under
        #   config['enabled'] == True.
        start = time.time()
        start = datetime.datetime.fromtimestamp(start).strftime('%Y-%m-%d %H:%M:%S')

        # Number of rows inserted until DELETE was called
        countQuery = sqlalchemy.select([sqlalchemy.func.count()]).select_from(readings).where(readings.c.ts < start)
        countBefore = get_count(countQuery)

        # Number of rows there were not sent to PI
        unsentQuery = sqlalchemy.select([sqlalchemy.func.count()]).select_from(readings).where(
            readings.c.ts <= last_connection)
        beforeUnsent = get_count(unsentQuery)

        # Enter this if statement iff DELETE is enabled
        if config['enabled'] is True:
            # If retainUnsent is True then delete the smaller of age_timestamp and last_connection
            #   Otherwise delete by age_timestamp
            if (config['retainUnsent'] is True) and \
                    (datetime.datetime.strptime(age_timestamp, '%Y-%m-%d %H:%M:%S.%f') > last_connection):
                # print('last_connection')
                deleteQuery = sqlalchemy.delete(tableName).where(tableName.c.ts <= last_connection).where(
                    tableName.c.id <= config['lastID'])
                execute_delete(stmt=deleteQuery)

            # All cases that do not fall under the IF statement uses age rather tha last_connection
            else:
                # print('age_timestamp')
                # DELETE all rows that are older (or equal) to the age_timestamp.
                #   DELETE FROM tableName WHERE ts <= age;
                deleteQuery = sqlalchemy.delete(tableName).where(tableName.c.ts <= age_timestamp).where(
                    tableName.c.id <= config['lastID'])
                execute_delete(stmt=deleteQuery)

        end = time.time()
        end = datetime.datetime.fromtimestamp(end).strftime('%Y-%m-%d %H:%M:%S')

        # Number of rows remain up to DELETE command
        countAfter = get_count(countQuery)

        # Add info to purgeStatus
        purgeStatus['startTime'] = start
        purgeStatus['complete'] = end

        # rowsRemoved: How many rows were removed
        purgeStatus['rowsRemoved'] = countBefore - countAfter

        # unsentRowsRemoved: How many rows that were not sent to PI were removed
        #   If config['retainUnsent'] is True,  then the value should be 0,  else it should be greater than 0
        afterUnsent = get_count(unsentQuery)
        purgeStatus['unsentRowsRemoved'] = beforeUnsent - afterUnsent

        # failedRemovals: How many rows that were expected to get removed weren't removed
        #   In cases where "config['retainUnsent']  is False and age_timestamp > last_connection" then failedRemovals
        #   is the number of rows remaining that are <=  age_timestamp,  in all other cases,  the expected is 0.
        if (config['retainUnsent'] is True) and \
                (datetime.datetime.strptime(age_timestamp,  '%Y-%m-%d %H:%M:%S.%f') > last_connection):
            failedToRemoveQuery = sqlalchemy.select([sqlalchemy.func.count()]).select_from(readings).where(
                readings.c.ts <= last_connection)
            purgeStatus['failedRemovals'] = get_count(failedToRemoveQuery)
        else:
            failedToRemoveQuery = sqlalchemy.select([sqlalchemy.func.count()]).select_from(readings).where(
                readings.c.ts <= age_timestamp)
            purgeStatus['failedRemovals'] = get_count(failedToRemoveQuery)

        # rowsRemaining: How many rows remain remain up-to the delete
        purgeStatus['rowsRemaining'] = countAfter

        # The purgeStatus dictionary is stored into a dictionary containing all other purge runs,  where the key is
        #   the `start` timestamp.
        data[start] = purgeStatus

        # Write to file
        f = open(logsFile,  'w')
        f.write(json.dumps(data))
        f.close()

    # Calculate how long to sleep fore before rerunning
    return convert_sleep(config['wait'])

"""
The main,  which would be replaced by the scheduler 
"""
if __name__ == '__main__':
    """
    The main / scheduler creates the logs.json file,  and executes the purge (returning how long to wait)
    till the next purge execution. Noticed that the purge process expects the table,  and config file. 
    This is because (theoretically) purge  would be executed on multiple tables,  where each table could 
    have its own configs. 
        
    As of now,  the example shows only 1 table,  but can be rewritten to show multiple tables without too much
    work. 
    """

    open(logsFile,  'w').close()

    while True:
        wait = purge(tableName=readings, configFile=configFile,  logsFile=logsFile)
        time.sleep(wait)

