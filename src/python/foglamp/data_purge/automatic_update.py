"""
Date: June 2017
Description: In essence, the purge process is: 
    1. getting a request from the scheduler
    2. reading the config file 
    3. send the request to the database for purging 
    4. verify (via either log file or db confirmation) that the data was removed 
Now, since neither the scheduler or database interface are currentnly avilable, the unit-test should
focus on: 
    1. Reading config files
    1a. verify that a user (or automated process) can execute config file update 
    2. Verify that data was written to logs file. 
            (In the example, the existing purge process write to log file)
 Given the information above, this script is a set of "unit-tests" that run simultaneously to sqlalchemy_insert
and sqlalchemy_purge scripts, doing the following actions: 
    1. convert config file to dict (read_config method) 
    2. update configuration file (update_config method) 
    3. check the number of lines in logs (number_of_lines method) 
    4. verify that there aren't any residue data after a delete (verify_remove method)
To complete the unit_tests: 
    1. verify data was removed from database (test_data_removal) 
    2. verify the number of lines in logs file increased (test_num_of_lines)
    3. that if automated process doesn't provide information for config, the config doesn't change 
        (test_no_config_file_changes)
    4. Test when enable is set to False
        - test_disable_purge method 
        - test_num_of_lines2 method 
    
"""
import datetime
import time
import yaml

def read_config():
    """
    Retrieve updated data from config file.
        This is intended as a tool to test the writting to config files 
    Returns:
        If read fails it returns 1
        If read doesn't fail it returns data 
    """
    read=None
    with open("config.yaml", 'r') as stream:
        try:
            read = yaml.load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            return 1
    return read

def update_config(original=None,enable=None,age=None,wait=None):
    """
    Update the config file based on user input
        Instead of manually accessing the config file each time to update it for
        testing purposes, this method automates the process based on user Input.
    Notice that if the 'user' inputs invalid values when testing, the code would utilize the
    existing information in the config file instead. This is because (my) assumption is that
    the documentation will clearly state what are valid, verses not valid values in the config. 
    In addition, the convert_timestamp and convert_wait in both purge processes check that the values
    are of that type. If not, then they use the default value of 5 seconds per wait, and 1 minute 
    for age. 
    Args:
        original: The current yaml file data 
        enable:  
        age: 
        wait: 
    Returns:
        If update fails then return 1
        If update doesn't fail than it should return results from  read_config() 
    """
    # Update the enabled value
    if enable is not None:
        if enable is True:
            enable=True
        elif enable is False:
            enable=False
        else:
            enable=original['enable']
    else:
        enable = original['enable']

    # Update the age value
    if age is not None: # Default 'age' is in minutes
        if (type(age) is str) and (age.isdigit() is True):
            age= age +" minute"
        elif (type(age) is int) or (type(age) is float):
           age=str(age)+" minute"
        elif ("sec" in age.lower()) or ("min" in age.lower()) or ("hr" in age.lower()) or ("hour" in age.lower()) or ("day" in age.lower()):
            pass
        else:
            age = original['age']
    else:
        age = original['age']

    # Update the wait value
    if wait is not None: # Default 'wait' is in second
        if (type(wait) is str) and (wait.isdigit() is True):
            age= age +" second"
        elif (type(wait) is int) or (type(wait) is float):
           age=str(age)+" second"
        elif ("sec" in wait.lower()) or ("min" in wait.lower()) or ("hr" in wait.lower()) or ("hour" in wait.lower()) or ("day" in wait.lower()):
            pass
        else:
            wait = original['wait']
    else:
        wait = original['wait']

    # Write to config file
    with open("config.yaml", 'w') as stream:
        try:
            yaml.dump({'enable': enable, 'age': age, 'wait': wait},stream,default_flow_style=False, allow_unicode=True)
        except yaml.YAMLError as exc:
            print(exc)
            return 1
        else:
            return read_config() # Read data in config file, and return it as dict

def number_of_lines():
    """
    Get the number of lines in log file. 
        This is intended as a tool to test that data information (when relevant) is writing to logs
    Returns:
        number of lines in log file
    """
    with open('logs.db') as f:
        return sum(1 for _ in f)

def verify_remove():
    """
    
    Returns:

    """
    verify=[]
    with open('logs.db') as f:
        reading=f.readlines()
    for i in range(1,len(reading)):
        verify.append(int(reading[i].split("|")[2].replace("\t","")))

    return all(x == 0 for x in verify)

def conver_timestamp(set_time=None):
    """
    Convert the information provided by config.yaml, to an actual timedelta format
    Args:
        set_time: 

    Returns:

    """
    time_dict={}
    tmp=0
    for value in set_time.split(" "):
        if value.isdigit() is True:
            tmp=int(value)
        else:
            time_dict[value] = tmp

    sec = datetime.timedelta(seconds=0)
    min = datetime.timedelta(minutes=0)
    hr  = datetime.timedelta(hours=0)
    day = datetime.timedelta(days=0)
    timestamp = 0
    for key in time_dict.keys():
        if 'sec' in key:
            sec = datetime.timedelta(seconds=time_dict[key])
        elif 'min' in key:
            min = datetime.timedelta(minutes=time_dict[key])
        elif ('hr' in key) or ('hour' in key):
            hr = datetime.timedelta(hours=time_dict[key])
        elif ('day' in key) or ('dy' in key):
            day = datetime.timedelta(days=time_dict[key])
    return sec+min+hr+day

def test_true_purge():
    orig_config=read_config()
    new_config = update_config(original=orig_config,enable=True)

    assert new_config['enable'] == True

def test_data_removal():
    assert verify_remove() is True

def test_num_of_lines():
    # Get wait time configurations
    config=read_config()
    sleep=conver_timestamp(config['wait'])
    before_sleep = number_of_lines()
    time.sleep(int(sleep.total_seconds())+1)
    after_sleep = number_of_lines()
    assert before_sleep < after_sleep

def test_no_config_file_changes():
    orig_config=read_config()
    updated_config=update_config(original=orig_config)

    assert updated_config == orig_config

def test_disable_purge():
    orig_config=read_config()
    new_config = update_config(original=orig_config,enable=False)

    assert new_config['enable'] == False

def test_num_of_lines2():
    # Get wait time configurations
    config=read_config()
    sleep=conver_timestamp(config['wait'])

    before_sleep = number_of_lines()
    time.sleep(int(sleep.total_seconds())+1)
    after_sleep = number_of_lines()
    assert before_sleep == after_sleep



