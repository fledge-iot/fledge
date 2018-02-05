# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


import asyncio
from unittest.mock import patch, call
import pytest
import logging
from foglamp.common.storage_client.storage_client import StorageClient
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
        pass

    def test_set_configuration(self):
        pass

    def test_purge_data(self):
        pass

    def test_run(self):
        pass