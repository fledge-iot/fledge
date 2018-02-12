# -*- coding: utf-8 -*-

import asyncio
import pytest
from unittest.mock import MagicMock

from foglamp.common.audit_logger import AuditLogger
from foglamp.common.storage_client.storage_client import StorageClient

__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("common", "audit-logger")
class TestAuditLogger():

    def test_constructor_no_storage(self):
        """ Test that we must construct with a storage client """
        with pytest.raises(TypeError) as excinfo:
            AuditLogger()
        assert 'Must be a valid Storage object' in str(excinfo.value)

    def test_singleton(self):
        """ Test that two audit loggers share the same state """
        storageMock1 = MagicMock(spec=StorageClient)
        a1 = AuditLogger(storageMock1)
        storageMock2 = MagicMock(spec=StorageClient)
        a2 = AuditLogger(storageMock2)
        assert a1._storage == a2._storage
        a1._storage.insert_into_tbl.reset_mock()

    def test_failure(self, event_loop):
        """ Test that audit log results in a database insert """
        storageMock = MagicMock(spec=StorageClient)
        audit = AuditLogger(storageMock)
        event_loop.run_until_complete(audit.failure('AUDTCODE', {'message': 'failure'}))
        assert audit._storage.insert_into_tbl.called is True
        audit._storage.insert_into_tbl.reset_mock()

    def test_warning(self, event_loop):
        """ Test that audit log results in a database insert """
        storageMock = MagicMock(spec=StorageClient)
        audit = AuditLogger(storageMock)
        event_loop.run_until_complete(audit.warning('AUDTCODE', { 'message': 'failure' }))
        assert audit._storage.insert_into_tbl.called is True
        audit._storage.insert_into_tbl.reset_mock()

    def test_information(self, event_loop):
        """ Test that audit log results in a database insert """
        storageMock = MagicMock(spec=StorageClient)
        audit = AuditLogger(storageMock)
        event_loop.run_until_complete(audit.information('AUDTCODE', { 'message': 'failure' }))
        assert audit._storage.insert_into_tbl.called is True
        audit._storage.insert_into_tbl.reset_mock()

    def test_success(self, event_loop):
        """ Test that audit log results in a database insert """
        storageMock = MagicMock(spec=StorageClient)
        audit = AuditLogger(storageMock)
        event_loop.run_until_complete(audit.success('AUDTCODE', { 'message': 'failure' }))
        assert audit._storage.insert_into_tbl.called is True
        audit._storage.insert_into_tbl.reset_mock()

    def test_failure_no_data(self, event_loop):
        """ Test that audit log results in a database insert """
        storageMock = MagicMock(spec=StorageClient)
        audit = AuditLogger(storageMock)
        event_loop.run_until_complete(audit.failure('AUDTCODE', None))
        assert audit._storage.insert_into_tbl.called is True
        audit._storage.insert_into_tbl.reset_mock()

    def test_warning_no_data(self, event_loop):
        """ Test that audit log results in a database insert """
        storageMock = MagicMock(spec=StorageClient)
        audit = AuditLogger(storageMock)
        event_loop.run_until_complete(audit.warning('AUDTCODE', None))
        assert audit._storage.insert_into_tbl.called is True
        audit._storage.insert_into_tbl.reset_mock()

    def test_information_no_data(self, event_loop):
        """ Test that audit log results in a database insert """
        storageMock = MagicMock(spec=StorageClient)
        audit = AuditLogger(storageMock)
        event_loop.run_until_complete(audit.information('AUDTCODE', None))
        assert audit._storage.insert_into_tbl.called is True
        audit._storage.insert_into_tbl.reset_mock()

    def test_success_no_data(self, event_loop):
        """ Test that audit log results in a database insert """
        storageMock = MagicMock(spec=StorageClient)
        audit = AuditLogger(storageMock)
        event_loop.run_until_complete(audit.success('AUDTCODE', None))
        assert audit._storage.insert_into_tbl.called is True
        audit._storage.insert_into_tbl.reset_mock()
