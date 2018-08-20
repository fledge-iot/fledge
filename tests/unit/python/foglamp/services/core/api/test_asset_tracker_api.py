# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


import asyncio
import json
from unittest.mock import MagicMock, patch
from aiohttp import web
import pytest

from foglamp.services.core import routes
from foglamp.services.core import connect
from foglamp.common.storage_client.storage_client import StorageClientAsync
from foglamp.services.core.api import asset_tracker


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("api", "asset-tracker")
class TestAssetTracker:

    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop)
        # fill the routes table
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    async def test_get_asset_track(self, client, loop):
        @asyncio.coroutine
        def async_mock():
            return {"rows": rows, 'count': 1}

        storage_client_mock = MagicMock(StorageClientAsync)
        rows = [{'asset': 'AirIntake', 'event': 'Ingest', 'foglamp': 'Booth1', 'service': 'PT100_In1', 'plugin': 'PT100', "timestamp": "2018-08-13 15:39:48.796263"},
                {'asset': 'AirIntake', 'event': 'Egress', 'foglamp': 'Booth1', 'service': 'Display', 'plugin': 'ShopFloorDisplay', "timestamp": "2018-08-13 16:00:00.134563"}]
        payload = {'where': {'condition': '=', 'value': 1, 'column': '1'}, 'return': ['asset', 'event', 'service', 'foglamp', 'plugin', {'alias': 'timestamp', 'column': 'ts', 'format': 'YYYY-MM-DD HH24:MI:SS.MS'}]}
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=asyncio.ensure_future(async_mock(), loop=loop)) as patch_query_payload:
                resp = await client.get('/foglamp/track')
                assert 200 == resp.status
                result = await resp.text()
                json_response = json.loads(result)
                assert {'track': rows} == json_response
            args, kwargs = patch_query_payload.call_args
            assert 'asset_tracker' == args[0]
            assert payload == json.loads(args[1])

    @pytest.mark.skip("Once initial code version approve, will add more tests")
    @pytest.mark.parametrize("request_params, payload", [
        ("asset", {}),
        ("event", {}),
        ("service", {})
    ])
    async def test_get_asset_track_with_params(self, client, request_params, payload, loop):
        pass
