"""
The following code updates the information in the statistics table, in order to show that statistics_history.py script
works properly. 
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
_host = "192.168.0.182"
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


def __list_stats_keys() -> list:
    """
    generate a list of distinct keys from statistics table 
    Returns:
        list of distinct keys
    """
    key_list = []
    stmt = sqlalchemy.select([_STATS_TABLE.c.key.distinct()]).select_from(_STATS_TABLE)
    result = _CONN.execute(stmt)
    result = result.fetchall()
    for i in range(len(result)):
        key_list.append(result[i][0].replace(" ", ""))

    return key_list

# List of PRIMARY KEY values in statistics
_STATS_KEY_VALUE_LIST = __list_stats_keys()


def __update_previous_value(key=''):
    """Query: 
    UPDATE 
        statistics 
    SET 
        previous_value = (SELECT value FROM statistics WHERE key='READINGS')
    WHERE 
        value = (SELECT value FROM statistics WHERE key='READINGS'); 
    """
    sub_select_stmt = sqlalchemy.select([_STATS_TABLE.c.value]).select_from(_STATS_TABLE).where(
        _STATS_TABLE.c.key == key)
    result = _CONN.execute(sub_select_stmt)
    result = int(result.fetchall()[0][0])
    update_stmt = _STATS_TABLE.update().values(previous_value=result).where(key == key)
    _CONN.execute(update_stmt)


def __update_stats_value(key=''):
    """
    Update `value` in statistics table 
    Args:
        key: The row name update is executed against (WHERE condition) 

    Returns:

    """
    val = random.randint(1, 10)
    stmt = sqlalchemy.select([_STATS_TABLE.c.value]).where(_STATS_TABLE.c.key == key)
    result = _CONN.execute(stmt)
    val = int(result.fetchall()[0][0]) + val
    stmt = _STATS_TABLE.update().values(value=val, ts=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                                        ).where(_STATS_TABLE.c.key == key)
    _CONN.execute(stmt)


if __name__ == '__main__':
    # Notice that previous_value gets updated prior to value
    for key in _STATS_KEY_VALUE_LIST:
        __update_previous_value(key=key)
        __update_stats_value(key=key)

