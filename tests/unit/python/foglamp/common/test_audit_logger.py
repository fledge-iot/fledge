import asyncio
import pytest
from unittest.mock import MagicMock
from unittest.mock import patch

from foglamp.common.audit_logger import AuditLogger
from foglamp.common.storage_client.storage_client import StorageClient

__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class TestAuditLogger():

    def test_constructor_no_storage(self):
        with pytest.raises(TypeError) as excinfo:
            AuditLogger()
        assert 'Must be a valid Storage object' in str(excinfo.value)

    def test_failure(self):
        storageMock = MagicMock(spec=StorageClient)
        audit = AuditLogger(storageMock)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(audit.failure('AUDTCODE', { 'message': 'failure' }))
        assert storageMock.insert_into_tbl.called == True
        assert storageMock.insert_into_tbl.call_count == 1
