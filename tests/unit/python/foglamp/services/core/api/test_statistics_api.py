# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test foglamp/services/core/api/statistics.py """

from unittest.mock import MagicMock, patch
from aiohttp import web
import pytest
import json

from foglamp.services.core import routes
from foglamp.services.core import connect
from foglamp.common.storage_client.storage_client import StorageClient

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

        mockedStorageClient = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=mockedStorageClient):
            with patch.object(mockedStorageClient, 'query_tbl_with_payload', return_value=result) as query_patch:
                resp = await client.get("/foglamp/statistics")
                assert 200 == resp.status
                r = await resp.text()
                assert result["rows"] == json.loads(r)

        args, kwargs = query_patch.call_args
        assert json.loads(args[1]) == payload
        query_patch.assert_called_once_with('statistics', args[1])

    async def test_get_stats_exception(self, client):
        result = {"message": "error"}

        mockedStorageClient = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=mockedStorageClient):
            with patch.object(mockedStorageClient, 'query_tbl_with_payload', return_value=result):
                resp = await client.get("/foglamp/statistics")
                assert 500 == resp.status
                assert "Internal Server Error" == resp.reason

    async def test_get_statistics_history(self, client):
        output = {"interval": 60, 'statistics': [
            {"READINGS": 0, "BUFFERED": 10, "history_ts": "2018-02-20 13:16:09"},
            {"READINGS": 1, "BUFFERED": 10, "history_ts": "2018-02-20 13:16:24"}]
                  }

        p1 = {"return": ["history_ts", "key", "value"]}
        p2 = {"return": ["schedule_interval"], "where": {"column": "process_name", "condition": "=", "value": "stats collector"}}

        def q_result(*args):
            table = args[0]
            payload = args[1]

            if table == 'statistics_history':
                assert p1 == json.loads(payload)
                return {"rows": [{"key": "READINGS", "value": 0, "history_ts": "2018-02-20 13:16:09.321589+05:30"},
                                 {"key": "BUFFERED", "value": 10, "history_ts": "2018-02-20 13:16:09.321589+05:30"},
                                 {"key": "READINGS", "value": 1, "history_ts": "2018-02-20 13:16:24.321589+05:30"},
                                 {"key": "BUFFERED", "value": 10, "history_ts": "2018-02-20 13:16:24.321589+05:30"}]}

            if table == 'schedules':
                assert p2 == json.loads(payload)
                return {"rows": [{"schedule_interval": "00:01:00"}]}

        mockedStorageClient = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=mockedStorageClient):
            with patch.object(mockedStorageClient, 'query_tbl_with_payload', side_effect=q_result) as query_patch:
                resp = await client.get("/foglamp/statistics/history")
            assert 200 == resp.status
            r = await resp.text()
            assert output == json.loads(r)
        assert query_patch.called
        assert 2 == query_patch.call_count

    async def test_get_statistics_history_limit(self, client):
        output = {"interval": 60, 'statistics': [
            {"READINGS": 0, "BUFFERED": 10, "history_ts": "2018-02-20 13:16:09"},
            {"READINGS": 1, "BUFFERED": 10, "history_ts": "2018-02-20 13:16:24"}]}

        p1 = {"aggregate": {"operation": "count", "column": "*"}}
        # payload limit will be request limit*2 i.e. via p1 query
        p2 = {"limit": 2, "return": ["history_ts", "key", "value"]}
        p3 = {"return": ["schedule_interval"],
              "where": {"column": "process_name", "condition": "=", "value": "stats collector"}}

        def q_result(*args):
            table = args[0]
            payload = args[1]

            if table == 'statistics':
                assert p1 == json.loads(payload)
                return {"rows": [{"count_*": 2}]}

            if table == 'statistics_history':
                assert p2 == json.loads(payload)
                return {"rows": [{"key": "READINGS", "value": 0, "history_ts": "2018-02-20 13:16:09.321589+05:30"},
                                 {"key": "BUFFERED", "value": 10, "history_ts": "2018-02-20 13:16:09.321589+05:30"},
                                 {"key": "READINGS", "value": 1, "history_ts": "2018-02-20 13:16:24.321589+05:30"},
                                 {"key": "BUFFERED", "value": 10, "history_ts": "2018-02-20 13:16:24.321589+05:30"}]}

            if table == 'schedules':
                assert p3 == json.loads(payload)
                return {"rows": [{"schedule_interval": "00:01:00"}]}

        mockedStorageClient = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=mockedStorageClient):
            with patch.object(mockedStorageClient, 'query_tbl_with_payload', side_effect=q_result) as query_patch:
                resp = await client.get("/foglamp/statistics/history?limit=1")
            assert 200 == resp.status
            r = await resp.text()
            assert output == json.loads(r)
        assert query_patch.called
        assert 3 == query_patch.call_count

    @pytest.mark.parametrize("request_limit", [-1, 'blah'])
    async def test_get_statistics_history_bad_limit(self, client, request_limit):
        mockedStorageClient = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=mockedStorageClient):
            with patch.object(mockedStorageClient, 'query_tbl_with_payload', return_value=None):
                resp = await client.get("/foglamp/statistics/history?limit={}".format(request_limit))
            assert 400 == resp.status
            assert "Limit must be a positive integer" == resp.reason

    async def test_get_statistics_history_no_stats_collector(self, client):
        p1 = {"return": ["schedule_interval"], "where": {"column": "process_name", "condition": "=", "value": "stats collector"}}

        def q_result(*args):
            table = args[0]
            payload = args[1]

            if table == 'schedules':
                assert p1 == json.loads(payload)
                return {"rows": []}

        mockedStorageClient = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=mockedStorageClient):
            with patch.object(mockedStorageClient, 'query_tbl_with_payload', side_effect=q_result) as query_patch:
                resp = await client.get("/foglamp/statistics/history")
            assert 404 == resp.status
            assert 'No stats collector schedule found' == resp.reason

        assert query_patch.called
        assert 1 == query_patch.call_count

    async def test_get_statistics_history_server_exception(self, client):
        p1 = {"return": ["history_ts", "key", "value"]}
        p2 = {"return": ["schedule_interval"],
              "where": {"column": "process_name", "condition": "=", "value": "stats collector"}}

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

        mockedStorageClient = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=mockedStorageClient):
            with patch.object(mockedStorageClient, 'query_tbl_with_payload', side_effect=q_result) as query_patch:
                resp = await client.get("/foglamp/statistics/history")
            assert 500 == resp.status
            assert "Internal Server Error" == resp.reason

        assert query_patch.called
        assert 2 == query_patch.call_count
