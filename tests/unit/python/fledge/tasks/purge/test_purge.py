# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import json
import pytest
import asyncio
import sys
from unittest.mock import patch, call, MagicMock
from fledge.common import logger
from fledge.common.storage_client.storage_client import StorageClientAsync, ReadingsStorageClientAsync
from fledge.common.statistics import Statistics
from fledge.tasks.purge.purge import Purge
from fledge.common.process import FledgeProcess
from fledge.common.configuration_manager import ConfigurationManager
from fledge.common.audit_logger import AuditLogger
from fledge.common.storage_client.exceptions import *


__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@asyncio.coroutine
def q_result(*args):
    table = args[0]
    if table == 'streams':
        rows = {"rows": [{"min_last_object": 0}], "count": 1}
        if len(args) == 2 and args[1] == 'any':
            rows = {"rows": [{"max_last_object": 0}], "count": 1}
        return rows


async def mock_value(val):
    return val


@pytest.allure.feature("unit")
@pytest.allure.story("tasks", "purge")
class TestPurge:
    """Test the units of purge.py"""

    def test_init(self):
        """Test that creating an instance of Purge calls init of FledgeProcess and creates loggers"""
        mock_storage_client_async = MagicMock(spec=StorageClientAsync)
        mock_audit_logger = AuditLogger(mock_storage_client_async)
        with patch.object(FledgeProcess, "__init__") as mock_process:
            with patch.object(logger, "setup") as log:
                with patch.object(mock_audit_logger, "__init__", return_value=None):
                    p = Purge()
                    assert isinstance(p, Purge)
                    assert isinstance(p._audit, AuditLogger)
            log.assert_called_once_with("Data Purge")
        mock_process.assert_called_once_with()

    async def test_write_statistics(self):
        """Test that write_statistics calls update statistics with defined keys and value increments"""

        mock_storage_client_async = MagicMock(spec=StorageClientAsync)
        mock_audit_logger = AuditLogger(mock_storage_client_async)
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        _rv = await mock_value("") if sys.version_info.major == 3 and sys.version_info.minor >= 8 else \
            asyncio.ensure_future(mock_value(""))
        
        with patch.object(FledgeProcess, '__init__'):
            with patch.object(Statistics, '_load_keys', return_value=_rv):
                with patch.object(Statistics, 'update', return_value=_rv) as mock_stats_update:
                    with patch.object(mock_audit_logger, "__init__", return_value=None):
                        p = Purge()
                        p._storage_async = mock_storage_client_async
                        await p.write_statistics(1, 2)
                mock_stats_update.assert_has_calls([call('PURGED', 1), call('UNSNPURGED', 2)])

    async def test_set_configuration(self):
        """Test that purge's set_configuration returns configuration item with key 'PURGE_READ' """
        mock_storage_client_async = MagicMock(spec=StorageClientAsync)
        mock_audit_logger = AuditLogger(mock_storage_client_async)
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        _rv = await mock_value("") if sys.version_info.major == 3 and sys.version_info.minor >= 8 else \
            asyncio.ensure_future(mock_value(""))
        with patch.object(FledgeProcess, '__init__'):
            with patch.object(mock_audit_logger, "__init__", return_value=None):
                p = Purge()
                p._storage = MagicMock(spec=StorageClientAsync)
                mock_cm = ConfigurationManager(p._storage)
                with patch.object(mock_cm, 'create_category', return_value=_rv) as mock_create_cat:
                    with patch.object(mock_cm, 'create_child_category', return_value=_rv) as mock_create_child_cat:
                        with patch.object(mock_cm, 'get_category_all_items', return_value=_rv) as mock_get_cat:
                            await p.set_configuration()
                        mock_get_cat.assert_called_once_with('PURGE_READ')
                    mock_create_child_cat.assert_called_once_with('Utilities', ['PURGE_READ'])
                args, _ = mock_create_cat.call_args
                assert 4 == len(args)
                assert 5 == len(args[1].keys())
                assert 'PURGE_READ' == args[0]
                assert 'Purge the readings, log, statistics history table' == args[2]
                assert args[3] is True

    @pytest.fixture()
    async def store_purge(self, **kwargs):
        if kwargs.get('age') == '-1' or kwargs.get('size') == '-1':
            raise StorageServerError(400, "Bla", "Some Error")
        return {"readings": 10, "removed": 1, "unsentPurged": 2, "unsentRetained": 7}

    config = {"purgeAgeSize": {"retainUnsent": {"value": "purge unsent"}, "age": {"value": "72"}, "size": {"value": "20"}},
              "purgeAge": {"retainUnsent": {"value": "purge unsent"}, "age": {"value": "72"}, "size": {"value": "0"}},
              "purgeSize": {"retainUnsent": {"value": "purge unsent"}, "age": {"value": "0"}, "size": {"value": "100"}},
              "retainAgeSize": {"retainUnsent": {"value": "retain unsent to all destinations"}, "age": {"value": "72"}, "size": {"value": "20"}},
              "retainAge": {"retainUnsent": {"value": "retain unsent to all destinations"}, "age": {"value": "72"}, "size": {"value": "0"}},
              "retainSize": {"retainUnsent": {"value": "retain unsent to all destinations"}, "age": {"value": "0"}, "size": {"value": "100"}},
              "retainSizeAny": {"retainUnsent": {"value": "retain unsent to any destination"}, "age": {"value": "0"}, "size": {"value": "100"}}
              }

    @pytest.mark.parametrize("conf, expected_return, expected_calls", [
        (config["purgeAgeSize"], (2, 4), {'sent_id': 0, 'size': '20', 'flag': 'purge'}),
        (config["purgeAge"], (1, 2), {'sent_id': 0, 'age': '72', 'flag': 'purge'}),
        (config["purgeSize"], (1, 2), {'sent_id': 0, 'size': '100', 'flag': 'purge'}),
        (config["retainAgeSize"], (2, 4), {'sent_id': 0, 'size': '20', 'flag': 'retainall'}),
        (config["retainAge"], (1, 2), {'sent_id': 0, 'age': '72', 'flag': 'retainall'}),
        (config["retainSize"], (1, 2), {'sent_id': 0, 'size': '100', 'flag': 'retainall'}),
        (config["retainSizeAny"], (1, 2), {'sent_id': 0, 'size': '100', 'flag': 'retainany'})
    ])
    async def test_purge_data(self, conf, expected_return, expected_calls):
        """Test that purge_data calls Storage's purge with defined configuration"""
        mock_storage_client_async = MagicMock(spec=StorageClientAsync)
        mock_audit_logger = AuditLogger(mock_storage_client_async)
        mock_stream_result = q_result('streams')
        payload = {"aggregate": {"operation": "min", "column": "last_object"}}
        if expected_calls["flag"] == "retainany":
            mock_stream_result = q_result('streams', 'any')
            payload = {"aggregate": {"operation": "max", "column": "last_object"}}
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await mock_stream_result
            _rv2 = await mock_value("")
        else:
            _rv1 = asyncio.ensure_future(mock_stream_result)
            _rv2 = asyncio.ensure_future(mock_value(""))

        with patch.object(FledgeProcess, '__init__'):
            with patch.object(mock_audit_logger, "__init__", return_value=None):
                p = Purge()
                p._logger = logger
                p._logger.info = MagicMock()
                p._logger.error = MagicMock()
                p._logger.debug = MagicMock()
                p._storage_async = MagicMock(spec=StorageClientAsync)
                p._readings_storage_async = MagicMock(spec=ReadingsStorageClientAsync)
                audit = p._audit
                with patch.object(p._storage_async, "query_tbl_with_payload", return_value=_rv1) as patch_storage:
                    with patch.object(p._readings_storage_async, 'purge',
                                      side_effect=self.store_purge) as mock_storage_purge:
                        with patch.object(audit, 'information', return_value=_rv2) as audit_info:
                            # Test the positive case when all if conditions in purge_data pass
                            t_expected_return = await p.purge_data(conf)
                            assert expected_return == await p.purge_data(conf)
                        assert audit_info.called
                    _, kwargs = mock_storage_purge.call_args
                    assert kwargs == expected_calls
                assert patch_storage.called
                assert 4 == patch_storage.call_count
                args, _ = patch_storage.call_args
                assert 'streams' == args[0]
                assert payload == json.loads(args[1])

    @pytest.mark.parametrize("conf, expected_return", [
        ({"retainUnsent": {"value": "purge unsent"}, "age": {"value": "0"}, "size": {"value": "0"}}, (0, 0)),
        ({"retainUnsent": {"value": "retain unsent to all destinations"}, "age": {"value": "0"},
          "size": {"value": "0"}}, (0, 0))
    ])
    async def test_purge_data_no_data_purged(self, conf, expected_return):
        """Test that purge_data logs message when no data was purged"""
        mock_storage_client_async = MagicMock(spec=StorageClientAsync)
        mock_audit_logger = AuditLogger(mock_storage_client_async)

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await q_result('streams')
            _rv2 = await mock_value("")
        else:
            _rv1 = asyncio.ensure_future(q_result('streams'))
            _rv2 = asyncio.ensure_future(mock_value(""))
        
        with patch.object(FledgeProcess, '__init__'):
            with patch.object(mock_audit_logger, "__init__", return_value=None):
                p = Purge()
                p._logger = logger
                p._logger.info = MagicMock()
                p._logger.error = MagicMock()
                p._storage_async = MagicMock(spec=StorageClientAsync)
                p._readings_storage_async = MagicMock(spec=ReadingsStorageClientAsync)
                audit = p._audit
                with patch.object(p._storage_async, "query_tbl_with_payload",
                                  return_value=_rv1) as patch_storage:
                    with patch.object(p._readings_storage_async, 'purge', side_effect=self.store_purge):
                        with patch.object(audit, 'information', return_value=_rv2):
                            assert expected_return == await p.purge_data(conf)
                            p._logger.info.assert_called_once_with("No rows purged")
                assert patch_storage.called
                assert 2 == patch_storage.call_count

    @pytest.mark.parametrize("conf, expected_return", [
        ({"retainUnsent": {"value": "retain unsent to all destinations"}, "age": {"value": "-1"},
          "size": {"value": "-1"}}, (0, 0))
    ])
    async def test_purge_error_storage_response(self, conf, expected_return):
        """Test that purge_data logs error when storage purge returns an error response"""
        mock_storage_client_async = MagicMock(spec=StorageClientAsync)
        mock_audit_logger = AuditLogger(mock_storage_client_async)

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await q_result('streams')
            _rv2 = await mock_value("")
        else:
            _rv1 = asyncio.ensure_future(q_result('streams'))
            _rv2 = asyncio.ensure_future(mock_value(""))
        
        with patch.object(FledgeProcess, '__init__'):
            with patch.object(mock_audit_logger, "__init__", return_value=None):
                p = Purge()
                p._logger = logger
                p._logger.info = MagicMock()
                p._logger.error = MagicMock()
                p._storage_async = MagicMock(spec=StorageClientAsync)
                p._readings_storage_async = MagicMock(spec=ReadingsStorageClientAsync)
                audit = p._audit
                with patch.object(p._storage_async, "query_tbl_with_payload",
                                  return_value=_rv1) as patch_storage:
                    with patch.object(p._readings_storage_async, 'purge', side_effect=self.store_purge):
                        with patch.object(audit, 'information', return_value=_rv2):
                            assert expected_return == await p.purge_data(conf)
                assert patch_storage.called
                assert 2 == patch_storage.call_count

    @pytest.mark.parametrize("conf, expected_error_key", [
        ({"retainUnsent": {"value": "retain unsent to all destinations"}, "age": {"value": "bla"},
          "size": {"value": "0"}}, "age"),
        ({"retainUnsent": {"value": "retain unsent to all destinations"}, "age": {"value": "0"},
          "size": {"value": "bla"}}, "size")])
    async def test_purge_data_invalid_conf(self, conf, expected_error_key):
        """Test that purge_data raises exception when called with invalid configuration"""
        mock_storage_client_async = MagicMock(spec=StorageClientAsync)
        mock_audit_logger = AuditLogger(mock_storage_client_async)
        expected_error_message = 'purge_data - Configuration item {} bla should be integer!'.format(expected_error_key)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await q_result('streams')
            _rv2 = await mock_value("")
        else:
            _rv1 = asyncio.ensure_future(q_result('streams'))
            _rv2 = asyncio.ensure_future(mock_value(""))
        
        with patch.object(FledgeProcess, '__init__'):
            with patch.object(mock_audit_logger, "__init__", return_value=None):
                p = Purge()
                p._logger = logger
                p._logger.info = MagicMock()
                p._logger.error = MagicMock()
                p._storage_async = MagicMock(spec=StorageClientAsync)
                p._readings_storage_async = MagicMock(spec=ReadingsStorageClientAsync)
                audit = p._audit
                with patch.object(p._storage_async, "query_tbl_with_payload", return_value=_rv1) as patch_storage:
                    with patch.object(p._readings_storage_async, 'purge', side_effect=self.store_purge):
                        with patch.object(audit, 'information', return_value=_rv2):
                            # Test the code block when purge failed because of invalid configuration
                            await p.purge_data(conf)
                            p._logger.error.assert_called_with(expected_error_message)
                assert patch_storage.called
                assert 2 == patch_storage.call_count

    async def test_run(self):
        """Test that run calls all units of purge process"""
        mock_storage_client_async = MagicMock(spec=StorageClientAsync)
        mock_audit_logger = AuditLogger(mock_storage_client_async)

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await mock_value("Some config")
            _rv2 = await mock_value((1, 2))
            _rv3 = await mock_value(None)
        else:
            _rv1 = asyncio.ensure_future(mock_value("Some config"))
            _rv2 = asyncio.ensure_future(mock_value((1, 2)))
            _rv3 = asyncio.ensure_future(mock_value(None))
        
        with patch.object(FledgeProcess, '__init__'):
            with patch.object(mock_audit_logger, "__init__", return_value=None):
                p = Purge()
                p._logger.exception = MagicMock()
                with patch.object(p, 'set_configuration', return_value=_rv1) as mock_set_config:
                    with patch.object(p, 'purge_data', return_value=_rv2) as mock_purge_data:
                        with patch.object(p, 'write_statistics', return_value=_rv3) as mock_write_stats:
                            with patch.object(p, 'purge_stats_history', return_value=_rv3) as mock_purge_stats_history:
                                with patch.object(p, 'purge_audit_trail_log', return_value=_rv3) as mock_purge_audit:
                                    await p.run()
                                    # Test the positive case when no error in try block
                                mock_purge_audit.assert_called_once_with("Some config")
                            mock_purge_stats_history.assert_called_once_with("Some config")
                        mock_write_stats.assert_called_once_with(1, 2)
                    mock_purge_data.assert_called_once_with("Some config")
                mock_set_config.assert_called_once_with()

    async def test_run_exception(self, event_loop):
        """Test that run calls all units of purge process and checks the exception handling"""

        async def mock_purge(x):
            await asyncio.sleep(0.1)
            raise Exception("")

        mock_storage_client_async = MagicMock(spec=StorageClientAsync)
        mock_audit_logger = AuditLogger(mock_storage_client_async)

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        _rv = await mock_value("Some config") if sys.version_info.major == 3 and sys.version_info.minor >= 8 else \
            asyncio.ensure_future(mock_value("Some config"))

        with patch.object(FledgeProcess, '__init__'):
            with patch.object(mock_audit_logger, "__init__", return_value=None):
                p = Purge()
                p._logger.exception = MagicMock()
                with patch.object(p, 'set_configuration', return_value=_rv):
                    with patch.object(p, 'purge_data', side_effect=mock_purge):
                        with patch.object(p, 'write_statistics'):
                            await p.run()
                # Test the negative case when function purge_data raise some exception
                p._logger.exception.assert_called_once_with("")
