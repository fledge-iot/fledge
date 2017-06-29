"""
June: July 2017 
Description: The following is the unit-test verifying that as the config gets updated,
    the purge logging gets updated appropriately. Since the config files will require a
    certain format (ie True/False, TIMESTAMP, time variable), negative testing currently 
    does not exist. 
"""
import datetime
import json
import time

configFile = 'config.json'
logsFile = 'logs.json'


def read_config():
    """
    Read configuration file
    Args:
        configFile: 
    Returns:
        json data a python dict 
    """
    with open(configFile) as json_data:
        data = json.load(json_data)
    return data

def read_logs():
    """
    Read data in logs file    
    Args:
        logfile: 
    Returns:
        json data as a python dict 

    """
    with open(logsFile) as json_data:
        data = json.load(json_data)
    return data

def convert_sleep(set_time=None):
    """
    Convert "wait time" in config file to seconds. If only an integer is specified, then 
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
    min = 0
    hr = 0
    dy = 0
    for key in time_dict:
        if "sec" in key:
            sec = time_dict[key]
        elif "min" in key:
            min = 60 * time_dict[key]
        elif ("hour" in key) or ("hr" in key):
            hr = 60 * 60 * time_dict[key]
        elif ("day" in key) or ("dy" in key):
            dy = 60 * 60 * 24 * time_dict[key]
        else:
            print("Error: Invalid Value(s) in config file")
            sys.exit()
    return sec+min+hr+dy

""" 
The following are "sanity" check tests are to make sure that the config file gets updated
as requested, so that when testing there aren't any issues. These tests are also done so that
by the time testing is done against the logging, the script is "aware" of the current 
state of configs (ie what each value is set to)
"""
def test_disable_retainUnsent():
    """
    Assert that retainUnsent is disabled (False)   
    """
    config_info = read_config()
    config_info['retainUnsent'] = False
    open(configFile, 'w').close()
    with open(configFile, 'r+') as conf:
        conf.write(json.dumps(config_info))
    config_info = read_config()

    assert config_info['retainUnsent'] is False

def test_enable_retainUnsent():
    """
    Assert that retainUnsent is enabled (True) 
    """
    config_info = read_config()
    config_info['retainUnsent'] = True
    open(configFile, 'w').close()
    with open(configFile, 'r+') as conf:
        conf.write(json.dumps(config_info))
    config_info = read_config()

    assert config_info['retainUnsent'] is True

def test_disable_enabled():
    """
    Assert that enabled is disabled (False)
    """
    config_info = read_config()
    config_info['enabled'] = False
    open(configFile, 'w').close()
    with open(configFile, 'r+') as conf:
        conf.write(json.dumps(config_info))
    config_info = read_config()

    assert config_info['enabled'] is False

def test_enable_enabled():
    """
    Assert that enabled is enabledd (True)
    """
    config_info = read_config()
    config_info['enabled'] = True
    open(configFile, 'w').close()
    with open(configFile, 'r+') as conf:
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
    open(configFile, 'w').close()
    with open(configFile, 'r+') as conf:
        conf.write(json.dumps(config_info))
    config_info = read_config()

    assert config_info['lastConnection'] == now

def test_update_wait():
    """
    Assert that `wait` is set to 90 seconds
    """
    wait = '90 seconds'
    config_info = read_config()
    config_info['wait'] = wait
    open(configFile, 'w').close()
    with open(configFile, 'r+') as conf:
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
    open(configFile, 'w').close()
    with open(configFile, 'r+') as conf:
        conf.write(json.dumps(config_info))
    config_info = read_config()

    assert config_info['age'] == age


"""
Start of actual testing that runs in parallel to the code
"""
# testing that logs get updated properly when needs to be
def test_disable_enabled2():
    """
    Assert that logs doesn't get updated when `enable` is False
    """
    config_info = read_config()
    config_info['enabled'] = False
    open(configFile, 'w').close()
    with open(configFile, 'r+') as conf:
        conf.write(json.dumps(config_info))
    config_info = read_config()
    data_before_wait = read_logs()
    time.sleep(convert_sleep(config_info['wait']))
    data_after_wait = read_logs()

    assert data_before_wait == data_after_wait

# Wait tests
def test_wait_less_than_expected():
    """
    Assert that unknown data is not logged by checking the logs 5 seconds before insert
    """
    wait_time= '30 seconds'
    config_info = read_config()
    config_info['wait'] = wait_time
    config_info['enabled'] = True # Has to be reset becuase previous test disables it.
    open(configFile, 'w').close()
    with open(configFile, 'r+') as conf:
        conf.write(json.dumps(config_info))

    data_before_wait = read_logs()
    time.sleep(convert_sleep(wait_time)-5)
    data_after_wait = read_logs()

    assert len(data_before_wait) == len(data_after_wait)


def test_wait_expected():
    """
    Assert that a new rows has been added after the set time
    """
    wait_time = '10 seconds'
    config_info = read_config()
    config_info['wait'] = wait_time
    open(configFile, 'w').close()
    with open(configFile, 'r+') as conf:
        conf.write(json.dumps(config_info))

    data_before_wait = read_logs()
    time.sleep(convert_sleep(wait_time))
    data_after_wait = read_logs()

    assert len(data_before_wait) + 1 == len(data_after_wait)

