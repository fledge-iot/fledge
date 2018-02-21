# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


import json
from unittest.mock import MagicMock, patch
from aiohttp import web
import pytest
from foglamp.services.core import routes
from foglamp.services.core import connect
from foglamp.common.storage_client.storage_client import StorageClient
from foglamp.services.core import server
from foglamp.services.core.scheduler.scheduler import Scheduler
from foglamp.services.core.scheduler.entities import ScheduledProcess

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("api", "core")
class TestScheduledProcesses:

    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop)
        # fill the routes table
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    async def test_get_scheduled_processes(self, client):

        async def mock_coro():
            processes = []
            process = ScheduledProcess()
            process.name = "foo"
            process.script = "bar"
            processes.append(process)
            return processes

        server.Server.scheduler = Scheduler(None, None)
        with patch.object(server.Server.scheduler, 'get_scheduled_processes', return_value=mock_coro()):
            resp = await client.get('/foglamp/schedule/process')
            result = await resp.text()
            json_response = json.loads(result)
        assert {'processes': ['foo']} == json_response

    async def test_get_scheduled_process(self, client):
        storage_client_mock = MagicMock(StorageClient)
        payload = '{"return": ["name"], "where": {"column": "name", "condition": "=", "value": "purge"}}'
        response = {'rows': [{'name': 'purge'}], 'count': 1}
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
                with patch.object(storage_client_mock, 'query_tbl_with_payload',
                                  return_value=response) as mock_storage_call:
                    resp = await client.get('/foglamp/schedule/process/purge')
                    assert 200 == resp.status
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert 'purge' == json_response
                mock_storage_call.assert_called_with('scheduled_processes', payload)

    async def test_get_scheduled_process_bad_data(self, client):
        storage_client_mock = MagicMock(StorageClient)
        response = {'rows': [], 'count': 0}
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
                with patch.object(storage_client_mock, 'query_tbl_with_payload',
                                  return_value=response):
                    resp = await client.get('/foglamp/schedule/process/bla')
                    assert 404 == resp.status
                    assert 'No such Scheduled Process: bla.' == resp.reason
