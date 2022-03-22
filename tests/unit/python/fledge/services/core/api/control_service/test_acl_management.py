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
    """ ACL API tests
    """

    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop, middlewares=[middleware.optional_auth_middleware])
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    async def test_get_all_acls(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        result = {'count': 2, 'rows': [
            {'name': 'demoACL', 'service': [{'name': 'Fledge Storage'}, {'type': 'Southbound'}],
             'url': [{'url': '/foglamp/south/operation', 'acl': [{'type': 'Southbound'}]}]},
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
