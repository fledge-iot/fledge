# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test rest server api for python/foglamp/services/core/api/common.py """

from aiohttp import web
import json
import pytest

from foglamp.services.core import routes


@pytest.allure.feature("unit")
@pytest.allure.story("api", "common")
async def test_ping(test_server, test_client, loop):
    app = web.Application()
    # fill route table
    routes.setup(app)

    server = await test_server(app)
    server.start_server(loop=loop)

    client = await test_client(app)

    resp = await client.get('/foglamp/ping')
    assert resp.status == 200
    content = await resp.text()
    content_dict = json.loads(content)
    assert content_dict["uptime"] > 0.0
