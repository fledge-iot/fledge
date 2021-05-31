# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test tasks/purge/__main__.py entry point

"""
import asyncio
import sys
import pytest
from unittest.mock import patch, MagicMock

from fledge.tasks import purge

from fledge.common import logger
from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.tasks.purge.purge import Purge
from fledge.common.process import FledgeProcess
from fledge.common.audit_logger import AuditLogger

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.fixture
async def _purge_instance():
    mockStorageClientAsync = MagicMock(spec=StorageClientAsync)
    mockAuditLogger = AuditLogger(mockStorageClientAsync)
    with patch.object(FledgeProcess, "__init__"):
        with patch.object(logger, "setup"):
            with patch.object(mockAuditLogger, "__init__", return_value=None):
                p = Purge()
    return p


@pytest.allure.feature("unit")
@pytest.allure.story("tasks", "purge")
async def test_main(_purge_instance):
    async def mock_coro():
        return None
    
    with patch.object(purge, "__name__", "__main__"):
        purge.purge_process = _purge_instance
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await mock_coro()
        else:
            _rv = asyncio.ensure_future(mock_coro())
        with patch.object(Purge, 'run', return_value=_rv):
            await purge.purge_process.run()
            purge.purge_process.run.assert_called_once_with()
