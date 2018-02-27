# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


import json
from unittest.mock import MagicMock, patch
from aiohttp import web
import pytest
from foglamp.services.core import routes
from foglamp.services.core.service_registry.service_registry import ServiceRegistry


__author__ = "Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("api", "service")
class TestService:
    @pytest.fixture
    def reset_service_registry(self):
        del ServiceRegistry._registry[:]
        yield
        del ServiceRegistry._registry[:]


    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop)
        # fill the routes table
        routes.setup(app)
        return loop.run_until_complete(test_client(app))


    async def test_get_health(self, reset_service_registry, client):
        # empty service registry
        resp = await client.get('/foglamp/service')
        assert 200 == resp.status
        result = await resp.text()
        json_response = json.loads(result)
        assert json_response == {'services': []}
        # populated service registry
        s_id_1 = ServiceRegistry.register(
            'sname1', 'Storage', 'saddress1', 1, 1,  'protocol1')
        s_id_2 = ServiceRegistry.register(
            'sname2', 'Southbound', 'saddress2', 2, 2,  'protocol2')
        s_id_3 = ServiceRegistry.register(
            'sname3', 'Southbound', 'saddress3', 3, 3,  'protocol3')
        resp = await client.get('/foglamp/service')
        assert 200 == resp.status
        result = await resp.text()
        json_response = json.loads(result)
        assert json_response == {'services': [{'type': 'Storage', 'service_port': 1, 'address': 'saddress1', 'protocol': 'protocol1', 'status': 'running', 'name': 'sname1', 'management_port': 1}, {'type': 'Southbound', 'service_port': 2, 'address': 'saddress2', 'protocol': 'protocol2', 'status': 'running', 'name': 'sname2', 'management_port': 2}, {'type': 'Southbound', 'service_port': 3, 'address': 'saddress3', 'protocol': 'protocol3', 'status': 'running', 'name': 'sname3', 'management_port': 3}]}

