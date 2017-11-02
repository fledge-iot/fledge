# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import asyncio
from datetime import datetime, timezone, timedelta
import pytest
import random
import uuid
import json

from foglamp import configuration_manager
from foglamp.data_purge.purge import Purge
from foglamp.storage.payload_builder import PayloadBuilder
from foglamp.storage.storage import Storage, Readings

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSI Soft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("data_purge")
class TestPurge:

    # TODO: FOGL-510 Hardcoded core_management_port needs to be removed, should be coming form a test configuration file
    _core_management_port = 39940

    _store = Storage("localhost", _core_management_port)
    _readings = Readings("localhost", _core_management_port)

    _CONFIG_CATEGORY_NAME = 'PURGE_READ'

    @classmethod
    @pytest.fixture(autouse=True)
    def _reset_db(cls):
        """Cleanup method, called after every test"""
        yield
        # Delete all test data from readings and logs
        cls._store.delete_from_tbl("readings", {})
        cls._store.delete_from_tbl("log", {})
    
        # Update statistics
        payload = PayloadBuilder().SET(value=0, previous_value=0).WHERE(["key", "=", "PURGED"]).\
            OR_WHERE(["key", "=", "UNSNPURGED"]).payload()
        cls._store.update_tbl("statistics", payload)
    
        # Update streams
        payload = PayloadBuilder().SET(last_object=0).payload()
        cls._store.update_tbl("streams", payload)

        # Restore default configuration
        cls._update_configuration()
    
    @classmethod
    def _insert_readings_data(cls, hours_delta):
        """Insert reads in readings table with specified time delta of user_ts (in hours)
        args:
            hours_delta: delta of user_ts (in hours)
        :return:
            The id of inserted row
    
        """
        readings = []

        read = dict()
        read["asset_code"] = "TEST_PURGE_UNIT"
        read["read_key"] = str(uuid.uuid4())
        read['reading'] = dict()
        read['reading']['rate'] = random.randint(1, 100)
        ts = str(datetime.now(tz=timezone.utc) - timedelta(hours=hours_delta))
        read["user_ts"] = ts

        readings.append(read)

        payload = dict()
        payload['readings'] = readings

        cls._readings.append(json.dumps(payload))

        payload = PayloadBuilder.AGGREGATE(["max", "id"]).payload()
        result = cls._store.query_tbl_with_payload("readings", payload)
        return int(result["rows"][0]["max_id"])
    
    @classmethod
    def _get_reads(cls):
        """Get values from readings table where asset_code is asset_code of test data
        """

        query_payload = PayloadBuilder().WHERE(["asset_code", "=", 'TEST_PURGE_UNIT']).payload()
        res = cls._readings.query(query_payload)
        return res
    
    @classmethod
    def _update_streams(cls, rows_to_update=1, id_last_object=0):
        """Update the table streams to simulate the last_object sent to historian
        args:
            rows_to_update: Number of rows to update, if -1, will update all rows
            id_last_object: value to update (last_row_id) sent to historian
        """
        if rows_to_update == 1:
            payload = PayloadBuilder().SET(last_object=id_last_object).WHERE(["id", "=", 1]).payload()
            cls._store.update_tbl("streams", payload)
        else:
            payload = PayloadBuilder().SET(last_object=id_last_object).payload()
            cls._store.update_tbl("streams", payload)

    @classmethod
    def _update_configuration(cls, age=72, retain_unsent=False) -> dict:
        """"Update the configuration table with the appropriate information regarding "PURE_READ" using pre-existing
            configuration_manager tools
        args:
            age: corresponds to the `age` value used for purging
            retainUnsent: corresponds to the `retainUnsent` value used for purging
        :return:
            The corresponding values set in the configuration for the purge process
        """
        event_loop = asyncio.get_event_loop()
        event_loop.run_until_complete(configuration_manager.set_category_item_value_entry(cls._CONFIG_CATEGORY_NAME,
                                                                                          'age', age))
        event_loop.run_until_complete(configuration_manager.set_category_item_value_entry(
            cls._CONFIG_CATEGORY_NAME, 'retainUnsent', retain_unsent))
        return event_loop.run_until_complete(configuration_manager.get_category_all_items(cls._CONFIG_CATEGORY_NAME))
    
    @classmethod
    def _get_stats(cls):
        """"Get data stored in statistics table to be verified
        :return:
            Values of column 'value' where key in PURGED, UNSNPURGED
        """
        payload = PayloadBuilder().SELECT("value").WHERE(["key", "=", 'PURGED']).payload()
        result_purged = cls._store.query_tbl_with_payload("statistics", payload)

        payload = PayloadBuilder().SELECT("value").WHERE(["key", "=", 'UNSNPURGED']).payload()
        result_unsnpurged = cls._store.query_tbl_with_payload("statistics", payload)

        return result_purged["rows"][0]["value"], result_unsnpurged["rows"][0]["value"]
    
    @classmethod
    def _get_log(cls):
        """"Get data stored in logs table to be verified
        :return:
            The log level and the log column values
        """
        payload = PayloadBuilder().WHERE(["code", "=", 'PURGE']).ORDER_BY({"ts", "desc"}).LIMIT(1).payload()
        result = cls._store.query_tbl_with_payload("log", payload)
        return int(result["rows"][0]["level"]), result["rows"][0]["log"]
    
    def test_no_read_purge(self):
        """Test that when there is no data in readings table, purge process runs but no data is purged"""
        purge = Purge("localhost", self._core_management_port)
        purge.start()

        log = self._get_log()
        assert log[0] == 0
        assert log[1]["rowsRemoved"] == 0
        assert log[1]["unsentRowsRemoved"] == 0
        assert log[1]["rowsRetained"] == 0
        assert log[1]["rowsRemaining"] == 0

        stats = self._get_stats()
        assert stats[0] == 0
        assert stats[1] == 0
    
    def test_unsent_read_purge_current(self):
        """Test that when there is unsent  data in readings table with user_ts < configured age,
        purge process runs but no data is purged
        Precondition:
            age=72
            retainUnsent=False
            readings in readings table = 1 with user_ts = now()
            last_object in streams = 0 (default for all rows)
        """
        
        last_id = self._insert_readings_data(0)

        purge = Purge("localhost", self._core_management_port)
        purge.start()

        log = self._get_log()
        assert log[0] == 0
        assert log[1]["rowsRemoved"] == 0
        assert log[1]["unsentRowsRemoved"] == 0
        assert log[1]["rowsRetained"] == 1
        assert log[1]["rowsRemaining"] == 1

        stats = self._get_stats()
        assert stats[0] == 0
        assert stats[1] == 0

        readings = self._get_reads()
        assert readings["count"] == 1
        assert readings["rows"][0]["id"] == last_id

    def test_unsent_read_purge_old(self):
        """Test that when there is unsent data in readings table with user_ts >= configured age,
        purge process runs and data is purged
            Precondition:
            age=72
            retainUnsent=False
            readings in readings table = 1 with user_ts = now() - 80 hours
            last_object in streams = 0 (default for all rows)
        """
        
        self._insert_readings_data(80)
        purge = Purge("localhost", self._core_management_port)
        purge.start()

        log = self._get_log()
        assert log[0] == 2
        assert log[1]["rowsRemoved"] == 1
        assert log[1]["unsentRowsRemoved"] == 1
        assert log[1]["rowsRetained"] == 0
        assert log[1]["rowsRemaining"] == 0

        stats = self._get_stats()
        assert stats[0] == 1
        assert stats[1] == 1

        readings = self._get_reads()
        assert readings["count"] == 0

    def test_one_dest_sent_reads_purge(self):
        """Test that when there is data in readings table which is sent to one historian but not to other
         with user_ts >= configured age and user_ts = now(),
        purge process runs and data is purged
        If retainUnsent=False then all readings older than the age passed in,
        regardless of the value of sent will be removed
        Precondition:
            age=72
            retainUnsent=False
            readings in readings table = 2, one with user_ts = [now() - 80 hours], another with user_ts = now()
            last_object in streams = id of last reading (for one row)
        """
        
        self._insert_readings_data(80)
        last_id = self._insert_readings_data(0)
        self._update_streams(rows_to_update=1, id_last_object=last_id)

        purge = Purge("localhost", self._core_management_port)
        purge.start()

        log = self._get_log()
        assert log[0] == 2
        assert log[1]["rowsRemoved"] == 1
        assert log[1]["unsentRowsRemoved"] == 1
        assert log[1]["rowsRetained"] == 1
        assert log[1]["rowsRemaining"] == 1

        stats = self._get_stats()
        assert stats[0] == 1
        assert stats[1] == 1

        readings = self._get_reads()
        assert readings["count"] == 1
        assert readings["rows"][0]["id"] == last_id
    
    def test_all_dest_sent_reads_purge(self):
        """ Test that when there is data in readings table which is sent to all historians
        with user_ts >= configured age and user_ts = now(),
        purge process runs and data is purged
        If retainUnsent=False then all readings older than the age passed in,
        regardless of the value of sent will be removed
        Precondition:
            age=72
            retainUnsent=False
            readings in readings table = 2, one with user_ts = [now() - 80 hours], another with user_ts = now()
            last_object in streams = id of last reading (for all rows)
        """
        
        self._insert_readings_data(80)
        last_id = self._insert_readings_data(0)
        self._update_streams(rows_to_update=-1, id_last_object=last_id)

        purge = Purge("localhost", self._core_management_port)
        purge.start()

        log = self._get_log()
        assert log[0] == 0
        assert log[1]["rowsRemoved"] == 1
        assert log[1]["unsentRowsRemoved"] == 0
        assert log[1]["rowsRetained"] == 0
        assert log[1]["rowsRemaining"] == 1

        stats = self._get_stats()
        assert stats[0] == 1
        assert stats[1] == 0

        readings = self._get_reads()
        assert readings["count"] == 1
        assert readings["rows"][0]["id"] == last_id

    def test_unsent_reads_retain(self):
        """Test that when there is unsent data in readings table with user_ts >= configured age and user_ts=now(),
        purge process runs and data is purged
            Precondition:
            age=72
            retainUnsent=True
            readings in readings table = 2, one with user_ts = [now() - 80 hours], another with user_ts = now()
            last_object in streams = 0 (default for all rows)
        """
        
        self._insert_readings_data(80)
        self._insert_readings_data(0)
        self._update_configuration(age=72, retain_unsent=True)

        purge = Purge("localhost", self._core_management_port)
        purge.start()

        log = self._get_log()
        assert log[0] == 0
        assert log[1]["rowsRemoved"] == 0
        assert log[1]["unsentRowsRemoved"] == 0
        assert log[1]["rowsRetained"] == 2
        assert log[1]["rowsRemaining"] == 2

        stats = self._get_stats()
        assert stats[0] == 0
        assert stats[1] == 0

        readings = self._get_reads()
        assert readings["count"] == 2

    def test_one_dest_sent_reads_retain(self):
        """Test that when there is data in readings table which is sent to one historian but not to other
         with user_ts >= configured age and user_ts = now(),
        purge process runs and data is retained
        Precondition:
            age=72
            retainUnsent=True
            readings in readings table = 2, one with user_ts = [now() - 80 hours], another with user_ts = now()
            last_object in streams = id of last reading (for one row)
        """
        
        self._insert_readings_data(80)
        last_id = self._insert_readings_data(0)
        self._update_configuration(age=72, retain_unsent=True)
        self._update_streams(rows_to_update=1, id_last_object=last_id)

        purge = Purge("localhost", self._core_management_port)
        purge.start()

        log = self._get_log()
        assert log[0] == 0
        assert log[1]["rowsRemoved"] == 0
        assert log[1]["unsentRowsRemoved"] == 0
        assert log[1]["rowsRetained"] == 2
        assert log[1]["rowsRemaining"] == 2

        stats = self._get_stats()
        assert stats[0] == 0
        assert stats[1] == 0

        readings = self._get_reads()
        assert readings["count"] == 2

    def test_all_dest_sent_reads_retain(self):
        """Test that when there is data in readings table which is sent to all historians
         with user_ts >= configured age and user_ts = now(),
        purge process runs and data is purged for only for read where user_ts >= configured age
        Precondition:
            age=72
            retainUnsent=True
            readings in readings table = 2, one with user_ts = [now() - 80 hours], another with user_ts = now()
            last_object in streams = id of last reading (for all rows)
        """
        
        self._insert_readings_data(80)
        last_id = self._insert_readings_data(0)
        self._update_configuration(age=72, retain_unsent=True)
        self._update_streams(rows_to_update=-1, id_last_object=last_id)

        purge = Purge("localhost", self._core_management_port)
        purge.start()

        log = self._get_log()
        assert log[0] == 0
        assert log[1]["rowsRemoved"] == 1
        assert log[1]["unsentRowsRemoved"] == 0
        assert log[1]["rowsRetained"] == 0
        assert log[1]["rowsRemaining"] == 1

        stats = self._get_stats()
        assert stats[0] == 1
        assert stats[1] == 0

        readings = self._get_reads()
        assert readings["count"] == 1
        assert readings["rows"][0]["id"] == last_id
    
    def test_config_age_purge(self):
        """Test that when there is unsent  data in readings table with user_ts < configured age and user_ts=now(),
        data older than configured data is deleted
        Precondition:
            age=10
            retainUnsent=False (default)
           readings in readings table = 2, one with user_ts = [now() - 15 hours], another with user_ts = now()
            last_object in streams = 0 (default for all rows)
        """
        
        self._insert_readings_data(15)
        last_id = self._insert_readings_data(0)
        self._update_configuration(age=15, retain_unsent=False)

        purge = Purge("localhost", self._core_management_port)
        purge.start()

        log = self._get_log()
        assert log[0] == 2
        assert log[1]["rowsRemoved"] == 1
        assert log[1]["unsentRowsRemoved"] == 1
        assert log[1]["rowsRetained"] == 1
        assert log[1]["rowsRemaining"] == 1

        stats = self._get_stats()
        assert stats[0] == 1
        assert stats[1] == 1

        readings = self._get_reads()
        assert readings["count"] == 1
        assert readings["rows"][0]["id"] == last_id
