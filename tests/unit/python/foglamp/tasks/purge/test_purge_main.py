# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test tasks/purge/__main__.py entry point

"""

import pytest
from unittest.mock import patch, MagicMock

from foglamp.tasks import purge

from foglamp.common import logger
from foglamp.common.storage_client.storage_client import StorageClientAsync
from foglamp.tasks.purge.purge import Purge
from foglamp.common.process import FoglampProcess
from foglamp.common.audit_logger import AuditLogger

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.fixture
async def _purge_instance():
    mockStorageClientAsync = MagicMock(spec=StorageClientAsync)
    mockAuditLogger = AuditLogger(mockStorageClientAsync)
    with patch.object(FoglampProcess, "__init__"):
        with patch.object(logger, "setup"):
            with patch.object(mockAuditLogger, "__init__", return_value=None):
                p = Purge()
    return p


@pytest.allure.feature("unit")
@pytest.allure.story("tasks", "purge")
def test_main(_purge_instance):
    with patch.object(purge, "__name__", "__main__"):
        purge.purge_process = _purge_instance
        with patch.object(Purge, 'run', return_value=None):
            purge.purge_process.run()
            purge.purge_process.run.assert_called_once_with()
