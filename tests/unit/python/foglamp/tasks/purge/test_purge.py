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


__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("tasks", "purge")
class TestPurge:
    """Test the units of purge.py"""

    def test_init(self):
        """Test that creating an instance of Purge calls init of FoglampProcess and creates loggers"""
        mock_store = MagicMock(spec=StorageClient)
        mock_ad = AuditLogger(mock_store)
        with patch.object(FoglampProcess, "__init__") as mock_process:
            with patch.object(logger, "setup") as log:
                with patch.object(mock_ad, "__init__", return_value=None):
                    p = Purge()
                assert isinstance(p._audit, AuditLogger)
            log.assert_called_once_with("Data Purge")
        mock_process.assert_called_once_with()

    def test_write_statistics(self):
        """Test that write_statistics calls update statistics with defined keys and value increments"""
        with patch.object(FoglampProcess, '__init__'):
            with patch.object(Statistics, '__init__', return_value=None):
                with patch.object(Statistics, 'update', return_value=asyncio.ensure_future(asyncio.sleep(0.1)))\
                        as mock_update:
                    p = Purge()
                    p.write_statistics(1, 2)
                    mock_update.assert_has_calls([call('PURGED', 1), call('UNSNPURGED', 2)])

    def test_set_configuration(self):
        """Test that purge's set_configuration returns configuration item with key 'PURGE_READ' """
        with patch.object(FoglampProcess, '__init__'):
            p = Purge()
            p._storage = MagicMock(spec=StorageClient)
            mock_cm = ConfigurationManager(p._storage)
            with patch.object(mock_cm, 'get_category_all_items', return_value=asyncio.ensure_future(asyncio.sleep(0.1))) \
                    as mock_get_cat:
                p.set_configuration()
                mock_get_cat.assert_called_once_with('PURGE_READ')

    @pytest.fixture()
    def store_purge(self, **kwargs):
        if kwargs.get('age') == '-1' or kwargs.get('size') == '-1':
            return {"message": "409 Conflict"}
        return {"readings": 10, "removed": 1, "unsentPurged": 2, "unsentRetained": 7}

    config = [{"retainUnsent": {"value": "False"}, "age": {"value": "72"}, "size": {"value": "20"}},
              {"retainUnsent": {"value": "False"}, "age": {"value": "72"}, "size": {"value": "0"}},
              {"retainUnsent": {"value": "False"}, "age": {"value": "0"}, "size": {"value": "100"}},
              {"retainUnsent": {"value": "True"}, "age": {"value": "72"}, "size": {"value": "20"}},
              {"retainUnsent": {"value": "True"}, "age": {"value": "72"}, "size": {"value": "0"}},
              {"retainUnsent": {"value": "True"}, "age": {"value": "0"}, "size": {"value": "100"}},
              {"retainUnsent": {"value": "False"}, "age": {"value": "0"}, "size": {"value": "0"}},
              {"retainUnsent": {"value": "True"}, "age": {"value": "0"}, "size": {"value": "0"}},
              {"retainUnsent": {"value": "True"}, "age": {"value": "-1"}, "size": {"value": "-1"}},
              {"retainUnsent": {"value": "True"}, "age": {"value": "bla"}, "size": {"value": "0"}},
              {"retainUnsent": {"value": "True"}, "age": {"value": "0"}, "size": {"value": "bla"}}]

    @pytest.mark.parametrize("conf, expected_return, expected_calls, valid_purge, valid_store_return", [
        (config[0], (2, 4), {'sent_id': 0, 'size': '20', 'flag': 'purge'}, True, True),
        (config[1], (1, 2), {'sent_id': 0, 'age': '72', 'flag': 'purge'}, True, True),
        (config[2], (1, 2), {'sent_id': 0, 'size': '100', 'flag': 'purge'}, True, True),
        (config[3], (2, 4), {'sent_id': 0, 'size': '20', 'flag': 'retain'}, True, True),
        (config[4], (1, 2), {'sent_id': 0, 'age': '72', 'flag': 'retain'}, True, True),
        (config[5], (1, 2), {'sent_id': 0, 'size': '100', 'flag': 'retain'}, True, True),
        (config[6], (0, 0), {'sent_id': 0, 'size': '100', 'flag': 'retain'}, False, True),
        (config[7], (0, 0), {'sent_id': 0, 'size': '100', 'flag': 'retain'}, False, True),
        (config[8], (0, 0), {'sent_id': 0, 'size': '100', 'flag': 'retain'}, True, False),
        (config[9], (0, 0), {'sent_id': 0, 'size': '100', 'flag': 'retain'}, False, False),
        (config[10], (0, 0), {'sent_id': 0, 'size': '100', 'flag': 'retain'}, False, False)
    ])
    def test_purge_data(self, conf, expected_return, expected_calls, valid_purge, valid_store_return):
        """Test that purge_data calls Storage's purge with defined values"""
        with patch.object(FoglampProcess, '__init__'):
            p = Purge()
            p._logger = logger
            p._logger.info = MagicMock()
            p._logger.error = MagicMock()
            p._storage = MagicMock(spec=StorageClient)
            p._readings_storage = MagicMock(spec=ReadingsStorageClient)
            audit = p._audit
            with patch.object(p._readings_storage, 'purge', side_effect=self.store_purge) as mock_storage_purge:
                with patch.object(audit, 'information', return_value=asyncio.ensure_future(asyncio.sleep(0.1))) \
                        as audit_info:
                    # Test the positive case when all if conditions in purge_data pass
                    if valid_purge and valid_store_return:
                        assert expected_return == p.purge_data(conf)
                        assert audit_info.called
                        args, kwargs = mock_storage_purge.call_args
                        assert kwargs == expected_calls
                    # Test the code block when no rows were purged
                    elif not valid_purge and valid_store_return:
                        assert expected_return == p.purge_data(conf)
                        p._logger.info.assert_called_once_with("No rows purged")
                    # Test the code block when purge failed
                    elif valid_purge and not valid_store_return:
                        assert expected_return == p.purge_data(conf)
                        p._logger.error.assert_called_with('Purge failed: %s', '409 Conflict')
                    # Test the code block when purge failed because of invalid configuration
                    else:
                        with pytest.raises(ValueError):
                            assert expected_return == p.purge_data(conf)
                        p._logger.error.assert_called_with('Configuration bla should be integer!')

    @pytest.mark.parametrize("input, expected_error", [
        ((1, 2), False),
        (Exception(), True),
    ])
    def test_run(self, input, expected_error):
        """Test that run calls all units of purge process"""
        with patch.object(FoglampProcess, '__init__'):
            p = Purge()
            config = "Some config"
            p._logger.exception = MagicMock()
            with patch.object(p, 'set_configuration', return_value=config) as mock_set_config:
                with patch.object(p, 'purge_data', return_value=input) as mock_purge_data:
                    with patch.object(p, 'write_statistics') as mock_write_stats:
                        p.run()
            # Test the positive case when no error in try block
            if not expected_error:
                mock_set_config.assert_called_once_with()
                mock_purge_data.assert_called_once_with(config)
                mock_write_stats.assert_called_once_with(1, 2)
            # Test the negative case when function purge_data raise some exception
            else:
                p._logger.exception.assert_called_once_with("'Exception' object is not iterable")
