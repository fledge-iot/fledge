
# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test fledge/common/web/middleware.py """

from aiohttp import web
import pytest
import json

from fledge.common.web import middleware
from fledge.services.core import routes

__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("common", "web")
class TestMiddleware:

    @pytest.fixture
    def client(self, loop, aiohttp_server, aiohttp_client):
        async def handler0(request):
            raise RuntimeError('Error text')

        async def handler1(request):
            raise web.HTTPConflict(reason="foo", text='{"key": "conflict"}')

        async def handler2(request):
            raise web.HTTPNotFound(text='{"key": "not found"}')

        async def handler4(request):
            return web.json_response({"key": "Okay"})

        app = web.Application(loop=loop, middlewares=[middleware.error_middleware])
        # fill the routes table
        routes.setup(app)
        app.router.add_route('GET', '/test', handler0)
        app.router.add_route('GET', '/test-web-ex1', handler1)
        app.router.add_route('GET', '/test-web-ex2', handler2)
        app.router.add_route('GET', '/test-okay', handler4)

        server = loop.run_until_complete(aiohttp_server(app))
        loop.run_until_complete(server.start_server(loop=loop))
        client = loop.run_until_complete(aiohttp_client(server))
        return client

    async def test_middleware_for_unhandled_exception(self, client):
        resp = await client.get('/test')

        assert 500 == resp.status
        txt = await resp.text()
        assert {"error": {"message": "[RuntimeError] Error text"}} == json.loads(txt)

    async def test_middleware_allows_exception_trace(self, client):
        resp = await client.get('/test?trace=1')

        assert 500 == resp.status
        txt = await resp.text()
        res_dict = json.loads(txt)
        assert '[RuntimeError] Error text' == res_dict["error"]["message"]
        # 2 additional key value pairs
        assert 'RuntimeError' == res_dict["error"]["exception"]
        assert 'RuntimeError' in res_dict["error"]["traceback"]

    async def test_http_exception(self, client):
        resp = await client.get('/test-web-ex1')

        assert 409 == resp.status
        assert "foo" == resp.reason
        txt = await resp.text()
        assert {'key': 'conflict'} == json.loads(txt)

    async def test_no_trace_for_http_exception(self, client):
        resp = await client.get('/test-web-ex1?trace=1')

        assert 409 == resp.status
        assert "foo" == resp.reason
        txt = await resp.text()
        assert {'key': 'conflict'} == json.loads(txt)

    async def test_another_http_exception(self, client):
        resp = await client.get('/test-web-ex2')

        assert 404 == resp.status
        assert "Not Found" == resp.reason
        txt = await resp.text()
        assert {'key': 'not found'} == json.loads(txt)

    async def test_http_ok(self, client):
        resp = await client.get('/test-okay')

        assert 200 == resp.status
        assert "OK" == resp.reason
        txt = await resp.text()
        assert {'key': 'Okay'} == json.loads(txt)
