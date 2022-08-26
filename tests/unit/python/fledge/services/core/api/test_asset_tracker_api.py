# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END


import asyncio
import json
from unittest.mock import MagicMock, patch
from aiohttp import web
import pytest
import sys

from fledge.services.core import routes
from fledge.services.core import connect
from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.services.core.api import asset_tracker


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
        async def async_mock():
            await asyncio.sleep(0)
            return {"rows": rows, 'count': 1}

        storage_client_mock = MagicMock(StorageClientAsync)
        rows = [{'asset': 'AirIntake', 'event': 'Ingest', 'fledge': 'Booth1', 'service': 'PT100_In1',
                 'plugin': 'PT100', "timestamp": "2018-08-13 15:39:48.796263", "deprecatedTimestamp": ""
                 },
                {'asset': 'AirIntake', 'event': 'Egress', 'fledge': 'Booth1', 'service': 'Display',
                 'plugin': 'ShopFloorDisplay', "timestamp": "2018-08-13 16:00:00.134563", "deprecatedTimestamp": ""
                 }
                ]
        payload = {'where': {'condition': '=', 'value': 1, 'column': '1'},
                   'return': ['asset', 'event', 'service', 'fledge', 'plugin',
                              {'alias': 'timestamp', 'column': 'ts', 'format': 'YYYY-MM-DD HH24:MI:SS.MS'},
                              {'alias': 'deprecatedTimestamp', 'column': 'deprecated_ts'}
                              ]
                   }

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        _rv = await async_mock() if sys.version_info.major == 3 and sys.version_info.minor >= 8 \
            else asyncio.ensure_future(async_mock())
        
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=_rv) as patch_query_payload:
                resp = await client.get('/fledge/track')
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
