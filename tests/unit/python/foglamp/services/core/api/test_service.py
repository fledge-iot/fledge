# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


import json
from aiohttp import web
import pytest
from foglamp.services.core import routes
from foglamp.services.core.service_registry.service_registry import ServiceRegistry
from foglamp.services.core.interest_registry.interest_registry import InterestRegistry


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

    async def test_get_health(self, mocker, reset_service_registry, client):
        # empty service registry
        resp = await client.get('/foglamp/service')
        assert 200 == resp.status
        result = await resp.text()
        json_response = json.loads(result)
        assert json_response == {'services': []}
        # populated service registry
        s_id_1 = ServiceRegistry.register(
            'name1', 'Storage', 'address1', 1, 1,  'protocol1')
        s_id_2 = ServiceRegistry.register(
            'name2', 'Southbound', 'address2', 2, 2,  'protocol2')
        s_id_3 = ServiceRegistry.register(
            'name3', 'Southbound', 'address3', 3, 3,  'protocol3')
        s_id_4 = ServiceRegistry.register(
            'name4', 'Southbound', 'address4', 4, 4,  'protocol4')

        mocker.patch.object(InterestRegistry, "__init__", return_value=None)
        mocker.patch.object(InterestRegistry, "get", return_value=list())

        ServiceRegistry.unregister(s_id_3)
        ServiceRegistry.mark_as_failed(s_id_4)

        resp = await client.get('/foglamp/service')
        assert 200 == resp.status
        result = await resp.text()
        json_response = json.loads(result)
        assert json_response == {
                    'services': [
                        {
                            'type': 'Storage',
                            'service_port': 1,
                            'address': 'address1',
                            'protocol': 'protocol1',
                            'status': 'running',
                            'name': 'name1',
                            'management_port': 1
                        },
                        {
                            'type': 'Southbound',
                            'service_port': 2,
                            'address': 'address2',
                            'protocol': 'protocol2',
                            'status': 'running',
                            'name': 'name2',
                            'management_port': 2
                        },
                        {
                            'type': 'Southbound',
                            'service_port': 3,
                            'address': 'address3',
                            'protocol': 'protocol3',
                            'status': 'down',
                            'name': 'name3',
                            'management_port': 3
                        },
                        {
                            'type': 'Southbound',
                            'service_port': 4,
                            'address': 'address4',
                            'protocol': 'protocol4',
                            'status': 'failed',
                            'name': 'name4',
                            'management_port': 4
                        }
                    ]
        }
