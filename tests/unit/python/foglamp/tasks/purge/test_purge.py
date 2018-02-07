# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


import asyncio
from unittest.mock import patch, call, MagicMock
import pytest
import logging
from foglamp.common.storage_client.storage_client import ReadingsStorageClient, StorageClient
from foglamp.common.statistics import Statistics
from foglamp.tasks.purge.purge import Purge
from foglamp.common.process import FoglampProcess


__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("tasks", "purge")
class TestPurge:
    """Test the units of purge.py"""

    def test_init(self):
        """Test that creating an instance of Purge calls init of FoglampProcess and creates logger"""
        with patch.object(FoglampProcess, "__init__") as fp:
            p = Purge()
            assert isinstance(p._logger, logging.Logger)
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

    def test_insert_into_log(self):
        # TODO: FOGL-701
        pass

    def test_set_configuration(self):
        pass

    config = [{"retainUnsent": {"value": "False"}, "age": {"value": "72"}, "size": {"value": "0"}},
              {"retainUnsent": {"value": "True"}, "age": {"value": "0"}, "size": {"value": "100"}}]

    @pytest.mark.parametrize("conf, flag", [
        (config[0], "purge"),
        (config[1], "retain")
    ])
    def test_purge_data(self, conf, flag):
        """Test that purge_data calls Storage's purge with defined values"""
        # TODO: FOGL-701 AuditLogger tests
        with patch.object(FoglampProcess, '__init__'):
            p = Purge()
            p._storage = MagicMock(spec=StorageClient)
            p._readings_storage = MagicMock(spec=ReadingsStorageClient)
            p._insert_into_log = MagicMock()
            with patch.object(p._readings_storage, 'purge') as mock_storage_purge:
                with patch.object(p, '_insert_into_log') as mock_insert:
                    p.purge_data(conf)
                assert mock_insert.called
            mock_storage_purge.assert_has_calls([call(age=conf["age"]["value"], flag=flag, sent_id=0)],
                                                [call(size=conf["size"]["value"], flag=flag, sent_id=0)])

    def test_run(self):
        pass
