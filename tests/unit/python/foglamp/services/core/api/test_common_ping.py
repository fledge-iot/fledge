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
import aiohttp
from aiohttp import web
import json
import pytest
import ssl
import pathlib

from foglamp.services.core import routes


@pytest.allure.feature("unit")
@pytest.allure.story("api", "common")
async def test_ping_http(test_server, test_client, loop):
    app = web.Application()
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
    app = web.Application()
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
