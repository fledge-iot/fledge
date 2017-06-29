"""
Date: June 2017
Description: The __init__.py can be used in one of two ways: 
        1. Declare all imports that'll be used in directory
        2. Declare global variables
Given that the connection, json objects are something that is used throughout, 
the __init__.py file provides the latter of the two. 
"""
import sqlalchemy

# Set variables as needed (specifically `host`)
user="foglamp"
db_user="foglamp"
host="192.168.0.182"
db="foglamp"

# Important files
configFile = 'config.json'
logsFile = 'logs.json'

# Create Connection
engine = sqlalchemy.create_engine('postgres://%s:%s@%s/%s' % (db_user,user,host,db), pool_size=20, max_overflow=0)
conn = engine.connect()

# table being used
t1 = sqlalchemy.Table('t1',sqlalchemy.MetaData(),
        sqlalchemy.Column('id',sqlalchemy.INTEGER,primary_key=True),
        sqlalchemy.Column('ts',sqlalchemy.TIMESTAMP,default=sqlalchemy.func.now()))