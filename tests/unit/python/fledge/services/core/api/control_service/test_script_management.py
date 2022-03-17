import asyncio
import json
import sys
from unittest.mock import MagicMock, patch
import pytest
from aiohttp import web

from fledge.services.core import connect
from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.common.web import middleware
from fledge.services.core import routes

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2022 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


async def mock_coro(*args, **kwargs):
    return None if len(args) == 0 else args[0]


@pytest.allure.feature("unit")
@pytest.allure.story("api", "script-management")
class TestScriptManagement:
    """ Automation script API tests
    """

    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop, middlewares=[middleware.optional_auth_middleware])
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    async def test_get_all_scripts(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        result = {"count": 2, "rows": [
            {"name": "demoScript", "steps": [{"delay": {"order": 0, "duration": 9003}}], "acl": ""},
            {"name": "testScript", "steps": [{"write": {"order": 0, "speed": 420}}], "acl": "testACL"}]}
        payload = {"return": ["name", "steps", "acl"]}
        value = await mock_coro(result) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(result))
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as patch_query_tbl:
                resp = await client.get('/fledge/control/script')
                assert 200 == resp.status
                result = await resp.text()
                assert 'scripts' in result
            args, _ = patch_query_tbl.call_args
            assert 'control_script' == args[0]
            assert payload == json.loads(args[1])

    async def test_bad_get_script_by_name(self, client):
        script_name = 'blah'
        storage_client_mock = MagicMock(StorageClientAsync)
        result = {"count": 0, "rows": []}
        payload = {"return": ["name", "steps", "acl"], "where": {"column": "name", "condition": "=", "value": "blah"}}
        value = await mock_coro(result) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(result))
        message = "Script with name {} is not found.".format(script_name)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as patch_query_tbl:
                resp = await client.get('/fledge/control/script/{}'.format(script_name))
                assert 404 == resp.status
                assert message == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {"message": message} == json_response
            args, _ = patch_query_tbl.call_args
            assert 'control_script' == args[0]
            assert payload == json.loads(args[1])

    async def test_good_get_script_by_name(self, client):
        script_name = 'demoScript'
        storage_client_mock = MagicMock(StorageClientAsync)
        result = {"count": 0, "rows": [
            {"name": script_name, "steps": [{"delay": {"order": 0, "duration": 9003}}], "acl": ""}]}
        payload = {"return": ["name", "steps", "acl"], "where": {"column": "name", "condition": "=",
                                                                 "value": script_name}}
        value = await mock_coro(result) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(result))
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as patch_query_tbl:
                resp = await client.get('/fledge/control/script/{}'.format(script_name))
                assert 200 == resp.status
                result = await resp.text()
                json_response = json.loads(result)
                assert script_name == json_response['name']
            args, _ = patch_query_tbl.call_args
            assert 'control_script' == args[0]
            assert payload == json.loads(args[1])

    @pytest.mark.parametrize("payload, message", [
        ({}, "Script name is required."),
        ({"name": 1}, "Script name must be a string."),
        ({"name": ""}, "Script name cannot be empty."),
        ({"name": "test"}, "steps parameter is required."),
        ({"name": "test", "steps": 1}, "steps must be a list."),
        ({"name": "test", "steps": [], "acl": 1}, "ACL name must be a string."),
        ({"name": "test", "steps": [{"a": 1}]}, "a is an invalid step. Supported step types are ['configure', 'delay', "
                                                "'operation', 'script', 'write'] with case-sensitive."),
        ({"name": "test", "steps": [1, 2]}, "Steps should be in list of dictionaries."),
        ({"name": "test", "steps": [{"delay": 1}]}, "For delay step nested elements should be in dictionary."),
        ({"name": "test", "steps": [{"delay": {}}]}, "order key is missing for delay step."),
        ({"name": "test", "steps": [{"delay": {"order": "1"}}]}, "order should be an integer for delay step."),
        ({"name": "test", "steps": [{"delay": {"order": 1}, "write": {}}]}, "order key is missing for write step."),
        ({"name": "test", "steps": [{"delay": {"order": 1}, "write": {"order": "1"}}]},
         "order should be an integer for write step."),
        ({"name": "test", "steps": [{"delay": {"order": 1}, "write": {"order": 1}}]},
         "order with value 1 is also found in write. It should be unique for each step item.")
    ])
    async def test_bad_add_script(self, client, payload, message):
        resp = await client.post('/fledge/control/script', data=json.dumps(payload))
        assert 400 == resp.status
        assert message == resp.reason
        result = await resp.text()
        json_response = json.loads(result)
        assert {"message": message} == json_response

    async def test_duplicate_add_script(self, client):
        script_name = "test"
        request_payload = {"name": script_name, "steps": []}
        result = {"count": 1, "rows": [{"name": script_name, "steps": [{"write": {"order": 1, "speed": 420}}]}]}
        value = await mock_coro(result) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(result))
        query_payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": script_name}}
        message = "Script with name {} already exists.".format(script_name)
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=value) as patch_query_tbl:
                resp = await client.post('/fledge/control/script', data=json.dumps(request_payload))
                assert 409 == resp.status
                assert message == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {"message": message} == json_response
            args, _ = patch_query_tbl.call_args
            assert 'control_script' == args[0]
            assert query_payload == json.loads(args[1])

    async def test_bad_add_script_with_acl(self, client):
        script_name = "test"
        acl_name = "blah"
        request_payload = {"name": script_name, "steps": [], "acl": acl_name}
        script_result = {"count": 0, "rows": []}
        acl_result = {"count": 0, "rows": []}
        script_query_payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": script_name}}
        acl_query_payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": acl_name}}

        @asyncio.coroutine
        def q_result(*args):
            table = args[0]
            payload = args[1]
            if table == 'control_acl':
                assert acl_query_payload == json.loads(payload)
                return script_result
            elif table == 'control_script':
                assert script_query_payload == json.loads(payload)
                return acl_result
            else:
                return {}

        message = "ACL with name {} is not found.".format(acl_name)
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result):
                resp = await client.post('/fledge/control/script', data=json.dumps(request_payload))
                assert 404 == resp.status
                assert message == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {"message": message} == json_response

    async def test_good_add_script(self, client):
        script_name = "test"
        request_payload = {"name": script_name, "steps": []}
        result = {"count": 0, "rows": []}
        insert_result = {"response": "inserted", "rows_affected": 1}
        script_query_payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": script_name}}
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
                    resp = await client.post('/fledge/control/script', data=json.dumps(request_payload))
                    assert 200 == resp.status
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert {'name': script_name, 'steps': []} == json_response
                args, _ = insert_tbl_patch.call_args_list[0]
                assert 'control_script' == args[0]
                expected = json.loads(args[1])
                assert {'name': script_name, 'steps': '[]'} == expected
            args, _ = query_tbl_patch.call_args_list[0]
            assert 'control_script' == args[0]
            expected = json.loads(args[1])
            assert script_query_payload == expected

    async def test_good_add_script_with_acl(self, client):
        script_name = "test"
        acl_name = "blah"
        request_payload = {"name": script_name, "steps": [], "acl": acl_name}
        script_result = {"count": 0, "rows": []}
        acl_result = {"count": 1, "rows": [{"name": acl_name, "service": [], "url": []}]}
        insert_result = {"response": "inserted", "rows_affected": 1}
        script_query_payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": script_name}}
        acl_query_payload = {"return": ["name"], "where": {"column": "name", "condition": "=", "value": acl_name}}
        insert_value = await mock_coro(insert_result) if sys.version_info >= (3, 8) else \
            asyncio.ensure_future(mock_coro(insert_result))

        @asyncio.coroutine
        def q_result(*args):
            table = args[0]
            payload = args[1]
            if table == 'control_acl':
                assert acl_query_payload == json.loads(payload)
                return acl_result
            elif table == 'control_script':
                assert script_query_payload == json.loads(payload)
                return script_result
            else:
                return {}

        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result):
                with patch.object(storage_client_mock, 'insert_into_tbl', return_value=insert_value
                                  ) as insert_tbl_patch:
                    resp = await client.post('/fledge/control/script', data=json.dumps(request_payload))
                    assert 200 == resp.status
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert {'acl': acl_name, 'name': script_name, 'steps': []} == json_response
                insert_args, _ = insert_tbl_patch.call_args_list[0]
                assert 'control_script' == insert_args[0]
                expected = json.loads(insert_args[1])
                assert {'name': script_name, 'steps': '[]', 'acl': acl_name} == expected
