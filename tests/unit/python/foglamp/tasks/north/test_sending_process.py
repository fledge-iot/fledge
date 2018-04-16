# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import pytest
import asyncio
from unittest.mock import patch, call, MagicMock
from foglamp.common import logger
import foglamp.plugins.north.common.common as plugin_common
from foglamp.common.storage_client.storage_client import ReadingsStorageClient, StorageClient
from foglamp.common.process import FoglampProcess
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.common.audit_logger import AuditLogger

__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class TestSendingProcess:
    """Test the units of sending_process.py"""

    def test_init(self, event_loop):
        """Test that creating an instance of SendingProcess calls init of FoglampProcess and creates loggers"""

        assert True

    def test_set_configuration(self, event_loop):
        """Test that sending_process's ... returns configuration item ... """

        assert True