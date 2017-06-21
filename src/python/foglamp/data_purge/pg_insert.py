"""
Date: June 21 2017 
Description: The following is the CREATE table and INSERT into table using SQLAlchemy
            It is intended to be used for when showing how purge (currently) works example. 
Lanague: Python + pg connector
"""

import psycopg2
import sys

# Prepare engine connection
engine = psycopg2.connect(host='192.168.0.182',port='5432',user='foglamp',password='foglamp',dbname='foglamp')
cur = engine.cursor()

# CREATE table
try:
    cur.execute('DROP TABLE IF EXISTS t1;')
except cur.Error as e:
    print(e)
    sys.exit()
try:
    cur.execute("""CREATE TABLE t1(
            id INTEGER NOT NULL DEFAULT 1,
            ts TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(id)
            );""")
except:
    print("Error")
    sys.exit()
print("Insert Start")
# # Execute Inserts
i=1
while True:
    try:
        cur.execute("INSERT INTO t1(id) VALUES (%s);" % i)
    except cur.Error as e:
        print(e)
        sys.exit()
    i+=1
    print(i)

