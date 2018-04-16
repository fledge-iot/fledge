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

from foglamp.tasks.north.sending_process import SendingProcess
import foglamp.tasks.north.sending_process as sp_module

__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class TestSendingProcess:
    """Test the units of sending_process.py"""

    def test_last_object_id_read(self, event_loop):
        """Tests the possible cases for the function last_object_id_read """

        def mock_query_tbl_row_0():
            """Mocks the query_tbl function of a StorageClient object - base case"""

            rows = {"rows": []}
            return rows

        def mock_query_tbl_row_1():
            """Mocks the query_tbl function of a StorageClient object - good case"""

            rows = {"rows": [{"last_object": 10}]}
            return rows

        def mock_query_tbl_row_2():
            """Mocks the query_tbl function of a StorageClient object - base case"""

            rows = {"rows": [{"last_object": 10}, {"last_object": 11}]}
            return rows

        sp = SendingProcess()
        sp._storage = MagicMock(spec=StorageClient)

        # Good Case
        with patch.object(sp._storage, 'query_tbl', return_value=mock_query_tbl_row_1()) as sp_mocked:
            position = sp._last_object_id_read(1)
            sp_mocked.assert_called_once_with('streams', 'id=1')
            assert position == 10

        # Bad cases
        sp._logger.error = MagicMock()
        with patch.object(sp._storage, 'query_tbl', return_value=mock_query_tbl_row_0()) as sp_mocked:
            try:
                sp._last_object_id_read(1)
            except Exception:
                pass

            sp._logger.error.assert_called_once_with(sp_module._MESSAGES_LIST["e000019"])

        sp._logger.error = MagicMock()
        with patch.object(sp._storage, 'query_tbl', return_value=mock_query_tbl_row_2()) as sp_mocked:
            try:
                sp._last_object_id_read(1)
            except Exception:
                pass

            sp._logger.error.assert_called_once_with(sp_module._MESSAGES_LIST["e000019"])

        assert True
