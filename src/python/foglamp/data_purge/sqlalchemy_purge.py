"""
Date: June 2017
Description: The following piece of code is the written purge script, with its main acting as a scheduler, based on
    configurations. As of now, all code is done using SQLAlchemy, with JSON files storing both config, and logged 
    information, with the knowledge that once the actual scheduler and the database will be done, then something else
    will be (potentially) used. 
"""
import datetime
import json
import os
import sys
import time

from __init__ import engine, conn, t1, configFile, logsFile



def conver_timestamp(set_time=None):
    """
    Convert "age" in config file to timedelta. If only an integer is specified, then 
        the code assumes that it is already in minutes (ie age:1 means wait 1 minute) 
    Args:
        set_time: 
    Returns:
        timedelta based on age in config file
    """
    if set_time.isdigit():
        return datetime.timedelta(minutes=int(set_time))
    time_dict={}
    tmp=0

    for value in set_time.split(" "):
        if value.isdigit() is True:
            tmp=int(value)
        else:
            time_dict[value] = tmp

    sec = datetime.timedelta(seconds=0)
    min = datetime.timedelta(minutes=0)
    hr  = datetime.timedelta(hours=0)
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
    Convert "wait time" in config file to seconds. If only an integer is specified, then 
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

def purge(tableName=None, configFile=None, logsFile=None):
    """
    The actual purge process reads the configuration file, and based off the information in it does the following: 
        1. Gets important COUNT information that will be stored in the database
        2. Call the DELETE command so that data will be purged
        3. Based on prior and post DELETE COUNTS, calculate information to be logged 
        4. log information 
    Since the database layer is yet to be complete, please consider the queries generated in this method as the basis
    for what the db layer needs to accomplish in order for purging to work. 
    Args:
        tableName
        configFile
        logsFile
    Returns:
        amount of time to wait until next execution (based on config.yaml)
    """

    # Reload config (JSON File) - age, enabled, wait, pi_date
    with open(configFile,'r') as conf:
        config=json.load(conf)

    data = {}
    purgeStatus = {}

    if os.path.getsize("logs.json") > 0:
        with open('logs.json', 'r') as f:
            data=json.load(f)

    if config['enabled'] is True: # meaning that config info is authorizing the purge
        age_timestamp = datetime.datetime.strftime(datetime.datetime.now() - conver_timestamp(set_time=config['age']),'%Y-%m-%d %H:%M:%S')
        print(config['lastConnection'])
        last_connection = datetime.datetime.strptime(config['lastConnection'], '%Y-%m-%d %H:%M:%S')

        # Time that purge process begins (NOW) - the script will ignore everything after now for purging
        start = time.time()
        start = datetime.datetime.fromtimestamp(start).strftime('%Y-%m-%d %H:%M:%S.%s')

        # totalCount: Number of rows up to DELETE
        #   SELECT COUNT(*) FROM tableName WHERE ts <= start;
        totalCountQuery = sqlalchemy.select([sqlalchemy.func.count()]).select_from(tableName).where(tableName.c.ts <= start)
        totalCount = get_count(totalCountQuery)

        # expectDELETE: Number of rows expected to get deleted
        #   SELECT COUNT(*) FROM tableName WHERE ts <= age AND ts <= start;
        expectDeleteQuery = sqlalchemy.select([sqlalchemy.func.count()]).select_from(tableName).where(tableName.c.ts <= age_timestamp).where(tableName.c.ts <= start)
        expectDelete = get_count(expectDeleteQuery)

        # unsentExpect: Number of unsent rows that are expected to get DELETE
        #   SELECT COUNT(*) FROM tableName WHERE ts <= age AND ts > lastConnection AND ts <= start;
        unsentExpectQuery = sqlalchemy.select([sqlalchemy.func.count()]).select_from(tableName).where(tableName.c.ts <= age_timestamp).where(tableName.c.ts > last_connection).where(tableName.c.ts <= start)
        unsentExpect = get_count(unsentExpectQuery)

        # Delete information that is older than age_timestamp ignoring the last time Pi was connected
        if config['retainUnsent'] is False:
            # DELETE all rows that are older (or equal) to the age_timestamp.
            #   DELETE FROM tableName WHERE ts <= age;
            deleteQuery = sqlalchemy.delete(tableName).where(tableName.c.ts <= age_timestamp).where(tableName.c.ts <= start)
            execute_delete(stmt=deleteQuery)

        # Delete information that is older than both age_timestamp and last_connection date
        elif config['retainUnsent'] is True:
            # DELETE all rows that re older (or equal) to age_timestamp, and have been already added to the Pi System
            #   DELETE FROM tableName WHERE ts <= age AND ts < lastConnection;
            deleteQuery = sqlalchemy.delete(tableName).where(tableName.c.ts <= age_timestamp).where(tableName.c.ts < last_connection).where(tableName.c.ts <= start)
            execute_delete(stmt=deleteQuery)

        # Time when DELETE finished executing
        end = time.time()
        end = datetime.datetime.fromtimestamp(end).strftime('%Y-%m-%d %H:%M:%S.%s')

        # remainingTotal - Number of rows remaining up to the DELETE
        #   SELECT COUNT(*) FROM tableName WHERE ts <= start;
        remainingTotalQuery = sqlalchemy.select([sqlalchemy.func.count()]).select_from(tableName).where(tableName.c.ts <= start)
        remainingTotal = get_count(remainingTotalQuery)

        # notRemoved: Numbers of rows that were not removed, but were expected to
        #   SELECT COUNT(*) FROM tableName WHERE ts <= age AND ts <= start;
        # If config['retainUnsent'] is False then expect 0, else expect expectDelete - unsentExpect
        notRemovedQuery =  sqlalchemy.select([sqlalchemy.func.count()]).select_from(tableName).where(tableName.c.ts <= age_timestamp).where(tableName.c.ts <= start)
        notRemoved = get_count(notRemovedQuery)

        # unsentNotRemovedExpect: Number of rows that were not sent to PI were expected to get DELETED, but were not.
        #   SELECT COUNT(*) FROM tableName WHERE ts <= age AND ts > lastConnection AND ts <= start
        # If config['retainUnsent'] is False then expect 0, else expect unsentNotRemovedExpect == unsentExpect
        unsentNotRemovedExpectQuery = sqlalchemy.select([sqlalchemy.func.count()]).select_from(tableName).where(tableName.c.ts <= age_timestamp).where(tableName.c.ts > last_connection).where(tableName.c.ts <= start)
        unsentNotRemovedExpect = get_count(unsentNotRemovedExpectQuery)


        # Add info to purgeStatus
        purgeStatus['startTime'] = start
        purgeStatus['complete'] = end





        # rowsRemoved: How many rows were removed
        purgeStatus['rowsRemoved'] = totalCount - remainingTotal

        # unsentRowsRemoved: How many rows that were not sent to PI were removed
        #   If config['retainUnsent'] is True, then the value should be 0, else it should be greater than 0
        purgeStatus['unsentRowsRemoved'] = unsentExpect - unsentNotRemovedExpect

        # failedRemovals: How many rows that were expected to get removed weren't removed
        #   Unless there was some disconnection during the DELETE, this value should always return 0
        purgeStatus['failedRemoval'] = notRemoved

        # rowsRemaining: How many rows remain remain up-to the delete
        purgeStatus['rowsRemain'] = remainingTotal

        data[start] = purgeStatus

    # Write as JSON object.
    f = open('logs.json','w')
    f.write(json.dumps(data))
    f.close()
    return convert_sleep(config['wait'])

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
        tableName: 
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

if __name__ == '__main__':
    """
    The main / scheduler creates the logs.json file, and executes the purge (returning how long to wait)
    till the next purge execution. Noticed that the purge process expects the table, and config file. 
    This is because (theoretically) purge  would be executed on multiple tables, where each table could 
    have its own configs. 
        
    As of now, the example shows only 1 table, but can be rewritten to show multiple tables without too much
    work. 
    """

    open(logsFile, 'w').close()
    while True:
        wait=purge(tableName=t1,configFile=configFile, logsFile=logsFile)
        time.sleep(wait)
