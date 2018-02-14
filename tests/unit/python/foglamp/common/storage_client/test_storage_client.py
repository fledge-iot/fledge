# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test foglamp/common/storage_client/storage_client.py """
import pytest

from unittest.mock import MagicMock, patch
import json
from aiohttp import web

from foglamp.common.service_record import ServiceRecord
from foglamp.common.storage_client.storage_client import StorageClient
from foglamp.common.storage_client.exceptions import *

__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class FakeFoglampStorageSrvr:

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

    def test_init(self):
        svc = {"id": 1, "name": "foo", "address": "local", "service_port": 1000, "management_port": 2000,
               "type": "Storage", "protocol": "http"}
        with patch.object(StorageClient, '_get_storage_service', return_value=svc):
            sc = StorageClient(1, 2)
            assert "local:1000" == sc.base_url
            assert "local:2000" == sc.management_api_url

    def test_init_with_invalid_storage_service(self):
        svc = {"id": 1, "name": "foo", "address": "local", "service_port": 1000, "management_port": 2000,
               "type": "xStorage", "protocol": "http"}
        with pytest.raises(Exception) as excinfo:
            with patch.object(StorageClient, '_get_storage_service', return_value=svc):
                sc = StorageClient(1, 2)
        # assert logger called to log warning with
        # 'Storage should be a valid *Storage* micro-service instance'
        assert excinfo.type is InvalidServiceInstance

    def test_init_with_service_record(self):
        mockServiceRecord = MagicMock(ServiceRecord)
        mockServiceRecord._address = "local"
        mockServiceRecord._type = "Storage"
        mockServiceRecord._port = 1000
        mockServiceRecord._management_port = 2000

        sc = StorageClient(1, 2, mockServiceRecord)
        assert "local:1000" == sc.base_url
        assert "local:2000" == sc.management_api_url

    def test_init_with_invalid_service_record(self):
        with pytest.raises(Exception) as excinfo:
            sc = StorageClient(1, 2, "blah")
        # assert logger called to log warning with
        # 'Storage should be a valid FogLAMP micro-service instance'
        assert excinfo.type is InvalidServiceInstance

    def test_init_with_service_record_non_storage_type(self):
        mockServiceRecord = MagicMock(ServiceRecord)
        mockServiceRecord._address = "local"
        mockServiceRecord._type = "xStorage"
        mockServiceRecord._port = 1000
        mockServiceRecord._management_port = 2000

        with pytest.raises(Exception) as excinfo:
            sc = StorageClient(1, 2, mockServiceRecord)
        # assert logger called to log warning with
        # 'Storage should be a valid *Storage* micro-service instance'
        assert excinfo.type is InvalidServiceInstance

    @pytest.mark.asyncio
    async def test_insert_into_tbl(self, event_loop):
        # start at class/module level setup
        fake_storage_srvr = FakeFoglampStorageSrvr(loop=event_loop)
        await fake_storage_srvr.start()

        mockServiceRecord = MagicMock(ServiceRecord)
        mockServiceRecord._address = "127.0.0.1"
        mockServiceRecord._type = "Storage"
        mockServiceRecord._port = 8080
        mockServiceRecord._management_port = 2000

        sc = StorageClient(1, 2, mockServiceRecord)
        assert "127.0.0.1:8080" == sc.base_url

        with pytest.raises(Exception) as excinfo:
            res = sc.insert_into_tbl("z", {"k": "v"})
        assert excinfo.type is TypeError
        assert "Provided data to insert must be a valid JSON" in str(excinfo.value)

        # res = sc.insert_into_tbl("z", json.dumps({"k": "v"}))
        # print(res)

        # TODO: call via actual code
        # async with aiohttp.ClientSession(loop=event_loop) as session:
        #     async with session.post('http://127.0.0.1:8080/storage/table/z',
        #                             data=None) as resp:
        #         print(await resp.json())

        # stop at class/module level teardown
        await fake_storage_srvr.stop()


@pytest.allure.feature("unit")
@pytest.allure.story("common", "storage_client")
class TestReadingsSC:
    pass

