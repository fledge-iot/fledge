# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from aiohttp import web
import pytest
import time
from unittest.mock import patch

from foglamp.services.common.microservice_management import routes
from foglamp.services.common.microservice import FoglampMicroservice
from foglamp.common.service_record import ServiceRecord
from foglamp.services.common import utils as utils

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class mServiceThing(FoglampMicroservice):

    async def shutdown(self, request):
        return web.json_response({'shutdown': 1})

    async def change(self, request):
        pass

    def run(self):
        pass


@pytest.allure.feature("unit")
@pytest.allure.story("services", "common")
class TestUtils:

    utils._MAX_ATTEMPTS = 2

    async def test_ping_service_pass(self, test_server, loop):
        # GIVEN a service is running at a given URL
        app = web.Application()
        with patch.object(FoglampMicroservice, "__init__", return_value=None):
            m = mServiceThing()
            m._start_time = time.time()
            # fill route table
            routes.setup(app, m)

            server = await test_server(app)
            server.start_server(loop=loop)
            # for index, route in enumerate(app.router.routes()):
            #     res_info = route.resource.get_info()
            #     print(res_info)

        # =  s_id, s_name, s_type, s_protocol, s_address, s_port, m_port):

        # WHEN the service is pinged with a valid URL
        service = ServiceRecord("d", "test", "Southbound", "http", server.host, 1, server.port)
        resp = await utils.ping_service(service, loop=loop)

        # THEN ping response is received
        assert resp is True

    async def test_ping_service_fail_bad_url(self, test_server, loop):
        # GIVEN a service is running at a given URL
        app = web.Application()
        with patch.object(FoglampMicroservice, "__init__", return_value=None):
            m = mServiceThing()
            m._start_time = time.time()
            # fill route table
            routes.setup(app, m)

            server = await test_server(app)
            server.start_server(loop=loop)

        # WHEN the service is pinged with a BAD URL
        service = ServiceRecord("d", "test", "Southbound", "http", server.host+"1", 1, server.port)
        resp = await utils.ping_service(service, loop=loop)

        # THEN ping response is NOT received
        assert resp is False

    async def test_shutdown_service_pass(self, test_server, loop):
        # GIVEN a service is running at a given URL
        app = web.Application()
        with patch.object(FoglampMicroservice, "__init__", return_value=None):
            m = mServiceThing()
            # fill route table
            routes.setup(app, m)

            server = await test_server(app)
            server.start_server(loop=loop)

        # WHEN shutdown call is made at the valid URL
        service = ServiceRecord("d", "test", "Southbound", "http", server.host, 1, server.port)
        resp = await utils.shutdown_service(service, loop=loop)

        # THEN shutdown returns success
        assert resp is True

    async def test_shutdown_service_fail_bad_url(self, test_server, loop):
        # GIVEN a service is running at a given URL
        app = web.Application()
        with patch.object(FoglampMicroservice, "__init__", return_value=None):
            m = mServiceThing()
            # fill route table
            routes.setup(app, m)

            server = await test_server(app)
            server.start_server(loop=loop)

        # WHEN shutdown call is made at the invalid URL
        service = ServiceRecord("d", "test", "Southbound", "http", server.host, 1, server.port+1)

        resp = await utils.shutdown_service(service, loop=loop)

        # THEN shutdown fails
        assert resp is False
