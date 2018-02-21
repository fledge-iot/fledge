# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import pathlib
import aiohttp
from aiohttp import web
from aiohttp.test_utils import unused_port

import pytest

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


HOST = '127.0.0.1'
PORT = unused_port()


class FakeServer:

    def __init__(self, *, loop):
        self.loop = loop
        self.app = web.Application(loop=loop)
        self.app.router.add_routes([
            web.post('/foglamp/fileupload', self.fhandler)
        ])
        self.handler = None
        self.server = None

    async def start(self):
        self.handler = self.app.make_handler()
        self.server = await self.loop.create_server(self.handler, HOST, PORT, ssl=None)

    async def stop(self):
        self.server.close()
        await self.server.wait_closed()
        await self.app.shutdown()
        await self.handler.shutdown()
        await self.app.cleanup()

    async def fhandler(self, request):
        data = await request.post()
        print(len(data))
        # contains the name of the file in string format
        key_file = data.get('key')
        cert_file = data.get('cert')

        if not key_file or not cert_file:
            raise web.HTTPBadRequest(reason="key or certs file is missing")

        key_filename = key_file.filename
        cert_filename = cert_file.filename

        # cert and key filenames should match
        if cert_filename and key_filename:
            if cert_filename.split(".")[0] != key_filename.split(".")[0]:
                raise web.HTTPBadRequest(reason="key and certs file name should match")

        # .file contains the actual file data that needs to be stored somewhere.
        # TODO: write contents to directory
        if key_file:
            key_file_data = data['key'].file
            key_file_content = key_file_data.read()

        if cert_file:
            cert_file_data = data['cert'].file
            cert_file_content = cert_file_data.read()

        return web.json_response({"key_filename": key_filename, "cert_filename": cert_filename})


@pytest.fixture
def certs_path():
    return pathlib.Path(__file__).parent


@pytest.mark.asyncio
async def test_multiple_files_upload(event_loop, certs_path):
    fake_server = FakeServer(loop=event_loop)
    await fake_server.start()

    async with aiohttp.ClientSession() as session:
        url = 'http://{}:{}/foglamp/fileupload'.format(HOST, PORT)
        files = {'key': open(str(certs_path / 'certs/foglamp.key'), 'rb'),
                 'cert': open(str(certs_path / 'certs/foglamp.cert'), 'rb')}
        async with session.post(url, data=files) as resp:
            assert 200 == resp.status

    await fake_server.stop()


@pytest.mark.asyncio
async def test_file_upload_with_different_names(event_loop, certs_path):
    fake_server = FakeServer(loop=event_loop)
    await fake_server.start()

    async with aiohttp.ClientSession() as session:
        url = 'http://{}:{}/foglamp/fileupload'.format(HOST, PORT)
        files = {'key': open(str(certs_path / 'certs/server.key'), 'rb'),
                 'cert': open(str(certs_path / 'certs/foglamp.cert'), 'rb')
                 }
        async with session.post(url, data=files) as resp:
            assert 400 == resp.status

    await fake_server.stop()


@pytest.mark.asyncio
async def test_bad_key_file_upload(event_loop, certs_path):
    fake_server = FakeServer(loop=event_loop)
    await fake_server.start()

    async with aiohttp.ClientSession() as session:
        url = 'http://{}:{}/foglamp/fileupload'.format(HOST, PORT)
        files = {'bad_key': open(str(certs_path / 'certs/foglamp.key'), 'rb'),
                 'cert': open(str(certs_path / 'certs/foglamp.cert'), 'rb')
                 }
        async with session.post(url, data=files) as resp:
            assert 400 == resp.status
            assert 'key or certs file is missing' == resp.reason

    await fake_server.stop()


@pytest.mark.asyncio
async def test_bad_cert_file_upload(event_loop, certs_path):
    fake_server = FakeServer(loop=event_loop)
    await fake_server.start()

    async with aiohttp.ClientSession() as session:
        url = 'http://{}:{}/foglamp/fileupload'.format(HOST, PORT)
        files = {'bad_cert': open(str(certs_path / 'certs/foglamp.cert'), 'rb'),
                 'key': open(str(certs_path / 'certs/foglamp.key'), 'rb')}
        async with session.post(url, data=files) as resp:
            assert 400 == resp.status
            assert 'key or certs file is missing' == resp.reason

    await fake_server.stop()
