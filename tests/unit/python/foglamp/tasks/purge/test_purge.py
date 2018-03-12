# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import pytest
import asyncio
from unittest.mock import patch, call, MagicMock
from foglamp.common import logger
from foglamp.common.storage_client.storage_client import ReadingsStorageClient, StorageClient
from foglamp.common.statistics import Statistics
from foglamp.tasks.purge.purge import Purge
from foglamp.common.process import FoglampProcess
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.common.audit_logger import AuditLogger
from foglamp.common.storage_client.exceptions import *


__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("tasks", "purge")
class TestPurge:
    """Test the units of purge.py"""

    def test_init(self, event_loop):
        """Test that creating an instance of Purge calls init of FoglampProcess and creates loggers"""
        mockStorageClient = MagicMock(spec=StorageClient)
        mockAuditLogger = AuditLogger(mockStorageClient)
        with patch.object(FoglampProcess, "__init__") as mock_process:
            with patch.object(logger, "setup") as log:
                with patch.object(mockAuditLogger, "__init__", return_value=None):
                    p = Purge(loop=event_loop)
                assert isinstance(p, Purge)
                assert isinstance(p._audit, AuditLogger)
            log.assert_called_once_with("Data Purge")
        mock_process.assert_called_once_with()

    def test_write_statistics(self, event_loop):
        """Test that write_statistics calls update statistics with defined keys and value increments"""

        @asyncio.coroutine
        def mock_s_update():
            return ""

        mockStorageClient = MagicMock(spec=StorageClient)
        mockAuditLogger = AuditLogger(mockStorageClient)
        with patch.object(FoglampProcess, '__init__'):
            with patch.object(Statistics, 'update', return_value=mock_s_update()) as mock_stats_update:
                with patch.object(mockAuditLogger, "__init__", return_value=None):
                    p = Purge(loop=event_loop)
                    p._storage = mockStorageClient
                    p.write_statistics(1, 2)
                    mock_stats_update.assert_has_calls([call('PURGED', 1), call('UNSNPURGED', 2)])

    def test_set_configuration(self, event_loop):
        """Test that purge's set_configuration returns configuration item with key 'PURGE_READ' """

        @asyncio.coroutine
        def mock_cm_return():
            return ""

        mockStorageClient = MagicMock(spec=StorageClient)
        mockAuditLogger = AuditLogger(mockStorageClient)
        with patch.object(FoglampProcess, '__init__'):
            with patch.object(mockAuditLogger, "__init__", return_value=None):
                p = Purge(loop=event_loop)
                p._storage = MagicMock(spec=StorageClient)
                mock_cm = ConfigurationManager(p._storage)
                with patch.object(mock_cm, 'create_category', return_value=mock_cm_return()) as mock_create_cat:
                    with patch.object(mock_cm, 'get_category_all_items', return_value=mock_cm_return()) \
                            as mock_get_cat:
                        p.set_configuration()
                        mock_get_cat.assert_called_once_with('PURGE_READ')
                    args, kwargs = mock_create_cat.call_args
                    assert len(args) == 3
                    assert args[0] == 'PURGE_READ'

    @pytest.fixture()
    def store_purge(self, **kwargs):
        if kwargs.get('age') == '-1' or kwargs.get('size') == '-1':
            raise StorageServerError(400, "Bla", "Some Error")
        return {"readings": 10, "removed": 1, "unsentPurged": 2, "unsentRetained": 7}

    config = {"purgeAgeSize": {"retainUnsent": {"value": "False"}, "age": {"value": "72"}, "size": {"value": "20"}},
              "purgeAge": {"retainUnsent": {"value": "False"}, "age": {"value": "72"}, "size": {"value": "0"}},
              "purgeSize": {"retainUnsent": {"value": "False"}, "age": {"value": "0"}, "size": {"value": "100"}},
              "retainAgeSize": {"retainUnsent": {"value": "True"}, "age": {"value": "72"}, "size": {"value": "20"}},
              "retainAge": {"retainUnsent": {"value": "True"}, "age": {"value": "72"}, "size": {"value": "0"}},
              "retainSize": {"retainUnsent": {"value": "True"}, "age": {"value": "0"}, "size": {"value": "100"}}}

    @pytest.mark.parametrize("conf, expected_return, expected_calls", [
        (config["purgeAgeSize"], (2, 4), {'sent_id': 0, 'size': '20', 'flag': 'purge'}),
        (config["purgeAge"], (1, 2), {'sent_id': 0, 'age': '72', 'flag': 'purge'}),
        (config["purgeSize"], (1, 2), {'sent_id': 0, 'size': '100', 'flag': 'purge'}),
        (config["retainAgeSize"], (2, 4), {'sent_id': 0, 'size': '20', 'flag': 'retain'}),
        (config["retainAge"], (1, 2), {'sent_id': 0, 'age': '72', 'flag': 'retain'}),
        (config["retainSize"], (1, 2), {'sent_id': 0, 'size': '100', 'flag': 'retain'})
    ])
    def test_purge_data(self, event_loop, conf, expected_return, expected_calls):
        """Test that purge_data calls Storage's purge with defined configuration"""

        @asyncio.coroutine
        def mock_audit_info():
            return ""

        mockStorageClient = MagicMock(spec=StorageClient)
        mockAuditLogger = AuditLogger(mockStorageClient)

        with patch.object(FoglampProcess, '__init__'):
            with patch.object(mockAuditLogger, "__init__", return_value=None):
                p = Purge(loop=event_loop)
                p._logger = logger
                p._logger.info = MagicMock()
                p._logger.error = MagicMock()
                p._storage = MagicMock(spec=StorageClient)
                p._readings_storage = MagicMock(spec=ReadingsStorageClient)
                audit = p._audit
                with patch.object(p._readings_storage, 'purge', side_effect=self.store_purge) as mock_storage_purge:
                    with patch.object(audit, 'information', return_value=mock_audit_info()) as audit_info:
                        # Test the positive case when all if conditions in purge_data pass
                        assert expected_return == p.purge_data(conf)
                        assert audit_info.called
                        args, kwargs = mock_storage_purge.call_args
                        assert kwargs == expected_calls

    @pytest.mark.parametrize("conf, expected_return", [
        ({"retainUnsent": {"value": "False"}, "age": {"value": "0"}, "size": {"value": "0"}}, (0, 0)),
        ({"retainUnsent": {"value": "True"}, "age": {"value": "0"}, "size": {"value": "0"}}, (0, 0))
    ])
    def test_purge_data_no_data_purged(self, event_loop, conf, expected_return):
        """Test that purge_data logs message when no data was purged"""

        @asyncio.coroutine
        def mock_audit_info():
            return ""

        mockStorageClient = MagicMock(spec=StorageClient)
        mockAuditLogger = AuditLogger(mockStorageClient)

        with patch.object(FoglampProcess, '__init__'):
            with patch.object(mockAuditLogger, "__init__", return_value=None):
                p = Purge(loop=event_loop)
                p._logger = logger
                p._logger.info = MagicMock()
                p._logger.error = MagicMock()
                p._storage = MagicMock(spec=StorageClient)
                p._readings_storage = MagicMock(spec=ReadingsStorageClient)
                audit = p._audit
                with patch.object(p._readings_storage, 'purge', side_effect=self.store_purge):
                    with patch.object(audit, 'information', return_value=mock_audit_info()):
                        assert expected_return == p.purge_data(conf)
                        p._logger.info.assert_called_once_with("No rows purged")

    @pytest.mark.parametrize("conf, expected_return", [
        ({"retainUnsent": {"value": "True"}, "age": {"value": "-1"}, "size": {"value": "-1"}}, (0, 0))
    ])
    def test_purge_error_storage_response(self, event_loop, conf, expected_return):
        """Test that purge_data logs error when storage purge returns an error response"""

        @asyncio.coroutine
        def mock_audit_info():
            return ""

        mockStorageClient = MagicMock(spec=StorageClient)
        mockAuditLogger = AuditLogger(mockStorageClient)

        with patch.object(FoglampProcess, '__init__'):
            with patch.object(mockAuditLogger, "__init__", return_value=None):
                p = Purge(loop=event_loop)
                p._logger = logger
                p._logger.info = MagicMock()
                p._logger.error = MagicMock()
                p._storage = MagicMock(spec=StorageClient)
                p._readings_storage = MagicMock(spec=ReadingsStorageClient)
                audit = p._audit
                with patch.object(p._readings_storage, 'purge', side_effect=self.store_purge):
                    with patch.object(audit, 'information', return_value=mock_audit_info()):
                        assert expected_return == p.purge_data(conf)

    @pytest.mark.parametrize("conf, expected_error_key",
                             [({"retainUnsent": {"value": "True"}, "age": {"value": "bla"}, "size": {"value": "0"}},
                               "age"),
                              ({"retainUnsent": {"value": "True"}, "age": {"value": "0"}, "size": {"value": "bla"}},
                               "size")])
    def test_purge_data_invalid_conf(self, event_loop, conf, expected_error_key):
        """Test that purge_data raises exception when called with invalid configuration"""

        @asyncio.coroutine
        def mock_audit_info():
            return ""

        mockStorageClient = MagicMock(spec=StorageClient)
        mockAuditLogger = AuditLogger(mockStorageClient)

        with patch.object(FoglampProcess, '__init__'):
            with patch.object(mockAuditLogger, "__init__", return_value=None):
                p = Purge(loop=event_loop)
                p._logger = logger
                p._logger.info = MagicMock()
                p._logger.error = MagicMock()
                p._storage = MagicMock(spec=StorageClient)
                p._readings_storage = MagicMock(spec=ReadingsStorageClient)
                audit = p._audit
                with patch.object(p._readings_storage, 'purge', side_effect=self.store_purge):
                    with patch.object(audit, 'information', return_value=mock_audit_info()):
                        # Test the code block when purge failed because of invalid configuration
                        p.purge_data(conf)
                        p._logger.error.assert_called_with('Configuration item {} bla should be integer!'.
                                                           format(expected_error_key))

    def test_run(self, event_loop):
        """Test that run calls all units of purge process"""
        @asyncio.coroutine
        def mock_audit_info():
            return ""

        mockStorageClient = MagicMock(spec=StorageClient)
        mockAuditLogger = AuditLogger(mockStorageClient)

        with patch.object(FoglampProcess, '__init__'):
            with patch.object(mockAuditLogger, "__init__", return_value=None):
                p = Purge(loop=event_loop)
                config = "Some config"
                p._logger.exception = MagicMock()
                with patch.object(p, 'set_configuration', return_value=config) as mock_set_config:
                    with patch.object(p, 'purge_data', return_value=(1, 2)) as mock_purge_data:
                        with patch.object(p, 'write_statistics') as mock_write_stats:
                            p.run()
                # Test the positive case when no error in try block
                mock_set_config.assert_called_once_with()
                mock_purge_data.assert_called_once_with(config)
                mock_write_stats.assert_called_once_with(1, 2)

    def test_run_exception(self, event_loop):
        """Test that run calls all units of purge process and checks the exception handling"""
        @asyncio.coroutine
        def mock_audit_info():
            return ""

        mockStorageClient = MagicMock(spec=StorageClient)
        mockAuditLogger = AuditLogger(mockStorageClient)

        with patch.object(FoglampProcess, '__init__'):
            with patch.object(mockAuditLogger, "__init__", return_value=None):
                p = Purge(loop=event_loop)
                config = "Some config"
                p._logger.exception = MagicMock()
                with patch.object(p, 'set_configuration', return_value=config):
                    with patch.object(p, 'purge_data', return_value=Exception()):
                        with patch.object(p, 'write_statistics'):
                            p.run()
                # Test the negative case when function purge_data raise some exception
                p._logger.exception.assert_called_once_with("'Exception' object is not iterable")
