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
            if log_severity[i]['index'] == 1:
                assert 'FATAL' == log_severity[i]['name']
            elif log_severity[i]['index'] == 2:
                assert 'ERROR' == log_severity[i]['name']
            elif log_severity[i]['index'] == 3:
                assert 'WARNING' == log_severity[i]['name']
            elif log_severity[i]['index'] == 4:
                assert 'INFORMATION' == log_severity[i]['name']

    async def test_audit_log_codes(self, client):
        storage_client_mock = MagicMock(StorageClient)
        response = {"rows": [{"code": "PURGE", "description": "Data Purging Process"},
                             {"code": "LOGGN", "description": "Logging Process"},
                             {"code": "STRMN", "description": "Streaming Process"},
                             {"code": "SYPRG", "description": "System Purge"}
                             ]}

        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl', return_value=response):
                resp = await client.get('/foglamp/audit/logcode')
                assert 200 == resp.status
                result = await resp.text()
                json_response = json.loads(result)
                log_codes = [key['code'] for key in json_response['logCode']]

                # verify the default log_codes with their values which are defined in init.sql
                assert 4 == len(log_codes)
                assert 'PURGE' in log_codes
                assert 'LOGGN' in log_codes
                assert 'STRMN' in log_codes
                assert 'SYPRG' in log_codes

    # TODO: source request params as it needs validation, a bit tricky to mock with existing code
    # '?source=PURGE','?source=PURGE&severity=error')
    @pytest.mark.parametrize("request_params", [
        '',
        '?skip=1',
        '?severity=error',
        '?severity=ERROR&limit=1',
        '?severity=INFORMATION&limit=1&skip=1',
        '?source=&severity=&limit=&skip='
    ])
    async def test_get_audit_with_params(self, client, request_params):
        storage_client_mock = MagicMock(StorageClient)
        response = {"rows": [{"log": {"end_time": "2018-01-30 18:39:48.1517317788", "rowsRemaining": 0,
                                  "start_time": "2018-01-30 18:39:48.1517317788", "rowsRemoved": 0,
                                  "unsentRowsRemoved": 0, "rowsRetained": 0},
                          "code": "PURGE", "level": "4", "id": 2,
                          "ts": "2018-01-30 18:39:48.796263+05:30", 'count': 1}]}
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=response):
                    resp = await client.get('/foglamp/audit{}'.format(request_params))
                    assert 200 == resp.status
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert 1 == json_response['totalCount']
                    assert 1 == len(json_response['audit'])

    # TODO: add source request param with invalid data, a bit tricky to mock with existing code
    @pytest.mark.parametrize("request_params, response_code, response_message", [
        ('?limit=invalid', 400, "Limit must be a positive integer"),
        ('?limit=-1', 400, "Limit must be a positive integer"),
        ('?skip=invalid', 400, "Skip/Offset must be a positive integer"),
        ('?skip=-1', 400, "Skip/Offset must be a positive integer"),
        ('?severity=BLA', 400, "'BLA' is not a valid severity")
    ])
    async def test_params_with_bad_data(self, client, request_params, response_code, response_message):
        resp = await client.get('/foglamp/audit{}'.format(request_params))
        assert response_code == resp.status
        assert response_message == resp.reason
