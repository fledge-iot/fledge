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
import datetime
import json
import sqlalchemy
import sqlalchemy.dialects.postgresql
import sqlalchemy.exc
import sys
import time


configFile = '../../foglamp/data_purge/config.json'
logsFile = '../../foglamp/data_purge/logs.json'

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
    with open(configFile) as json_data:
        data = json.load(json_data)
    return data

def read_logs():
    """
    Read data in logs file     
    Returns:
        json data as a python dict 

    """
    with open(logsFile) as json_data:
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

def get_nth_id():
    """
        Update the config file to have row ID somewhere within the oldest 100 rows  
        The method runs at the end of each test (parts II through IV) such that the lastID
        gets updated each time.
         
        The return is relevant only for check_id(),  in all other cases it's being ignored. 
    Returns: 
        id 
    """
    # rand = random.randint(1, 100)

    stmt = "SELECT id FROM (SELECT id FROM readings ORDER BY id ASC LIMIT 100)t ORDER BY id DESC LIMIT 1"
    rowID = execute_query(stmt)

    config_info = read_config()
    config_info["lastID"] = id
    open(configFile,  'w').close()
    with open(configFile,  'r+') as conf:
        conf.write(json.dumps(config_info))
    return rowID

""" 
PART I - Verify the update of config files
"""
def test_disable_retainUnsent():
    """
    Assert that retainUnsent is disabled (False)   
    """
    config_info = read_config()
    config_info['retainUnsent'] = False
    open(configFile,  'w').close()
    with open(configFile,  'r+') as conf:
        conf.write(json.dumps(config_info))
    config_info = read_config()

    assert config_info['retainUnsent'] is False

def test_enable_retainUnsent():
    """
    Assert that retainUnsent is enabled (True) 
    """
    config_info = read_config()
    config_info['retainUnsent'] = True
    open(configFile,  'w').close()
    with open(configFile,  'r+') as conf:
        conf.write(json.dumps(config_info))
    config_info = read_config()

    assert config_info['retainUnsent'] is True

def test_disable_enabled():
    """
    Assert that enabled is disabled (False)
    """
    config_info = read_config()
    config_info['enabled'] = False
    open(configFile,  'w').close()
    with open(configFile,  'r+') as conf:
        conf.write(json.dumps(config_info))
    config_info = read_config()

    assert config_info['enabled'] is False

def test_enable_enabled():
    """
    Assert that enabled is enabled (True)
    """
    config_info = read_config()
    config_info['enabled'] = True
    open(configFile,  'w').close()
    with open(configFile,  'r+') as conf:
        conf.write(json.dumps(config_info))
    config_info = read_config()

    assert config_info['enabled'] is True

def test_update_lastConnection():
    """
    Assert that `lastConnection` is set to NOW
    """
    now = str(datetime.datetime.now()).split(".")[0]
    config_info = read_config()
    config_info['lastConnection'] = now
    open(configFile,  'w').close()
    with open(configFile,  'r+') as conf:
        conf.write(json.dumps(config_info))
    config_info = read_config()

    assert config_info['lastConnection'] == now

def test_update_wait():
    """
    Assert that `wait` is set to 30 seconds
    """
    wait = '30 seconds'
    config_info = read_config()
    config_info['wait'] = wait
    open(configFile,  'w').close()
    with open(configFile,  'r+') as conf:
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
    open(configFile,  'w').close()
    with open(configFile,  'r+') as conf:
        conf.write(json.dumps(config_info))
    config_info = read_config()

    assert config_info['age'] == age

def check_id():
    """
    Assert that lastID gets updated properly
    """
    rowID = get_nth_id()
    config_info = read_config()
    assert config_info["lastID"] == rowID

"""
PART II - verify that updates of logs get done correctly
"""


# testing that logs get updated properly when needs to be
def test_disable_enabled2():
    """
    Assert that logs doesn't get updated when `enable` is False
    """
    config_info = read_config()
    config_info['enabled'] = False
    open(configFile,  'w').close()
    with open(configFile,  'r+') as conf:
        conf.write(json.dumps(config_info))
    data_before_wait = read_logs()
    time.sleep(convert_sleep(config_info['wait'])*2)
    data_after_wait = read_logs()

    assert data_before_wait == data_after_wait

def test_enable_enabled2():
    """
    Assert that logs does get updated when `enable` is True
    """
    config_info = read_config()
    config_info['enabled'] = True
    open(configFile,  'w').close()
    with open(configFile,  'r+') as conf:
        conf.write(json.dumps(config_info))
    data_before_wait = read_logs()
    time.sleep(convert_sleep(config_info['wait'])*2)
    data_after_wait = read_logs()

    assert len(data_before_wait)+1 <= len(data_after_wait)

# Wait tests
def test_wait_less_than_expected():
    """
    Assert that when the wait is less than actual wait (30 seconds),  no rows get inserted.
        Since the code runs in parallel to the purge process,  there is a chance that 
        test will fail,  if it runs around the 30 second mark of the wait before purge. 
    """
    data_before_wait = read_logs()
    # By 'default' the config wait is set to 30 seconds
    data_after_wait = read_logs()

    assert len(data_before_wait) == len(data_after_wait)

def test_wait_expected():
    """
    Assert that 1 row (at most) has been added to the JSON object
        The number of rows for data_after_wait = data_before_wait or data_before_wait+1
    """
    config_info = read_config()
    wait_time = '10 seconds'

    config_info['wait'] = wait_time
    config_info['enabled'] = True
    open(configFile,  'w').close()
    with open(configFile,  'r+') as conf:
        conf.write(json.dumps(config_info))

    data_before_wait = read_logs()
    time.sleep(convert_sleep(wait_time))
    data_after_wait = read_logs()

    assert len(data_before_wait.keys()) + 2 > len(data_after_wait.keys())

"""
PART III - verify that values in logs are valid ( >= 0)
"""

def test_rowsRemoved_is_valid():
    """
    Assert that the number of rows removed is >= 0,  ie not negative
    """
    config_info = read_config()
    time.sleep(convert_sleep(config_info['wait']) * 2)
    logs = read_logs()

    assert [logs[date]['rowsRemoved'] >= 0 for date in sorted(list(logs.keys()))]

def test_failedRemovals_is_valid():
    """
    Assert that all expected rows were removed
    """
    config_info = read_config()
    time.sleep(convert_sleep(config_info['wait']) * 2)
    logs = read_logs()

    assert [logs[date]['failedRemovals'] == 0 for date in sorted(list(logs.keys()))]

def test_unsentRowsRemoved_is_valid():
    """
    Assert that in general the number of rows removed (that were not sent to PI) is >= 0
    """
    config_info = read_config()
    time.sleep(convert_sleep(config_info['wait']) * 2)
    logs = read_logs()

    assert [logs[date]['unsentRowsRemoved'] >= 0 for date in sorted(list(logs.keys()))]

def test_rowsRemaining_is_valid():
    """
    Assert that the number of rows that remain is >= 0
    """
    config_info = read_config()
    time.sleep(convert_sleep(config_info['wait']) * 2)
    logs = read_logs()

    assert [logs[date]['rowsRemaining'] >= 0 for date in sorted(list(logs.keys()))]

"""
PART IV - Validate that behavior as configs change 
"""


def test_retainUnsent_true():
    """
    Assert that when retainUnsent is True,  logs[latestDate]['unsentRowsRemoved'] == 0
    """
    config_info = read_config()
    config_info['retainUnsent'] = True

    open(configFile,  'w').close()
    with open(configFile,  'r+') as conf:
        conf.write(json.dumps(config_info))

    time.sleep(convert_sleep(config_info['wait']) * 2)
    logs = read_logs()

    date = sorted(list(logs.keys()))[-1]
    assert ((logs[date]['unsentRowsRemoved'] == 0) and (logs[date]['rowsRemaining'] >= 0)
            and (logs[date]['failedRemovals'] == 0) and (logs[date]['rowsRemoved'] >= 0))


def test_retainUnsent_false():
    """
    Assert that when retainUnsent is False,  logs[latestDate]['unsentRowsRemoved'] > 0
    """
    config_info = read_config()
    config_info['retainUnsent'] = False

    open(configFile,  'w').close()
    with open(configFile,  'r+') as conf:
        conf.write(json.dumps(config_info))

    time.sleep(convert_sleep(config_info['wait']) * 2)
    logs = read_logs()

    date = sorted(list(logs.keys()))[-1]
    assert ((logs[date]['unsentRowsRemoved'] == 0) and (logs[date]['rowsRemaining'] >= 0)
            and (logs[date]['failedRemovals'] == 0) and (logs[date]['rowsRemoved'] >= 0))

