# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test rest server api for python/foglamp/services/core/api/common.py

These 2 def shall be tested via python/foglamp/services/core/server.py
    - rest_api_config
    - get_certificates
This test file assumes those 2 units are tested
"""

import json
import ssl
import pathlib
from unittest.mock import MagicMock, patch, call
import aiohttp
from aiohttp import web
import pytest
from foglamp.services.core import routes
from foglamp.services.core import connect
from foglamp.common.web import middleware
from foglamp.common.storage_client.storage_client import StorageClient


@pytest.allure.feature("unit")
@pytest.allure.story("api", "common")
async def test_ping_http(test_server, test_client, loop):
    payload = '{"return": ["key", "description", "value"], "sort": {"column": "key", "direction": "asc"}}'
    result = {"rows": [
                {"value": 1, "key": "PURGED", "description": "blah6"},
                {"value": 2, "key": "READINGS", "description": "blah1"},
                {"value": 3, "key": "SENT_1", "description": "blah2"},
                {"value": 4, "key": "SENT_2", "description": "blah3"},
                {"value": 5, "key": "SENT_3", "description": "blah4"},
                {"value": 6, "key": "SENT_4", "description": "blah5"},
               ]}

    mockedStorageClient = MagicMock(StorageClient)
    with patch.object(middleware._logger, 'info') as logger_info:
        with patch.object(connect, 'get_storage', return_value=mockedStorageClient):
            with patch.object(mockedStorageClient, 'query_tbl_with_payload', return_value=result) as query_patch:
                app = web.Application(loop=loop, middlewares=[middleware.optional_auth_middleware])
                # fill route table
                routes.setup(app)

                server = await test_server(app)
                server.start_server(loop=loop)

                client = await test_client(server)
                # note: If the parameter is app aiohttp.web.Application
                # the tool creates TestServer implicitly for serving the application.
                resp = await client.get('/foglamp/ping', headers={'authorization': "token"})
                assert 200 == resp.status
                content = await resp.text()
                content_dict = json.loads(content)
                assert 0.0 < content_dict["uptime"]
                assert 2 == content_dict["dataRead"]
                assert 18 == content_dict["dataSent"]
                assert 1 == content_dict["dataPurged"]
                assert content_dict["authenticationOptional"] is True
        query_patch.assert_called_once_with('statistics', payload)
    log_params = 'Received %s request for %s', 'GET', '/foglamp/ping'
    logger_info.assert_called_once_with(*log_params)


@pytest.allure.feature("unit")
@pytest.allure.story("api", "common")
async def test_ping_http_auth_required(test_server, test_client, loop):
    payload = '{"return": ["key", "description", "value"], "sort": {"column": "key", "direction": "asc"}}'
    result = {"rows": [
                {"value": 1, "key": "PURGED", "description": "blah6"},
                {"value": 2, "key": "READINGS", "description": "blah1"},
                {"value": 3, "key": "SENT_1", "description": "blah2"},
                {"value": 4, "key": "SENT_2", "description": "blah3"},
                {"value": 5, "key": "SENT_3", "description": "blah4"},
                {"value": 6, "key": "SENT_4", "description": "blah5"},
               ]}

    mockedStorageClient = MagicMock(StorageClient)
    with patch.object(middleware._logger, 'info') as logger_info:
        with patch.object(connect, 'get_storage', return_value=mockedStorageClient):
            with patch.object(mockedStorageClient, 'query_tbl_with_payload', return_value=result) as query_patch:
                app = web.Application(loop=loop, middlewares=[middleware.auth_middleware])
                # fill route table
                routes.setup(app)

                server = await test_server(app)
                server.start_server(loop=loop)

                client = await test_client(server)
                # note: If the parameter is app aiohttp.web.Application
                # the tool creates TestServer implicitly for serving the application.
                resp = await client.get('/foglamp/ping')
                assert 200 == resp.status
                content = await resp.text()
                content_dict = json.loads(content)
                assert 0.0 < content_dict["uptime"]
                assert 2 == content_dict["dataRead"]
                assert 18 == content_dict["dataSent"]
                assert 1 == content_dict["dataPurged"]
                assert content_dict["authenticationOptional"] is False
        query_patch.assert_called_once_with('statistics', payload)
    log_params = 'Received %s request for %s', 'GET', '/foglamp/ping'
    logger_info.assert_called_once_with(*log_params)


@pytest.fixture
def certs_path():
    return pathlib.Path(__file__).parent


@pytest.fixture
def ssl_ctx(certs_path):
    ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_ctx.load_cert_chain(
        str(certs_path / 'certs/foglamp.cert'),
        str(certs_path / 'certs/foglamp.key'))
    return ssl_ctx


@pytest.allure.feature("unit")
@pytest.allure.story("api", "common")
async def test_ping_https(test_server, ssl_ctx, test_client, loop):
    payload = '{"return": ["key", "description", "value"], "sort": {"column": "key", "direction": "asc"}}'
    result = {"rows": [
                {"value": 1, "key": "PURGED", "description": "blah6"},
                {"value": 2, "key": "READINGS", "description": "blah1"},
                {"value": 3, "key": "SENT_1", "description": "blah2"},
                {"value": 4, "key": "SENT_2", "description": "blah3"},
                {"value": 5, "key": "SENT_3", "description": "blah4"},
                {"value": 6, "key": "SENT_4", "description": "blah5"},
               ]}

    mockedStorageClient = MagicMock(StorageClient)
    with patch.object(middleware._logger, 'info') as logger_info:
        with patch.object(connect, 'get_storage', return_value=mockedStorageClient):
            with patch.object(mockedStorageClient, 'query_tbl_with_payload', return_value=result) as query_patch:
                app = web.Application(loop=loop, middlewares=[middleware.optional_auth_middleware])
                # fill route table
                routes.setup(app)

                server = await test_server(app, ssl=ssl_ctx)
                server.start_server(loop=loop)

                url = 'https://127.0.0.1:{}/foglamp/ping'.format(server.port)
                async with aiohttp.ClientSession(loop=loop) as session:
                    async with session.get(url, verify_ssl=False) as resp:
                        assert 200 == resp.status
                        content = await resp.text()
                        content_dict = json.loads(content)
                        assert 0.0 < content_dict["uptime"]

                with pytest.raises(aiohttp.ClientConnectorSSLError) as error_exec:
                    client = await test_client(server)
                    resp = await client.get('/foglamp/ping')
                assert "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed" in str(error_exec)

                with pytest.raises(aiohttp.ClientConnectorSSLError) as error_exec:
                    # self signed certificate,
                    # and we are not using SSL context here for client as verifier
                    connector = aiohttp.TCPConnector(verify_ssl=True, loop=loop)
                    client = await test_client(server, connector=connector)
                    await client.get('/foglamp/ping')
                assert "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed" in str(error_exec)

                connector = aiohttp.TCPConnector(verify_ssl=False, loop=loop)
                client = await test_client(server, connector=connector)
                resp = await client.get('/foglamp/ping')
                s = resp.request_info.url.human_repr()
                assert "https" == s[:5]
                assert 200 == resp.status
                content = await resp.text()
                content_dict = json.loads(content)
                assert 0.0 < content_dict["uptime"]
                assert 2 == content_dict["dataRead"]
                assert 18 == content_dict["dataSent"]
                assert 1 == content_dict["dataPurged"]
                assert content_dict["authenticationOptional"] is True
        calls = [call('statistics', payload),
                 call('statistics', payload)]
        query_patch.assert_has_calls(calls)
    calls = [call('Received %s request for %s', 'GET', '/foglamp/ping'),
             call('Received %s request for %s', 'GET', '/foglamp/ping')]
    logger_info.assert_has_calls(calls)


@pytest.allure.feature("unit")
@pytest.allure.story("api", "common")
async def test_ping_https_auth_required(test_server, ssl_ctx, test_client, loop):
    payload = '{"return": ["key", "description", "value"], "sort": {"column": "key", "direction": "asc"}}'
    result = {"rows": [
                {"value": 1, "key": "PURGED", "description": "blah6"},
                {"value": 2, "key": "READINGS", "description": "blah1"},
                {"value": 3, "key": "SENT_1", "description": "blah2"},
                {"value": 4, "key": "SENT_2", "description": "blah3"},
                {"value": 5, "key": "SENT_3", "description": "blah4"},
                {"value": 6, "key": "SENT_4", "description": "blah5"},
               ]}

    mockedStorageClient = MagicMock(StorageClient)
    with patch.object(middleware._logger, 'info') as logger_info:
        with patch.object(connect, 'get_storage', return_value=mockedStorageClient):
            with patch.object(mockedStorageClient, 'query_tbl_with_payload', return_value=result) as query_patch:
                app = web.Application(loop=loop, middlewares=[middleware.auth_middleware])
                # fill route table
                routes.setup(app)

                server = await test_server(app, ssl=ssl_ctx)
                server.start_server(loop=loop)

                url = 'https://127.0.0.1:{}/foglamp/ping'.format(server.port)
                async with aiohttp.ClientSession(loop=loop) as session:
                    async with session.get(url, verify_ssl=False) as resp:
                        assert 200 == resp.status
                        content = await resp.text()
                        content_dict = json.loads(content)
                        assert 0.0 < content_dict["uptime"]

                with pytest.raises(aiohttp.ClientConnectorSSLError) as error_exec:
                    client = await test_client(server)
                    await client.get('/foglamp/ping')
                assert "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed" in str(error_exec)

                with pytest.raises(aiohttp.ClientConnectorSSLError) as error_exec:
                    # self signed certificate,
                    # and we are not using SSL context here for client as verifier
                    connector = aiohttp.TCPConnector(verify_ssl=True, loop=loop)
                    client = await test_client(server, connector=connector)
                    resp = await client.get('/foglamp/ping')
                assert "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed" in str(error_exec)

                connector = aiohttp.TCPConnector(verify_ssl=False, loop=loop)
                client = await test_client(server, connector=connector)
                resp = await client.get('/foglamp/ping')
                s = resp.request_info.url.human_repr()
                assert "https" == s[:5]
                assert 200 == resp.status
                content = await resp.text()
                content_dict = json.loads(content)
                assert 0.0 < content_dict["uptime"]
                assert 2 == content_dict["dataRead"]
                assert 18 == content_dict["dataSent"]
                assert 1 == content_dict["dataPurged"]
                assert content_dict["authenticationOptional"] is False
        calls = [call('statistics', payload),
                 call('statistics', payload)]
        query_patch.assert_has_calls(calls)
    calls = [call('Received %s request for %s', 'GET', '/foglamp/ping'),
             call('Received %s request for %s', 'GET', '/foglamp/ping')]
    logger_info.assert_has_calls(calls)


@pytest.allure.feature("unit")
@pytest.allure.story("api", "common")
async def test_shutdown_http(test_server, test_client, loop):
    app = web.Application()
    # fill route table
    routes.setup(app)

    server = await test_server(app)
    server.start_server(loop=loop)

    client = await test_client(server)
    resp = await client.put('/foglamp/shutdown', data=None)
    assert 200 == resp.status
    content = await resp.text()
    content_dict = json.loads(content)
    assert "FogLAMP shutdown has been scheduled. Wait for few seconds for process cleanup." == content_dict["message"]


