"""
June: July 2017 
Description: The following tests verify that the behavior of the code is expected. The test itself 
                is broken into the following parts: 
        Part I: Making sure that the config file (config.json) gets updated properly. This part can be
                run without the purge processes running in parallel
        Part II: Making sure that the logs file (logs.json) get updated properly. It does not
                check the validation of data,  but rather that the data is properly created based
                configurations. 
        Part III: Data validation - check that the information in logs.json (based on config.json) is
                correct. (example,  when 
        
verifying that as the config gets updated, 
    the purge logging gets updated appropriately. Since the config files will require a
    certain format (ie True/False,  TIMESTAMP,  time variable),  negative testing currently 
    does not exist. 
    
Since INSERTS and DELETE occur simultaneously,  there is a chance that some of the tests will not consistently pass. 
- test_disable_unsent_rows
- any failedRemoval Test 

"""
import json
import sqlalchemy
import sqlalchemy.dialects.postgresql
import sqlalchemy.exc
import sys
import time


config_file = '../../foglamp/data_purge/config.json'
logs_file = ' ../../foglamp/data_purge/logs.json'



readings = sqlalchemy.Table('readings', sqlalchemy.MetaData(),
sqlalchemy.Column('id', sqlalchemy.BIGINT, primary_key=True),
    sqlalchemy.Column('asset_code', sqlalchemy.VARCHAR(50)),
    sqlalchemy.Column('read_key', sqlalchemy.dialects.postgresql.UUID,
                      default='00000000-0000-0000-0000-000000000000'),
    sqlalchemy.Column('reading', sqlalchemy.dialects.postgresql.JSON, default='{}'),
    sqlalchemy.Column('user_ts', sqlalchemy.TIMESTAMP(6), default=time.strftime('%Y-%m-%d %H:%M:%S',
                                                                                time.localtime(time.time()))),
    sqlalchemy.Column('ts', sqlalchemy.TIMESTAMP(6),  default=time.strftime('%Y-%m-%d %H:%M:%S',
                                                                            time.localtime(time.time())))
)


def read_config():
    """
    Read configuration file

    Returns:
        json data a python dict 
    """
    with open(config_file) as json_data:
        data = json.load(json_data)
    return data


def read_logs():
    """
    Read data in logs file     
    Returns:
        json data as a python dict 

    """
    with open(logs_file) as json_data:
        data = json.load(json_data)
    return data


def convert_sleep(set_time=None):
    """
    Convert "wait time" in config file to seconds. If only an integer is specified,  then 
        the code assumes that it is already in seconds (ie wait:1 means wait 1 second) 
    Args:
        set_time: 

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
    sec = 0
    minute = 0
    hr = 0
    dy = 0
    for key in time_dict:
        if "sec" in key:
            sec = time_dict[key]
        elif "min" in key:
            minute = 60 * time_dict[key]
        elif ("hour" in key) or ("hr" in key):
            hr = 60 * 60 * time_dict[key]
        elif ("day" in key) or ("dy" in key):
            dy = 60 * 60 * 24 * time_dict[key]
        else:
            print("Error: Invalid Value(s) in config file")
            sys.exit()
    return sec+minute+hr+dy


def execute_query(stmt):
    """
    Imitate connection to Postgres and execute query against it
    Args:
        stmt: 
    Returns:
        Result Value
    """
    user = "foglamp"
    db_user = "foglamp"
    host = "127.0.0.1"
    db = "foglamp"

    engine = sqlalchemy.create_engine('postgres://%s:%s@%s/%s' % (db_user,  user,  host,  db),  pool_size=20,
                                      max_overflow=0)
    conn = engine.connect()

    try:
        result = conn.execute(stmt)
    except sqlalchemy.exc as e:
        print(e)
        sys.exit()
    else:
        return int(result.fetchall()[0][0])

"""
PART IV - Validate that behavior as configs change 
"""


def disable_retain_unsent_data():
    """
    Assert that when retainUnsent is False, unsentRowsRemoved > 0
    """
    config_info = read_config()
    config_info['retainUnsent'] = False
    config_info['age'] = '5 second'
    open(config_file, 'w').close()
    with open(config_file, 'r+') as conf:
        conf.write(json.dumps(config_info))

    time.sleep(convert_sleep(config_info['wait']) * 2)
    logs = read_logs()

    date = sorted(list(logs.keys()))[-1]
    print(date)
    # print(logs[date]['unsentRowsRemoved'])
    # assert logs[date]['unsentRowsRemoved'] > 0

if __name__ == '__main__':
    disable_retain_unsent_data()

# def test_enable_unsent_data():
#     """
#     Assert that when retainUnsent is True, unsentRowsRemoved = 0
#     """
#     config_info = read_config()
#     config_info['retainUnsent'] = True
#     config_info['age'] = '5 second'
#     open(config_file, 'w').close()
#     with open(config_file, 'r+') as conf:
#         conf.write(json.dumps(config_info))
#
#     time.sleep(convert_sleep(config_info['wait']) * 2)
#
#     logs = read_logs()
#
#     date = sorted(list(logs.keys()))[-1]
#     print(logs[date]['unsentRowsRemoved'])
#     assert logs[date]['unsentRowsRemoved'] == 0

#
# def test_retainUnsent_true():
#     """
#     Assert that when retainUnsent is True,  logs[latestDate]['unsentRowsRemoved'] == 0
#     """
#     config_info = read_config()
#     config_info['retainUnsent'] = True
#
#     open(config_file,  'w').close()
#     with open(config_file,  'r+') as conf:
#         conf.write(json.dumps(config_info))
#
#     time.sleep(convert_sleep(config_info['wait']) * 2)
#     logs = read_logs()
#
#     date = sorted(list(logs.keys()))[-1]
#     assert ((logs[date]['unsentRowsRemoved'] == 0) and (logs[date]['rowsRemaining'] >= 0)
#             and (logs[date]['failedRemovals'] == 0) and (logs[date]['rowsRemoved'] >= 0))
#
#
# def test_retainUnsent_false():
#     """
#     Assert that when retainUnsent is False,  logs[latestDate]['unsentRowsRemoved'] > 0
#     """
#     config_info = read_config()
#     config_info['retainUnsent'] = False
#
#     open(config_file,  'w').close()
#     with open(config_file,  'r+') as conf:
#         conf.write(json.dumps(config_info))
#
#     time.sleep(convert_sleep(config_info['wait']) * 2)
#     logs = read_logs()
#
#     date = sorted(list(logs.keys()))[-1]
#     assert ((logs[date]['unsentRowsRemoved'] == 0) and (logs[date]['rowsRemaining'] >= 0)
#             and (logs[date]['failedRemovals'] == 0) and (logs[date]['rowsRemoved'] >= 0))

