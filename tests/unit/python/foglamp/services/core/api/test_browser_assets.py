# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


import asyncio
import json
from unittest.mock import MagicMock, patch

from aiohttp import web
from aiohttp.web_urldispatcher import PlainResource, DynamicResource
import pytest

from foglamp.services.core.api import browser
from foglamp.services.core import connect
from foglamp.common.storage_client.storage_client import ReadingsStorageClientAsync

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


URLS = ['foglamp/asset',
        '/foglamp/asset/fogbench%2fhumidity',
        '/foglamp/asset/fogbench%2fhumidity/temperature',
        '/foglamp/asset/fogbench%2fhumidity/temperature/summary',
        '/foglamp/asset/fogbench%2fhumidity/temperature/series']

PAYLOADS = ['{"aggregate": {"column": "*", "alias": "count", "operation": "count"}, "group": "asset_code"}',
            '{"return": ["reading", {"format": "YYYY-MM-DD HH24:MI:SS.MS", "column": "user_ts", "alias": "timestamp"}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity"}, "limit": 20, "sort": {"column": "user_ts", "direction": "desc"}}',
            '{"return": [{"format": "YYYY-MM-DD HH24:MI:SS.MS", "column": "user_ts", "alias": "timestamp"}, {"json": {"properties": "temperature", "column": "reading"}, "alias": "temperature"}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity"}, "limit": 20, "sort": {"column": "user_ts", "direction": "desc"}}',
            '{"aggregate": [{"operation": "min", "alias": "min", "json": {"properties": "temperature", "column": "reading"}}, {"operation": "max", "alias": "max", "json": {"properties": "temperature", "column": "reading"}}, {"operation": "avg", "alias": "average", "json": {"properties": "temperature", "column": "reading"}}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity"}}',
            '{"aggregate": [{"operation": "min", "alias": "min", "json": {"properties": "temperature", "column": "reading"}}, {"operation": "max", "alias": "max", "json": {"properties": "temperature", "column": "reading"}}, {"operation": "avg", "alias": "average", "json": {"properties": "temperature", "column": "reading"}}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity"}, "group": {"format": "YYYY-MM-DD HH24:MI:SS", "column": "user_ts", "alias": "timestamp"}, "limit": 20, "sort": {"column": "user_ts", "direction": "desc"}}'
            ]
RESULTS = [{'rows': [{'count': 10, 'asset_code': 'TI sensorTag/luxometer'}], 'count': 1},
           {'rows': [{'reading': {'temperature': 26, 'humidity': 93}, 'timestamp': '2018-02-16 15:08:51.026'}], 'count': 1},
           {'rows': [{'temperature': 26, 'timestamp': '2018-02-16 15:08:51.026'}], 'count': 1},
           {'rows': [{'max': '9', 'min': '9', 'average': '9'}], 'count': 1},
           {'rows': [{'average': '26', 'timestamp': '2018-02-16 15:08:51', 'max': '26', 'min': '26'}], 'count': 1}
           ]

FIXTURE_1 = [(url, payload, result) for url, payload, result in zip(URLS, PAYLOADS, RESULTS)]
FIXTURE_2 = [(url, 400, payload) for url, payload in zip(URLS, PAYLOADS)]


@asyncio.coroutine
def mock_coro(*args, **kwargs):
    if len(args) > 0:
        return args[0]
    else:
        return ""


@pytest.allure.feature("unit")
@pytest.allure.story("api", "assets")
class TestBrowserAssets:
    """Browser Assets"""

    @pytest.fixture
    async def app(self):
        app = web.Application()
        browser.setup(app)
        return app

    @pytest.fixture
    def client(self, app, loop, test_client):
        return loop.run_until_complete(test_client(app))

    def test_routes_count(self, app):
        assert 5 == len(app.router.resources())

    def test_routes_info(self, app):
        for index, route in enumerate(app.router.routes()):
            res_info = route.resource.get_info()
            if index == 0:
                assert "GET" == route.method
                assert type(route.resource) is PlainResource
                assert "/foglamp/asset" == res_info["path"]
                assert str(route.handler).startswith("<function asset_counts")
            elif index == 1:
                assert "GET" == route.method
                assert type(route.resource) is DynamicResource
                assert "/foglamp/asset/{asset_code}" == res_info["formatter"]
                assert str(route.handler).startswith("<function asset")
            elif index == 2:
                assert "GET" == route.method
                assert type(route.resource) is DynamicResource
                assert "/foglamp/asset/{asset_code}/{reading}" == res_info["formatter"]
                assert str(route.handler).startswith("<function asset_reading")
            elif index == 3:
                assert "GET" == route.method
                assert type(route.resource) is DynamicResource
                assert "/foglamp/asset/{asset_code}/{reading}/summary" == res_info["formatter"]
                assert str(route.handler).startswith("<function asset_summary")
            elif index == 4:
                assert "GET" == route.method
                assert type(route.resource) is DynamicResource
                assert "/foglamp/asset/{asset_code}/{reading}/series" == res_info["formatter"]
                assert str(route.handler).startswith("<function asset_averages")

    @pytest.mark.parametrize("request_url, payload, result", FIXTURE_1)
    async def test_end_points(self, client, request_url, payload, result):
        readings_storage_client_mock = MagicMock(ReadingsStorageClientAsync)
        with patch.object(connect, 'get_readings_async', return_value=readings_storage_client_mock):
            with patch.object(readings_storage_client_mock, 'query', return_value=mock_coro(result)) as query_patch:
                resp = await client.get(request_url)
                assert 200 == resp.status
                r = await resp.text()
                json_response = json.loads(r)
                if str(request_url).endswith("summary"):
                    assert {'temperature': result['rows'][0]} == json_response
                elif str(request_url) == 'foglamp/asset':
                    result['rows'][0]['assetCode'] = result['rows'][0].pop('asset_code')
                    assert result['rows'] == json_response
                else:
                    assert result['rows'] == json_response
            args, kwargs = query_patch.call_args
            assert json.loads(payload) == json.loads(args[0])
            query_patch.assert_called_once_with(args[0])

    @pytest.mark.parametrize("request_url, response_code, payload", FIXTURE_2)
    async def test_bad_request(self, client, request_url, response_code, payload):
        readings_storage_client_mock = MagicMock(ReadingsStorageClientAsync)
        result = {'message': 'ERROR: something went wrong', 'retryable': False, 'entryPoint': 'retrieve'}
        with patch.object(connect, 'get_readings_async', return_value=readings_storage_client_mock):
            with patch.object(readings_storage_client_mock, 'query', return_value=mock_coro(result)) as query_patch:
                resp = await client.get(request_url)
                assert response_code == resp.status
                assert result['message'] == resp.reason
            args, kwargs = query_patch.call_args
            assert json.loads(payload) == json.loads(args[0])
            query_patch.assert_called_once_with(args[0])

    @pytest.mark.parametrize("request_url", URLS)
    async def test_http_exception(self, client, request_url):
        with patch.object(connect, 'get_readings_async', return_value=Exception):
            resp = await client.get(request_url)
            assert 500 == resp.status
            assert 'Internal Server Error' == resp.reason

    @pytest.mark.parametrize("group_name, payload, result", [
        ('seconds', '{"aggregate": [{"alias": "min", "operation": "min", "json": {"properties": "temperature", "column": "reading"}}, {"alias": "max", "operation": "max", "json": {"properties": "temperature", "column": "reading"}}, {"alias": "average", "operation": "avg", "json": {"properties": "temperature", "column": "reading"}}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity"}, "group": {"alias": "timestamp", "format": "YYYY-MM-DD HH24:MI:SS", "column": "user_ts"}, "limit": 20, "sort": {"column": "user_ts", "direction": "desc"}}',
         {'count': 1, 'rows': [{'min': '9', 'average': '9', 'max': '9', 'timestamp': '2018-02-19 17:35:25'}]}),
        ('minutes', '{"aggregate": [{"alias": "min", "operation": "min", "json": {"properties": "temperature", "column": "reading"}}, {"alias": "max", "operation": "max", "json": {"properties": "temperature", "column": "reading"}}, {"alias": "average", "operation": "avg", "json": {"properties": "temperature", "column": "reading"}}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity"}, "group": {"alias": "timestamp", "format": "YYYY-MM-DD HH24:MI", "column": "user_ts"}, "limit": 20, "sort": {"column": "user_ts", "direction": "desc"}}',
         {'count': 1, 'rows': [{'min': '9', 'average': '9', 'max': '9', 'timestamp': '2018-02-19 17:35'}]}),
        ('hours', '{"aggregate": [{"alias": "min", "operation": "min", "json": {"properties": "temperature", "column": "reading"}}, {"alias": "max", "operation": "max", "json": {"properties": "temperature", "column": "reading"}}, {"alias": "average", "operation": "avg", "json": {"properties": "temperature", "column": "reading"}}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity"}, "group": {"alias": "timestamp", "format": "YYYY-MM-DD HH24", "column": "user_ts"}, "limit": 20, "sort": {"column": "user_ts", "direction": "desc"}}',
         {'count': 1, 'rows': [{'min': '9', 'average': '9', 'max': '9', 'timestamp': '2018-02-19 17'}]})
    ])
    async def test_asset_averages_with_valid_group_name(self, client, group_name, payload, result):
        readings_storage_client_mock = MagicMock(ReadingsStorageClientAsync)
        with patch.object(connect, 'get_readings_async', return_value=readings_storage_client_mock):
            with patch.object(readings_storage_client_mock, 'query', return_value=mock_coro(result)) as query_patch:
                resp = await client.get('foglamp/asset/fogbench%2Fhumidity/temperature/series?group={}'
                                        .format(group_name))
                assert 200 == resp.status
                r = await resp.text()
                json_response = json.loads(r)
                assert result['rows'] == json_response
            args, kwargs = query_patch.call_args
            assert json.loads(payload) == json.loads(args[0])
            query_patch.assert_called_once_with(args[0])

    @pytest.mark.parametrize("request_param, response_message", [
        ('?group=BLA', "BLA is not a valid group"),
        ('?group=0', "0 is not a valid group"),
        ('?limit=invalid', "Limit must be a positive integer"),
        ('?limit=-1', "Limit must be a positive integer"),
        ('?skip=invalid', "Skip/Offset must be a positive integer"),
        ('?skip=-1', "Skip/Offset must be a positive integer"),
        ('?seconds=invalid', "Time must be a positive integer"),
        ('?seconds=-1', "Time must be a positive integer"),
        ('?minutes=invalid', "Time must be a positive integer"),
        ('?minutes=-1', "Time must be a positive integer"),
        ('?hours=invalid', "Time must be a positive integer"),
        ('?hours=-1', "Time must be a positive integer")
    ])
    async def test_request_params_with_bad_data(self, client, request_param, response_message):
        resp = await client.get('foglamp/asset/fogbench%2Fhumidity/temperature/series{}'.format(request_param))
        assert 400 == resp.status
        assert response_message == resp.reason

    @pytest.mark.parametrize("request_params, payload", [
        ('?limit=5', '{"return": [{"alias": "timestamp", "column": "user_ts", "format": "YYYY-MM-DD HH24:MI:SS.MS"}, {"json": {"properties": "temperature", "column": "reading"}, "alias": "temperature"}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity"}, "limit": 5, "sort": {"column": "user_ts", "direction": "desc"}}'),
        ('?skip=1', '{"return": [{"alias": "timestamp", "column": "user_ts", "format": "YYYY-MM-DD HH24:MI:SS.MS"}, {"json": {"properties": "temperature", "column": "reading"}, "alias": "temperature"}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity"}, "limit": 20, "skip": 1, "sort": {"column": "user_ts", "direction": "desc"}}'),
        ('?limit=5&skip=1', '{"return": [{"alias": "timestamp", "column": "user_ts", "format": "YYYY-MM-DD HH24:MI:SS.MS"}, {"json": {"properties": "temperature", "column": "reading"}, "alias": "temperature"}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity"}, "limit": 5, "skip": 1, "sort": {"column": "user_ts", "direction": "desc"}}'),
        ('?seconds=3600', '{"return": [{"alias": "timestamp", "column": "user_ts", "format": "YYYY-MM-DD HH24:MI:SS.MS"}, {"json": {"properties": "temperature", "column": "reading"}, "alias": "temperature"}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity", "and": {"column": "user_ts", "condition": "newer", "value": 3600}}, "limit": 20, "sort": {"column": "user_ts", "direction": "desc"}}'),
        ('?minutes=20', '{"return": [{"alias": "timestamp", "column": "user_ts", "format": "YYYY-MM-DD HH24:MI:SS.MS"}, {"json": {"properties": "temperature", "column": "reading"}, "alias": "temperature"}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity", "and": {"column": "user_ts", "condition": "newer", "value": 1200}}, "limit": 20, "sort": {"column": "user_ts", "direction": "desc"}}'),
        ('?hours=3', '{"return": [{"alias": "timestamp", "column": "user_ts", "format": "YYYY-MM-DD HH24:MI:SS.MS"}, {"json": {"properties": "temperature", "column": "reading"}, "alias": "temperature"}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity", "and": {"column": "user_ts", "condition": "newer", "value": 10800}}, "limit": 20, "sort": {"column": "user_ts", "direction": "desc"}}'),
        ('?seconds=60&minutes=10', '{"return": [{"alias": "timestamp", "column": "user_ts", "format": "YYYY-MM-DD HH24:MI:SS.MS"}, {"json": {"properties": "temperature", "column": "reading"}, "alias": "temperature"}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity", "and": {"column": "user_ts", "condition": "newer", "value": 60}}, "limit": 20, "sort": {"column": "user_ts", "direction": "desc"}}'),
        ('?seconds=600&hours=1', '{"return": [{"alias": "timestamp", "column": "user_ts", "format": "YYYY-MM-DD HH24:MI:SS.MS"}, {"json": {"properties": "temperature", "column": "reading"}, "alias": "temperature"}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity", "and": {"column": "user_ts", "condition": "newer", "value": 600}}, "limit": 20, "sort": {"column": "user_ts", "direction": "desc"}}'),
        ('?minutes=20&hours=1', '{"return": [{"alias": "timestamp", "column": "user_ts", "format": "YYYY-MM-DD HH24:MI:SS.MS"}, {"json": {"properties": "temperature", "column": "reading"}, "alias": "temperature"}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity", "and": {"column": "user_ts", "condition": "newer", "value": 1200}}, "limit": 20, "sort": {"column": "user_ts", "direction": "desc"}}'),
        ('?seconds=10&minutes=10&hours=1', '{"return": [{"alias": "timestamp", "column": "user_ts", "format": "YYYY-MM-DD HH24:MI:SS.MS"}, {"json": {"properties": "temperature", "column": "reading"}, "alias": "temperature"}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity", "and": {"column": "user_ts", "condition": "newer", "value": 10}}, "limit": 20, "sort": {"column": "user_ts", "direction": "desc"}}')
    ])
    async def test_limit_skip_time_units_payload(self, client, request_params, payload):
        readings_storage_client_mock = MagicMock(ReadingsStorageClientAsync)
        with patch.object(connect, 'get_readings_async', return_value=readings_storage_client_mock):
            with patch.object(readings_storage_client_mock, 'query', return_value=mock_coro({'count': 0, 'rows': []})) \
                    as query_patch:
                resp = await client.get('foglamp/asset/fogbench%2Fhumidity/temperature{}'.format(request_params))
                assert 200 == resp.status
                r = await resp.text()
                json_response = json.loads(r)
                assert [] == json_response
            args, kwargs = query_patch.call_args
            assert json.loads(payload) == json.loads(args[0])
            query_patch.assert_called_once_with(args[0])
