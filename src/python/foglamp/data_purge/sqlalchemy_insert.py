"""
Date: June 21 2017 
Description: The following is the CREATE table and INSERT into table using SQLAlchemy
            It is intended to be used for when showing how purge (currently) works example. 
Lanague: Python + SQLAlchemy
"""
import sys
import sqlalchemy
import sqlalchemy.dialects
import time

# Set variables for connecting to database
user="foglamp"
db_user="foglamp"
host="127.0.0.1"
db="foglamp"

# Create Connection
engine = sqlalchemy.create_engine('postgres://%s:%s@%s/%s' % (db_user,user,host,db), pool_size=20, max_overflow=0)
conn = engine.connect()

# Important files
configFile = 'config.json'
logsFile = 'logs.json'

readings = sqlalchemy.Table('readings',sqlalchemy.MetaData(),
        sqlalchemy.Column('id',sqlalchemy.BIGINT,primary_key=True),
        sqlalchemy.Column('asset_code',sqlalchemy.VARCHAR(50)),
        sqlalchemy.Column('read_key',sqlalchemy.dialects.postgresql.UUID, default='00000000-0000-0000-0000-000000000000'),
        sqlalchemy.Column('reading',sqlalchemy.dialects.postgresql.JSON,default='{}'),
        sqlalchemy.Column('user_ts',sqlalchemy.TIMESTAMP(6),default=time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))),
        sqlalchemy.Column('ts',sqlalchemy.TIMESTAMP(6), default=time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))))



def execute_query(stmt):
    """
    EXECUTE query 
    Args:
        stmt: 
    Returns:
        largest ID
    """
    try:
        result = conn.execute(stmt)
    except:
        print("SELECT Error")
        sys.exit()
    else:
        result = result.fetchall()[0][0]

    if result is None:
        return 0
    return int(result)

i= execute_query(("SELECT MAX(%s) FROM %s;" % (readings.c.id,readings)))

while True:
    stmt = readings.insert().values(id=i)
    try:
        conn.execute(stmt)
    except:
        print("INSERT Error")
        sys.exit()
    i+=1


