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
