# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Test tasks/statistics/statistics_history.py"""

import asyncio
from unittest.mock import patch, MagicMock
import pytest
from datetime import datetime
import ast
from foglamp.common import logger
from foglamp.common.storage_client.storage_client import StorageClientAsync
from foglamp.tasks.statistics.statistics_history import StatisticsHistory
from foglamp.common.process import FoglampProcess

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


pytestmark = pytest.mark.asyncio

@asyncio.coroutine
def mock_coro(*args, **kwargs):
    if len(args) > 0:
        return args[0]
    else:
        return ""


@pytest.allure.feature("unit")
@pytest.allure.story("tasks", "statistics")
class TestStatisticsHistory:
    """Test the units of statistics_history.py
    """

    async def test_init(self):
        """Test that creating an instance of StatisticsHistory calls init of FoglampProcess and creates loggers"""
        with patch.object(FoglampProcess, "__init__") as mock_process:
            with patch.object(logger, "setup") as log:
                sh = StatisticsHistory()
                assert isinstance(sh, StatisticsHistory)
            log.assert_called_once_with("StatisticsHistory")
        mock_process.assert_called_once_with()

    async def test_stats_keys(self):
        storage_return = {'count': 10,
                          'rows': [{'key': 'PURGED'}, {'key': 'SENT_4'}, {'key': 'UNSENT'}, {'key': 'SENT_2'},
                                   {'key': 'SENT_1'}, {'key': 'READINGS'}, {'key': 'BUFFERED'}, {'key': 'UNSNPURGED'},
                                   {'key': 'DISCARDED'}]}
        mockStorageClientAsync = MagicMock(spec=StorageClientAsync)
        with patch.object(FoglampProcess, '__init__'):
            with patch.object(logger, "setup"):
                sh = StatisticsHistory()
                sh._storage_async = mockStorageClientAsync
                with patch.object(sh._storage_async, "query_tbl_with_payload", return_value=mock_coro(storage_return)) as patch_storage:
                    stats_keys = await sh._stats_keys()
                    assert stats_keys == ['PURGED', 'SENT_4', 'UNSENT', 'SENT_2', 'SENT_1',
                                                'READINGS', 'BUFFERED', 'UNSNPURGED', 'DISCARDED']
                    patch_storage.assert_called_once_with('statistics', '{"modifier": "distinct", "return": ["key"]}')

    async def test_insert_into_stats_history(self):
        mockStorageClientAsync = MagicMock(spec=StorageClientAsync)
        with patch.object(FoglampProcess, '__init__'):
            with patch.object(logger, "setup"):
                sh = StatisticsHistory()
                sh._storage_async = mockStorageClientAsync
                with patch.object(sh._storage_async, "insert_into_tbl", return_value=mock_coro(None)) as patch_storage:
                    ts = datetime.now()
                    await sh._insert_into_stats_history(key='Bla', value=1, history_ts=ts)
                    args, kwargs = patch_storage.call_args
                    assert args[0] == "statistics_history"
                    payload = ast.literal_eval(args[1])
                    assert payload["key"] == "Bla"
                    assert payload["value"] == 1
                    try:
                        datetime.strptime(payload["history_ts"], "%Y-%m-%d %H:%M:%S.%f")
                        assert True
                    except ValueError:
                        assert False

    async def test_update_previous_value(self):
        mockStorageClientAsync = MagicMock(spec=StorageClientAsync)
        with patch.object(FoglampProcess, '__init__'):
            with patch.object(logger, "setup"):
                sh = StatisticsHistory()
                sh._storage_async = mockStorageClientAsync
                with patch.object(sh._storage_async, "update_tbl", return_value=mock_coro(None)) as patch_storage:
                    await sh._update_previous_value(key='Bla', value=1)
                    args, kwargs = patch_storage.call_args
                    assert args[0] == "statistics"
                    payload = ast.literal_eval(args[1])
                    assert payload["where"]["value"] == "Bla"
                    assert payload["values"]["previous_value"] == 1

    async def test_select_from_statistics(self):
        mockStorageClientAsync = MagicMock(spec=StorageClientAsync)
        with patch.object(FoglampProcess, '__init__'):
            with patch.object(logger, "setup"):
                sh = StatisticsHistory()
                sh._storage_async = mockStorageClientAsync
                with patch.object(sh._storage_async, "query_tbl_with_payload", return_value=mock_coro({"a": 1})) as patch_storage:
                    val = await sh._select_from_statistics(key='Bla')
                    assert val == {"a": 1}
                    args, kwargs = patch_storage.call_args
                    assert args[0] == "statistics"
                    payload = ast.literal_eval(args[1])
                    assert payload["where"]["value"] == "Bla"

    async def test_run(self):
        mockStorageClientAsync = MagicMock(spec=StorageClientAsync)
        with patch.object(FoglampProcess, '__init__'):
            with patch.object(logger, "setup"):
                sh = StatisticsHistory()
                sh._storage_async = mockStorageClientAsync
                retval = {'rows': [
                    {'previous_value': 1, 'value': 5, 'key': 'PURGED'}], 'count': 1}
                with patch.object(sh, "_stats_keys", return_value=mock_coro(['PURGED'])) as mock_keys:
                    with patch.object(sh, "_select_from_statistics", return_value=mock_coro(retval)) as mock_select_stat:
                        with patch.object(sh, "_insert_into_stats_history", return_value=mock_coro(None)) as mock_insert_history:
                            with patch.object(sh, "_update_previous_value", return_value=mock_coro(None)) as mock_update:
                                await sh.run()
                            mock_update.assert_called_once_with(key='PURGED', value=5)
                        args, kwargs = mock_insert_history.call_args
                        assert kwargs["key"] == "PURGED"
                    mock_select_stat.assert_called_once_with(key='PURGED')
                mock_keys.assert_called_once_with()
