"""
The following tests verify that statistics.value, statistics.previous_value, adn statistics_history.value
are all valid. 
"""
import sqlalchemy
import time

# Set variables for connecting to database
_db_type = "postgres"
_user = "foglamp"
_db_user = "foglamp"
_host = "127.0.0.1"
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
            The point is to know how many actions happened during the X time
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


def compare_value_in_statistics():
    """Assert that statistics.value >= 0"""
    _set = []
    stmt = sqlalchemy.select([_STATS_TABLE.c.value]).select_from(_STATS_TABLE)
    result = _CONN.execute(stmt)
    for value in result.fetchall():
        _set.append(value[0])

    assert(x >= 0 for x in _set)


def compare_value_to_previous_value():
    """Assert that statistics.value >= statistics.previous_value"""
    _set = {}
    stmt = sqlalchemy.select([_STATS_TABLE.c.value, _STATS_TABLE.c.previous_value]).select_from(_STATS_TABLE)
    result = _CONN.execute(stmt)
    for value in result.fetchall():
        _set[value[0]] = value[1]

    assert(x >= _set[x] for x in _set.keys())


def compare_value_statistics_history():
    """Assert that statistics_history.value >= 0"""
    _set = []
    stmt = sqlalchemy.select([_STATS_HISTORY_TABLE.c.value]).select_from(_STATS_HISTORY_TABLE)
    result = _CONN.execute(stmt)
    for value in result.fetchall():
        _set.append(value[0])

    assert(x >= 0 for x in _set)
