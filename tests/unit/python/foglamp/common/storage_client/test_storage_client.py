# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test foglamp/common/storage_client/storage_client.py """
import pytest

from unittest.mock import MagicMock, patch
import json
import asyncio
from aiohttp import web
from aiohttp.test_utils import unused_port

from foglamp.common.service_record import ServiceRecord
from foglamp.common.storage_client.storage_client import StorageClient
from foglamp.common.storage_client.exceptions import *

__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

HOST = '127.0.0.1'
PORT = unused_port()


class FakeFoglampStorageSrvr:

    def __init__(self, *, loop):
        self.loop = loop
        self.app = web.Application(loop=loop)
        self.app.router.add_routes([
            web.post('/storage/table/{tbl_name}', self.query_with_payload_insert_into_or_update_tbl_handler),
            web.put('/storage/table/{tbl_name}', self.query_with_payload_insert_into_or_update_tbl_handler),
            web.delete('/storage/table/{tbl_name}', self.delete_from_tbl_handler),
            web.get('/storage/table/{tbl_name}', self.query_tbl_handler),
            web.put('/storage/table/{tbl_name}/query', self.query_with_payload_insert_into_or_update_tbl_handler)
        ])
        self.runner = None

    async def start(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        svc = web.TCPSite(self.runner, host=HOST, port=PORT, ssl_context=None)
        await svc.start()

    async def stop(self):
        await self.runner.cleanup()

    async def query_with_payload_insert_into_or_update_tbl_handler(self, request):
        payload = await request.json()

        if payload.get("bad_request", None):
            return web.HTTPBadRequest(reason="bad data")

        if payload.get("internal_server_err", None):
            return web.HTTPInternalServerError(reason="something wrong")

        return web.json_response({
           "called": payload
        })

    async def delete_from_tbl_handler(self, request):
        try:
            payload = await request.json()

            if payload.get("bad_request", None):
                return web.HTTPBadRequest(reason="bad data")

            if payload.get("internal_server_err", None):
                return web.HTTPInternalServerError(reason="something wrong")
        except:
            payload = 1

        return web.json_response({
            "called": payload
        })

    async def query_tbl_handler(self, request):

        # add side effect based on query param foo `?foo=`

        res = 1
        if request.query.get('foo', None):
            res = 'foo passed'

        if request.query.get("bad_foo", None):
            return web.HTTPBadRequest(reason="bad data")

        if request.query.get("internal_server_err_foo", None):
            return web.HTTPInternalServerError(reason="something wrong")

        return web.json_response({
            "called": res
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
        # 'POST', '/storage/table/{tbl_name}', data

        fake_storage_srvr = FakeFoglampStorageSrvr(loop=event_loop)
        await fake_storage_srvr.start()

        mockServiceRecord = MagicMock(ServiceRecord)
        mockServiceRecord._address = HOST
        mockServiceRecord._type = "Storage"
        mockServiceRecord._port = PORT
        mockServiceRecord._management_port = 2000

        sc = StorageClient(1, 2, mockServiceRecord)
        assert "{}:{}".format(HOST, PORT) == sc.base_url

        with pytest.raises(Exception) as excinfo:
            args = None, '{"k": "v"}'
            futures = [event_loop.run_in_executor(None, sc.insert_into_tbl, *args)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is ValueError
        assert "Table name is missing" in str(excinfo.value)

        with pytest.raises(Exception) as excinfo:
            args = "aTable", None
            futures = [event_loop.run_in_executor(None, sc.insert_into_tbl, *args)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is ValueError
        assert "Data to insert is missing" in str(excinfo.value)

        with pytest.raises(Exception) as excinfo:
            args = "aTable", {"k": "v"}
            futures = [event_loop.run_in_executor(None, sc.insert_into_tbl, *args)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is TypeError
        assert "Provided data to insert must be a valid JSON" in str(excinfo.value)

        args = "aTable", json.dumps({"k": "v"})
        futures = [event_loop.run_in_executor(None, sc.insert_into_tbl, *args)]
        for response in await asyncio.gather(*futures):
            assert {"k": "v"} == response["called"]

        with pytest.raises(Exception) as excinfo:
            args = "aTable", json.dumps({"bad_request": "v"})
            futures = [event_loop.run_in_executor(None, sc.insert_into_tbl, *args)]
            for response in await asyncio.gather(*futures):
                pass
        # assert logger called twice
        assert excinfo.type is BadRequest

        with pytest.raises(Exception) as excinfo:
            args = "aTable", json.dumps({"internal_server_err": "v"})
            futures = [event_loop.run_in_executor(None, sc.insert_into_tbl, *args)]
            for response in await asyncio.gather(*futures):
                pass
        # assert logger called once
        assert excinfo.type is StorageServerInternalError

        await fake_storage_srvr.stop()

    @pytest.mark.asyncio
    async def test_update_tbl(self, event_loop):
        # PUT, '/storage/table/{tbl_name}', data

        fake_storage_srvr = FakeFoglampStorageSrvr(loop=event_loop)
        await fake_storage_srvr.start()

        mockServiceRecord = MagicMock(ServiceRecord)
        mockServiceRecord._address = HOST
        mockServiceRecord._type = "Storage"
        mockServiceRecord._port = PORT
        mockServiceRecord._management_port = 2000

        sc = StorageClient(1, 2, mockServiceRecord)
        assert "{}:{}".format(HOST, PORT) == sc.base_url

        with pytest.raises(Exception) as excinfo:
            args = None, json.dumps({"k": "v"})
            futures = [event_loop.run_in_executor(None, sc.update_tbl, *args)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is ValueError
        assert "Table name is missing" in str(excinfo.value)

        with pytest.raises(Exception) as excinfo:
            args = "aTable", None
            futures = [event_loop.run_in_executor(None, sc.update_tbl, *args)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is ValueError
        assert "Data to update is missing" in str(excinfo.value)

        with pytest.raises(Exception) as excinfo:
            args = "aTable", {"k": "v"}
            futures = [event_loop.run_in_executor(None, sc.update_tbl, *args)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is TypeError
        assert "Provided data to update must be a valid JSON" in str(excinfo.value)

        args = "aTable", json.dumps({"k": "v"})
        futures = [event_loop.run_in_executor(None, sc.update_tbl, *args)]
        for response in await asyncio.gather(*futures):
            assert {"k": "v"} == response["called"]

        with pytest.raises(Exception) as excinfo:
            args = "aTable", json.dumps({"bad_request": "v"})
            futures = [event_loop.run_in_executor(None, sc.update_tbl, *args)]
            for response in await asyncio.gather(*futures):
                pass
        # assert logger called twice
        assert excinfo.type is BadRequest

        with pytest.raises(Exception) as excinfo:
            args = "aTable", json.dumps({"internal_server_err": "v"})
            futures = [event_loop.run_in_executor(None, sc.update_tbl, *args)]
            for response in await asyncio.gather(*futures):
                pass
        # assert logger called once
        assert excinfo.type is StorageServerInternalError

        await fake_storage_srvr.stop()

    @pytest.mark.asyncio
    async def test_delete_from_tbl(self, event_loop):
        # 'DELETE', '/storage/table/{tbl_name}', condition (optional)

        fake_storage_srvr = FakeFoglampStorageSrvr(loop=event_loop)
        await fake_storage_srvr.start()

        mockServiceRecord = MagicMock(ServiceRecord)
        mockServiceRecord._address = HOST
        mockServiceRecord._type = "Storage"
        mockServiceRecord._port = PORT
        mockServiceRecord._management_port = 2000

        sc = StorageClient(1, 2, mockServiceRecord)
        assert "{}:{}".format(HOST, PORT) == sc.base_url

        with pytest.raises(Exception) as excinfo:
            futures = [event_loop.run_in_executor(None, sc.delete_from_tbl, None)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is ValueError
        assert "Table name is missing" in str(excinfo.value)

        args = "aTable", None  # delete without condition is allowed
        futures = [event_loop.run_in_executor(None, sc.delete_from_tbl, *args)]
        for response in await asyncio.gather(*futures):
            assert 1 == response["called"]

        with pytest.raises(Exception) as excinfo:
            args = "aTable", {"condition": "v"}
            futures = [event_loop.run_in_executor(None, sc.delete_from_tbl, *args)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is TypeError
        assert "condition payload must be a valid JSON" in str(excinfo.value)

        args = "aTable", json.dumps({"condition": "v"})
        futures = [event_loop.run_in_executor(None, sc.delete_from_tbl, *args)]
        for response in await asyncio.gather(*futures):
            assert {"condition": "v"} == response["called"]

        with pytest.raises(Exception) as excinfo:
            args = "aTable", json.dumps({"bad_request": "v"})
            futures = [event_loop.run_in_executor(None, sc.delete_from_tbl, *args)]
            for response in await asyncio.gather(*futures):
                pass
        # assert logger called twice
        assert excinfo.type is BadRequest

        with pytest.raises(Exception) as excinfo:
            args = "aTable", json.dumps({"internal_server_err": "v"})
            futures = [event_loop.run_in_executor(None, sc.delete_from_tbl, *args)]
            for response in await asyncio.gather(*futures):
                pass
        # assert logger called once
        assert excinfo.type is StorageServerInternalError

        await fake_storage_srvr.stop()

    @pytest.mark.asyncio
    async def test_query_tbl(self, event_loop):
        # 'GET', '/storage/table/{tbl_name}', *allows query params

        fake_storage_srvr = FakeFoglampStorageSrvr(loop=event_loop)
        await fake_storage_srvr.start()

        mockServiceRecord = MagicMock(ServiceRecord)
        mockServiceRecord._address = HOST
        mockServiceRecord._type = "Storage"
        mockServiceRecord._port = PORT
        mockServiceRecord._management_port = 2000

        sc = StorageClient(1, 2, mockServiceRecord)
        assert "{}:{}".format(HOST, PORT) == sc.base_url

        with pytest.raises(Exception) as excinfo:
            futures = [event_loop.run_in_executor(None, sc.query_tbl, None)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is ValueError
        assert "Table name is missing" in str(excinfo.value)

        args = "aTable", None  # query_tbl without query param is == SELECT *
        futures = [event_loop.run_in_executor(None, sc.query_tbl, *args)]
        for response in await asyncio.gather(*futures):
            assert 1 == response["called"]

        args = "aTable", 'foo=v1&bar=v2'
        futures = [event_loop.run_in_executor(None, sc.query_tbl, *args)]
        for response in await asyncio.gather(*futures):
            assert 'foo passed' == response["called"]

        with pytest.raises(Exception) as excinfo:
            args = "aTable", 'bad_foo=1'
            futures = [event_loop.run_in_executor(None, sc.query_tbl, *args)]
            for response in await asyncio.gather(*futures):
                pass
        # assert logger called twice
        assert excinfo.type is BadRequest

        with pytest.raises(Exception) as excinfo:
            args = "aTable", 'internal_server_err_foo=1'
            futures = [event_loop.run_in_executor(None, sc.query_tbl, *args)]
            for response in await asyncio.gather(*futures):
                pass
        # assert logger called once
        assert excinfo.type is StorageServerInternalError

        await fake_storage_srvr.stop()

    @pytest.mark.asyncio
    async def test_query_tbl_with_payload(self, event_loop):
        # 'PUT', '/storage/table/{tbl_name}/query', query_payload

        fake_storage_srvr = FakeFoglampStorageSrvr(loop=event_loop)
        await fake_storage_srvr.start()

        mockServiceRecord = MagicMock(ServiceRecord)
        mockServiceRecord._address = HOST
        mockServiceRecord._type = "Storage"
        mockServiceRecord._port = PORT
        mockServiceRecord._management_port = 2000

        sc = StorageClient(1, 2, mockServiceRecord)
        assert "{}:{}".format(HOST, PORT) == sc.base_url

        with pytest.raises(Exception) as excinfo:
            args = None, json.dumps({"k": "v"})
            futures = [event_loop.run_in_executor(None, sc.query_tbl_with_payload, *args)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is ValueError
        assert "Table name is missing" in str(excinfo.value)

        with pytest.raises(Exception) as excinfo:
            args = "aTable", None
            futures = [event_loop.run_in_executor(None, sc.query_tbl_with_payload, *args)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is ValueError
        assert "Query payload is missing" in str(excinfo.value)

        with pytest.raises(Exception) as excinfo:
            args = "aTable", {"k": "v"}
            futures = [event_loop.run_in_executor(None, sc.query_tbl_with_payload, *args)]
            for response in await asyncio.gather(*futures):
                pass
        assert excinfo.type is TypeError
        assert "Query payload must be a valid JSON" in str(excinfo.value)

        args = "aTable", json.dumps({"k": "v"})
        futures = [event_loop.run_in_executor(None, sc.query_tbl_with_payload, *args)]
        for response in await asyncio.gather(*futures):
            assert {"k": "v"} == response["called"]

        with pytest.raises(Exception) as excinfo:
            args = "aTable", json.dumps({"bad_request": "v"})
            futures = [event_loop.run_in_executor(None, sc.query_tbl_with_payload, *args)]
            for response in await asyncio.gather(*futures):
                pass
        # assert logger called twice
        assert excinfo.type is BadRequest

        with pytest.raises(Exception) as excinfo:
            args = "aTable", json.dumps({"internal_server_err": "v"})
            futures = [event_loop.run_in_executor(None, sc.query_tbl_with_payload, *args)]
            for response in await asyncio.gather(*futures):
                pass
        # assert logger called once
        assert excinfo.type is StorageServerInternalError

        await fake_storage_srvr.stop()


@pytest.allure.feature("unit")
@pytest.allure.story("common", "storage_client")
class TestReadingsSC:
    pass

