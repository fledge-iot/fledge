# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


import json
from unittest.mock import MagicMock, patch
from aiohttp import web
import pytest
from foglamp.services.core import routes


__author__ = "Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("api", "service")
class TestAudit:
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
        s_id_1 = ServiceRegistry.register(
            'sname1', 'Storage', 'saddress1', 1, 1,  'protocol1')
        resp = await client.get('/foglamp/service')
        assert 200 == resp.status
        result = await resp.text()
        json_response = json.loads(result)

