import asyncio
import json
import sys
from unittest.mock import MagicMock, patch
import pytest
from aiohttp import web

from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.common.alert_manager import AlertManager
from fledge.services.core import connect, routes, server
from fledge.services.core.api import alerts


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2024 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

class TestAlerts:
    """ Alerts API tests """

    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop)
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    async def async_mock(self, return_value):
        return return_value

    def setup_method(self):
        storage_client_mock = MagicMock(StorageClientAsync)
        server.Server._alert_manager = AlertManager(storage_client_mock)

    def teardown_method(self):
        server.Server._alert_manager = None

    async def test_get_all(self, client):
        rv = await self.async_mock([]) if sys.version_info.major == 3 and sys.version_info.minor >= 8 \
            else asyncio.ensure_future(self.async_mock([]))

        with patch.object(server.Server._alert_manager, 'get_all', return_value=rv):
            resp = await client.get('/fledge/alert')
            assert 200 == resp.status
            json_response = json.loads(await resp.text())
            assert 'alerts' in json_response
            assert [] == json_response['alerts']

    async def test_bad_get_all(self, client):
        with patch.object(server.Server._alert_manager, 'get_all', side_effect=Exception):
            with patch.object(alerts._LOGGER, 'error') as patch_logger:
                resp = await client.get('/fledge/alert')
                assert 500 == resp.status
                assert '' == resp.reason
                json_response = json.loads(await resp.text())
                assert 'message' in json_response
                assert '' == json_response['message']
            assert 1 == patch_logger.call_count

    async def test_delete(self, client):
        rv = await self.async_mock("Nothing to delete.") \
            if sys.version_info.major == 3 and sys.version_info.minor >= 8 else (
            asyncio.ensure_future(self.async_mock("Nothing to delete.")))
        with patch.object(server.Server._alert_manager, 'delete', return_value=rv):
            resp = await client.delete('/fledge/alert')
            assert 200 == resp.status
            json_response = json.loads(await resp.text())
            assert 'message' in json_response
            assert "Nothing to delete." == json_response['message']

    @pytest.mark.parametrize("url, msg, exception, status_code, log_count", [
        ('/fledge/alert', '', Exception, 500, 1),
        ('/fledge/alert/blah', 'blah alert not found.', KeyError, 404, 0)
    ])
    async def test_bad_delete(self, client, url, msg, exception, status_code, log_count):
        with patch.object(server.Server._alert_manager, 'delete', side_effect=exception):
            with patch.object(alerts._LOGGER, 'error') as patch_logger:
                resp = await client.delete(url)
                assert status_code == resp.status
                assert msg == resp.reason
                json_response = json.loads(await resp.text())
                assert 'message' in json_response
                assert msg == json_response['message']
            assert log_count == patch_logger.call_count
