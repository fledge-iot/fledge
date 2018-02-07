# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


import asyncio
from unittest.mock import patch, call, MagicMock
import pytest
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
        with patch.object(FoglampProcess, "__init__") as fp:
            with patch.object(logger, "setup") as log:
                with patch.object(mock_ad, "__init__", return_value=None):
                    p = Purge()
                assert isinstance(p._audit, AuditLogger)
            log.assert_called_once_with("Data Purge")
        fp.assert_called_once_with()

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
        if 'age' in kwargs:
            if kwargs.get('flag') == 'purge':
                return {"readings": 10, "removed": 1, "unsentPurged": 2, "unsentRetained": 0}
            if kwargs.get('flag') == 'retain':
                return {"readings": 60, "removed": 10, "unsentPurged": 0, "unsentRetained": 30}
        elif 'size' in kwargs:
            return {"readings": 10, "removed": 1, "unsentPurged": 2, "unsentRetained": 7}

    config = [{"retainUnsent": {"value": "False"}, "age": {"value": "72"}, "size": {"value": "0"}},
              {"retainUnsent": {"value": "True"}, "age": {"value": "0"}, "size": {"value": "100"}}]

    @pytest.mark.parametrize("conf, flag, expected", [
        (config[0], "purge", (2, 4)),
        (config[1], "retain", (11, 2))
    ])
    def test_purge_data(self, conf, flag, expected):
        """Test that purge_data calls Storage's purge with defined values"""
        with patch.object(FoglampProcess, '__init__'):
            p = Purge()
            p._logger = MagicMock(spec=logger)
            p._storage = MagicMock(spec=StorageClient)
            p._readings_storage = MagicMock(spec=ReadingsStorageClient)
            audit = p._audit
            with patch.object(p._readings_storage, 'purge', side_effect=self.store_purge) as mock_storage_purge:
                with patch.object(audit, 'information', return_value=asyncio.ensure_future(asyncio.sleep(0.1))) \
                        as audit_info:
                    assert expected == p.purge_data(conf)
            assert audit_info.called
            mock_storage_purge.assert_has_calls([call(age=conf["age"]["value"], flag=flag, sent_id=0)],
                                                [call(size=conf["size"]["value"], flag=flag, sent_id=0)])

    def test_run(self):
        """Test that run calls all units of purge process"""
        with patch.object(FoglampProcess, '__init__'):
            p = Purge()
            config = "Some config"
            with patch.object(p, 'set_configuration', return_value=config) as sc:
                with patch.object(p, 'purge_data', return_value=(1, 2)) as pd:
                    with patch.object(p, 'write_statistics') as ws:
                        p.run()
            sc.assert_called_once_with()
            pd.assert_called_once_with(config)
            ws.assert_called_once_with(1, 2)
