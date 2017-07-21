"""
The following piece of code takes the information found in the statistics table, and stores it's delta value 
(statistics.value - statistics.prev_val) inside the statistics_history table. To complete this, SQLAlchemy will be used 
to execute SELECT statements against statistics, and INSERT against the statistics_history table. 
"""
import sqlalchemy
import time
import random

__author__ = "Ori Shadmon"
__copyright__ = "Copyright (c) 2017 OSI Soft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


# Set variables for connecting to database
_db_type = "postgres"
_user = "foglamp"
_db_user = "foglamp"
_host = "10.0.0.179"
_db = "foglamp"

# Create Connection
_ENGINE = sqlalchemy.create_engine('%s://%s:%s@%s/%s' % (_db_type, _db_user, _user, _host, _db),  pool_size=20,
                                   max_overflow=0)
_CONN = _ENGINE.connect()
# Deceleration of tables in SQLAlchemy format
_STATS_TABLE = sqlalchemy.Table('statistics', sqlalchemy.MetaData(),
                                sqlalchemy.Column('key', sqlalchemy.CHAR(10), primary_key=True),
                                sqlalchemy.Column('description', sqlalchemy.VARCHAR('255'), default=''),
                                sqlalchemy.Column('value', sqlalchemy.BIGINT, default=0),
                                sqlalchemy.Column('previous_value', sqlalchemy.BIGINT, default=0),
                                sqlalchemy.Column('ts', sqlalchemy.TIMESTAMP(6), default=
                                time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))))

"""Description of each column 
key - Corresponding statistics.key value, so that there is awareness of what the history is of
history_ts - the newest timestamp in statistics for that key 
value - delta value between `value` and `prev_val` of statistics
ts - current timestamp 
"""
_STATS_HISTORY_TABLE = sqlalchemy.Table('statistics_history', sqlalchemy.MetaData(),
                                        sqlalchemy.Column('key', sqlalchemy.CHAR(10)),
                                        sqlalchemy.Column('history_ts', sqlalchemy.TIMESTAMP(6), default=
                                        time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))),
                                        sqlalchemy.Column('value', sqlalchemy.BIGINT, default=0),
                                        sqlalchemy.Column('ts', sqlalchemy.TIMESTAMP(6), default=
                                        time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
                                        )

# List of PRIMARY KEY values in statistics (based on 'foglamp_init_ddl.sql')
_STATS_KEY_VALUE_LIST = ['READINGS', 'BUFFERED', 'SENT', 'UNSENT', 'PURGED', 'UNSNPURGED', 'DISCARDED']

def update_stats_value(key=''):
    """
    Update values in statistics table
        This method is TEMPORARY, and will exist until statistics is officallu updated. 
    Args:
        key: The row name update is executed against (WHERE condition) 

    Returns:

    """
    value = random.randint(11,20)
    previous_value = random.randint(1,10)
    stmt = _STATS_TABLE.update().values(value=value, previous_value=previous_value,
                                       ts=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))).where(
        _STATS_TABLE.c.key == key)

    _CONN.execute(stmt)

def __insert_into_stats_history(key='', history_ts=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
                              value=0, ts=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))):
    """
    INSERT values in statistics_history
    Args:
        key: corresponding stats_key_value
        history_ts: timestamp in statistics table for corresponding key 
        value: delta between `value` and `prev_val`
        ts: current_timestamp
    Returns:
        Return the number of rows inserted. Since each process inserts only 1 row, the expected count should always 
        be 1. 
    """
    stmt = _STATS_HISTORY_TABLE.insert().values(key=key, history_ts=history_ts, value=value, ts=ts)
    _CONN.execute(stmt)




def __select_from_statistics_key(key='') -> dict:
    """
    SELECT data from statistics for the statistics_history table
    Args:
        key: The row name update is executed against (WHERE condition)

    Returns:

    """
    stmt = sqlalchemy.select([_STATS_TABLE.c.value, _STATS_TABLE.c.previous_value,
                              _STATS_TABLE.c.ts]).where(_STATS_TABLE.c.key == key)

    result = _CONN.execute(stmt)
    return result.fetchall()


def stats_hisory_main():
    """
    1. SELECT against the  stats table,
    2. INSERT into history table, setting value to be the delta between stats.value and stats.previous_value 
    3. UPDATE the stats table with new values
    Returns:

    """
    for key in _STATS_KEY_VALUE_LIST:
        result_set=__select_from_statistics_key(key=key)
        value = result_set[0][0]
        previous_value = result_set[0][1]
        history_ts = time.mktime(result_set[0][2].timetuple())
        history_ts = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(history_ts))
        __insert_into_stats_history(key=key, history_ts=history_ts, value=value-previous_value)
        update_stats_value(key=key) # Temporary function that updates the stats table

if __name__ == '__main__':

    while True:
        stats_hisory_main()
        time.sleep(5)