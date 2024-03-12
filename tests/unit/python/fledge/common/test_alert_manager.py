import asyncio
import json
import sys

from unittest.mock import MagicMock, patch
import pytest
from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.common.alert_manager import AlertManager


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2024 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

class TestAlertManager:
    """ Alert Manager """
    alert_manager = None

    async def async_mock(self, ret_val):
        return ret_val

    def setup_method(self):
        storage_client_mock = MagicMock(StorageClientAsync)
        self.alert_manager = AlertManager(storage_client=storage_client_mock)
        self.alert_manager.storage_client = storage_client_mock
        #self.alert_manager.alerts = []

    def teardown_method(self):
        self.alert_manager.alerts = []
        self.alert_manager = None

    async def test_urgency(self):
        urgencies = self.alert_manager.urgency
        assert 4 == len(urgencies)
        assert ['Critical', 'High', 'Normal', 'Low'] == list(urgencies.keys())

    @pytest.mark.parametrize("urgency_index, urgency", [
        ('1', 'UNKNOWN'),
        ('High', 'UNKNOWN'),
        (0, 'UNKNOWN'),
        (1, 'Critical'),
        (2, 'High'),
        (3, 'Normal'),
        (4, 'Low')
    ])
    async def test__urgency_name_by_value(self, urgency_index, urgency):
        value = self.alert_manager._urgency_name_by_value(value=urgency_index)
        assert urgency == value

    @pytest.mark.parametrize("storage_result, response", [
        ({"rows": [], 'count': 0}, []),
        ({"rows": [{"key": "RW", "message": "The Service RW restarted 1 times", "urgency": 3,
                    "timestamp": "2024-03-01 09:40:34.482"}], 'count': 1}, [{"key": "RW", "message":
            "The Service RW restarted 1 times", "urgency": "Normal", "timestamp": "2024-03-01 09:40:34.482"}])
    ])
    async def test_get_all(self, storage_result, response):
        rv = await self.async_mock(storage_result) if sys.version_info.major == 3 and sys.version_info.minor >= 8 \
            else asyncio.ensure_future(self.async_mock(storage_result))
        with patch.object(self.alert_manager.storage_client, 'query_tbl_with_payload', return_value=rv
                          ) as patch_query_tbl:
            result = await self.alert_manager.get_all()
            assert response == result
        args, _ = patch_query_tbl.call_args
        assert 'alerts' == args[0]
        assert {"return": ["key", "message", "urgency", {"column": "ts", "alias": "timestamp",
                                                         "format": "YYYY-MM-DD HH24:MI:SS.MS"}]} == json.loads(args[1])


    async def test_bad_get_all(self):
        storage_result = {"rows": [{}], 'count': 1}
        rv = await self.async_mock(storage_result) if sys.version_info.major == 3 and sys.version_info.minor >= 8 \
            else asyncio.ensure_future(self.async_mock(storage_result))
        with patch.object(self.alert_manager.storage_client, 'query_tbl_with_payload', return_value=rv
                          ) as patch_query_tbl:
            with pytest.raises(Exception) as ex:
                await self.alert_manager.get_all()
            assert "'key'" == str(ex.value)
        args, _ = patch_query_tbl.call_args
        assert 'alerts' == args[0]
        assert {"return": ["key", "message", "urgency", {"column": "ts", "alias": "timestamp",
                                                         "format": "YYYY-MM-DD HH24:MI:SS.MS"}]} == json.loads(args[1])

    async def test_get_by_key_when_in_cache(self):
        self.alert_manager.alerts = [{"key": "RW", "message": "The Service RW restarted 1 times", "urgency": 3,
                    "timestamp": "2024-03-01 09:40:34.482"}]
        key = "RW"
        result = await self.alert_manager.get_by_key(key)
        assert self.alert_manager.alerts[0] == result

    async def test_get_by_key_not_found(self):
        key = "Sine"
        storage_result = {"rows": [], 'count': 1}
        rv = await self.async_mock(storage_result) if sys.version_info.major == 3 and sys.version_info.minor >= 8 \
            else asyncio.ensure_future(self.async_mock(storage_result))
        with patch.object(self.alert_manager.storage_client, 'query_tbl_with_payload', return_value=rv
                          ) as patch_query_tbl:
            with pytest.raises(Exception) as ex:
                await self.alert_manager.get_by_key(key)
            assert ex.type is KeyError
            assert "'{} alert not found.'".format(key) == str(ex.value)
        args, _ = patch_query_tbl.call_args
        assert 'alerts' == args[0]
        assert {"return": ["key", "message", "urgency", {"column": "ts", "alias": "timestamp",
                                                         "format": "YYYY-MM-DD HH24:MI:SS.MS"}],
                "where": {"column": "key", "condition": "=", "value": key}} == json.loads(args[1])

    async def test_get_by_key_when_not_in_cache(self):
        key = 'update'
        storage_result = {"rows": [{"key": "RW", "message": "The Service RW restarted 1 times", "urgency": 3,
                    "timestamp": "2024-03-01 09:40:34.482"}], 'count': 1}
        rv = await self.async_mock(storage_result) if sys.version_info.major == 3 and sys.version_info.minor >= 8 \
            else asyncio.ensure_future(self.async_mock(storage_result))
        with patch.object(self.alert_manager.storage_client, 'query_tbl_with_payload', return_value=rv
                          ) as patch_query_tbl:
            result = await self.alert_manager.get_by_key(key)
            storage_result['rows'][0]['urgency'] = 'Normal'
            assert storage_result['rows'][0] == result
        args, _ = patch_query_tbl.call_args
        assert 'alerts' == args[0]
        assert {"return": ["key", "message", "urgency", {"column": "ts", "alias": "timestamp",
                                                         "format": "YYYY-MM-DD HH24:MI:SS.MS"}],
                "where": {"column": "key", "condition": "=", "value": key}} == json.loads(args[1])

    async def test_add(self):
        params = {"key": "update", 'message': 'New version available', 'urgency': 'High'}
        storage_result = {'rows_affected': 1, "response": "inserted"}
        rv = await self.async_mock(storage_result) if sys.version_info.major == 3 and sys.version_info.minor >= 8 \
            else asyncio.ensure_future(self.async_mock(storage_result))
        with patch.object(self.alert_manager.storage_client, 'insert_into_tbl', return_value=rv
                          ) as insert_tbl_patch:
            result = await self.alert_manager.add(params)
            assert 'alert' in result
            assert params == result['alert']
        args, _ = insert_tbl_patch.call_args
        assert 'alerts' == args[0]
        assert params == json.loads(args[1])

    async def test_bad_add(self):
        params = {"key": "update", 'message': 'New version available', 'urgency': 'High'}
        storage_result = {}
        rv = await self.async_mock(storage_result) if sys.version_info.major == 3 and sys.version_info.minor >= 8 \
            else asyncio.ensure_future(self.async_mock(storage_result))
        with patch.object(self.alert_manager.storage_client, 'insert_into_tbl', return_value=rv
                          ) as insert_tbl_patch:
            with pytest.raises(Exception) as ex:
                await self.alert_manager.add(params)
            assert "'response'" == str(ex.value)
        args, _ = insert_tbl_patch.call_args
        assert 'alerts' == args[0]
        assert params == json.loads(args[1])

    async def test_delete(self):
        storage_result = {'rows_affected': 1, "response": "deleted"}
        rv = await self.async_mock(storage_result) if sys.version_info.major == 3 and sys.version_info.minor >= 8 \
            else asyncio.ensure_future(self.async_mock(storage_result))
        with patch.object(self.alert_manager.storage_client, 'delete_from_tbl', return_value=rv
                          ) as delete_tbl_patch:
            result = await self.alert_manager.delete()
            assert 'alert' in result
            assert "Delete all alerts." == result
        args, _ = delete_tbl_patch.call_args
        assert 'alerts' == args[0]

    async def test_delete_by_key(self):
        key = "RW"
        self.alert_manager.alerts = [{"key": key, "message": "The Service RW restarted 1 times", "urgency": 3,
                                      "timestamp": "2024-03-01 09:40:34.482"}]
        storage_result = {'rows_affected': 1, "response": "deleted"}
        rv = await self.async_mock(storage_result) if sys.version_info.major == 3 and sys.version_info.minor >= 8 \
            else asyncio.ensure_future(self.async_mock(storage_result))
        with patch.object(self.alert_manager.storage_client, 'delete_from_tbl', return_value=rv
                          ) as delete_tbl_patch:
            result = await self.alert_manager.delete(key)
            assert 'alert' in result
            assert "{} alert is deleted.".format(key) == result
        args, _ = delete_tbl_patch.call_args
        assert 'alerts' == args[0]
        assert {"where": {"column": "key", "condition": "=", "value": key}} == json.loads(args[1])

    async def test_bad_delete(self):
        with pytest.raises(Exception) as ex:
            await self.alert_manager.delete("Update")
        assert ex.type is KeyError
        assert "" == str(ex.value)

