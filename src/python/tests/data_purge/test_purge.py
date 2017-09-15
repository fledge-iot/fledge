#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END
"""
Description: The following are tests verify that purge processes executes properly. Note that the test process executes
in a chronological order, and waits for each step to finish before moving on to the next one; whereas in integration 
with the actual process, purge would occur in parallel to inserts.

List of Test: 
- Test 0: Verify that code to change configuration works 
- Test 1: Have the age of delete be >= 72hrs and retaining data unsent to Pi System try to purge current data
            (expect - Unable to purge because data is < 72hrs old)
- Test 2: Have the age of delete be >= 72hrs and ignore  retaining data unsent to Pi System try to to purge current data
            (expect - Unable to purge because data is < 72hrs old)
- Test 3: Have the age of delete be >= 72hrs and retain data unsent to Pi System try to purge data that's >= 72hrs
            (expect - Only data that has been sent to Pi gets deleted)
- Test 4: Have the age of delete be >= 72hrs and ignore retaining data unsent to Pi System try to delete data
        that's >= 72hrs
            (expect - All data gets deleted)
- Test 5: Have the age of delete be >=  0hrs and retaining data unsent to Pi System try to purge current data
            (expect - Only data that has been sent to Pi gets deleted)
- Test 6: Have the age of delete be >=  0hrs and ignore retaining data unsent to Pi System try to purge current data
            (expect - All data gets deleted)
            
"""
import asyncio 
import datetime
import pytest
import random
import sqlalchemy
import uuid

from foglamp import configuration_manager
from foglamp.data_purge.purge import (_READING_TABLE, _LOG_TABLE,  execute_command, 
                                      _CONFIG_CATEGORY_NAME, set_configuration, purge)

__author__ = "Ori Shadmon"
__copyright__ = "Copyright (c) 2017 OSI Soft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

"""Support methods for testing"""


@pytest.fixture(scope="module")
def clean_tables(): 
    """"Clean data from reading and log tables. In addition also remove 'PURGE_READ' row from configuration table"""
    config_table = sqlalchemy.Table('configuration', sqlalchemy.MetaData(),
                                    sqlalchemy.Column('key', sqlalchemy.CHAR(10), primary_key=True), 
                                    sqlalchemy.Column('description', sqlalchemy.VARCHAR(255)), 
                                    sqlalchemy.Column('value', sqlalchemy.dialects.postgresql.JSONB, default={}), 
                                    sqlalchemy.Column('ts',  sqlalchemy.TIMESTAMP(6),
                                                      default=sqlalchemy.func.current_timestamp(),
                                                      onupdate=sqlalchemy.func.current_timestamp()))

    execute_command(_READING_TABLE.delete())
    execute_command(_LOG_TABLE.delete())
    execute_command(config_table.delete().where(config_table.c.key == _CONFIG_CATEGORY_NAME)) 


@pytest.fixture(scope="module")
def insert_into_reading():
    """"Insert 1000 rows of data into readings table"""
    insert_stmt = "('%s', '%s', '{}')"
    k = 0 
    for i in range(100): 
        stmt = "INSERT INTO readings(asset_code, read_key, reading) VALUES" 
        for j in range(10): 
            if j == 9:  
                stmt = stmt + " " + insert_stmt % (str(k), uuid.uuid4()) + ";" 
            else: 
                stmt = stmt + " " + insert_stmt % (str(k), uuid.uuid4()) + ", "
            k =+ 1
        execute_command(stmt)


@pytest.fixture(scope="module")
def min_max_id()->(int, int):
    """"Get the min and max IDs from readings table
    :return:
        min_id: smallest row ID in readings table (result[0])  
        max_id: largest row ID in readings table  (result[1]) 
    """
    stmt = sqlalchemy.select([sqlalchemy.func.min(_READING_TABLE.c.id), 
                              sqlalchemy.func.max(_READING_TABLE.c.id)]).select_from(_READING_TABLE)
    result = execute_command(stmt).fetchall()[0]
    return result[0], result[1]


@pytest.fixture(scope="module")
def update_timestamp_values(min_id=0, max_id=1000):
    """"Update the timestamp value to be at least 72 hours old (in chronologically order)
    :args:
        min_id: smallest row ID in readings table
        max_id: largest row ID in readings table
    """
    lower_limit = 0
    min_time = 75
    max_time = 80
    for upper_limit in range(min_id, max_id+10, 100): 
        stmt = sqlalchemy.select([sqlalchemy.func.current_timestamp() - datetime.timedelta(
            hours=random.randint(min_time, max_time))])
        timestamp = execute_command(stmt).fetchall()[0][0]
        stmt = _READING_TABLE.update().values(ts=timestamp, user_ts=timestamp).where(
            _READING_TABLE.c.id <= upper_limit).where(_READING_TABLE.c.id > lower_limit)
        execute_command(stmt)
        lower_limit = upper_limit  
        min_time = max_time
        max_time = max_time+5


@pytest.fixture(scope="module")
def update_last_object(min_id=0, max_id=1000)->int:
    """"Update the last row sent to OSI's Pi System
    :return:
        last_object_id: the last row ID sent to Pi System
    """
    last_object_id = random.randint(min_id+1, max_id-1)
    stmt = "UPDATE streams SET last_object = %s WHERE last_object = (SELECT MIN(last_object) FROM streams);"
    execute_command(stmt % last_object_id)
    return last_object_id
 

@pytest.fixture(scope="module")
def update_configuration(age=72, retain_unsent=False)->dict:
    """"Update the configuration table with the appropriate information regarding "PURE_READ" using pre-existing
        configuration_manager tools
    :args:
        age: corresponds to the `age` value used for purging
        retainUnsent: corresponds to the `retainUnsent` value used for purging
    :return:
        The corresponding values set in the configuration for the purge process 
    """
    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(configuration_manager.set_category_item_value_entry(_CONFIG_CATEGORY_NAME, 
                                                                                      'age', age))
    event_loop.run_until_complete(configuration_manager.set_category_item_value_entry(_CONFIG_CATEGORY_NAME,
                                                                                      'retainUnsent', retain_unsent))
    return event_loop.run_until_complete(configuration_manager.get_category_all_items(_CONFIG_CATEGORY_NAME))


@pytest.fixture(scope="module")
def get_log()->dict:
    """"Get data stored in logs table to be verified
    :return:
        A dictionary of values that are stored in the log table regarding the latest transaction
    """
    return execute_command("SELECT log FROM log").fetchall()[0][0] 


@pytest.fixture(scope="module")
def get_count()->int: 
    """"Get number of rows in table
    :return: 
        row count for readings table
    """
    stmt = sqlalchemy.select([sqlalchemy.func.count()]).select_from(_READING_TABLE)
    return execute_command(stmt).fetchall()[0][0] 

"""Test Cases"""

@pytest.allure.feature("unit")
@pytest.allure.story("data_purge")
def test_config_change():
    """"Test that changes to the config work properly
    :assert:
        age --> Updated age value
        retain_unsent --> Updated retain_unsent value
    """
    clean_tables()
    config = set_configuration()
    assert config['age']['value'] == "72"
    assert config['retainUnsent']['value'] == "False" 

    config = update_configuration(age=0, retain_unsent=True) 
    assert config['age']['value'] == "0" 
    assert config['retainUnsent']['value'] == "True"

    clean_tables()


@pytest.allure.feature("unit")
@pytest.allure.story("data_purge")
def test_default_config():
    """"Test that when the configuration is set to default and data is of now, no rows are being deleted
     :assert:
        age == 72 
        retainUnsent == False
        total_purged -->  Against both a hard-set value (0) and results stored in log
        unsent_purged --> Against both a hard-set value (0) and results stored in log
        results stored in log are asserted either against a hard-set value, or a value that's derived from within
        the test.
    """
    clean_tables() 
    config = set_configuration() 
    assert config['age']['value'] == "72"
    assert config['retainUnsent']['value'] == "False" 
   
    insert_into_reading()
    row_count = get_count() 
    min_id, max_id = min_max_id() 
    update_last_object(min_id=min_id, max_id=max_id)
    total_purged, unsent_purged = purge(config, _READING_TABLE)

    log = get_log() 

    assert total_purged == 0
    assert total_purged == log['rowsRemoved']
    assert unsent_purged == 0 
    assert unsent_purged == log['unsentRowsRemoved'] 
    assert log['failedRemovals'] == 0 
    assert log['rowsRemaining'] == row_count - total_purged 
    clean_tables() 


@pytest.allure.feature("unit")
@pytest.allure.story("data_purge")
def test_enable_retainunsent_default_age():
    """"Test that as long as age is greater than the oldest rows inserted no rows are removed    
    :assert:
        age == 72
        retainUnsent == True
        total_purged -->  Against both a hard-set value (0) and results stored in log
        unsent_purged --> Against both a hard-set value (0) and results stored in log
        results stored in log are asserted either against a hard-set value, or a value that's derived from within
        the test.
    """
    clean_tables()
    set_configuration()
    config = update_configuration(age=72, retain_unsent=True) 
    assert config['age']['value'] == "72"
    assert config['retainUnsent']['value'] == "True" 

    insert_into_reading()
    row_count = get_count() 
    min_id, max_id = min_max_id() 
    update_last_object(min_id=min_id, max_id=max_id)
   
    total_purged, unsent_purged = purge(config, _READING_TABLE)
    log = get_log() 

    assert total_purged == 0
    assert total_purged == log['rowsRemoved']
    assert unsent_purged == 0 
    assert unsent_purged == log['unsentRowsRemoved'] 
    assert log['failedRemovals'] == 0 
    assert log['rowsRemaining'] == row_count - total_purged 
    clean_tables() 


@pytest.allure.feature("unit")
@pytest.allure.story("data_purge")
def test_default_config_old_data(): 
    """"Test all data older than or equal to 72hrs gets dropped
    :assert: 
        age == 72
        retainUnsent == False
        total_purged -->  Against both a hard-set value (row_count) and results stored in log
        unsent_purged --> Against both a hard-set value and results stored in log
        results stored in log are asserted either against a hard-set value, or a value that's derived from within
        the test.
    """
    clean_tables()
    config = set_configuration() 
    assert config['age']['value'] == "72" 
    assert config['retainUnsent']['value'] == "False"
   
    insert_into_reading()
    row_count = get_count()
    min_id, max_id = min_max_id() 
    update_timestamp_values(min_id=min_id, max_id=max_id)  
    last_object_id = update_last_object(min_id=min_id, max_id=max_id)

    total_purged, unsent_purged = purge(config, _READING_TABLE)
    log = get_log()
   
    assert total_purged == row_count
    assert total_purged == log['rowsRemoved'] 
    assert unsent_purged == max_id - last_object_id
    assert unsent_purged == log['unsentRowsRemoved'] 
    assert log['failedRemovals'] == 0 
    assert log['rowsRemaining'] == row_count - total_purged 
    clean_tables()


@pytest.allure.feature("unit")
@pytest.allure.story("data_purge")
def test_enable_retainunsent_default_age_old_data():
    """"Test that only data that's older than 72hrs and has been sent to OSI's PI gets removed
    :assert:
        age == 72
        retainUnsent == True
        total_purged -->  Against both a hard-set value and results stored in log
        unsent_purged --> Against both a hard-set value (0) and results stored in log
        results stored in log are asserted either against a hard-set value, or a value that's derived from within
        the test.
    """
    clean_tables()
    set_configuration() 
    config = update_configuration(age=72, retain_unsent=True) 
    assert config['age']['value'] == "72" 
    assert config['retainUnsent']['value'] == "True"
   
    insert_into_reading()
    row_count = get_count()
    min_id, max_id = min_max_id() 
    update_timestamp_values(min_id=min_id, max_id=max_id)
    last_object_id = update_last_object(min_id=min_id, max_id=max_id)

    total_purged, unsent_purged = purge(config, _READING_TABLE)
    log = get_log()

    assert total_purged == row_count - (max_id - last_object_id)
    assert total_purged == log['rowsRemoved'] 
    assert unsent_purged == 0 
    assert unsent_purged == log['unsentRowsRemoved'] 
    assert log['failedRemovals'] == 0 
    assert log['rowsRemaining'] == row_count - total_purged 
    clean_tables()


@pytest.allure.feature("unit")
@pytest.allure.story("data_purge")
def test_delete_stored_data():
    """"Test that only data that's been sent to Pi  has been deleted
    :assert: 
        age == 72
        retainUnsent == False
        total_purged -->  Against both a hard-set value and results stored in log
        unsent_purged --> Against both a hard-set value (0) and results stored in log
        results stored in log are asserted either against a hard-set value, or a value that's derived from within
        the test.
    """
    clean_tables()
    set_configuration() 
    config = update_configuration(age=0, retain_unsent=True)
    assert config['age']['value'] == "0"
    assert config['retainUnsent']['value'] == "True"

    insert_into_reading()
    row_count = get_count()

    min_id, max_id = min_max_id()
    last_object_id = update_last_object(min_id=min_id, max_id=max_id)

    total_purged, unsent_purged = purge(config, _READING_TABLE)
    log = get_log()

    assert total_purged == row_count - (max_id - last_object_id) 
    assert total_purged == log['rowsRemoved']
    assert unsent_purged == 0
    assert unsent_purged == log['unsentRowsRemoved']
    assert log['failedRemovals'] == 0
    assert log['rowsRemaining'] == row_count - total_purged
    
    clean_tables()


@pytest.allure.feature("unit")
@pytest.allure.story("data_purge")
def test_delete_all_stored_data():
    """"Test that all data has been deleted
    :assert:
        age == 72
        retainUnsent == False
        total_purged -->  Against both a hard-set value and results stored in log
        unsent_purged --> Against both a hard-set value and results stored in log
        results stored in log are asserted either against a hard-set value, or a value that's derived from within
        the test.
    """
    clean_tables()
    set_configuration()
    config = update_configuration(age=0, retain_unsent=False)
    assert config['age']['value'] == "0" 
    assert config['retainUnsent']['value'] == "False"

    insert_into_reading()
    set_configuration()
    row_count = get_count()
    min_id, max_id = min_max_id()
    last_object_id = update_last_object(min_id=min_id, max_id=max_id)

    total_purged, unsent_purged = purge(config, _READING_TABLE)
    log = get_log()

    assert total_purged == row_count
    assert total_purged == log['rowsRemoved']
    assert unsent_purged == max_id - last_object_id
    assert unsent_purged == log['unsentRowsRemoved']
    assert log['failedRemovals'] == 0
    assert log['rowsRemaining'] == row_count - total_purged
    clean_tables()

