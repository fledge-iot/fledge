"""
Date: June 21 2017 
Description: The following is the CREATE table and INSERT into table using SQLAlchemy
            It is intended to be used for when showing how purge (currently) works example. 
Lanague: Python + SQLAlchemy
"""
import sqlalchemy
import sys
import time
import datetime

# Prepare engine connection
engine = sqlalchemy.create_engine('postgres://foglamp:foglamp@192.168.0.182/foglamp')
conn = engine.connect()
t1 = sqlalchemy.Table('t1',sqlalchemy.MetaData(),
        sqlalchemy.Column('id',sqlalchemy.INTEGER,primary_key=True),
        sqlalchemy.Column('ts',sqlalchemy.TIMESTAMP,default=sqlalchemy.func.now()))

# CREATE table
try:
    t1.drop(engine)
except:
    print("Error")
    sys.exit()
try:
    t1.create(engine)
except:
    print("Error")
    sys.exit()

# Execute Inserts
i=1

while True:
    stmt = t1.insert().values(id=i)
    try:
        conn.execute(stmt)
    except conn.Error as e:
        print(e)
        sys.exit()
    i+=1


