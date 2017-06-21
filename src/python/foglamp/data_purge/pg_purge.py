"""
Date: June 2017
Description: The following is a simple purger application that not only call execution of deletes, but 
    also verifies  data was dropped. Since this component is somewhere between the Scheduler, and Database 
    I there are extra methods imitating those. Secondly, since (to me) it is still not clear where 
    data would be stored, 
Lanague: Python + SQLAlchemy
"""
import datetime
import psycopg2
import sqlalchemy
import sys
import time
import yaml

# t1 = sqlalchemy.Table('t1',sqlalchemy.MetaData(),
#         sqlalchemy.Column('id',sqlalchemy.INTEGER,primary_key=True),
#         sqlalchemy.Column('ts',sqlalchemy.TIMESTAMP))
#
engine = psycopg2.connect(host='192.168.0.182',port='5432',user='foglamp',password='foglamp',dbname='foglamp')
cur = engine.cursor()

open('logs.db','w').close()

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
    Returns:
        amount of time to wait until next excution (based on config.yaml)
    """
    # Reald config (yaml File)
    with open('config.yaml','r') as conf:
        config = yaml.load(conf)
    set_time=config['age']

    # Prepare Query stmts
    timestamp = datetime.datetime.strftime(datetime.datetime.now() - conver_timestamp(set_time=set_time),'%Y-%m-%d %H:%M:%S')

    delete = "DELETE from t1 WHERE ts <= %s" % timestamp
    # Rows count up to timestamp
    count1 = "SELECT COUNT(*) FROM t1 WHERE ts <= %s" % timestamp
    # Row count after TIMESTAMP
    count2 = "SELECT COUNT(*) FROM t1 WHERE ts > %s" % timestamp

    # Timestamp of execution
    timestamp = time.time()
    timestamp = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

    # Call query execution
    lthen=get_count(count1)
    database_manage(delete)
    verify=get_count(count1) # Expect 0 each time
    remainder = get_count(count2)

    # Write to log
    f.write('%s\t%s\t\t%s\t%s\n' % (timestamp,lthen,verify,remainder))
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
        result = cur.execute(stmt)
    except cur.Error as e:
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
    try:
        cur.execute(stmt)
    except cur.Error as e:
        print(e)
        sys.exit()
    else:
        cur.execute("commit")

if __name__ == '__main__':
    """The main, which in part also acts a scheduler"""
    f = open('logs.db', 'a')
    f.write('%s\t\t%s\t%s\t%s\n' % ('TIMESTAMP','Total Removed', 'Verify','Reminder'))
    f.close()
    # Imitate scheduler
    while True:
        f = open('logs.db', 'a')
        wait=purge()
        f.close()
        time.sleep(wait)



