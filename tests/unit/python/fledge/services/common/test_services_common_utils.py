# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

from aiohttp import web
import pytest
import time
from unittest.mock import patch

from fledge.services.common.microservice_management import routes
from fledge.services.common.microservice import FledgeMicroservice
from fledge.common.service_record import ServiceRecord
from fledge.services.common import utils as utils

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class mServiceThing(FledgeMicroservice):

    async def shutdown(self, request):
        return web.json_response({'shutdown': 1})

    async def change(self, request):
        pass

    async def get_track(self, request):
        pass

    async def add_track(self, request):
        pass

    def run(self):
        pass


@pytest.allure.feature("unit")
@pytest.allure.story("services", "common")
class TestUtils:

    utils._MAX_ATTEMPTS = 2

    async def test_ping_service_pass(self, aiohttp_server, loop):
        # GIVEN a service is running at a given URL
        app = web.Application()
        with patch.object(FledgeMicroservice, "__init__", return_value=None):
            m = mServiceThing()
            m._start_time = time.time()
            # fill route table
            routes.setup(app, m)

            server = await aiohttp_server(app)
            await server.start_server(loop=loop)

            # WHEN the service is pinged with a valid URL
            with patch.object(utils._logger, "info") as log:
                service = ServiceRecord("d", "test", "Southbound", "http", server.host, 1, server.port)
                url_ping = "{}://{}:{}/fledge/service/ping".format(service._protocol, service._address, service._management_port)
                log_params = 'Ping received for Service %s id %s at url %s', service._name, service._id, url_ping
                resp = await utils.ping_service(service, loop=loop)

            # THEN ping response is received
            assert resp is True
            log.assert_called_once_with(*log_params)

    async def test_ping_service_fail_bad_url(self, aiohttp_server, loop):
        # GIVEN a service is running at a given URL
        app = web.Application()
        with patch.object(FledgeMicroservice, "__init__", return_value=None):
            m = mServiceThing()
            m._start_time = time.time()
            # fill route table
            routes.setup(app, m)

            server = await aiohttp_server(app)
            await server.start_server(loop=loop)

            # WHEN the service is pinged with a BAD URL
            with patch.object(utils._logger, "error") as log:
                service = ServiceRecord("d", "test", "Southbound", "http", server.host+"1", 1, server.port)
                url_ping = "{}://{}:{}/fledge/service/ping".format(service._protocol, service._address, service._management_port)
                log_params = 'Ping not received for Service %s id %s at url %s attempt_count %s', service._name, service._id, \
                       url_ping, utils._MAX_ATTEMPTS+1
                resp = await utils.ping_service(service, loop=loop)

            # THEN ping response is NOT received
            assert resp is False
            log.assert_called_once_with(*log_params)

    async def test_shutdown_service_pass(self, aiohttp_server, loop):
        # GIVEN a service is running at a given URL
        app = web.Application()
        with patch.object(FledgeMicroservice, "__init__", return_value=None):
            m = mServiceThing()
            # fill route table
            routes.setup(app, m)

            server = await aiohttp_server(app)
            await server.start_server(loop=loop)

            # WHEN shutdown call is made at the valid URL
            with patch.object(utils._logger, "info") as log:
                service = ServiceRecord("d", "test", "Southbound", "http", server.host, 1, server.port)
                url_shutdown = "{}://{}:{}/fledge/service/shutdown".format(service._protocol, service._address,
                                                                            service._management_port)
                log_params1 = "Shutting down the %s service %s ...", service._type, service._name
                log_params2 = 'Service %s, id %s at url %s successfully shutdown', service._name, service._id, url_shutdown
                resp = await utils.shutdown_service(service, loop=loop)

            # THEN shutdown returns success
            assert resp is True
            log.assert_called_with(*log_params2)
            assert 2 == log.call_count

    async def test_shutdown_service_fail_bad_url(self, aiohttp_server, loop):
        # GIVEN a service is running at a given URL
        app = web.Application()
        with patch.object(FledgeMicroservice, "__init__", return_value=None):
            m = mServiceThing()
            # fill route table
            routes.setup(app, m)

            server = await aiohttp_server(app)
            await server.start_server(loop=loop)

            # WHEN shutdown call is made at the invalid URL
            with patch.object(utils._logger, "info") as log1:
                with patch.object(utils._logger, "exception") as log2:
                    service = ServiceRecord("d", "test", "Southbound", "http", server.host, 1, server.port+1)
                    log_params1 = "Shutting down the %s service %s ...", service._type, service._name
                    resp = await utils.shutdown_service(service, loop=loop)

            # THEN shutdown fails
            assert resp is False
            log1.assert_called_with(*log_params1)
            assert log2.called is True
