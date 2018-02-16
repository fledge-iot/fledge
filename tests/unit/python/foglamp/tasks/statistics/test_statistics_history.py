# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Test tasks/statistics/statistics_history.py"""

from unittest.mock import patch, MagicMock
import pytest

from foglamp.common import logger
from foglamp.common.storage_client.storage_client import StorageClient
from foglamp.tasks.statistics.statistics_history import StatisticsHistory
from foglamp.common.process import FoglampProcess


__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("tasks", "statistics")
class TestStatisticsHistory:
    """Test the units of statistics_history.py
    """

    def test_init(self):
        """Test that creating an instance of StatisticsHistory calls init of FoglampProcess and creates loggers"""
        with patch.object(FoglampProcess, "__init__") as mock_process:
            with patch.object(logger, "setup") as log:
                sh = StatisticsHistory()
                assert isinstance(sh, StatisticsHistory)
            log.assert_called_once_with("StatisticsHistory")
        mock_process.assert_called_once_with()
