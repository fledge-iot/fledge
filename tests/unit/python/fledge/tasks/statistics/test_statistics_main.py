# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

"""Test tasks/statistics/__main__.py entry point"""

from unittest.mock import patch, MagicMock
import pytest

from fledge.tasks.statistics import statistics_history
from fledge.common import logger
from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.tasks.statistics.statistics_history import StatisticsHistory
from fledge.common.process import FledgeProcess
from fledge.common.audit_logger import AuditLogger

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.fixture
async def _stats_history_instance():
    mock_storage_client = MagicMock(spec=StorageClientAsync)
    mock_audit_logger = AuditLogger(mock_storage_client)
    with patch.object(FledgeProcess, "__init__"):
        with patch.object(logger, "setup"):
            with patch.object(mock_audit_logger, "__init__", return_value=None):
                stats = StatisticsHistory()
    return stats


@pytest.allure.feature("unit")
@pytest.allure.story("tasks", "statistics")
def test_main(_stats_history_instance):
    with patch.object(statistics_history, "__name__", "__main__"):
        with patch.object(StatisticsHistory, 'run', return_value=None):
            assert isinstance(_stats_history_instance, StatisticsHistory)
            _stats_history_instance.run()
            _stats_history_instance.run.assert_called_once_with()
