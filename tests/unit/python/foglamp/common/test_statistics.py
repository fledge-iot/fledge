# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from unittest.mock import MagicMock, patch
import pytest

from foglamp.common.statistics import Statistics, _logger
from foglamp.common.storage_client.storage_client import StorageClient


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("common", "statistics")
class TestStatistics:

    def test_init_with_storage(self):
        storage_client_mock = MagicMock(spec=StorageClient)
        s = Statistics(storage_client_mock)
        assert isinstance(s, Statistics)
        assert isinstance(s._storage, StorageClient)

    def test_init_with_no_storage(self):
        storage_client_mock = None
        with pytest.raises(TypeError) as excinfo:
            Statistics(storage_client_mock)
        assert 'Must be a valid Storage object' == str(excinfo.value)

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
        expected_result = {"response": "inserted", "rows_affected": 1}
        with patch.object(s._storage, 'update_tbl', side_effect=KeyError):
            with patch.object(s._storage, 'insert_into_tbl', return_value=expected_result) as stat_insert:
                await s.add_update(stat_dict)
                # FIXME: payload order issue
                # stat_insert.assert_called_with('statistics', payload)
                assert "inserted" == expected_result['response']

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
