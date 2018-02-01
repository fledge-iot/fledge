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

from aiohttp import web
import json
import pytest

from foglamp.services.core import routes


@pytest.allure.feature("unit")
@pytest.allure.story("api", "common")
async def test_ping_http(test_server, test_client, loop):
    app = web.Application()
    # fill route table
    routes.setup(app)

    server = await test_server(app)
    server.start_server(loop=loop)

    client = await test_client(app)
    resp = await client.get('/foglamp/ping')
    assert 200 == resp.status
    content = await resp.text()
    content_dict = json.loads(content)
    assert 0.0 < content_dict["uptime"]


@pytest.mark.skip(reason="To be done with self signed certs")
async def test_ping_https(test_server, test_client, loop):
    app = web.Application()
    # fill route table
    routes.setup(app)

    server = await test_server(app)
    # server.start_server(loop=loop, ssl=<ssl_ctx>)

    client = await test_client(app)

    resp = await client.get('/foglamp/ping')
    assert 200 == resp.status
    content = await resp.text()
    content_dict = json.loads(content)
    assert 0.0 < content_dict["uptime"]
