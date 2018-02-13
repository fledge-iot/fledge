# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test foglamp/common/storage_client/storage_client.py """
import pytest

import aiohttp
from aiohttp import web

__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class FakeFoglampStorage:

    def __init__(self, *, loop):
        self.loop = loop
        self.app = web.Application(loop=loop)
        self.app.router.add_routes([
            web.post('/storage/table/{tbl_name}', self.insert_into_tbl)
        ])
        self.runner = None

    async def start(self):
        # port = unused_port() default http is 8080
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        svc = web.TCPSite(self.runner, '127.0.0.1', ssl_context=None)
        await svc.start()

    async def stop(self):
        await self.runner.cleanup()

    async def insert_into_tbl(self, request):
        return web.json_response({
           "called": 1
        })


@pytest.allure.feature("unit")
@pytest.allure.story("common", "storage_client")
class TestStorageClient:

    @pytest.mark.asyncio
    async def insert_into_tbl(self, event_loop):
        # start at class/module level setup
        fake_storage = FakeFoglampStorage(loop=event_loop)
        await fake_storage.start()

        # TODO: call via actual code
        async with aiohttp.ClientSession(loop=event_loop) as session:
            async with session.post('http://127.0.0.1:8080/storage/table/z',
                                    data=None) as resp:
                print(await resp.json())

        # stop at class/module level teardown
        await fake_storage.stop()


@pytest.allure.feature("unit")
@pytest.allure.story("common", "storage_client")
class TestReadingsSC:
    pass

