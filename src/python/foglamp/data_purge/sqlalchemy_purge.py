"""
Date: June 2017
Description: The following is a simple purger application that not only call execution of deletes, but 
    also verifies  data was dropped. Since this component is somewhere between the Scheduler, and Database 
    I there are extra methods imitating those. Secondly, since (to me) it is still not clear where 
    data would be stored, 
Lanague: Python + SQLAlchemy

The focus of the code is the purge() method. Beyond that, everything else is extra stuff to show 
"""
import datetime
import json
import os
import sqlalchemy
import sys
import time


t1 = sqlalchemy.Table('t1',sqlalchemy.MetaData(),
        sqlalchemy.Column('id',sqlalchemy.INTEGER,primary_key=True),
        sqlalchemy.Column('ts',sqlalchemy.TIMESTAMP))

engine = sqlalchemy.create_engine('postgres://foglamp:foglamp@192.168.0.182/foglamp')
conn = engine.connect()

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

def purge():
    """
    The actual process for purging data. The numbers being retrieved, and stored to file can be considered
    "close" estimates becuase the database is always having rows inserted into it. The only way to get real
    values is if data is not being inserted, which is not possible to do given the type of enviornment delt 
    with. 

    Returns:
        amount of time to wait until next execution (based on config.yaml)
    """

    # Reald config (JSON File) - age, enabled, wait, date
    with open('config.json','r') as conf:
        config = json.load(conf)

    age_timestamp = datetime.datetime.strftime(datetime.datetime.now() - conver_timestamp(set_time=config['age']),'%Y-%m-%d %H:%M:%S')

    data = {}
    if os.path.getsize("logs.json") > 0:
        with open('logs.json', 'r') as f:
            data=json.load(f)

    if config['enabled'] is True: # Execute purge process if enabled
        purgeStatus = {}

        start = time.time()
        start = datetime.datetime.fromtimestamp(start).strftime('%Y-%m-%d %H:%M:%S.%s')

        # unsentRowsRemoved: How many rows that were not sent to PI were removed
        unsentRowsRemoved = 0
        if age_timestamp > str(config['pi_date']):
            query = sqlalchemy.select([sqlalchemy.func.count('*')]).select_from(t1).where(t1.c.ts <= age_timestamp).where(t1.c.ts >= str(config['pi_date']))
            unsentRowsRemoved=get_count(query)

        # Number of rows expected to get removed
        query = sqlalchemy.select([sqlalchemy.func.count('*')]).select_from(t1).where(t1.c.ts <= age_timestamp)
        expectRemoved = get_count(query)

        # Total Count
        query = sqlalchemy.select([sqlalchemy.func.count('*')]).select_from(t1)
        totalCount = get_count(query)

        # Execute DELETE stmt
        delete = t1.delete().where(t1.c.ts <= age_timestamp)
        database_manage(delete)

        # failedRemovals: How many rows that were expected to get removed weren't removed
        query = sqlalchemy.select([sqlalchemy.func.count('*')]).select_from(t1).where(t1.c.ts <= age_timestamp)
        failedRemovals = get_count(query)

        # rowsRemaining: How many rows remain remain up-to the delete
        query = sqlalchemy.select([sqlalchemy.func.count('*')]).select_from(t1).where(t1.c.ts <= start)
        rowsRemaining = get_count(query)

        # rowsRemoved: How many rows were removed
        rowsRemoved = totalCount - rowsRemaining

        end = time.time()
        end = datetime.datetime.fromtimestamp(end).strftime('%Y-%m-%d %H:%M:%S.%s')

        # Set data into table.
        purgeStatus['Start Time'] = start
        purgeStatus['Complete Time'] = end
        purgeStatus['Rows Remaining'] = rowsRemaining
        purgeStatus['Rows Removed'] = rowsRemoved
        purgeStatus['Expected Removed'] = expectRemoved
        purgeStatus['Failed Remove'] = failedRemovals
        purgeStatus['Unsent Removed Rows'] = unsentRowsRemoved

        data[start]=purgeStatus # Each new set of values is "saved" under its initial time.
        f = open('logs.json', 'w')
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

def database_manage(stmt=""):
    """
    Imitate connection to Postgres and execute INSERT query
    Args:
        stmt: 
    """
    start = time.time()
    start = datetime.datetime.fromtimestamp(start).strftime('%Y-%m-%d %H:%M:%S.%s')
    try:
        conn.execute(stmt)
    except conn.Error as e:
        print(e)
        sys.exit()
    else:
        conn.execute("commit")
    end = time.time()
    end = datetime.datetime.fromtimestamp(end).strftime('%Y-%m-%d %H:%M:%S.%s')

    return start, end

if __name__ == '__main__':
    """The main, which in part also acts a schedul"""
    open('logs.json', 'w').close()

    while True:
        wait=purge()
        time.sleep(wait)



