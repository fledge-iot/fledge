# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


import asyncio
import json
from unittest.mock import MagicMock, patch
from collections import Counter
from aiohttp import web
import pytest

from foglamp.services.core import routes
from foglamp.services.core import connect
from foglamp.common.storage_client.storage_client import StorageClientAsync
from foglamp.services.core.api import audit
from foglamp.common.audit_logger import AuditLogger

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("api", "audit")
class TestAudit:

    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop)
        # fill the routes table
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    @pytest.fixture()
    def get_log_codes(self):
        return {"rows": [{"code": "PURGE", "description": "Data Purging Process"},
                         {"code": "LOGGN", "description": "Logging Process"},
                         {"code": "STRMN", "description": "Streaming Process"},
                         {"code": "SYPRG", "description": "System Purge"},
                         {"code": "START", "description": "System Startup"},
                         {"code": "FSTOP", "description": "System Shutdown"},
                         {"code": "CONCH", "description": "Configuration Change"},
                         {"code": "CONAD", "description": "Configuration Addition"},
                         {"code": "SCHCH", "description": "Schedule Change"},
                         {"code": "SCHAD", "description": "Schedule Addition"},
                         {"code": "SRVRG", "description": "Service Registered"},
                         {"code": "SRVUN", "description": "Service Unregistered"},
                         {"code": "SRVFL", "description": "Service Fail"},
                         {"code": "NHCOM", "description": "North Process Complete"},
                         {"code": "NHDWN", "description": "North Destination Unavailable"},
                         {"code": "NHAVL", "description": "North Destination Available"},
                         {"code": "UPEXC", "description": "Update Complete"},
                         {"code": "BKEXC", "description": "Backup Complete"}
                         ]}

    async def test_get_severity(self, client):
        resp = await client.get('/foglamp/audit/severity')
        assert 200 == resp.status
        result = await resp.text()
        json_response = json.loads(result)
        log_severity = json_response['logSeverity']

        # verify the severity count
        assert 4 == len(log_severity)

        # verify the name and value of severity
        for i in range(len(log_severity)):
            if log_severity[i]['index'] == 0:
                assert 'SUCCESS' == log_severity[i]['name']
            elif log_severity[i]['index'] == 1:
                assert 'FAILURE' == log_severity[i]['name']
            elif log_severity[i]['index'] == 2:
                assert 'WARNING' == log_severity[i]['name']
            elif log_severity[i]['index'] == 4:
                assert 'INFORMATION' == log_severity[i]['name']

    async def test_audit_log_codes(self, client, get_log_codes):
        async def get_log_codes_async():
            return get_log_codes

        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl', return_value=get_log_codes_async()) as log_code_patch:
                resp = await client.get('/foglamp/audit/logcode')
                assert 200 == resp.status
                result = await resp.text()
                json_response = json.loads(result)
                codes = [key['code'] for key in json_response['logCode']]
                expected_code_list = [key['code'] for key in get_log_codes['rows']]

                # verify the default log_codes with their values which are defined in init.sql
                assert 18 == len(codes)
                assert Counter(expected_code_list) == Counter(codes)
            log_code_patch.assert_called_once_with('log_codes')

    @pytest.mark.parametrize("request_params, payload", [
        ('', {"return": ["code", "level", "log", {"column": "ts", "format": "YYYY-MM-DD HH24:MI:SS.MS", "alias": "timestamp"}], "where": {"column": "1", "condition": "=", "value": 1}, "sort": {"column": "ts", "direction": "desc"}, "limit": 20}),
        ('?source=PURGE', {'return': ['code', 'level', 'log', {'format': 'YYYY-MM-DD HH24:MI:SS.MS', 'column': 'ts', 'alias': 'timestamp'}], 'where': {'value': 1, 'and': {'value': 'PURGE', 'column': 'code', 'condition': '='}, 'column': '1', 'condition': '='}, 'sort': {'direction': 'desc', 'column': 'ts'}, 'limit': 20}),
        ('?skip=1', {'where': {'value': 1, 'column': '1', 'condition': '='}, 'limit': 20, 'return': ['code', 'level', 'log', {'column': 'ts', 'format': 'YYYY-MM-DD HH24:MI:SS.MS', 'alias': 'timestamp'}], 'skip': 1, 'sort': {'direction': 'desc', 'column': 'ts'}}),
        ('?severity=failure', {'where': {'and': {'value': 1, 'column': 'level', 'condition': '='}, 'value': 1, 'column': '1', 'condition': '='}, 'limit': 20, 'return': ['code', 'level', 'log', {'column': 'ts', 'format': 'YYYY-MM-DD HH24:MI:SS.MS', 'alias': 'timestamp'}], 'sort': {'direction': 'desc', 'column': 'ts'}}),
        ('?severity=FAILURE&limit=1', {'limit': 1, 'sort': {'direction': 'desc', 'column': 'ts'}, 'return': ['code', 'level', 'log', {'column': 'ts', 'format': 'YYYY-MM-DD HH24:MI:SS.MS', 'alias': 'timestamp'}], 'where': {'value': 1, 'condition': '=', 'and': {'value': 1, 'condition': '=', 'column': 'level'}, 'column': '1'}}),
        ('?severity=INFORMATION&limit=1&skip=1', {'limit': 1, 'sort': {'direction': 'desc', 'column': 'ts'}, 'return': ['code', 'level', 'log', {'column': 'ts', 'format': 'YYYY-MM-DD HH24:MI:SS.MS', 'alias': 'timestamp'}], 'skip': 1, 'where': {'value': 1, 'condition': '=', 'and': {'value': 4, 'condition': '=', 'column': 'level'}, 'column': '1'}}),
        ('?source=&severity=&limit=&skip=', {'limit': 20, 'sort': {'direction': 'desc', 'column': 'ts'}, 'return': ['code', 'level', 'log', {'column': 'ts', 'format': 'YYYY-MM-DD HH24:MI:SS.MS', 'alias': 'timestamp'}], 'where': {'value': 1, 'condition': '=', 'column': '1'}})
    ])
    async def test_get_audit_with_params(self, client, request_params, payload, get_log_codes, loop):
        storage_client_mock = MagicMock(StorageClientAsync)
        response = {"rows": [{"log": {"end_time": "2018-01-30 18:39:48.1517317788", "rowsRemaining": 0,
                                      "start_time": "2018-01-30 18:39:48.1517317788", "rowsRemoved": 0,
                                      "unsentRowsRemoved": 0, "rowsRetained": 0},
                              "code": "PURGE", "level": "4", "id": 2,
                              "timestamp": "2018-01-30 18:39:48.796263", 'count': 1}]}
        @asyncio.coroutine
        def async_mock():
            return response

        @asyncio.coroutine
        def async_mock_log():
            return get_log_codes

        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl', return_value=asyncio.ensure_future(async_mock_log(), loop=loop)):
                with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=asyncio.ensure_future(async_mock(), loop=loop)) as log_code_patch:
                    resp = await client.get('/foglamp/audit{}'.format(request_params))
                    assert 200 == resp.status
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert 1 == json_response['totalCount']
                    assert 1 == len(json_response['audit'])
                args, kwargs = log_code_patch.call_args
                assert 'log' == args[0]
                p = json.loads(args[1])
                assert payload == p

    @pytest.mark.parametrize("request_params, response_code, response_message", [
        ('?source=BLA', 400, "BLA is not a valid source"),
        ('?source=1234', 400, "1234 is not a valid source"),
        ('?limit=invalid', 400, "Limit must be a positive integer"),
        ('?limit=-1', 400, "Limit must be a positive integer"),
        ('?skip=invalid', 400, "Skip/Offset must be a positive integer"),
        ('?skip=-1', 400, "Skip/Offset must be a positive integer"),
        ('?severity=BLA', 400, "'BLA' is not a valid severity")
    ])
    async def test_source_param_with_bad_data(self, client, request_params, response_code, response_message, get_log_codes, loop):
        @asyncio.coroutine
        def async_mock_log():
            return get_log_codes

        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl', return_value=asyncio.ensure_future(async_mock_log(), loop=loop)):
                resp = await client.get('/foglamp/audit{}'.format(request_params))
                assert response_code == resp.status
                assert response_message == resp.reason

    async def test_get_audit_http_exception(self, client):
        with patch.object(connect, 'get_storage_async', return_value=Exception):
            resp = await client.get('/foglamp/audit')
            assert 500 == resp.status
            assert 'Internal Server Error' == resp.reason

    async def test_create_audit_entry(self, client, loop):
        request_data = {"source": "LMTR", "severity": "warning", "details": {"message": "Engine oil pressure low"}}
        response = {'details': {'message': 'Engine oil pressure low'}, 'source': 'LMTR',
                    'timestamp': '2018-03-05 07:36:52.823', 'severity': 'warning'}

        async def async_mock():
            return response

        storage_mock = MagicMock(spec=StorageClientAsync)
        AuditLogger(storage_mock)
        with patch.object(storage_mock, 'insert_into_tbl', return_value=asyncio.ensure_future(async_mock(), loop=loop)) as insert_tbl_patch:
            resp = await client.post('/foglamp/audit', data=json.dumps(request_data))
            assert 200 == resp.status
            result = await resp.text()
            json_response = json.loads(result)
            assert response['details'] == json_response['details']
            assert response['source'] == json_response['source']
            assert response['severity'] == json_response['severity']
            assert 'timestamp' in json_response

    @pytest.mark.parametrize("request_data, expected_response", [
        ({"source": "LMTR", "severity": "", "details": {"message": "Engine oil pressure low"}}, "Missing required parameter severity"),
        ({"source": "LMTR", "severity": None, "details": {"message": "Engine oil pressure low"}}, "Missing required parameter severity"),
        ({"source": "", "severity": "WARNING", "details": {"message": "Engine oil pressure low"}}, "Missing required parameter source"),
        ({"source": None, "severity": "WARNING", "details": {"message": "Engine oil pressure low"}}, "Missing required parameter source"),
        ({"source": "LMTR", "severity": "WARNING", "details": None}, "Missing required parameter details"),
        ({"source": "LMTR", "severity": "WARNING", "details": ""}, "Details should be a valid json object"),
    ])
    async def test_create_audit_entry_with_bad_data(self, client, request_data, expected_response):
        resp = await client.post('/foglamp/audit', data=json.dumps(request_data))
        assert 400 == resp.status
        assert expected_response == resp.reason

    async def test_create_audit_entry_with_attribute_error(self, client):
        request_data = {"source": "LMTR", "severity": "blah", "details": {"message": "Engine oil pressure low"}}
        with patch.object(audit._logger, "error", return_value=None) as audit_logger_patch:
            with patch.object(AuditLogger, "__init__", return_value=None):
                resp = await client.post('/foglamp/audit', data=json.dumps(request_data))
                assert 404 == resp.status
                assert 'severity type blah is not supported' == resp.reason
        args, kwargs = audit_logger_patch.call_args
        assert ('Error in create_audit_entry(): %s | %s', 'severity type blah is not supported', "'AuditLogger' object has no attribute 'blah'") == args

    async def test_create_audit_entry_with_exception(self, client):
        request_data = {"source": "LMTR", "severity": "blah", "details": {"message": "Engine oil pressure low"}}
        with patch.object(AuditLogger, "__init__", return_value=""):
            resp = await client.post('/foglamp/audit', data=json.dumps(request_data))
            assert 500 == resp.status
            assert "__init__() should return None, not 'str'" == resp.reason
