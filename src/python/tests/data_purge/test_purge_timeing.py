"""
The following are tests to make sure that the logs directory gets updated appropriately based on changes in the
 configuration file. 
"""

import json
import random
import sys
import time


configFile = '../../foglamp/data_purge/config.json'
logsFile = '../../foglamp/data_purge/logs.json'


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


# testing that logs get updated properly when needs to be
def test_disable_enabled():
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

    # re-enable config set to have purging execute
    config_info = read_config()
    config_info['enabled'] = True
    open(configFile, 'w').close()
    with open(configFile, 'r+') as conf:
        conf.write(json.dumps(config_info))

    assert data_before_wait == data_after_wait


def test_enable_enabled():
    """
    Assert that logs gets updated when `enable` is True 
    """
    config_info = read_config()
    config_info['enabled'] = True
    open(configFile, 'w').close()
    with open(configFile, 'r+') as conf:
        conf.write(json.dumps(config_info))
    data_before_wait = read_logs()
    time.sleep(convert_sleep(config_info['wait']) * 2)
    data_after_wait = read_logs()

    assert len(data_before_wait)+1 <= len(data_after_wait)


# Wait tests
def test_wait_less_than_expected():
    """
    Assert that in a time period less than config (skip wait), logs don't get updated.
    Since the code my not be in sync with the test, the assumption is that the total
    number of rows added is no more than 1. 
    """
    config_info = read_config()
    sleep_time = convert_sleep(config_info['wait'])
    if 0 <= sleep_time <= 5:
        sleep_time = 3
    else:
        sleep_time = sleep_time - random.randint(5, sleep_time)

    data_before_wait = read_logs()
    time.sleep(sleep_time)
    data_after_wait = read_logs()

    assert len(data_before_wait)+1 >= len(data_after_wait)


def test_wait_expected():
    """
    Assert that there is an increase of values logged 
    """
    config_info = read_config()
    open(configFile,  'w').close()
    with open(configFile,  'r+') as conf:
        conf.write(json.dumps(config_info))

    data_before_wait = read_logs()
    time.sleep(convert_sleep(config_info['wait']))
    data_after_wait = read_logs()

    assert len(data_before_wait.keys()) < len(data_after_wait.keys())

