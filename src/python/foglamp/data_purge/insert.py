import sqlalchemy
import time
import datetime
def insert():
   engine = sqlalchemy.create_engine('postgres://foglamp:foglamp@192.168.0.182/foglamp')
   conn = engine.connect()
   i=20000001
   while True:
     ts = time.time()
     st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
     stmt=("INSERT INTO t1 VALUES(%s,'%s');" % (i,st))
     try:
        conn.execute(stmt)
     except conn.Error as e:
        print(e)
        sys.exit()
     i+=1

if __name__ == '__main__':
   insert()

