import asyncio
import json
import sys
from unittest.mock import MagicMock, patch
import pytest
from aiohttp import web

from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.common.web import middleware
from fledge.services.core import connect
from fledge.services.core import routes

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2022 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


async def mock_coro(*args, **kwargs):
    return None if len(args) == 0 else args[0]


@pytest.allure.feature("unit")
@pytest.allure.story("api", "acl-management")
class TestACLManagement:
    """ ACL API tests """

    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop, middlewares=[middleware.optional_auth_middleware])
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    async def test_get_all_acls(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        result = {'count': 2, 'rows': [
            {'name': 'demoACL', 'service': [{'name': 'Fledge Storage'}, {'type': 'Southbound'}],
             'url': [{'url': '/fledge/south/operation', 'acl': [{'type': 'Southbound'}]}]},
            {'name': 'testACL', 'service': [], 'url': []}]}
        payload = {"return": ["name", "service", "url"]}
        value = await mock_coro(result) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(result))
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as patch_query_tbl:
                resp = await client.get('/fledge/ACL')
                assert 200 == resp.status
                result = await resp.text()
                assert 'acls' in result
            args, _ = patch_query_tbl.call_args
            assert 'control_acl' == args[0]
            assert payload == json.loads(args[1])

    async def test_bad_get_acl_by_name(self, client):
        acl_name = 'blah'
        storage_client_mock = MagicMock(StorageClientAsync)
        result = {"count": 0, "rows": []}
        payload = {"return": ["name", "service", "url"], "where": {"column": "name", "condition": "=",
                                                                   "value": acl_name}}
        value = await mock_coro(result) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(result))
        message = "ACL with name {} is not found.".format(acl_name)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as patch_query_tbl:
                resp = await client.get('/fledge/ACL/{}'.format(acl_name))
                assert 404 == resp.status
                assert message == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {"message": message} == json_response
            args, _ = patch_query_tbl.call_args
            assert 'control_acl' == args[0]
            assert payload == json.loads(args[1])

    async def test_good_get_acl_by_name(self, client):
        acl_name = 'demoACL'
        storage_client_mock = MagicMock(StorageClientAsync)
        result = {'count': 1, 'rows': [
            {'name': acl_name, 'service': [{'name': 'Fledge Storage'}, {'type': 'Southbound'}],
             'url': [{'url': '/fledge/south/operation', 'acl': [{'type': 'Southbound'}]}]}]}
        payload = {"return": ["name", "service", "url"], "where": {"column": "name", "condition": "=",
                                                                   "value": acl_name}}
        value = await mock_coro(result) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(result))
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as patch_query_tbl:
                resp = await client.get('/fledge/ACL/{}'.format(acl_name))
                assert 200 == resp.status
                result = await resp.text()
                json_response = json.loads(result)
                assert acl_name == json_response['name']
            args, _ = patch_query_tbl.call_args
            assert 'control_acl' == args[0]
            assert payload == json.loads(args[1])

    @pytest.mark.parametrize("payload, message", [
        ({}, "ACL name is required."),
        ({"name": 1}, "ACL name must be a string."),
        ({"name": ""}, "ACL name cannot be empty."),
        ({"name": "test"}, "service parameter is required."),
        ({"name": "test", "service": 1}, "service must be a list."),
        ({"name": "test", "service": []}, "url parameter is required."),
        ({"name": "test", "service": [], "url": 1}, "url must be a list.")
    ])
    async def test_bad_add_acl(self, client, payload, message):
        resp = await client.post('/fledge/ACL', data=json.dumps(payload))
        assert 400 == resp.status
        assert message == resp.reason
        result = await resp.text()
        json_response = json.loads(result)
        assert {"message": message} == json_response

    async def test_duplicate_add_acl(self, client):
        acl_name = "testACL"
        request_payload = {"name": acl_name, "service": [], "url": []}
        result = {'count': 1, 'rows': [
            {'name': acl_name, 'service': [{'name': 'Fledge Storage'}, {'type': 'Southbound'}],
             'url': [{'url': '/fledge/south/operation', 'acl': [{'type': 'Southbound'}]}]}]}
        value = await mock_coro(result) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(result))
        query_payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": acl_name}}
        message = "ACL with name {} already exists.".format(acl_name)
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as patch_query_tbl:
                resp = await client.post('/fledge/ACL', data=json.dumps(request_payload))
                assert 409 == resp.status
                assert message == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {"message": message} == json_response
            args, _ = patch_query_tbl.call_args
            assert 'control_acl' == args[0]
            assert query_payload == json.loads(args[1])
    
    async def test_good_add_acl(self, client):
        acl_name = "testACL"
        request_payload = {"name": acl_name, "service": [], "url": []}
        result = {"count": 0, "rows": []}
        insert_result = {"response": "inserted", "rows_affected": 1}
        acl_query_payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": acl_name}}
        if sys.version_info >= (3, 8):
            value = await mock_coro(result)
            insert_value = await mock_coro(insert_result)
        else:
            value = asyncio.ensure_future(mock_coro(result))
            insert_value = asyncio.ensure_future(mock_coro(insert_result))
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as query_tbl_patch:
                with patch.object(storage_client_mock, 'insert_into_tbl', return_value=insert_value
                                  ) as insert_tbl_patch:
                    resp = await client.post('/fledge/ACL', data=json.dumps(request_payload))
                    assert 200 == resp.status
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert {'name': acl_name, 'service': [], 'url': []} == json_response
                args, _ = insert_tbl_patch.call_args_list[0]
                assert 'control_acl' == args[0]
                assert {'name': acl_name, 'service': '[]', 'url': '[]'} == json.loads(args[1])
            args, _ = query_tbl_patch.call_args_list[0]
            assert 'control_acl' == args[0]
            assert acl_query_payload == json.loads(args[1])

    @pytest.mark.parametrize("payload, message", [
        ({}, "Nothing to update for the given payload."),
        ({"service": 1}, "service must be a list."),
        ({"url": 1}, "url must be a list.")
    ])
    async def test_bad_update_acl(self, client, payload, message):
        acl_name = "testACL"
        resp = await client.put('/fledge/ACL/{}'.format(acl_name), data=json.dumps(payload))
        assert 400 == resp.status
        assert message == resp.reason
        result = await resp.text()
        json_response = json.loads(result)
        assert {"message": message} == json_response

    async def test_update_acl_not_found(self, client):
        acl_name = "testACL"
        req_payload = {"service": []}
        result = {"count": 0, "rows": []}
        value = await mock_coro(result) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(result))
        query_payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": acl_name}}
        message = "ACL with name {} is not found.".format(acl_name)
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as query_tbl_patch:
                resp = await client.put('/fledge/ACL/{}'.format(acl_name), data=json.dumps(req_payload))
                assert 404 == resp.status
                assert message == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {"message": message} == json_response
            args, _ = query_tbl_patch.call_args
            assert 'control_acl' == args[0]
            assert query_payload == json.loads(args[1])

    @pytest.mark.parametrize("payload", [
        {"service": []},
        {"service": [{"service": [{"name": "Sinusoid"}, {"type": "Southbound"}]}]},
        {"service": [], "url": []},
        {"service": [], "url": [{"url": "/fledge/south/operation", "acl": [{"type": "Southbound"}]}]},
        {"service": [{"service": [{"name": "Sinusoid"}, {"type": "Southbound"}]}],
         "url": [{"url": "/fledge/south/operation", "acl": [{"type": "Southbound"}]}]}
    ])
    async def test_update_acl(self, client, payload):
        acl_name = "testACL"
        update_result = {"response": "updated", "rows_affected": 1}
        query_tbl_result = {"count": 1, "rows": [{"name": acl_name, "service": [], "url": []}]}
        query_payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": acl_name}}
        if sys.version_info >= (3, 8):
            rv = await mock_coro(query_tbl_result)
            update_value = await mock_coro(update_result)
        else:
            rv = asyncio.ensure_future(mock_coro(query_tbl_result))
            update_value = asyncio.ensure_future(mock_coro(update_result))
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=rv) as patch_query_tbl:
                with patch.object(storage_client_mock, 'update_tbl', return_value=update_value) as patch_update_tbl:
                    resp = await client.put('/fledge/ACL/{}'.format(acl_name), data=json.dumps(payload))
                    assert 200 == resp.status
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert {"message": "ACL {} updated successfully.".format(acl_name)} == json_response
                update_args, _ = patch_update_tbl.call_args
                assert 'control_acl' == update_args[0]
            query_args, _ = patch_query_tbl.call_args
            assert 'control_acl' == query_args[0]
            assert query_payload == json.loads(query_args[1])
