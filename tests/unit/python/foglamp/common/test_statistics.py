import asyncio
import pytest
from unittest.mock import MagicMock
from unittest.mock import patch

from foglamp.common.statistics import Statistics
from foglamp.common.storage_client.storage_client import StorageClient

__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class TestStatistics():

    def test_constructor_no_storage(self):
        """ Test that we msut construct with a storage client """
        with pytest.raises(TypeError) as excinfo:
            Statistics()
        assert 'Must be a valid Storage object' in str(excinfo.value)

    def test_singleton(self):
        """ Test that two audit loggers share the same state """
        storageMock1 = MagicMock(spec=StorageClient)
        s1 = Statistics(storageMock1)
        storageMock2 = MagicMock(spec=StorageClient)
        s2 = Statistics(storageMock2)
        assert s1._storage == s2._storage
        s1._storage.insert_into_tbl.reset_mock()

    def test_register(self):
        """ Test that audit log results in a database insert """
        storageMock = MagicMock(spec=StorageClient)
        stats = Statistics(storageMock)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(stats.register('T1Stat', 'Test stat'))
        assert stats._storage.insert_into_tbl.called == True
        stats._storage.insert_into_tbl.reset_mock()

    def test_register_twice(self):
        """ Test that audit log results in a database insert """
        storageMock = MagicMock(spec=StorageClient)
        stats = Statistics(storageMock)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(stats.register('T2Stat', 'Test stat'))
        count = stats._storage.insert_into_tbl.call_count
        loop.run_until_complete(stats.register('T2Stat', 'Test stat'))
        assert stats._storage.insert_into_tbl.called == True
        assert count == stats._storage.insert_into_tbl.call_count
        stats._storage.insert_into_tbl.reset_mock()

    def test_keys_not_reloaded(self):
        """ Test that audit log results in a database insert """
        storageMock = MagicMock(spec=StorageClient)
        stats = Statistics(storageMock)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(stats.register('T3Stat', 'Test stat'))
        count = stats._storage.query_tbl_with_payload.call_count
        loop.run_until_complete(stats.register('T3Stat', 'Test stat'))
        assert count == stats._storage.query_tbl_with_payload.call_count
