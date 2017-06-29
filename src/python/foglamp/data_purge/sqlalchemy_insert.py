"""
Date: June 21 2017 
Description: The following is the CREATE table and INSERT into table using SQLAlchemy
            It is intended to be used for when showing how purge (currently) works example. 
Lanague: Python + SQLAlchemy
"""
import sys
from __init__ import engine, conn, t1


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


