import asyncio
import json
import sys

from unittest.mock import MagicMock, patch
import pytest
from aiohttp import web

from fledge.common.audit_logger import AuditLogger
from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.common.web import middleware
from fledge.services.core import connect, routes
from fledge.services.core.api.control_service import entrypoint


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2023 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


async def mock_coro(*args):
    return None if len(args) == 0 else args[0]


@pytest.allure.feature("unit")
@pytest.allure.story("api", "entrypoint")
class TestEntrypoint:
    """ Control Flow Entrypoint API tests"""

    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop, middlewares=[middleware.optional_auth_middleware])
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    async def test_get_all_entrypoints(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        storage_result = {'count': 3, 'rows': [
            {'name': 'EP1', 'description': 'EP1', 'type': 1, 'operation_name': 'OP1', 'destination': 0,
             'destination_arg': '', 'anonymous': 't'},
            {'name': 'EP2', 'description': 'Ep2', 'type': 0, 'operation_name': '', 'destination': 0,
             'destination_arg': '', 'anonymous': 'f'},
            {'name': 'EP3', 'description': 'EP3', 'type': 1, 'operation_name': 'OP2', 'destination': 0,
             'destination_arg': '', 'anonymous': 'f'}]}
        expected_api_response = {"controls": [{"name": "EP1", "description": "EP1", "permitted": True},
                                              {"name": "EP2", "description": "Ep2", "permitted": True},
                                              {"name": "EP3", "description": "EP3", "permitted": True}]}
        rv = await mock_coro(storage_result) if sys.version_info >= (3, 8) else asyncio.ensure_future(
            mock_coro(storage_result))
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl', return_value=rv) as patch_query_tbl:
                resp = await client.get('/fledge/control/manage')
                assert 200 == resp.status
                json_response = json.loads(await resp.text())
                assert 'controls' in json_response
                assert expected_api_response == json_response
            patch_query_tbl.assert_called_once_with('control_api')
