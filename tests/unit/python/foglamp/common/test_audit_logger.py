# -*- coding: utf-8 -*-

import asyncio
import pytest
from unittest.mock import MagicMock

from foglamp.common.audit_logger import AuditLogger
from foglamp.common.storage_client.storage_client import StorageClientAsync

__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@asyncio.coroutine
def mock_coro():
    return None

@pytest.allure.feature("unit")
@pytest.allure.story("common", "audit-logger")
class TestAuditLogger():

    @pytest.mark.asyncio
    async def test_constructor_no_storage(self):
        """ Test that we must construct with a storage client """
        with pytest.raises(TypeError) as excinfo:
            AuditLogger()
        assert 'Must be a valid Storage object' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_singleton(self, event_loop):
        """ Test that two audit loggers share the same state """
        storageMock1 = MagicMock(spec=StorageClientAsync)
        attrs = {'insert_into_tbl.return_value': asyncio.ensure_future(mock_coro(), loop=event_loop)}
        storageMock1.configure_mock(**attrs)
        a1 = AuditLogger(storageMock1)

        storageMock2 = MagicMock(spec=StorageClientAsync)
        attrs = {'insert_into_tbl.return_value': asyncio.ensure_future(mock_coro(), loop=event_loop)}
        storageMock2.configure_mock(**attrs)
        a2 = AuditLogger(storageMock2)

        assert a1._storage == a2._storage
        a1._storage.insert_into_tbl.reset_mock()

    @pytest.mark.asyncio
    async def test_failure(self, event_loop):
        """ Test that audit log results in a database insert """
        storageMock = MagicMock(spec=StorageClientAsync)
        attrs = {'insert_into_tbl.return_value': asyncio.ensure_future(mock_coro(), loop=event_loop)}
        storageMock.configure_mock(**attrs)
        audit = AuditLogger(storageMock)
        await audit.failure('AUDTCODE', {'message': 'failure'})
        assert audit._storage.insert_into_tbl.called is True
        audit._storage.insert_into_tbl.reset_mock()

    @pytest.mark.asyncio
    async def test_warning(self, event_loop):
        """ Test that audit log results in a database insert """
        storageMock = MagicMock(spec=StorageClientAsync)
        attrs = {'insert_into_tbl.return_value': asyncio.ensure_future(mock_coro(), loop=event_loop)}
        storageMock.configure_mock(**attrs)
        audit = AuditLogger(storageMock)
        await audit.warning('AUDTCODE', { 'message': 'failure' })
        assert audit._storage.insert_into_tbl.called is True
        audit._storage.insert_into_tbl.reset_mock()

    @pytest.mark.asyncio
    async def test_information(self, event_loop):
        """ Test that audit log results in a database insert """
        storageMock = MagicMock(spec=StorageClientAsync)
        attrs = {'insert_into_tbl.return_value': asyncio.ensure_future(mock_coro(), loop=event_loop)}
        storageMock.configure_mock(**attrs)
        audit = AuditLogger(storageMock)
        await audit.information('AUDTCODE', { 'message': 'failure' })
        assert audit._storage.insert_into_tbl.called is True
        audit._storage.insert_into_tbl.reset_mock()

    @pytest.mark.asyncio
    async def test_success(self, event_loop):
        """ Test that audit log results in a database insert """
        storageMock = MagicMock(spec=StorageClientAsync)
        attrs = {'insert_into_tbl.return_value': asyncio.ensure_future(mock_coro(), loop=event_loop)}
        storageMock.configure_mock(**attrs)
        audit = AuditLogger(storageMock)
        await audit.success('AUDTCODE', { 'message': 'failure' })
        assert audit._storage.insert_into_tbl.called is True
        audit._storage.insert_into_tbl.reset_mock()

    @pytest.mark.asyncio
    async def test_failure_no_data(self, event_loop):
        """ Test that audit log results in a database insert """
        storageMock = MagicMock(spec=StorageClientAsync)
        attrs = {'insert_into_tbl.return_value': asyncio.ensure_future(mock_coro(), loop=event_loop)}
        storageMock.configure_mock(**attrs)
        audit = AuditLogger(storageMock)
        await audit.failure('AUDTCODE', None)
        assert audit._storage.insert_into_tbl.called is True
        audit._storage.insert_into_tbl.reset_mock()

    @pytest.mark.asyncio
    async def test_warning_no_data(self, event_loop):
        """ Test that audit log results in a database insert """
        storageMock = MagicMock(spec=StorageClientAsync)
        attrs = {'insert_into_tbl.return_value': asyncio.ensure_future(mock_coro(), loop=event_loop)}
        storageMock.configure_mock(**attrs)
        audit = AuditLogger(storageMock)
        await audit.warning('AUDTCODE', None)
        assert audit._storage.insert_into_tbl.called is True
        audit._storage.insert_into_tbl.reset_mock()

    @pytest.mark.asyncio
    async def test_information_no_data(self, event_loop):
        """ Test that audit log results in a database insert """
        storageMock = MagicMock(spec=StorageClientAsync)
        attrs = {'insert_into_tbl.return_value': asyncio.ensure_future(mock_coro(), loop=event_loop)}
        storageMock.configure_mock(**attrs)
        audit = AuditLogger(storageMock)
        await audit.information('AUDTCODE', None)
        assert audit._storage.insert_into_tbl.called is True
        audit._storage.insert_into_tbl.reset_mock()

    @pytest.mark.asyncio
    async def test_success_no_data(self, event_loop):
        """ Test that audit log results in a database insert """
        storageMock = MagicMock(spec=StorageClientAsync)
        attrs = {'insert_into_tbl.return_value': asyncio.ensure_future(mock_coro(), loop=event_loop)}
        storageMock.configure_mock(**attrs)
        audit = AuditLogger(storageMock)
        await audit.success('AUDTCODE', None)
        assert audit._storage.insert_into_tbl.called is True
        audit._storage.insert_into_tbl.reset_mock()
