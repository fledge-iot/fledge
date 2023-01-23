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

from fledge.common.audit_logger import AuditLogger
from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.services.core import routes, connect
from fledge.services.core.api.asset_tracker import _logger, common_utils


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


async def mock_coro(return_value):
    return return_value


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
                 'plugin': 'PT100', "timestamp": "2018-08-13 15:39:48.796263", "deprecatedTimestamp": "", 'data': '{}'},
                {'asset': 'AirIntake', 'event': 'Egress', 'fledge': 'Booth1', 'service': 'Display',
                 'plugin': 'ShopFloorDisplay', "timestamp": "2018-08-13 16:00:00.134563", "deprecatedTimestamp": "",
                 'data': '{}'}]
        payload = {'where': {'condition': '=', 'value': 1, 'column': '1'},
                   'return': ['asset', 'event', 'service', 'fledge', 'plugin',
                              {'alias': 'timestamp', 'column': 'ts', 'format': 'YYYY-MM-DD HH24:MI:SS.MS'},
                              {'alias': 'deprecatedTimestamp', 'column': 'deprecated_ts'}, 'data'
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

    async def test_bad_deprecate_entry(self, client):
        result = {"message": "failed"}
        _rv = await mock_coro(result) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(result))
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=_rv):
                resp = await client.put('/fledge/track/service/XXX/asset/XXX/event/XXXX')
                assert 500 == resp.status

    async def test_deprecate_entry_not_found(self, client):
        result = {"count": 0, "rows": []}
        _rv = await mock_coro(result) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(result))
        storage_client_mock = MagicMock(StorageClientAsync)
        asset = "blah"
        service = "Test"
        event = "Ingest"
        message = "No record found in asset tracker for given service: {} asset: {} event: {}".format(
            service, asset, event)
        query_payload = {"return": ["deprecated_ts"],
                         "where": {"column": "service", "condition": "=", "value": service,
                                   "and": {"column": "asset", "condition": "=", "value": asset,
                                           "and": {"column": "event", "condition": "=", "value": event}}}}
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=_rv) as patch_query_tbl:
                resp = await client.put('/fledge/track/service/{}/asset/{}/event/{}'.format(service, asset, event))
                assert 404 == resp.status
                assert message == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {"message": message} == json_response
            args, _ = patch_query_tbl.call_args
            assert 'asset_tracker' == args[0]
            assert query_payload == json.loads(args[1])

    async def test_already_deprecated_entry(self, client):
        result = {'count': 1, 'rows': [{'deprecated_ts': '2022-11-18 06:11:13.657'}]}
        _rv = await mock_coro(result) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(result))
        storage_client_mock = MagicMock(StorageClientAsync)
        asset = "Airtake"
        service = "Sparkplug"
        event = "Ingest"
        message = "'{} asset record already deprecated.'".format(asset)
        query_payload = {"return": ["deprecated_ts"],
                         "where": {"column": "service", "condition": "=", "value": service,
                                   "and": {"column": "asset", "condition": "=", "value": asset,
                                           "and": {"column": "event", "condition": "=", "value": event}}}}
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=_rv) as patch_query_tbl:
                resp = await client.put('/fledge/track/service/{}/asset/{}/event/{}'.format(service, asset, event))
                assert 400 == resp.status
                assert message == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {"message": message} == json_response
            args, _ = patch_query_tbl.call_args
            assert 'asset_tracker' == args[0]
            assert query_payload == json.loads(args[1])

    @pytest.mark.parametrize("event, operator, event_list, audit_event", [
        ("Ingest", "in", ["Ingest", "store"], "Ingest & store"),
        ("store", "in", ["Ingest", "store"], "Ingest & store"),
        ("Filter", "=", "Filter", "Filter"),
        ("Egress", "=", "Egress", "Egress")
    ])
    async def test_deprecate_entry(self, client, event, operator, event_list, audit_event):
        asset = "Airtake"
        service = "Sparkplug"
        ts = "2022-11-18 14:27:25.396383+05:30"
        query_payload = {"return": ["deprecated_ts"],
                         "where": {"column": "service", "condition": "=", "value": service,
                                   "and": {"column": "asset", "condition": "=", "value": asset,
                                           "and": {"column": "event", "condition": "=", "value": event}}}}
        update_payload = {"values": {"deprecated_ts": ts},
                          "where": {"column": "service", "condition": "=", "value": service,
                                    "and": {"column": "asset", "condition": "=", "value": asset,
                                            "and": {"column": "event", "condition": operator,
                                                    "value": event_list,
                                                    "and": {"column": "deprecated_ts", "condition": "isnull"}}}}}
        query_result = {'count': 1, 'rows': [{'deprecated_ts': ''}]}
        update_result = {"response": "updated", "rows_affected": 1}
        message = "For {} event, {} asset record entry has been deprecated.".format(event, asset)
        if sys.version_info >= (3, 8):
            _rv = await mock_coro(query_result)
            _rv2 = await mock_coro(update_result)
            _rv3 = await mock_coro(None)
        else:
            _rv = asyncio.ensure_future(mock_coro(query_result))
            _rv2 = asyncio.ensure_future(mock_coro(update_result))
            _rv3 = asyncio.ensure_future(mock_coro(None))

        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=_rv) as patch_query_tbl:
                with patch.object(common_utils, 'local_timestamp', return_value=ts):
                    with patch.object(storage_client_mock, 'update_tbl', return_value=_rv2) as patch_update_tbl:
                        with patch.object(AuditLogger, '__init__', return_value=None):
                            with patch.object(AuditLogger, 'information', return_value=_rv3) as patch_audit:
                                with patch.object(_logger, "info") as log_info:
                                    resp = await client.put('/fledge/track/service/{}/asset/{}/event/{}'.format(
                                        service, asset, event))
                                    assert 200 == resp.status
                                    result = await resp.text()
                                    json_response = json.loads(result)
                                    assert {'success': message} == json_response
                                assert 1 == log_info.call_count
                                log_info.assert_called_once_with(message)
                            patch_audit.assert_called_once_with(
                                'ASTDP', {'asset': asset, 'event': audit_event, 'service': service})
                    args, _ = patch_update_tbl.call_args
                    assert 'asset_tracker' == args[0]
                    assert update_payload == json.loads(args[1])
            args1, _ = patch_query_tbl.call_args
            assert 'asset_tracker' == args1[0]
            assert query_payload == json.loads(args1[1])
