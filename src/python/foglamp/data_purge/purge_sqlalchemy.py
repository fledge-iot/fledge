import datetime
import sqlalchemy
import sys
import time
import yaml

t1 = sqlalchemy.Table('t1',sqlalchemy.MetaData(),
        sqlalchemy.Column('value',sqlalchemy.INTEGER,primary_key=True),
        sqlalchemy.Column('ts',sqlalchemy.TIMESTAMP))

engine = sqlalchemy.create_engine('postgres://foglamp:foglamp@192.168.0.182/foglamp')
conn = engine.connect()

def conver_timestamp(set_time=None):
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
    with open('config.yaml','r') as conf:
        config = yaml.load(conf)
    set_time=config['delete']
    timestamp = datetime.datetime.strftime(datetime.datetime.now() - conver_timestamp(set_time=set_time),'%Y-%m-%d %H:%M:%S')
    stmt = t1.delete().where(t1.c.ts <= timestamp)
    stmt = stmt.compile(compile_kwargs={"literal_binds": True})

    if config['no_pi_delete'] is True: # If we don't care about when PI was last connected then delete
        database_manage(stmt)
    elif datetime.datetime.strptime(timestamp,'%Y-%m-%d %H:%M:%S') < config['last_pi_connection']:
        database_manage(stmt)
    else:
        print("No DELETES")
    time.sleep(5)

def database_manage(stmt=""):
    """Imitate connection to Postgres """
    stmt = "SELECT COUNT(*) FROM t1"
    try:
        result = conn.execute(stmt)
    except conn.Error as e:
        print(e)
        sys.exit()
    else:
        print("before "+str(result.fetchall()[0][0]))

    try:
        conn.execute(stmt)
    except conn.Error as e:
        print(e)
        sys.exit()
    else:
        conn.execute("commit")


    try:
        result = conn.execute(stmt)
    except conn.Error as e:
        print(e)
        sys.exit()
    else:
        print("after  " + str(result.fetchall()[0][0]))

if __name__ == '__main__':
    # Imitate scheduler
    while True:
        purge()
        time.sleep(5)

