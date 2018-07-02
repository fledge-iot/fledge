# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test foglamp/services/core/api/statistics.py """

import asyncio
import json

from unittest.mock import MagicMock, patch
from aiohttp import web
import pytest

from foglamp.services.core import routes
from foglamp.services.core import connect
from foglamp.common.storage_client.storage_client import StorageClientAsync

__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("api", "statistics")
class TestStatistics:

    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop)
        # fill the routes table
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    async def test_get_stats(self, client):
        payload = {"return": ["key", "description", "value"], "sort": {"column": "key", "direction": "asc"}}
        result = {"rows": [{"value": 0, "key": "BUFFERED", "description": "blah1"},
                           {"value": 1, "key": "READINGS", "description": "blah2"}]
                  }

        @asyncio.coroutine
        def mock_coro():
            return result

        mock_async_storage_client = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=mock_async_storage_client):
            with patch.object(mock_async_storage_client, 'query_tbl_with_payload', return_value=mock_coro()) as query_patch:
                resp = await client.get("/foglamp/statistics")
                assert 200 == resp.status
                r = await resp.text()
                assert result["rows"] == json.loads(r)

        args, kwargs = query_patch.call_args
        assert json.loads(args[1]) == payload
        query_patch.assert_called_once_with('statistics', args[1])

    async def test_get_stats_exception(self, client):
        result = {"message": "error"}

        @asyncio.coroutine
        def mock_coro():
            return result

        mock_async_storage_client = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=mock_async_storage_client):
            with patch.object(mock_async_storage_client, 'query_tbl_with_payload', return_value=mock_coro()):
                resp = await client.get("/foglamp/statistics")
                assert 500 == resp.status
                assert "Internal Server Error" == resp.reason

    @pytest.mark.parametrize("interval, schedule_interval", [
        (60, "00:01:00"),
        (100, "0:01:40"),
        (3660, "1:01:00"),
        (3660, "01:01:00"),
        (86400, "1 day"),
        (86500, "1 day, 00:01:40"),
        (86500, "1 day 00:01:40"),
        (86400, "1 day 0:00:00"),
        (86400, "1 day, 0:00:00"),
        (172800, "2 days"),
        (172900, "2 days, 0:01:40"),
        (179999, "2 days, 01:59:59"),
        (179940, "2 days 01:59:00"),
        (176459, "2 days 1:00:59"),
        (0, "0 days"),
        (0, "0 days, 00:00:00"),
        (0, "0 days 00:00:00"),
        (3601, "0 days, 1:00:01"),
        (100, "0 days 0:01:40"),
        (864000, "10 days"),
        (867600, "10 days, 01:00:00"),
        (864000, "10 days 00:00:00"),
        (864000, "10 days, 0:00:00"),
        (867600, "10 days 1:00:00")
    ])
    async def test_get_statistics_history(self, client, interval, schedule_interval):
        output = {"interval": interval, 'statistics': [{"READINGS": 1, "BUFFERED": 10, "history_ts": "2018-02-20 13:16:24.321589"},
                                                       {"READINGS": 0, "BUFFERED": 10, "history_ts": "2018-02-20 13:16:09.321589"}]}
        p1 = {"return": [{"alias": "history_ts", "column": "history_ts", "format": "YYYY-MM-DD HH24:MI:SS.MS"}, "key", "value"], "sort": {"column": "history_ts", "direction": "desc"}}
        p2 = {"return": ["schedule_interval"],
              "where": {"column": "process_name", "condition": "=", "value": "stats collector"}}

        @asyncio.coroutine
        def q_result(*args):
            table = args[0]
            payload = args[1]

            if table == 'statistics_history':
                assert p1 == json.loads(payload)
                return {"rows": [{"key": "READINGS", "value": 1, "history_ts": "2018-02-20 13:16:24.321589"},
                                 {"key": "BUFFERED", "value": 10, "history_ts": "2018-02-20 13:16:24.321589"},
                                 {"key": "READINGS", "value": 0, "history_ts": "2018-02-20 13:16:09.321589"},
                                 {"key": "BUFFERED", "value": 10, "history_ts": "2018-02-20 13:16:09.321589"}]}

            if table == 'schedules':
                assert p2 == json.loads(payload)
                return {"rows": [{"schedule_interval": schedule_interval}]}

        mock_async_storage_client = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=mock_async_storage_client):
            with patch.object(mock_async_storage_client, 'query_tbl_with_payload', side_effect=q_result) as query_patch:
                resp = await client.get("/foglamp/statistics/history")
            assert 200 == resp.status
            r = await resp.text()
            assert output == json.loads(r)
        assert query_patch.called
        assert 2 == query_patch.call_count

    async def test_get_statistics_history_limit(self, client):
        output = {"interval": 60, 'statistics': [{"READINGS": 1, "BUFFERED": 10, "history_ts": "2018-02-20 13:16:24.321589"},
                                                 {"READINGS": 0, "BUFFERED": 10, "history_ts": "2018-02-20 13:16:09.321589"}]}

        p1 = {"aggregate": {"operation": "count", "column": "*"}}
        # payload limit will be request limit*2 i.e. via p1 query
        p2 = {"return": [{"column": "history_ts", "format": "YYYY-MM-DD HH24:MI:SS.MS", "alias": "history_ts"}, "key", "value"], "sort": {"column": "history_ts", "direction": "desc"}, "limit": 2}
        p3 = {"return": ["schedule_interval"],
              "where": {"column": "process_name", "condition": "=", "value": "stats collector"}}

        @asyncio.coroutine
        def q_result(*args):
            table = args[0]
            payload = args[1]

            if table == 'statistics':
                assert p1 == json.loads(payload)
                return {"rows": [{"count_*": 2}]}

            if table == 'statistics_history':
                assert p2 == json.loads(payload)
                return {"rows": [{"key": "READINGS", "value": 1, "history_ts": "2018-02-20 13:16:24.321589"},
                                 {"key": "BUFFERED", "value": 10, "history_ts": "2018-02-20 13:16:24.321589"},
                                 {"key": "READINGS", "value": 0, "history_ts": "2018-02-20 13:16:09.321589"},
                                 {"key": "BUFFERED", "value": 10, "history_ts": "2018-02-20 13:16:09.321589"}]}

            if table == 'schedules':
                assert p3 == json.loads(payload)
                return {"rows": [{"schedule_interval": "00:01:00"}]}

        mock_async_storage_client = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=mock_async_storage_client):
            with patch.object(mock_async_storage_client, 'query_tbl_with_payload', side_effect=q_result) as query_patch:
                resp = await client.get("/foglamp/statistics/history?limit=1")
            assert 200 == resp.status
            r = await resp.text()
            assert output == json.loads(r)
        assert query_patch.called
        assert 3 == query_patch.call_count

    @pytest.mark.parametrize("request_limit", [-1, 'blah'])
    async def test_get_statistics_history_bad_limit(self, client, request_limit):
        mock_async_storage_client = MagicMock(StorageClientAsync)
        result = {"rows": [{"schedule_interval": "00:01:00"}]}

        @asyncio.coroutine
        def mock_coro():
            return result

        with patch.object(connect, 'get_storage_async', return_value=mock_async_storage_client):
            with patch.object(mock_async_storage_client, 'query_tbl_with_payload', return_value=mock_coro()):
                resp = await client.get("/foglamp/statistics/history?limit={}".format(request_limit))
            assert 400 == resp.status
            assert "Limit must be a positive integer" == resp.reason

    async def test_get_statistics_history_no_stats_collector(self, client):
        p1 = {"return": ["schedule_interval"],
              "where": {"column": "process_name", "condition": "=", "value": "stats collector"}}

        @asyncio.coroutine
        def q_result(*args):
            table = args[0]
            payload = args[1]

            if table == 'schedules':
                assert p1 == json.loads(payload)
                return {"rows": []}

        mock_async_storage_client = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=mock_async_storage_client):
            with patch.object(mock_async_storage_client, 'query_tbl_with_payload', side_effect=q_result) as query_patch:
                resp = await client.get("/foglamp/statistics/history")
            assert 404 == resp.status
            assert 'No stats collector schedule found' == resp.reason

        assert query_patch.called
        assert 1 == query_patch.call_count

    async def test_get_statistics_history_server_exception(self, client):
        p1 = {"return": ["history_ts", "key", "value"]}
        p2 = {"return": ["schedule_interval"],
              "where": {"column": "process_name", "condition": "=", "value": "stats collector"}}

        @asyncio.coroutine
        def q_result(*args):
            table = args[0]
            payload = args[1]

            if table == 'statistics_history':
                assert p1 == json.loads(payload)
                # no rows
                return {"message": "error"}
            if table == 'schedules':
                assert p2 == json.loads(payload)
                return {"rows": [{"schedule_interval": "00:01:00"}]}

        mock_async_storage_client = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=mock_async_storage_client):
            with patch.object(mock_async_storage_client, 'query_tbl_with_payload', side_effect=q_result) as query_patch:
                resp = await client.get("/foglamp/statistics/history")
            assert 500 == resp.status
            assert "Internal Server Error" == resp.reason

        assert query_patch.called
        assert 2 == query_patch.call_count

    async def test_get_statistics_history_by_key(self, client):
        output = {"interval": 15, 'statistics': [{"READINGS": 1, "history_ts": "2018-02-20 13:16:24.321589"}, {"READINGS": 0, "history_ts": "2018-02-20 13:16:09.321589"}]}
        p1 = {'where': {'value': 'stats collector', 'condition': '=', 'column': 'process_name'}, 'return': ['schedule_interval']}
        p2 = {'aggregate': {'column': '*', 'operation': 'count'}}
        p3 = {'return': [{'column': 'history_ts', 'alias': 'history_ts', 'format': 'YYYY-MM-DD HH24:MI:SS.MS'}, 'key', 'value'], 'where': {'column': 'key', 'condition': '=', 'value': 'READINGS'}, 'sort': {'column': 'history_ts', 'direction': 'desc'}}

        @asyncio.coroutine
        def q_result(*args):
            table = args[0]
            payload = args[1]

            if table == 'schedules':
                assert p1 == json.loads(payload)
                return {"rows": [{"schedule_interval": "00:00:15"}]}

            if table == 'statistics':
                assert p2 == json.loads(payload)
                return {"rows": [{"count_*": 2}]}

            if table == 'statistics_history':
                assert p3 == json.loads(payload)
                return {"rows": [{"key": "READINGS", "value": 1, "history_ts": "2018-02-20 13:16:24.321589"},
                                 {"key": "READINGS", "value": 0, "history_ts": "2018-02-20 13:16:09.321589"}]}

        mock_async_storage_client = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=mock_async_storage_client):
            with patch.object(mock_async_storage_client, 'query_tbl_with_payload', side_effect=q_result) as query_patch:
                resp = await client.get("/foglamp/statistics/history?key=READINGS")
            assert 200 == resp.status
            r = await resp.text()
            assert output == json.loads(r)
        assert query_patch.called
        assert 2 == query_patch.call_count

    async def test_get_statistics_history_by_key_with_limit(self, client):
        output = {"interval": 15, 'statistics': [{"READINGS": 1, "history_ts": "2018-02-20 13:16:24.321589"}]}
        p1 = {'where': {'value': 'stats collector', 'condition': '=', 'column': 'process_name'}, 'return': ['schedule_interval']}
        p3 = {'return': [{'column': 'history_ts', 'alias': 'history_ts', 'format': 'YYYY-MM-DD HH24:MI:SS.MS'}, 'key', 'value'], 'where': {'column': 'key', 'condition': '=', 'value': 'READINGS'}, 'sort': {'column': 'history_ts', 'direction': 'desc'}, 'limit': 1}

        @asyncio.coroutine
        def q_result(*args):
            table = args[0]
            payload = args[1]

            if table == 'schedules':
                assert p1 == json.loads(payload)
                return {"rows": [{"schedule_interval": "00:00:15"}]}

            if table == 'statistics_history':
                assert p3 == json.loads(payload)
                return {"rows": [{"key": "READINGS", "value": 1, "history_ts": "2018-02-20 13:16:24.321589"}]}

        mock_async_storage_client = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=mock_async_storage_client):
            with patch.object(mock_async_storage_client, 'query_tbl_with_payload', side_effect=q_result) as query_patch:
                resp = await client.get("/foglamp/statistics/history?key=READINGS&limit=1")
            assert 200 == resp.status
            r = await resp.text()
            assert output == json.loads(r)
        assert query_patch.called
        assert 2 == query_patch.call_count

    async def test_get_statistics_history_with_bad_key(self, client):
        output = {"interval": 15, 'statistics': [{}]}
        p1 = {'where': {'value': 'stats collector', 'condition': '=', 'column': 'process_name'}, 'return': ['schedule_interval']}
        p2 = {'aggregate': {'column': '*', 'operation': 'count'}}
        p3 = {'return': [{'column': 'history_ts', 'alias': 'history_ts', 'format': 'YYYY-MM-DD HH24:MI:SS.MS'}, 'key', 'value'], 'where': {'column': 'key', 'condition': '=', 'value': 'blah'}, 'sort': {'column': 'history_ts', 'direction': 'desc'}}

        @asyncio.coroutine
        def q_result(*args):
            table = args[0]
            payload = args[1]

            if table == 'schedules':
                assert p1 == json.loads(payload)
                return {"rows": [{"schedule_interval": "00:00:15"}]}

            if table == 'statistics':
                assert p2 == json.loads(payload)
                return {"rows": [{"count_*": 0}]}

            if table == 'statistics_history':
                assert p3 == json.loads(payload)
                return {"rows": []}

        mock_async_storage_client = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=mock_async_storage_client):
            with patch.object(mock_async_storage_client, 'query_tbl_with_payload', side_effect=q_result) as query_patch:
                resp = await client.get("/foglamp/statistics/history?key=blah")
            assert 200 == resp.status
            r = await resp.text()
            assert output == json.loads(r)
        assert query_patch.called
        assert 2 == query_patch.call_count
