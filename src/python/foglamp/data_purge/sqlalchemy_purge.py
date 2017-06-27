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
import yaml


t1 = sqlalchemy.Table('t1',sqlalchemy.MetaData(),
        sqlalchemy.Column('id',sqlalchemy.INTEGER,primary_key=True),
        sqlalchemy.Column('ts',sqlalchemy.TIMESTAMP))

engine = sqlalchemy.create_engine('postgres://foglamp:foglamp@192.168.0.182/foglamp')
conn = engine.connect()

def conver_timestamp(set_time=None):
    """
    Convert the information provided by config.yaml, to an actual timedelta format
    Args:
        set_time: 

    Returns:

    """
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

def purge():
    """
        Actual Purge process
    The numbers are roughly calculated because INSERTS are consistently running as other processes 
    are being executed. 
    Returns:
        amount of time to wait until next execution (based on config.yaml)
    """

    # Reald config (YAML File) - age, enabled, wait, date
    with open('config.yaml','r') as conf:
        config = yaml.load(conf)
    age_timestamp = datetime.datetime.strftime(datetime.datetime.now() - conver_timestamp(set_time=config['age']),'%Y-%m-%d %H:%M:%S')
    data = {}
    if os.path.getsize("logs.json") > 0:

        with open('logs.json', 'r') as f:
            data=json.load(f)

    if config['enabled'] is True: # If it's enabled
        purgeStatus = {}

        # unsentRowsRemoved: How many rows that were not sent to PI were removed
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
        start, end = database_manage(delete)

        # failedRemovals: How many rows that were expected to get removed weren't removed
        query = sqlalchemy.select([sqlalchemy.func.count('*')]).select_from(t1).where(t1.c.ts <= age_timestamp)
        failedRemovals = get_count(query)

        # rowsRemaining: How many rows remain remain up-to the delete
        query = sqlalchemy.select([sqlalchemy.func.count('*')]).select_from(t1).where(t1.c.ts <= start)
        rowsRemaining = get_count(query)

        # rowsRemoved: How many rows were removed
        rowsRemoved = totalCount - rowsRemaining



        purgeStatus['Start Time'] = start
        purgeStatus['Complete Time'] = end
        purgeStatus['Rows Remaining'] = rowsRemaining
        purgeStatus['Rows Removed'] = rowsRemoved
        purgeStatus['Expected Removed'] = expectRemoved
        purgeStatus['Failed Remove'] = failedRemovals
        purgeStatus['Unsent Removed Rows'] = unsentRowsRemoved

        data[start]=purgeStatus
        f = open('logs.json', 'w')
        f.write(json.dumps(data))
        f.close()

    return config['wait']

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



