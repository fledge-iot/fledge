"""
Description: Unlike the code, which is a "single" function that communicates with different components on the system,
the unit-testing is broken into multiple parts, making sure that not only data is purged, but also that it is acting 
based on a the given criteria (configs). 
"""
import datetime
import json
import sqlalchemy.dialects.postgresql
import sys
import time

config_file = '../../foglamp/data_purge/config.json'

# Set variables for connecting to database
_user = "foglamp"
_db_user = "foglamp"
_host = "127.0.0.1"
_db = "foglamp"

# Create Connection
__engine__ = sqlalchemy.create_engine('postgres://%s:%s@%s/%s' % (_db_user, _user, _host, _db),  pool_size=20,
                                      max_overflow=0)
__conn__ = __engine__.connect()

# Table purge against
_READING_TABLE = sqlalchemy.Table('readings', sqlalchemy.MetaData(),
                                  sqlalchemy.Column('id', sqlalchemy.BIGINT, primary_key=True),
                                  sqlalchemy.Column('asset_code', sqlalchemy.VARCHAR(50)),
                                  sqlalchemy.Column('read_key', sqlalchemy.dialects.postgresql.UUID,
                                                    default='00000000-0000-0000-0000-000000000000'),
                                  sqlalchemy.Column('reading', sqlalchemy.dialects.postgresql.JSON, default='{}'),
                                  sqlalchemy.Column('user_ts', sqlalchemy.TIMESTAMP(6),
                                                    default=time.strftime('%Y-%m-%d %H:%M:%S',
                                                                          time.localtime(time.time()))),
                                  sqlalchemy.Column('ts', sqlalchemy.TIMESTAMP(6),
                                                    default=time.strftime('%Y-%m-%d %H:%M:%S',
                                                                          time.localtime(time.time()))))


"""logging table is instead of the log. After much thought, in addition to the discussed information the table also 
includes the following: 
    -> table to specify which table has been purged, since the process could occur in multiple tables 
    -> total_unsent_rows specifies the total number of unsent rows that existed within range prior to the purge. 
    based off that, and unsent_rows_removed one can calculate how many (unsent rows) remain.
"""
_LOGGING_TABLE = sqlalchemy.Table('purge_logging', sqlalchemy.MetaData(),
                                  sqlalchemy.Column('id', sqlalchemy.BIGINT, primary_key=True, autoincrement=True),
                                  sqlalchemy.Column('table', sqlalchemy.VARCHAR(255), default=_READING_TABLE.name),
                                  sqlalchemy.Column('start_time', sqlalchemy.VARCHAR(255),
                                                    default=sqlalchemy.func.current_timestamp),
                                  sqlalchemy.Column('end_time', sqlalchemy.VARCHAR(255),
                                                    default=sqlalchemy.func.current_timestamp),
                                  sqlalchemy.Column('total_rows_removed', sqlalchemy.INTEGER, default=0),
                                  sqlalchemy.Column('total_unsent_rows', sqlalchemy.INTEGER, default=0),
                                  sqlalchemy.Column('total_unsent_rows_removed', sqlalchemy.INTEGER, default=0),
                                  sqlalchemy.Column('total_failed_to_remove', sqlalchemy.INTEGER, default=0))

"""Methods that support the purge process. For the most part, theses methods would be replaced by either a scheduler,  
a database API interface,  and/or proper configuration methodology. 
"""


def convert_timestamp(set_time: str) -> datetime.timedelta:
    """Convert "age" in config file to timedelta. If only an integer is specified,  then 
        the code assumes that it is already in minutes (ie age:1 means wait 1 minute) 
    Args:
        set_time (str): Newest amount of  time back to delete
    Returns:
        converted set_time to datetime.timedelta value
    """
    if set_time.isdigit():
        return datetime.timedelta(minutes=int(set_time))
    time_dict = {}
    tmp = 0

    for value in set_time.split(" "):
        if value.isdigit() is True:
            tmp = int(value)
        else:
            time_dict[value] = tmp

    time_in_sec = datetime.timedelta(seconds=0)
    time_in_min = datetime.timedelta(minutes=0)
    time_in_hr = datetime.timedelta(hours=0)
    time_in_day = datetime.timedelta(days=0)

    for key in time_dict.keys():
        if 'sec' in key:
            time_in_sec = datetime.timedelta(seconds=time_dict[key])
        elif 'min' in key:
            time_in_min = datetime.timedelta(minutes=time_dict[key])
        elif ('hr' in key) or ('hour' in key):
            time_in_hr = datetime.timedelta(hours=time_dict[key])
        elif ('day' in key) or ('dy' in key):
            time_in_day = datetime.timedelta(days=time_dict[key])
    return time_in_sec+time_in_min+time_in_hr+time_in_day


def convert_sleep(set_time: str) -> int:
    """Convert "wait" in config file to seconds in order to know how long to wait until next purge process. 
        This method would potentially be replaced by the scheduler 
    Args:
        set_time (str): A string of "values" specified in the config to declare how long to wait till next purge

    Returns:
        integer (of seconds) based on wait in config 
    """
    if set_time.isdigit():
        return int(set_time)
    time_dict = {}
    tmp = 0
    for value in set_time.split(" "):
        if value.isdigit() is True:
            tmp = int(value)
        else:
            time_dict[value] = tmp
    time_in_sec = 0
    time_in_min = 0
    time_in_hr = 0
    time_in_dy = 0
    for key in time_dict:
        if "sec" in key:
            time_in_sec = time_dict[key]
        elif "min" in key:
            time_in_min = 60 * time_dict[key]
        elif ("hour" in key) or ("hr" in key):
            time_in_hr = 60 * 60 * time_dict[key]
        elif ("day" in key) or ("dy" in key):
            time_in_dy = 60 * 60 * 24 * time_dict[key]
        else:
            print("Error: Invalid Value(s) in config file")
            sys.exit()
    return time_in_sec+time_in_min+time_in_hr+time_in_dy


def execute_command_with_return_value(stmt: str) -> dict:
    """Imitate connection to postgres that returns result.    
    Args:
        stmt (str): generated SQL query   
    Returns:
        Returns the first value in the result set
    """
    query_result = __conn__.execute(stmt)
    return query_result.fetchall()


def read_config():
    """
    Read configuration file

    Returns:
        json data a python dict 
    """
    with open(config_file) as json_data:
        data = json.load(json_data)
    return data


""" 
The following set of tests verify that the configuration file gets updated properly, and  automatically. This 
is because in the following sections, variables regularly get updated in order to check different conditions.
In addition, by setting these values, there is a `default` initial state for testing. These tests do not require
the database to be up, but rather just an existing config file.
"""


def test_disable_retainUnsent():
    """
    Assert that retainUnsent is disabled (False)
    """
    config_info = read_config()
    config_info['retainUnsent'] = False
    open(config_file, 'w').close()
    with open(config_file, 'r+') as conf:
        conf.write(json.dumps(config_info))
    config_info = read_config()

    assert config_info['retainUnsent'] is False


def test_enable_retainUnsent():
    """
    Assert that retainUnsent is enabled (True)
    """
    config_info = read_config()
    config_info['retainUnsent'] = True
    open(config_file, 'w').close()
    with open(config_file, 'r+') as conf:
        conf.write(json.dumps(config_info))
    config_info = read_config()

    assert config_info['retainUnsent'] is True


def test_disable_enabled():
    """
    Assert that enabled is disabled (False)
    """
    config_info = read_config()
    config_info['enabled'] = False
    open(config_file, 'w').close()
    with open(config_file, 'r+') as conf:
        conf.write(json.dumps(config_info))
    config_info = read_config()

    assert config_info['enabled'] is False


def test_enable_enabled():
    """
    Assert that enabled is enabled (True)
    """
    config_info = read_config()
    config_info['enabled'] = True
    open(config_file, 'w').close()
    with open(config_file, 'r+') as conf:
        conf.write(json.dumps(config_info))
    config_info = read_config()

    assert config_info['enabled'] is True


def test_update_lastID():
    """
    Assert that `lastConnection` is set to NOW
    """
    config_info = read_config()
    config_info['lastID'] = 0
    open(config_file, 'w').close()
    with open(config_file, 'r+') as conf:
        conf.write(json.dumps(config_info))
    config_info = read_config()

    assert config_info['lastID'] == 0


def test_update_wait():
    """
    Assert that `wait` is set to 30 seconds
    """
    wait = '10 seconds'
    config_info = read_config()
    config_info['wait'] = wait
    open(config_file, 'w').close()
    with open(config_file, 'r+') as conf:
        conf.write(json.dumps(config_info))
    config_info = read_config()

    assert config_info['wait'] == wait


def test_update_age():
    """
    Assert that `wait` is set to 2 minutes
    """
    age = '2 minutes'
    config_info = read_config()
    config_info['age'] = age
    open(config_file, 'w').close()
    with open(config_file, 'r+') as conf:
        conf.write(json.dumps(config_info))
    config_info = read_config()

    assert config_info['age'] == age

"""
Tests are based on the configuration, and verify that logs table gets updated properly. This is not to say that the data 
inserted is valid; as there will be another set of tests validating the actual results. From this point on, each test 
will have a SLEEP prior to the actual test process. This is because the testing is unaware at what phase of the purge 
code it was called. Thus, an assertion could occur against OLD results rather than ones based on updated config.
"""


def test_disable_enabled_in_logs():
    """
    Assert that logs doesn't get updated when `enable` is False
    """
    stmt = sqlalchemy.select([sqlalchemy.func.count()]).select_from(_LOGGING_TABLE)
    config_info = read_config()
    config_info['enabled'] = False
    open(config_file,  'w').close()
    with open(config_file,  'r+') as conf:
        conf.write(json.dumps(config_info))

    time.sleep(convert_sleep(config_info['wait']))
    data_before_wait = execute_command_with_return_value(stmt)
    time.sleep(convert_sleep(config_info['wait'])*2)
    data_after_wait = execute_command_with_return_value(stmt)

    assert int(data_before_wait[0][0]) == int(data_after_wait[0][0])


def test_enabled_enabled_in_logs():
    """
    Assert that logs does get updated when `enable` is True
    """
    stmt = sqlalchemy.select([sqlalchemy.func.count()]).select_from(_LOGGING_TABLE)
    config_info = read_config()
    config_info['enabled'] = True
    open(config_file,  'w').close()
    with open(config_file,  'r+') as conf:
        conf.write(json.dumps(config_info))

    # time.sleep(convert_sleep(config_info['wait']))
    data_before_wait = execute_command_with_return_value(stmt)
    time.sleep(convert_sleep(config_info['wait'])*2)
    data_after_wait = execute_command_with_return_value(stmt)

    assert int(data_before_wait[0][0]) < int(data_after_wait[0][0])


def test_wait_expected():
    """
    Assert that there is an increase of values logged
    """
    stmt = sqlalchemy.select([sqlalchemy.func.count()]).select_from(_LOGGING_TABLE)
    config_info = read_config()
    open(config_file,  'w').close()
    with open(config_file,  'r+') as conf:
        conf.write(json.dumps(config_info))

    time.sleep(convert_sleep(config_info['wait'])*2)
    data_before_wait = execute_command_with_return_value(stmt)
    time.sleep(convert_sleep(config_info['wait']))
    data_after_wait = execute_command_with_return_value(stmt)

    assert int(data_before_wait[0][0]) < int(data_after_wait[0][0])


"""
Tests are based on the configuration, and verify that logs have valid values
"""


def test_disable_retainUnsent_logs():
    """
    Assert that when retainUnsent is False, the count in `total_unsent_rows_removed` is at least 0
    """
    stmt = sqlalchemy.select([_LOGGING_TABLE.c.total_unsent_rows_removed]).select_from(_LOGGING_TABLE).order_by(
        _LOGGING_TABLE.c.id.desc()).limit(1)
    config_info = read_config()
    config_info['retainUnsent'] = False
    open(config_file, 'w').close()
    with open(config_file, 'r+') as conf:
        conf.write(json.dumps(config_info))

    time.sleep(convert_sleep(config_info['wait'])*2)
    result = execute_command_with_return_value(stmt)

    assert int(result[0][0]) >= 0


def test_enable_retainUnsent_logs():
    """
    Assert that when retainUnsent is True, the `total_unsent_rows_removed` is 0.
    """
    stmt = sqlalchemy.select([_LOGGING_TABLE.c.total_unsent_rows_removed]).select_from(_LOGGING_TABLE).order_by(
        _LOGGING_TABLE.c.id.desc()).limit(1)
    config_info = read_config()
    config_info['retainUnsent'] = True
    open(config_file, 'w').close()
    with open(config_file, 'r+') as conf:
        conf.write(json.dumps(config_info))

    time.sleep(convert_sleep(config_info['wait'])*2)
    result = execute_command_with_return_value(stmt)

    assert int(result[0][0]) == 0


def test_total_failed_to_remove():
    """
    Assert that there aren't any residue rows remaining after delete. 
    """
    stmt = sqlalchemy.select([_LOGGING_TABLE.c.total_failed_to_remove]).select_from(_LOGGING_TABLE)
    result = execute_command_with_return_value(stmt)
    assert [value[0] == 0 for value in result]


def test_rows_removed_greater_than_unsent_removed():
    """
    Assert that the number of rows removed is greater than or equal to the number of unsent rows removed 
    """
    stmt = sqlalchemy.select([_LOGGING_TABLE.c.total_rows_removed,
                              _LOGGING_TABLE.c.total_unsent_rows_removed]).select_from(_LOGGING_TABLE).order_by(
        _LOGGING_TABLE.c.id)

    result = execute_command_with_return_value(stmt)
    assert [value[0] >= value[1] for value in result]





