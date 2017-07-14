""" 
The following set of tests verify that the configuration file gets updated properly, and  automatically. 
This is because in the following sections, variables regularly in order to check different if conditions. 
"""
import json
import sys


configFile = '../../foglamp/data_purge/config.json'


def read_config():
    """
    Read configuration file

    Returns:
        json data a python dict 
    """
    with open(configFile) as json_data:
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
    Assert that enabled is enabled (True)
    """
    config_info = read_config()
    config_info['enabled'] = True
    open(configFile, 'w').close()
    with open(configFile, 'r+') as conf:
        conf.write(json.dumps(config_info))
    config_info = read_config()

    assert config_info['enabled'] is True


def test_update_lastID():
    """
    Assert that `lastConnection` is set to NOW
    """
    config_info = read_config()
    config_info['lastID'] = 0
    open(configFile, 'w').close()
    with open(configFile, 'r+') as conf:
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

