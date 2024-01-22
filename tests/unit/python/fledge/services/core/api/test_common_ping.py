# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test rest server api for python/fledge/services/core/api/common.py

These 2 def shall be tested via python/fledge/services/core/server.py
    - rest_api_config
    - get_certificates
This test file assumes those 2 units are tested
"""

import re
import asyncio
import json
import ssl
import socket
import subprocess
import pathlib
import time
from unittest.mock import MagicMock, patch
import pytest
import sys

import aiohttp
from aiohttp import web

from fledge.services.core import connect, routes, server as core_server
from fledge.services.core.api.common import _logger
from fledge.common.alert_manager import AlertManager
from fledge.common.web import middleware
from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.common.configuration_manager import ConfigurationManager

SEMANTIC_VERSIONING_REGEX = "^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)$"


@pytest.fixture
def certs_path():
    return pathlib.Path(__file__).parent


@pytest.fixture
def ssl_ctx(certs_path):
    ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_ctx.load_cert_chain(
        str(certs_path / 'certs/fledge.cert'),
        str(certs_path / 'certs/fledge.key'))
    return ssl_ctx


@pytest.fixture
def get_machine_detail():
    host_name = socket.gethostname()
    # all addresses for the host
    all_ip_addresses_cmd_res = subprocess.run(['hostname', '-I'], stdout=subprocess.PIPE)
    ip_addresses = all_ip_addresses_cmd_res.stdout.decode('utf-8').replace("\n", "").strip().split(" ")
    return host_name, ip_addresses


@pytest.allure.feature("unit")
@pytest.allure.story("api", "common")
async def test_ping_http_allow_ping_true(aiohttp_server, aiohttp_client, loop, get_machine_detail):
    payload = '{"return": ["key", "description", "value"], "sort": {"column": "key", "direction": "asc"}}'
    result = {"rows": [
        {"value": 1, "key": "PURGED", "description": "blah6"},
        {"value": 2, "key": "READINGS", "description": "blah1"},
        {"value": 3, "key": "North Readings to PI", "description": "blah2"},
        {"value": 4, "key": "North Statistics to PI", "description": "blah3"},
        {"value": 10, "key": "North Statistics to OCS", "description": "blah5"},
        {"value": 100, "key": "Readings Sent", "description": "Readings Sent North"},
    ]}

    async def mock_coro(*args, **kwargs):
        return result
    
    # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
    if sys.version_info.major == 3 and sys.version_info.minor >= 8:
        _rv = await mock_coro()
    else:
        _rv = asyncio.ensure_future(mock_coro())
    
    host_name, ip_addresses = get_machine_detail
    attrs = {"query_tbl_with_payload.return_value": await mock_coro()}
    mock_storage_client_async = MagicMock(spec=StorageClientAsync, **attrs)
    core_server.Server._alert_manager = AlertManager(mock_storage_client_async)
    core_server.Server._alert_manager.alerts = []
    with patch.object(middleware._logger, 'debug') as logger_info:
        with patch.object(connect, 'get_storage_async', return_value=mock_storage_client_async):
            with patch.object(mock_storage_client_async, 'query_tbl_with_payload', return_value=_rv) as query_patch:
                    app = web.Application(loop=loop, middlewares=[middleware.optional_auth_middleware])
                    # fill route table
                    routes.setup(app)
                    server = await aiohttp_server(app)
                    await server.start_server(loop=loop)

                    client = await aiohttp_client(server)
                    # note: If the parameter is app aiohttp.web.Application
                    # the tool creates TestServer implicitly for serving the application.
                    time.sleep(1)
                    resp = await client.get('/fledge/ping', headers={'authorization': "token"})
                    assert 200 == resp.status
                    content = await resp.text()
                    content_dict = json.loads(content)
                    assert isinstance(content_dict["uptime"], int)
                    assert 1 <= content_dict["uptime"]
                    assert 2 == content_dict["dataRead"]
                    assert 100 == content_dict["dataSent"]
                    assert 1 == content_dict["dataPurged"]
                    assert content_dict["authenticationOptional"] is True
                    assert content_dict['serviceName'] == "Fledge"
                    assert content_dict['hostName'] == host_name
                    assert content_dict['ipAddresses'] == ip_addresses
                    assert content_dict['health'] == "green"
                    assert content_dict['safeMode'] is False
                    assert re.match(SEMANTIC_VERSIONING_REGEX, content_dict['version']) is not None
                    assert content_dict['alerts'] == 0
            query_patch.assert_called_once_with('statistics', payload)
        log_params = 'Received %s request for %s', 'GET', '/fledge/ping'
        logger_info.assert_called_once_with(*log_params)


@pytest.allure.feature("unit")
@pytest.allure.story("api", "common")
async def test_ping_http_allow_ping_false(aiohttp_server, aiohttp_client, loop, get_machine_detail):
    payload = '{"return": ["key", "description", "value"], "sort": {"column": "key", "direction": "asc"}}'

    async def mock_coro(*args, **kwargs):
        result = {"rows": [
            {"value": 1, "key": "PURGED", "description": "blah6"},
            {"value": 2, "key": "READINGS", "description": "blah1"},
            {"value": 3, "key": "North Readings to PI", "description": "blah2"},
            {"value": 4, "key": "North Statistics to PI", "description": "blah3"},
            {"value": 10, "key": "North Statistics to OCS", "description": "blah5"},
            {"value": 100, "key": "Readings Sent", "description": "Readings Sent North"},
        ]}
        return result

    # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
    if sys.version_info.major == 3 and sys.version_info.minor >= 8:
        _rv = await mock_coro()
    else:
        _rv = asyncio.ensure_future(mock_coro())
    
    host_name, ip_addresses = get_machine_detail
    mock_storage_client_async = MagicMock(StorageClientAsync)
    with patch.object(middleware._logger, 'debug') as logger_info:
        with patch.object(connect, 'get_storage_async', return_value=mock_storage_client_async):
            with patch.object(mock_storage_client_async, 'query_tbl_with_payload', return_value=_rv) as query_patch:
                    app = web.Application(loop=loop, middlewares=[middleware.optional_auth_middleware])
                    # fill route table
                    routes.setup(app)

                    server = await aiohttp_server(app)
                    await server.start_server(loop=loop)

                    client = await aiohttp_client(server)
                    # note: If the parameter is app aiohttp.web.Application
                    # the tool creates TestServer implicitly for serving the application.
                    resp = await client.get('/fledge/ping', headers={'authorization': "token"})
                    assert 200 == resp.status
                    content = await resp.text()
                    content_dict = json.loads(content)
                    assert 0 <= content_dict["uptime"]
                    assert 2 == content_dict["dataRead"]
                    assert 100 == content_dict["dataSent"]
                    assert 1 == content_dict["dataPurged"]
                    assert content_dict["authenticationOptional"] is True
                    assert content_dict['serviceName'] == "Fledge"
                    assert content_dict['hostName'] == host_name
                    assert content_dict['ipAddresses'] == ip_addresses
                    assert content_dict['health'] == "green"
                    assert content_dict['safeMode'] is False
                    assert re.search(SEMANTIC_VERSIONING_REGEX, content_dict['version']) is not None
                    assert content_dict['alerts'] == 0
            query_patch.assert_called_once_with('statistics', payload)
        log_params = 'Received %s request for %s', 'GET', '/fledge/ping'
        logger_info.assert_called_once_with(*log_params)


@pytest.allure.feature("unit")
@pytest.allure.story("api", "common")
async def test_ping_http_auth_required_allow_ping_true(aiohttp_server, aiohttp_client, loop, get_machine_detail):
    payload = '{"return": ["key", "description", "value"], "sort": {"column": "key", "direction": "asc"}}'
    result = {"rows": [
                {"value": 1, "key": "PURGED", "description": "blah6"},
                {"value": 2, "key": "READINGS", "description": "blah1"},
                {"value": 3, "key": "North Readings to PI", "description": "blah2"},
                {"value": 4, "key": "North Statistics to PI", "description": "blah3"},
                {"value": 10, "key": "North Statistics to OCS", "description": "blah5"},
                {"value": 100, "key": "Readings Sent", "description": "Readings Sent North"},
               ]}

    @asyncio.coroutine
    def mock_coro(*args, **kwargs):
        return result

    async def mock_get_category_item():
        return {"value": "true"}

    # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
    if sys.version_info.major == 3 and sys.version_info.minor >= 8:
        _rv1 = await mock_coro()
        _rv2 = await mock_get_category_item()
    else:
        _rv1 = asyncio.ensure_future(mock_coro())
        _rv2 = asyncio.ensure_future(mock_get_category_item())
    
    host_name, ip_addresses = get_machine_detail
    mock_storage_client_async = MagicMock(StorageClientAsync)
    with patch.object(middleware._logger, 'debug') as logger_info:
        with patch.object(connect, 'get_storage_async', return_value=mock_storage_client_async):
            with patch.object(mock_storage_client_async, 'query_tbl_with_payload', return_value=_rv1) as query_patch:
                with patch.object(ConfigurationManager, "get_category_item", return_value=_rv2) as mock_get_cat:
                    app = web.Application(loop=loop, middlewares=[middleware.auth_middleware])
                    # fill route table
                    routes.setup(app)

                    server = await aiohttp_server(app)
                    await server.start_server(loop=loop)

                    client = await aiohttp_client(server)
                    # note: If the parameter is app aiohttp.web.Application
                    # the tool creates TestServer implicitly for serving the application.
                    resp = await client.get('/fledge/ping')
                    assert 200 == resp.status
                    content = await resp.text()
                    content_dict = json.loads(content)
                    assert 0 <= content_dict["uptime"]
                    assert 2 == content_dict["dataRead"]
                    assert 100 == content_dict["dataSent"]
                    assert 1 == content_dict["dataPurged"]
                    assert content_dict["authenticationOptional"] is False
                    assert content_dict['serviceName'] == "Fledge"
                    assert content_dict['hostName'] == host_name
                    assert content_dict['ipAddresses'] == ip_addresses
                    assert content_dict['health'] == "green"
                    assert content_dict['safeMode'] is False
                    assert re.match(SEMANTIC_VERSIONING_REGEX, content_dict['version']) is not None
                    assert content_dict['alerts'] == 0
                mock_get_cat.assert_called_once_with('rest_api', 'allowPing')
            query_patch.assert_called_once_with('statistics', payload)
        log_params = 'Received %s request for %s', 'GET', '/fledge/ping'
        logger_info.assert_called_once_with(*log_params)


@pytest.allure.feature("unit")
@pytest.allure.story("api", "common")
async def test_ping_http_auth_required_allow_ping_false(aiohttp_server, aiohttp_client, loop, get_machine_detail):
    result = {"rows": [
        {"value": 1, "key": "PURGED", "description": "blah6"},
        {"value": 2, "key": "READINGS", "description": "blah1"},
        {"value": 3, "key": "North Readings to PI", "description": "blah2"},
        {"value": 4, "key": "North Statistics to PI", "description": "blah3"},
        {"value": 5, "key": "North Statistics to OCS", "description": "blah5"},
        {"value": 100, "key": "Readings Sent", "description": "Readings Sent North"},
    ]}

    @asyncio.coroutine
    def mock_coro(*args, **kwargs):
        return result

    async def mock_get_category_item():
        return {"value": "false"}

    # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
    if sys.version_info.major == 3 and sys.version_info.minor >= 8:
        _rv1 = await mock_coro()
        _rv2 = await mock_get_category_item()
    else:
        _rv1 = asyncio.ensure_future(mock_coro())
        _rv2 = asyncio.ensure_future(mock_get_category_item())
    
    mock_storage_client_async = MagicMock(StorageClientAsync)
    with patch.object(middleware._logger, 'debug') as logger_info:
        with patch.object(connect, 'get_storage_async', return_value=mock_storage_client_async):
            with patch.object(mock_storage_client_async, 'query_tbl_with_payload', return_value=_rv1) as query_patch:
                with patch.object(ConfigurationManager, "get_category_item", return_value=_rv2) as mock_get_cat:
                    with patch.object(_logger, 'warning') as logger_warn:
                        app = web.Application(loop=loop, middlewares=[middleware.auth_middleware])
                        # fill route table
                        routes.setup(app)

                        server = await aiohttp_server(app)
                        await server.start_server(loop=loop)

                        client = await aiohttp_client(server)
                        # note: If the parameter is app aiohttp.web.Application
                        # the tool creates TestServer implicitly for serving the application.
                        resp = await client.get('/fledge/ping')
                        assert 401 == resp.status
                    logger_warn.assert_called_once_with('A valid token required to ping; as auth is mandatory & allow ping is set to false.')
                mock_get_cat.assert_called_once_with('rest_api', 'allowPing')
            assert 0 == query_patch.call_count
    log_params = 'Received %s request for %s', 'GET', '/fledge/ping'
    logger_info.assert_called_once_with(*log_params)


@pytest.allure.feature("unit")
@pytest.allure.story("api", "common")
async def test_ping_https_allow_ping_true(aiohttp_server, ssl_ctx, aiohttp_client, loop, get_machine_detail):
    payload = '{"return": ["key", "description", "value"], "sort": {"column": "key", "direction": "asc"}}'
    result = {"rows": [
                {"value": 1, "key": "PURGED", "description": "blah6"},
                {"value": 2, "key": "READINGS", "description": "blah1"},
                {"value": 3, "key": "North Readings to PI", "description": "blah2"},
                {"value": 4, "key": "North Statistics to PI", "description": "blah3"},
                {"value": 10, "key": "North Statistics to OCS", "description": "blah5"},
                {"value": 100, "key": "Readings Sent", "description": "Readings Sent North"},
               ]}

    @asyncio.coroutine
    def mock_coro(*args, **kwargs):
        return result

    # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
    if sys.version_info.major == 3 and sys.version_info.minor >= 8:
        _rv = await mock_coro()
    else:
        _rv = asyncio.ensure_future(mock_coro())
    
    host_name, ip_addresses = get_machine_detail
    mock_storage_client_async = MagicMock(StorageClientAsync)
    with patch.object(middleware._logger, 'debug') as logger_info:
        with patch.object(connect, 'get_storage_async', return_value=mock_storage_client_async):
            with patch.object(mock_storage_client_async, 'query_tbl_with_payload', return_value=_rv) as query_patch:
                    app = web.Application(loop=loop, middlewares=[middleware.optional_auth_middleware])
                    # fill route table
                    routes.setup(app)

                    server = await aiohttp_server(app, ssl=ssl_ctx)
                    await server.start_server(loop=loop)

                    with pytest.raises(Exception) as error_exec:
                        client = await aiohttp_client(server)
                        await client.get('/fledge/ping')
                    assert "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed" in str(error_exec)

                    with pytest.raises(Exception) as error_exec:
                        # self signed certificate,
                        # and we are not using SSL context here for client as verifier
                        connector = aiohttp.TCPConnector(verify_ssl=True, loop=loop)
                        client = await aiohttp_client(server, connector=connector)
                        await client.get('/fledge/ping')
                    assert "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed" in str(error_exec)

                    connector = aiohttp.TCPConnector(verify_ssl=False, loop=loop)
                    client = await aiohttp_client(server, connector=connector)
                    resp = await client.get('/fledge/ping')
                    s = resp.request_info.url.human_repr()
                    assert "https" == s[:5]
                    assert 200 == resp.status
                    content = await resp.text()
                    content_dict = json.loads(content)
                    assert 0 <= content_dict["uptime"]
                    assert 2 == content_dict["dataRead"]
                    assert 100 == content_dict["dataSent"]
                    assert 1 == content_dict["dataPurged"]
                    assert content_dict["authenticationOptional"] is True
                    assert content_dict['serviceName'] == "Fledge"
                    assert content_dict['hostName'] == host_name
                    assert content_dict['ipAddresses'] == ip_addresses
                    assert content_dict['health'] == "green"
                    assert content_dict['safeMode'] is False
                    assert re.match(SEMANTIC_VERSIONING_REGEX, content_dict['version']) is not None
                    assert content_dict['alerts'] == 0
            query_patch.assert_called_once_with('statistics', payload)
        logger_info.assert_called_once_with('Received %s request for %s', 'GET', '/fledge/ping')


@pytest.allure.feature("unit")
@pytest.allure.story("api", "common")
async def test_ping_https_allow_ping_false(aiohttp_server, ssl_ctx, aiohttp_client, loop, get_machine_detail):
    payload = '{"return": ["key", "description", "value"], "sort": {"column": "key", "direction": "asc"}}'
    result = {"rows": [
        {"value": 1, "key": "PURGED", "description": "blah6"},
        {"value": 2, "key": "READINGS", "description": "blah1"},
        {"value": 3, "key": "North Readings to PI", "description": "blah2"},
        {"value": 4, "key": "North Statistics to PI", "description": "blah3"},
        {"value": 6, "key": "North Statistics to OCS", "description": "blah5"},
        {"value": 100, "key": "Readings Sent", "description": "Readings Sent North"},
    ]}

    @asyncio.coroutine
    def mock_coro(*args, **kwargs):
        return result

    # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
    if sys.version_info.major == 3 and sys.version_info.minor >= 8:
        _rv = await mock_coro()
    else:
        _rv = asyncio.ensure_future(mock_coro())
    
    host_name, ip_addresses = get_machine_detail
    mock_storage_client_async = MagicMock(StorageClientAsync)
    with patch.object(middleware._logger, 'debug') as logger_info:
        with patch.object(connect, 'get_storage_async', return_value=mock_storage_client_async):
            with patch.object(mock_storage_client_async, 'query_tbl_with_payload', return_value=_rv) as query_patch:
                    app = web.Application(loop=loop, middlewares=[middleware.optional_auth_middleware])
                    # fill route table
                    routes.setup(app)

                    server = await aiohttp_server(app, ssl=ssl_ctx)
                    await server.start_server(loop=loop)

                    with pytest.raises(Exception) as error_exec:
                        client = await aiohttp_client(server)
                        await client.get('/fledge/ping')
                    assert "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed" in str(error_exec)

                    with pytest.raises(Exception) as error_exec:
                        # self signed certificate,
                        # and we are not using SSL context here for client as verifier
                        connector = aiohttp.TCPConnector(verify_ssl=True, loop=loop)
                        client = await aiohttp_client(server, connector=connector)
                        await client.get('/fledge/ping')
                    assert "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed" in str(error_exec)

                    connector = aiohttp.TCPConnector(verify_ssl=False, loop=loop)
                    client = await aiohttp_client(server, connector=connector)
                    resp = await client.get('/fledge/ping')
                    s = resp.request_info.url.human_repr()
                    assert "https" == s[:5]
                    assert 200 == resp.status
                    content = await resp.text()
                    content_dict = json.loads(content)
                    assert content_dict['serviceName'] == "Fledge"
                    assert content_dict['hostName'] == host_name
                    assert content_dict['ipAddresses'] == ip_addresses
                    assert content_dict['health'] == "green"
                    assert re.match(SEMANTIC_VERSIONING_REGEX, content_dict['version']) is not None
                    assert content_dict['alerts'] == 0
            query_patch.assert_called_once_with('statistics', payload)
        logger_info.assert_called_once_with('Received %s request for %s', 'GET', '/fledge/ping')


@pytest.allure.feature("unit")
@pytest.allure.story("api", "common")
async def test_ping_https_auth_required_allow_ping_true(aiohttp_server, ssl_ctx, aiohttp_client, loop, get_machine_detail):
    payload = '{"return": ["key", "description", "value"], "sort": {"column": "key", "direction": "asc"}}'
    result = {"rows": [
                {"value": 1, "key": "PURGED", "description": "blah6"},
                {"value": 2, "key": "READINGS", "description": "blah1"},
                {"value": 3, "key": "North Readings to PI", "description": "blah2"},
                {"value": 4, "key": "North Statistics to PI", "description": "blah3"},
                {"value": 10, "key": "North Statistics to OCS", "description": "blah5"},
                {"value": 100, "key": "Readings Sent", "description": "Readings Sent North"},
               ]}

    @asyncio.coroutine
    def mock_coro(*args, **kwargs):
        return result

    async def mock_get_category_item():
        return {"value": "true"}

    # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
    if sys.version_info.major == 3 and sys.version_info.minor >= 8:
        _rv1 = await mock_coro()
        _rv2 = await mock_get_category_item()
    else:
        _rv1 = asyncio.ensure_future(mock_coro())
        _rv2 = asyncio.ensure_future(mock_get_category_item())    
    
    host_name, ip_addresses = get_machine_detail
    mock_storage_client_async = MagicMock(StorageClientAsync)
    with patch.object(middleware._logger, 'debug') as logger_info:
        with patch.object(connect, 'get_storage_async', return_value=mock_storage_client_async):
            with patch.object(mock_storage_client_async, 'query_tbl_with_payload', return_value=_rv1) as query_patch:
                with patch.object(ConfigurationManager, "get_category_item", return_value=_rv2) as mock_get_cat:
                    app = web.Application(loop=loop, middlewares=[middleware.auth_middleware])
                    # fill route table
                    routes.setup(app)

                    server = await aiohttp_server(app, ssl=ssl_ctx)
                    await server.start_server(loop=loop)

                    with pytest.raises(Exception) as error_exec:
                        client = await aiohttp_client(server)
                        await client.get('/fledge/ping')
                    assert "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed" in str(error_exec)

                    with pytest.raises(Exception) as error_exec:
                        # self signed certificate,
                        # and we are not using SSL context here for client as verifier
                        connector = aiohttp.TCPConnector(verify_ssl=True, loop=loop)
                        client = await aiohttp_client(server, connector=connector)
                        await client.get('/fledge/ping')
                    assert "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed" in str(error_exec)

                    connector = aiohttp.TCPConnector(verify_ssl=False, loop=loop)
                    client = await aiohttp_client(server, connector=connector)
                    resp = await client.get('/fledge/ping')
                    s = resp.request_info.url.human_repr()
                    assert "https" == s[:5]
                    assert 200 == resp.status
                    content = await resp.text()
                    content_dict = json.loads(content)
                    assert 0 <= content_dict["uptime"]
                    assert 2 == content_dict["dataRead"]
                    assert 100 == content_dict["dataSent"]
                    assert 1 == content_dict["dataPurged"]
                    assert content_dict["authenticationOptional"] is False
                    assert content_dict['serviceName'] == "Fledge"
                    assert content_dict['hostName'] == host_name
                    assert content_dict['ipAddresses'] == ip_addresses
                    assert content_dict['health'] == "green"
                    assert content_dict['safeMode'] is False
                    assert re.match(SEMANTIC_VERSIONING_REGEX, content_dict['version']) is not None
                    assert content_dict['alerts'] == 0
                    mock_get_cat.assert_called_once_with('rest_api', 'allowPing')
                query_patch.assert_called_once_with('statistics', payload)
            logger_info.assert_called_once_with('Received %s request for %s', 'GET', '/fledge/ping')


@pytest.allure.feature("unit")
@pytest.allure.story("api", "common")
async def test_ping_https_auth_required_allow_ping_false(aiohttp_server, ssl_ctx, aiohttp_client, loop, get_machine_detail):
    @asyncio.coroutine
    def mock_coro(*args, **kwargs):
        result = {"rows": [
            {"value": 1, "key": "PURGED", "description": "blah6"},
            {"value": 2, "key": "READINGS", "description": "blah1"},
            {"value": 3, "key": "North Readings to PI", "description": "blah2"},
            {"value": 4, "key": "North Statistics to PI", "description": "blah3"},
            {"value": 6, "key": "North Statistics to OCS", "description": "blah5"},
            {"value": 100, "key": "Readings Sent", "description": "Readings Sent North"},
        ]}
        return result

    async def mock_get_category_item():
        return {"value": "false"}

    # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
    if sys.version_info.major == 3 and sys.version_info.minor >= 8:
        _rv1 = await mock_coro()
        _rv2 = await mock_get_category_item()
    else:
        _rv1 = asyncio.ensure_future(mock_coro())
        _rv2 = asyncio.ensure_future(mock_get_category_item())    
    
    mock_storage_client_async = MagicMock(StorageClientAsync)
    with patch.object(middleware._logger, 'debug') as logger_info:
        with patch.object(connect, 'get_storage_async', return_value=mock_storage_client_async):
            with patch.object(mock_storage_client_async, 'query_tbl_with_payload', return_value=_rv1) as query_patch:
                with patch.object(ConfigurationManager, "get_category_item", return_value=_rv2) as mock_get_cat:
                    with patch.object(_logger, 'warning') as logger_warn:
                        app = web.Application(loop=loop, middlewares=[middleware.auth_middleware])
                        # fill route table
                        routes.setup(app)

                        server = await aiohttp_server(app, ssl=ssl_ctx)
                        await server.start_server(loop=loop)

                        with pytest.raises(Exception) as error_exec:
                            client = await aiohttp_client(server)
                            await client.get('/fledge/ping')
                        assert "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed" in str(error_exec)

                        with pytest.raises(Exception) as error_exec:
                            # self signed certificate,
                            # and we are not using SSL context here for client as verifier
                            connector = aiohttp.TCPConnector(verify_ssl=True, loop=loop)
                            client = await aiohttp_client(server, connector=connector)
                            await client.get('/fledge/ping')
                        assert "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed" in str(error_exec)

                        connector = aiohttp.TCPConnector(verify_ssl=False, loop=loop)
                        client = await aiohttp_client(server, connector=connector)
                        resp = await client.get('/fledge/ping')
                        s = resp.request_info.url.human_repr()
                        assert "https" == s[:5]
                        assert 401 == resp.status
                    logger_warn.assert_called_once_with('A valid token required to ping; as auth is mandatory & allow ping is set to false.')
                mock_get_cat.assert_called_once_with('rest_api', 'allowPing')
            assert 0 == query_patch.call_count
        logger_info.assert_called_once_with('Received %s request for %s', 'GET', '/fledge/ping')


@pytest.allure.feature("unit")
@pytest.allure.story("api", "common")
async def test_shutdown_http(aiohttp_server, aiohttp_client, loop):
    app = web.Application()
    # fill route table
    routes.setup(app)

    server = await aiohttp_server(app)
    await server.start_server(loop=loop)

    client = await aiohttp_client(server)
    resp = await client.put('/fledge/shutdown', data=None)
    assert 200 == resp.status
    content = await resp.text()
    content_dict = json.loads(content)
    assert "Fledge shutdown has been scheduled. Wait for few seconds for process cleanup." == content_dict["message"]


@pytest.allure.feature("unit")
@pytest.allure.story("api", "common")
async def test_restart_http(aiohttp_server, aiohttp_client, loop):
    app = web.Application()
    # fill route table
    routes.setup(app)

    server = await aiohttp_server(app)
    await server.start_server(loop=loop)

    with patch.object(_logger, 'info') as logger_info:
        client = await aiohttp_client(server)
        resp = await client.put('/fledge/restart', data=None)
        assert 200 == resp.status
        content = await resp.text()
        content_dict = json.loads(content)
        assert "Fledge restart has been scheduled." == content_dict["message"]
    logger_info.assert_called_once_with('Executing controlled shutdown and start')
