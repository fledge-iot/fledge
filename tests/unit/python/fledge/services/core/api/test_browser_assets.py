# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END


import asyncio
import json
from unittest.mock import MagicMock, patch

from aiohttp import web
from aiohttp.web_urldispatcher import PlainResource, DynamicResource
import pytest

from fledge.services.core.api import browser
from fledge.services.core import connect
from fledge.common.storage_client.storage_client import ReadingsStorageClientAsync

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


URLS = ['fledge/asset',
        '/fledge/asset/fogbench%2fhumidity',
        '/fledge/asset/fogbench%2fhumidity/temperature',
        '/fledge/asset/fogbench%2fhumidity/temperature/series']

PAYLOADS = ['{"aggregate": {"column": "*", "alias": "count", "operation": "count"}, "group": "asset_code"}',
            '{"return": ["reading", {"column": "user_ts", "alias": "timestamp"}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity"}, "limit": 20, "sort": {"column": "user_ts", "direction": "desc"}}',
            '{"return": [{"column": "user_ts", "alias": "timestamp"}, {"json": {"properties": "temperature", "column": "reading"}, "alias": "temperature"}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity"}, "limit": 20, "sort": {"column": "user_ts", "direction": "desc"}}',
            '{"aggregate": [{"operation": "min", "alias": "min", "json": {"properties": "temperature", "column": "reading"}}, {"operation": "max", "alias": "max", "json": {"properties": "temperature", "column": "reading"}}, {"operation": "avg", "alias": "average", "json": {"properties": "temperature", "column": "reading"}}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity"}, "group": {"format": "YYYY-MM-DD HH24:MI:SS", "column": "user_ts", "alias": "timestamp"}, "limit": 20, "sort": {"column": "user_ts", "direction": "desc"}}'
            ]
RESULTS = [{'rows': [{'count': 10, 'asset_code': 'TI sensorTag/luxometer'}], 'count': 1},
           {'rows': [{'reading': {'temperature': 26, 'humidity': 93}, 'timestamp': '2018-02-16 15:08:51.026'}], 'count': 1},
           {'rows': [{'temperature': 26, 'timestamp': '2018-02-16 15:08:51.026'}], 'count': 1},
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
        assert 9 == len(app.router.resources())

    def test_routes_info(self, app):
        for index, route in enumerate(app.router.routes()):
            res_info = route.resource.get_info()
            if index == 0:
                assert "GET" == route.method
                assert type(route.resource) is PlainResource
                assert "/fledge/asset" == res_info["path"]
                assert str(route.handler).startswith("<function asset_counts")
            elif index == 1:
                assert "GET" == route.method
                assert type(route.resource) is DynamicResource
                assert "/fledge/asset/{asset_code}" == res_info["formatter"]
                assert str(route.handler).startswith("<function asset")
            elif index == 2:
                assert "GET" == route.method
                assert type(route.resource) is DynamicResource
                assert "/fledge/asset/{asset_code}/summary" == res_info["formatter"]
                assert str(route.handler).startswith("<function asset_all_readings_summary")
            elif index == 3:
                assert "GET" == route.method
                assert type(route.resource) is DynamicResource
                assert "/fledge/asset/{asset_code}/{reading}" == res_info["formatter"]
                assert str(route.handler).startswith("<function asset_reading")
            elif index == 4:
                assert "GET" == route.method
                assert type(route.resource) is DynamicResource
                assert "/fledge/asset/{asset_code}/{reading}/summary" == res_info["formatter"]
                assert str(route.handler).startswith("<function asset_summary")
            elif index == 5:
                assert "GET" == route.method
                assert type(route.resource) is DynamicResource
                assert "/fledge/asset/{asset_code}/{reading}/series" == res_info["formatter"]
                assert str(route.handler).startswith("<function asset_averages")
            elif index == 6:
                assert "GET" == route.method
                assert type(route.resource) is DynamicResource
                assert "/fledge/asset/{asset_code}/bucket/{bucket_size}" == res_info["formatter"]
                assert str(route.handler).startswith("<function asset_datapoints_with_bucket_size")
            elif index == 7:
                assert "GET" == route.method
                assert type(route.resource) is DynamicResource
                assert "/fledge/asset/{asset_code}/{reading}/bucket/{bucket_size}" == res_info["formatter"]
                assert str(route.handler).startswith("<function asset_readings_with_bucket_size")

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
                elif str(request_url) == 'fledge/asset':
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

    @pytest.mark.parametrize("status_code, message, storage_result, payload", [
        (400, "ERROR: something went wrong", {'message': 'ERROR: something went wrong', 'retryable': False,
                                             'entryPoint': 'retrieve'},
         '{"where": {"value": "fogbench/humidity", "column": "asset_code", "condition": "="}, "return": ["reading"], '
         '"sort": {"column": "user_ts", "direction": "desc"}, "limit": 1}'),
        (404, "fogbench/humidity asset_code not found", {"rows": [], "count": 0},
         '{"where": {"value": "fogbench/humidity", "column": "asset_code", "condition": "="}, "return": ["reading"], '
         '"sort": {"column": "user_ts", "direction": "desc"}, "limit": 1}'),
        (404, "temperature reading key is not found", {"count": 1, "rows": [{"reading": {"temp": 286.8, "visibility": 10000,
                                                                                 "pressure": 1000, "humidity": 93}}]},
         '{"where": {"value": "fogbench/humidity", "column": "asset_code", "condition": "="}, "return": ["reading"], '
         '"sort": {"column": "user_ts", "direction": "desc"}, "limit": 1}')
    ])
    async def test_bad_summary(self, client, status_code, message, storage_result, payload):
        readings_storage_client_mock = MagicMock(ReadingsStorageClientAsync)
        with patch.object(connect, 'get_readings_async', return_value=readings_storage_client_mock):
            with patch.object(readings_storage_client_mock, 'query', return_value=mock_coro(storage_result)) \
                    as query_patch:
                resp = await client.get('/fledge/asset/fogbench%2fhumidity/temperature/summary')
                assert status_code == resp.status
                assert message == resp.reason
            args, kwargs = query_patch.call_args
            assert json.loads(payload) == json.loads(args[0])
            query_patch.assert_called_once_with(args[0])

    async def test_good_summary(self, client):
        result1 = {"count": 1, "rows": [{"reading": {"temperature": 286.8, "visibility": 10000, "pressure": 1000,
                                                     "humidity": 93}}]}
        result2 = {'rows': [{'max': '9', 'min': '9', 'average': '9'}], 'count': 1}
        payload = '{"aggregate": [{"operation": "min", "alias": "min", "json": {"properties": "temperature", "column": ' \
                  '"reading"}}, {"operation": "max", "alias": "max", "json": {"properties": "temperature", "column": ' \
                  '"reading"}}, {"operation": "avg", "alias": "average", "json": {"properties": "temperature", ' \
                  '"column": "reading"}}], "where": {"column": "asset_code", "condition": "=", ' \
                  '"value": "fogbench/humidity"}}'
        asset_payload = '{"return": ["reading"], "where": {"column": "asset_code", "condition": "=", ' \
            '"value": "fogbench/humidity"}, "limit": 1, "sort": {"column": "user_ts", "direction": "desc"}}'
        readings_storage_client_mock = MagicMock(ReadingsStorageClientAsync)
        with patch.object(connect, 'get_readings_async', return_value=readings_storage_client_mock):
            with patch.object(readings_storage_client_mock, 'query', side_effect=[mock_coro(result1),
                                                                                  mock_coro(result2)]) as query_patch:
                resp = await client.get('/fledge/asset/fogbench%2fhumidity/temperature/summary')
                assert 200 == resp.status
                r = await resp.text()
                json_response = json.loads(r)
                assert {'temperature': result2['rows'][0]} == json_response
            args, kwargs = query_patch.call_args
            assert json.loads(payload) == json.loads(args[0])
            assert 2 == query_patch.call_count
            args0, kwargs0 = query_patch.call_args_list[0]
            args1, kwargs1 = query_patch.call_args_list[1]
            assert json.loads(asset_payload) == json.loads(args0[0])
            assert json.loads(payload) == json.loads(args1[0])

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
                resp = await client.get('fledge/asset/fogbench%2Fhumidity/temperature/series?group={}'
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
        resp = await client.get('fledge/asset/fogbench%2Fhumidity/temperature/series{}'.format(request_param))
        assert 400 == resp.status
        assert response_message == resp.reason

    @pytest.mark.parametrize("request_params, payload", [
        ('?limit=5', '{"return": [{"alias": "timestamp", "column": "user_ts"}, {"json": {"properties": "temperature", "column": "reading"}, "alias": "temperature"}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity"}, "limit": 5, "sort": {"column": "user_ts", "direction": "desc"}}'),
        ('?skip=1', '{"return": [{"alias": "timestamp", "column": "user_ts"}, {"json": {"properties": "temperature", "column": "reading"}, "alias": "temperature"}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity"}, "limit": 20, "skip": 1, "sort": {"column": "user_ts", "direction": "desc"}}'),
        ('?limit=5&skip=1', '{"return": [{"alias": "timestamp", "column": "user_ts"}, {"json": {"properties": "temperature", "column": "reading"}, "alias": "temperature"}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity"}, "limit": 5, "skip": 1, "sort": {"column": "user_ts", "direction": "desc"}}'),
        ('?seconds=3600', '{"return": [{"alias": "timestamp", "column": "user_ts"}, {"json": {"properties": "temperature", "column": "reading"}, "alias": "temperature"}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity", "and": {"column": "user_ts", "condition": "newer", "value": 3600}}, "sort": {"column": "user_ts", "direction": "desc"}}'),
        ('?minutes=20', '{"return": [{"alias": "timestamp", "column": "user_ts"}, {"json": {"properties": "temperature", "column": "reading"}, "alias": "temperature"}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity", "and": {"column": "user_ts", "condition": "newer", "value": 1200}}, "sort": {"column": "user_ts", "direction": "desc"}}'),
        ('?hours=3', '{"return": [{"alias": "timestamp", "column": "user_ts"}, {"json": {"properties": "temperature", "column": "reading"}, "alias": "temperature"}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity", "and": {"column": "user_ts", "condition": "newer", "value": 10800}}, "sort": {"column": "user_ts", "direction": "desc"}}'),
        ('?seconds=60&minutes=10', '{"return": [{"alias": "timestamp", "column": "user_ts"}, {"json": {"properties": "temperature", "column": "reading"}, "alias": "temperature"}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity", "and": {"column": "user_ts", "condition": "newer", "value": 60}}, "sort": {"column": "user_ts", "direction": "desc"}}'),
        ('?seconds=600&hours=1', '{"return": [{"alias": "timestamp", "column": "user_ts"}, {"json": {"properties": "temperature", "column": "reading"}, "alias": "temperature"}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity", "and": {"column": "user_ts", "condition": "newer", "value": 600}}, "sort": {"column": "user_ts", "direction": "desc"}}'),
        ('?minutes=20&hours=1', '{"return": [{"alias": "timestamp", "column": "user_ts"}, {"json": {"properties": "temperature", "column": "reading"}, "alias": "temperature"}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity", "and": {"column": "user_ts", "condition": "newer", "value": 1200}}, "sort": {"column": "user_ts", "direction": "desc"}}'),
        ('?seconds=10&minutes=10&hours=1', '{"return": [{"alias": "timestamp", "column": "user_ts"}, {"json": {"properties": "temperature", "column": "reading"}, "alias": "temperature"}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity", "and": {"column": "user_ts", "condition": "newer", "value": 10}}, "sort": {"column": "user_ts", "direction": "desc"}}')
    ])
    async def test_limit_skip_time_units_payload(self, client, request_params, payload):
        readings_storage_client_mock = MagicMock(ReadingsStorageClientAsync)
        with patch.object(connect, 'get_readings_async', return_value=readings_storage_client_mock):
            with patch.object(readings_storage_client_mock, 'query', return_value=mock_coro({'count': 0, 'rows': []})) \
                    as query_patch:
                resp = await client.get('fledge/asset/fogbench%2Fhumidity/temperature{}'.format(request_params))
                assert 200 == resp.status
                r = await resp.text()
                json_response = json.loads(r)
                assert [] == json_response
            args, kwargs = query_patch.call_args
            assert json.loads(payload) == json.loads(args[0])
            query_patch.assert_called_once_with(args[0])

# TODO This test is looking for the query that caused the error in FOGL-2365 it should be replaced
# by the right test
#
#    async def test_asset_all_readings_summary_when_no_asset_code_found(self, client):
#        readings_storage_client_mock = MagicMock(ReadingsStorageClientAsync)
#        with patch.object(connect, 'get_readings_async', return_value=readings_storage_client_mock):
#            with patch.object(readings_storage_client_mock, 'query', return_value=mock_coro({'count': 0, 'rows': []})) as query_patch:
#                resp = await client.get('fledge/asset/fogbench_humidity/summary')
#                assert 404 == resp.status
#                assert 'fogbench_humidity asset_code not found' == resp.reason
#            query_patch.assert_called_once_with('{"return": ["reading"], "where": {"column": "asset_code", "condition": "=", "value": "fogbench_humidity"}}')

    async def test_asset_all_readings_summary(self, client):
        @asyncio.coroutine
        def q_result(*args):
            if payload1 == args[0]:
                return {'rows': [{'reading': {'humidity': 20}}], 'count': 1}
            if payload2 == args[0]:
                return {'count': 1, 'rows': [{'min': 13.0, 'max': 83.0, 'average': 33.5}]}

        payload1 = {"return": ["reading"],
                    "where": {"column": "asset_code", "condition": "=", "value": "fogbench_humidity"}}
        payload2 = {
            "aggregate": [{"operation": "min", "json": {"properties": "humidity", "column": "reading"}, "alias": "min"},
                          {"operation": "max", "json": {"properties": "humidity", "column": "reading"}, "alias": "max"},
                          {"operation": "avg", "json": {"properties": "humidity", "column": "reading"},
                           "alias": "average"}],
            "where": {"column": "asset_code", "condition": "=", "value": "fogbench_humidity"}, "limit": 20}

        readings_storage_client_mock = MagicMock(ReadingsStorageClientAsync)
        with patch.object(connect, 'get_readings_async', return_value=readings_storage_client_mock):
            with patch.object(readings_storage_client_mock, 'query', side_effect=[q_result(payload1), q_result(payload2)]) as patch_query:
                resp = await client.get('fledge/asset/fogbench_humidity/summary')
                assert 200 == resp.status
                r = await resp.text()
                json_response = json.loads(r)
                assert [{'humidity': {'average': 33.5, 'max': 83.0, 'min': 13.0}}] == json_response
            assert 2 == patch_query.call_count
            args0, kwargs0 = patch_query.call_args_list[0]
            args1, kwargs1 = patch_query.call_args_list[1]
            # assert '{"return": ["reading"], "where": {"column": "asset_code", "condition": "=", "value": "fogbench_humidity"}}' in args0
            # FIXME: ordering issue and add tests for datetimeunits request param
            # assert '{"aggregate": [{"operation": "min", "json": {"column": "reading", "properties": "humidity"}, "alias": "min"}, {"operation": "max", "json": {"column": "reading", "properties": "humidity"}, "alias": "max"}, {"operation": "avg", "json": {"column": "reading", "properties": "humidity"}, "alias": "average"}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench_humidity"}, "limit": 20}' in args1

    @pytest.mark.skip(reason='TODO: FOGL-3541 rewrite tests')
    @pytest.mark.parametrize("asset_code", [
        "fogbench%2fhumidity",
        "fogbench%2fhumidity, fogbench%2ftemperature"
    ])
    async def test_asset_datapoints_with_bucket_size(self, asset_code, client):
        payload2 = {"aggregate": {"operation": "all"}, "where": {"and": {"column": "user_ts", "value": "1572851627.341446", "condition": ">="}, "column": "asset_code", "value": ["fogbench/humidity"], "condition": "in"}, "timebucket": {"timestamp": "user_ts", "size": "60", "alias": "timestamp", "format": "YYYY-MM-DD HH24:MI:SS"}, "limit": 1}
        result2 = {'rows': [{"min": 15082, "average": 15083, "timestamp": "2019-10-11 06:22:30", "max": 15086}], 'count': 1}
        payload1 = '{"sort": {"direction": "desc", "column": "user_ts"}, "where": {"column": "asset_code", "value": ["fogbench/humidity"], "condition": "in"}, "limit": 1}'
        result1 = {'rows': [{'reading': {'temperature': 70}}], 'count': 1}
        readings_storage_client_mock = MagicMock(ReadingsStorageClientAsync)
        res = [mock_coro(result1), mock_coro(result2)]
        patch_count = 2
        if len(asset_code.split(",")) >= 2:
            res = [mock_coro(result1), mock_coro(result1), mock_coro(result2)]
            patch_count = 3
        with patch.object(connect, 'get_readings_async', return_value=readings_storage_client_mock):
            with patch.object(readings_storage_client_mock, 'query', side_effect=res) as query_patch:
                resp = await client.get('fledge/asset/{}/bucket/60'.format(asset_code))
                assert 200 == resp.status
                r = await resp.text()
                json_response = json.loads(r)
                assert result2['rows'] == json_response
            assert patch_count == query_patch.call_count
            args, kwargs = query_patch.call_args_list[0]
            assert json.loads(payload1) == json.loads(args[0])
            # TODO: After datetime patch assert full payload
            # assert payload == json.loads(args[0])

    @pytest.mark.skip(reason='TODO: FOGL-3541 rewrite tests')
    async def test_asset_readings_with_bucket_size(self, client):
        payload2 = {"aggregate": [{"operation": "min", "json": {"properties": "temperature", "column": "reading"}, "alias": "min"}, {"operation": "max", "json": {"properties": "temperature", "column": "reading"}, "alias": "max"}, {"operation": "avg", "json": {"properties": "temperature", "column": "reading"}, "alias": "average"}], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity", "and": {"column": "user_ts", "condition": ">=", "value": "1570732140.0"}}, "timebucket": {"timestamp": "user_ts", "size": "60", "format": "YYYY-MM-DD HH24:MI:SS", "alias": "timestamp"}, "limit": 1}
        result2 = {'rows': [{"min": 15082, "average": 15083, "timestamp": "2019-10-11 06:22:30", "max": 15086}], 'count': 1}
        payload1 = '{"return": ["reading"], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity"}, "limit": 1, "sort": {"column": "user_ts", "direction": "desc"}}'
        result1 = {'rows': [{'reading': {'temperature': 70}}], 'count': 1}
        readings_storage_client_mock = MagicMock(ReadingsStorageClientAsync)
        # FIXME: datetime.now() patch
        # import datetime
        # target = datetime.datetime(2019, 10, 11)
        # with patch.object(datetime, 'datetime.now', MagicMock(wraps=datetime.datetime)) as dt_patch:
        #     dt_patch.now.return_value = target
        with patch.object(connect, 'get_readings_async', return_value=readings_storage_client_mock):
            with patch.object(readings_storage_client_mock, 'query', side_effect=[mock_coro(result1),
                                                                                  mock_coro(result2)]) as query_patch:
                resp = await client.get('fledge/asset/fogbench%2fhumidity/temperature/bucket/60')
                assert 200 == resp.status
                r = await resp.text()
                json_response = json.loads(r)
                assert result2['rows'] == json_response
            assert 2 == query_patch.call_count
            args, kwargs = query_patch.call_args_list[0]
            assert json.loads(payload1) == json.loads(args[0])
            args, kwargs = query_patch.call_args_list[1]
            assert payload2.keys() == json.loads(args[0]).keys()
            # TODO: After datetime patch assert full payload
            # assert payload == json.loads(args[0])

    @pytest.mark.skip(reason='TODO: FOGL-3541 rewrite tests')
    @pytest.mark.parametrize("storage_result, message", [
        ({'rows': [], 'count': 0}, "'fogbench/humidity asset code not found'"),
        ({'count': 1, 'rows': [{'reading': {'temp': 70}}]}, "'temperature reading key is not found for fogbench/humidity asset code'")
    ])
    async def test_bad_asset_readings_with_bucket_size(self, client, storage_result, message):
        payload = '{"return": ["reading"], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity"}, "limit": 1, "sort": {"column": "user_ts", "direction": "desc"}}'
        readings_storage_client_mock = MagicMock(ReadingsStorageClientAsync)
        with patch.object(connect, 'get_readings_async', return_value=readings_storage_client_mock):
            with patch.object(readings_storage_client_mock, 'query', return_value=mock_coro(storage_result)) as query_patch:
                resp = await client.get('fledge/asset/fogbench%2fhumidity/temperature/bucket/60')
                assert 404 == resp.status
                assert message == resp.reason
        assert 1 == query_patch.call_count
        args, kwargs = query_patch.call_args_list[0]
        assert json.loads(payload) == json.loads(args[0])

    @pytest.mark.skip(reason='TODO: FOGL-3541 rewrite tests')
    @pytest.mark.parametrize("url, code, storage_result, message, request_params, with_readings", [
        ('fledge/asset/fogbench%2ftemp/bucket/10', 404, {'rows': [], 'count': 0},
         "'fogbench/temp asset code not found'", "", False),
        ('fledge/asset/fogbench%2ftemp,sinusoid/bucket/10', 404, {'rows': [], 'count': 0},
         "'fogbench/temp asset code not found'", "", False),
        ('fledge/asset/fogbench%2ftemp/bucket/10', 400,
         {'rows': [{'reading': {'temp': 13.45}}], 'count': 1}, "length must be a positive integer",
         "?length=-10", False),
        ('fledge/asset/fogbench%2ftemp/bucket/10', 400,
         {'rows': [{'reading': {'temp': 13.45}}], 'count': 1}, "Invalid value for start. Error: ",
         "?start=1491613677888", False),
        ('fledge/asset/fogbench%2ftemp/bucket/10', 400,
         {'rows': [{'reading': {'temp': 13.45}}], 'count': 1},
         "Invalid value for start. Error: ",
         "?start=567199223456346457", False),
        ('fledge/asset/fogbench%2ftemp/temperature/bucket/60', 404, {'rows': [], 'count': 0},
         "'fogbench/temp asset code not found'", "", True),
        ('fledge/asset/fogbench%2ftemp/temperature/bucket/60', 400,
         {'rows': [{'reading': {'temperature': 13.45}}], 'count': 1}, "length must be a positive integer",
         "?length=-10", True),
        ('fledge/asset/fogbench%2ftemp/temperature/bucket/60', 400,
         {'rows': [{'reading': {'temperature': 13.45}}], 'count': 1},
         "Invalid value for start. Error: ", "?start=149199235346457788234", True)
    ])

    async def test_bad_asset_bucket_size_and_optional_params(self, client, url, code, storage_result, message,
                                                             request_params, with_readings):
        if request_params:
            url += request_params
        readings_storage_client_mock = MagicMock(ReadingsStorageClientAsync)
        if with_readings:
            payload = '{"return": ["reading"], "where": {"column": "asset_code", "condition": "=", "value": "fogbench/temp"}, "limit": 1, "sort": {"column": "user_ts", "direction": "desc"}}'
        else:
            payload = '{"where": {"column": "asset_code", "condition": "in", "value": ["fogbench/temp"]}, "limit": 1, "sort": {"column": "user_ts", "direction": "desc"}}'
        with patch.object(connect, 'get_readings_async', return_value=readings_storage_client_mock):
            with patch.object(readings_storage_client_mock, 'query', side_effect=[mock_coro(storage_result), mock_coro(storage_result)]) as query_patch:
                resp = await client.get(url)
                assert code == resp.status
                assert message in resp.reason
        assert 1 == query_patch.call_count
        args, kwargs = query_patch.call_args
        query_patch.assert_called_once_with(payload)

    @pytest.mark.parametrize("request_params, payload", [
        ('?limit=5&skip=1&order=asc',
         '{"return": ["reading", {"column": "user_ts", "alias": "timestamp"}],'
         ' "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity"},'
         ' "skip": 1, "limit": 5, '
         '"sort": {"column": "user_ts", "direction": "asc"}}'
         ),
        ('?limit=5&skip=1&order=desc',
         '{"return": ["reading", {"column": "user_ts", "alias": "timestamp"}],'
         ' "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity"},'
         ' "skip": 1,"limit": 5, '
         '"sort": {"column": "user_ts", "direction": "desc"}}'
         ),
        ('?limit=5&skip=1',
         '{"return": ["reading", {"column": "user_ts", "alias": "timestamp"}],'
         ' "where": {"column": "asset_code", "condition": "=", "value": "fogbench/humidity"},'
         ' "skip": 1,"limit": 5, '
         '"sort": {"column": "user_ts", "direction": "desc"}}'
         )
    ])
    async def test_order_payload_good(self, client, request_params, payload):
        readings_storage_client_mock = MagicMock(ReadingsStorageClientAsync)
        with patch.object(connect, 'get_readings_async', return_value=readings_storage_client_mock):
            with patch.object(readings_storage_client_mock, 'query', return_value=mock_coro({'count': 0, 'rows': []})) \
                    as query_patch:
                resp = await client.get('fledge/asset/fogbench%2Fhumidity{}'.format(request_params))
                assert 200 == resp.status
                r = await resp.text()
                json_response = json.loads(r)
                assert [] == json_response
            args, kwargs = query_patch.call_args
            assert json.loads(payload) == json.loads(args[0])
            query_patch.assert_called_once_with(args[0])

    @pytest.mark.parametrize("request_params, response_message", [
        ('?limit=5&skip=1&order=blah', 'order must be asc or desc')
    ])
    async def test_order_payload_bad(self, client, request_params, response_message):
        resp = await client.get('fledge/asset/fogbench%2Fhumidity{}'.format(request_params))
        assert 400 == resp.status
        assert response_message == resp.reason
        r = await resp.text()
        json_response = json.loads(r)
        assert {"message": response_message} == json_response
