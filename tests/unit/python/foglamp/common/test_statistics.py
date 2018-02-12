# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from unittest.mock import MagicMock, patch
import pytest
import asyncio

from foglamp.common.statistics import Statistics, _logger
from foglamp.common.storage_client.storage_client import StorageClient


__author__ = "Ashish Jabble, Mark Riddoch"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("common", "statistics")
class TestStatistics:

    def test_init_with_no_storage(self):
        storage_client_mock = None
        with pytest.raises(TypeError) as excinfo:
            Statistics(storage_client_mock)
        assert 'Must be a valid Storage object' == str(excinfo.value)

    def test_init_with_storage(self):
        storage_client_mock = MagicMock(spec=StorageClient)
        s = Statistics(storage_client_mock)
        assert isinstance(s, Statistics)
        assert isinstance(s._storage, StorageClient)

    def test_singleton(self):
        """ Test that two audit loggers share the same state """
        storageMock1 = MagicMock(spec=StorageClient)
        s1 = Statistics(storageMock1)
        storageMock2 = MagicMock(spec=StorageClient)
        s2 = Statistics(storageMock2)
        assert s1._storage == s2._storage
        s1._storage.insert_into_tbl.reset_mock()

    def test_register(self):
        """ Test that audit log results in a database insert """
        storageMock = MagicMock(spec=StorageClient)
        stats = Statistics(storageMock)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(stats.register('T1Stat', 'Test stat'))
        assert stats._storage.insert_into_tbl.called == True
        stats._storage.insert_into_tbl.reset_mock()

    def test_register_twice(self):
        """ Test that audit log results in a database insert """
        storageMock = MagicMock(spec=StorageClient)
        stats = Statistics(storageMock)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(stats.register('T2Stat', 'Test stat'))
        count = stats._storage.insert_into_tbl.call_count
        loop.run_until_complete(stats.register('T2Stat', 'Test stat'))
        assert stats._storage.insert_into_tbl.called == True
        assert count == stats._storage.insert_into_tbl.call_count
        stats._storage.insert_into_tbl.reset_mock()

    def test_keys_not_reloaded(self):
        """ Test that audit log results in a database insert """
        storageMock = MagicMock(spec=StorageClient)
        stats = Statistics(storageMock)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(stats.register('T3Stat', 'Test stat'))
        count = stats._storage.query_tbl_with_payload.call_count
        loop.run_until_complete(stats.register('T3Stat', 'Test stat'))
        assert count == stats._storage.query_tbl_with_payload.call_count

    async def test_update(self):
        storage_client_mock = MagicMock(spec=StorageClient)
        s = Statistics(storage_client_mock)
        payload = '{"where": {"column": "key", "condition": "=", "value": "READING"}, ' \
                  '"expressions": [{"column": "value", "operator": "+", "value": 5}]}'
        expected_result = {"response": "updated", "rows_affected": 1}
        with patch.object(s._storage, 'update_tbl', return_value=expected_result) as stat_update:
            await s.update('READING', 5)
            stat_update.assert_called_once_with('statistics', payload)
            assert "updated" == expected_result['response']

    @pytest.mark.parametrize("key, value_increment, exception_name, exception_message", [
        (123456, 120, TypeError, "key must be a string"),
        ('PURGED', '120', ValueError, "value must be an integer"),
        (None, '120', TypeError, "key must be a string"),
        ('123456', '120', ValueError, "value must be an integer"),
        ('READINGS', None, ValueError, "value must be an integer")
    ])
    async def test_update_with_invalid_params(self, key, value_increment, exception_name, exception_message):
        storage_client_mock = MagicMock(spec=StorageClient)
        s = Statistics(storage_client_mock)

        with pytest.raises(exception_name) as excinfo:
            await s.update(key, value_increment)
        assert exception_message == str(excinfo.value)

    async def test_update_exception(self):
        storage_client_mock = MagicMock(spec=StorageClient)
        s = Statistics(storage_client_mock)
        msg = 'Unable to update statistics value based on statistics_key %s and value_increment %d,' \
              ' error %s', 'BUFFERED', 5, ''
        with patch.object(s._storage, 'update_tbl', side_effect=Exception()):
            with pytest.raises(Exception):
                with patch.object(_logger, 'exception') as logger_exception:
                    await s.update('BUFFERED', 5)
            logger_exception.assert_called_once_with(*msg)

    async def test_add_update(self):
        stat_dict = {'FOGBENCH/TEMPERATURE': 1}
        storage_client_mock = MagicMock(spec=StorageClient)
        s = Statistics(storage_client_mock)
        payload = '{"where": {"column": "key", "condition": "=", "value": "FOGBENCH/TEMPERATURE"}, ' \
                  '"expressions": [{"column": "value", "operator": "+", "value": 1}]}'
        expected_result = {"response": "updated", "rows_affected": 1}
        with patch.object(s._storage, 'update_tbl', return_value=expected_result) as stat_update:
            await s.add_update(stat_dict)
            stat_update.assert_called_once_with('statistics', payload)
            assert "updated" == expected_result['response']

    async def test_insert_when_key_error(self):
        stat_dict = {'FOGBENCH/TEMPERATURE': 1}
        storage_client_mock = MagicMock(spec=StorageClient)
        s = Statistics(storage_client_mock)
        payload = '{"previous_value": 0, "value": 1, "key": "FOGBENCH/TEMPERATURE", ' \
                  '"description": "The number of readings received by FogLAMP since startup' \
                  ' for sensor FOGBENCH/TEMPERATURE"}'
        with pytest.raises(KeyError) as excinfo:
            await s.add_update(stat_dict)

    async def test_add_update_exception(self):
        stat_dict = {'FOGBENCH/TEMPERATURE': 1}
        storage_client_mock = MagicMock(spec=StorageClient)
        s = Statistics(storage_client_mock)
        msg = 'Unable to update statistics value based on statistics_key %s and value_increment' \
              ' %s, error %s', "FOGBENCH/TEMPERATURE", 1, ''
        with patch.object(s._storage, 'update_tbl', side_effect=Exception()):
            with pytest.raises(Exception):
                with patch.object(_logger, 'exception') as logger_exception:
                    await s.add_update(stat_dict)
            logger_exception.assert_called_once_with(*msg)
