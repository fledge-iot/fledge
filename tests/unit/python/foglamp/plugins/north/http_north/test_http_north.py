# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from unittest.mock import patch
from aiohttp import web
from aiohttp.test_utils import unused_port
import pytest
import asyncio

from foglamp.tasks.north.sending_process import SendingProcess
from foglamp.plugins.north.http_north import http_north
from foglamp.plugins.north.http_north.http_north import HttpNorthPlugin

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_HOST = '127.0.0.1'
_PORT = unused_port()
_URL = 'http://{}:{}/ingress/messages'.format(_HOST, _PORT)


class FakeServer:

    def __init__(self, *, loop):
        self.loop = loop
        self.app = web.Application(loop=loop)
        self.app.router.add_routes([
            web.post('/ingress/messages', self.receive_payload)
        ])
        self.handler = None
        self.server = None

    async def start(self):
        self.handler = self.app.make_handler()
        self.server = await self.loop.create_server(self.handler, _HOST, _PORT, ssl=None)

    async def stop(self):
        self.server.close()
        await self.server.wait_closed()
        await self.app.shutdown()
        await self.handler.shutdown()
        await self.app.cleanup()

    async def receive_payload(self, request):
        body = await request.json()
        return web.json_response(body)


@pytest.allure.feature("unit")
@pytest.allure.story("plugin", "north", "http")
@pytest.mark.asyncio
async def test_send_payload(event_loop):
    fake_server = FakeServer(loop=event_loop)
    await fake_server.start()

    payloads = [{'id': 1, 'asset_code': 'fogbench/temperature', 'read_key': '31e5ccbb-3e45-4038-95e9-7920834d0852', 'user_ts': '2018-02-26 12:12:54.171949+00', 'reading': {'ambient': 7, 'object': 28}}, {'id': 46, 'asset_code': 'fogbench/luxometer', 'read_key': '9b5beb10-5d87-4cd9-803e-02df7942139d', 'user_ts': '2018-02-27 11:46:57.368753+00', 'reading': {'lux': 92748.668}}]
    http_north.http_north = HttpNorthPlugin()
    http_north.http_north.event_loop = event_loop
    http_north.config = http_north._DEFAULT_CONFIG
    http_north.config['url']['value'] = _URL
    last_id, num_count = await http_north.http_north._send_payloads(payloads)
    assert (46, 2) == (last_id, num_count)

    await fake_server.stop()


@pytest.allure.feature("unit")
@pytest.allure.story("plugin", "north", "http")
@pytest.mark.skip(reason='FOGL-1144')
async def test_send_bad_payload():
    pass


@pytest.allure.feature("unit")
@pytest.allure.story("plugin", "north", "http")
@pytest.mark.skip(reason='FOGL-1144')
async def test_send_payload_server_error():
    pass


@pytest.allure.feature("unit")
@pytest.allure.story("plugin", "north", "http")
def test_plugin_info():
    assert http_north.plugin_info() == {
        'name': 'http_north',
        'version': '1.0.0',
        'type': 'north',
        'interface': '1.0',
        'config': http_north._DEFAULT_CONFIG
    }


@pytest.allure.feature("unit")
@pytest.allure.story("plugin", "north", "http")
@pytest.mark.asyncio
async def test_plugin_init():
    assert http_north.plugin_init(http_north._DEFAULT_CONFIG) == http_north._DEFAULT_CONFIG


@pytest.allure.feature("unit")
@pytest.allure.story("plugin", "north", "http")
@pytest.mark.asyncio
async def test_plugin_send(loop):
    async def mock_coro():
        return 1, 2

    data = {'applyFilter': {'default': 'False', 'type': 'boolean', 'description': 'Whether to apply filter before processing the data', 'value': 'False'}, 'shutdown_wait_time': {'default': '10', 'type': 'integer', 'description': 'how long (x seconds) the plugin should wait for pending tasks to complete or cancel otherwise', 'value': '10'}, 'sending_process_instance': SendingProcess(), '_CONFIG_CATEGORY_NAME': 'SEND_PR_3', 'enable': {'default': 'True', 'type': 'boolean', 'description': 'A switch that can be used to enable or disable execution of the sending process.', 'value': 'True'}, 'source': {'default': 'readings', 'type': 'string', 'description': 'Defines the source of the data to be sent on the stream, this may be one of either readings, statistics or audit.', 'value': 'readings'}, 'north': {'default': 'omf', 'type': 'string', 'description': 'The name of the north to use to translate the readings into the output format and send them', 'value': 'omf'}, 'stream_id': {'default': '3', 'type': 'integer', 'description': 'Stream ID', 'value': '3'}, 'blockSize': {'default': '5000', 'type': 'integer', 'description': 'The size of a block of readings to send in each transmission.', 'value': '5000'}, 'plugin': {'default': 'http_north', 'type': 'string', 'description': 'HTTP North Plugin', 'value': 'http_north'}, 'filterRule': {'default': '.[]', 'type': 'string', 'description': 'JQ formatted filter to apply (applicable if applyFilter is True)', 'value': '.[]'}, 'duration': {'default': '60', 'type': 'integer', 'description': 'How long the sending process should run (in seconds) before stopping.', 'value': '60'}, 'url': {'default': 'http://localhost:8118/ingress/messages', 'type': 'string', 'description': 'URI to accept data', 'value': 'http://localhost:8118/ingress/messages'}, 'sleepInterval': {'default': '5', 'type': 'integer', 'description': 'A period of time, expressed in seconds, to wait between attempts to send readings when there are no readings to be sent.', 'value': '5'}}
    payload = [{'asset_code': 'fogbench/temperature', 'reading': {'ambient': 7, 'object': 28}, 'id': 14,
                'read_key': '31e5ccbb-3e45-4038-95e9-7920834d0852', 'user_ts': '2018-02-26 12:12:54.171949+00'},
               {'asset_code': 'fogbench/wall clock', 'reading': {'tick': 'tock'}, 'id': 20,
                'read_key': '277a6ac9-4351-4807-8cfd-a709d6c346cd', 'user_ts': '2018-02-26 12:12:54.172166+00'}]
    http_north.http_north = HttpNorthPlugin()
    http_north.http_north.event_loop = loop
    with patch.object(http_north.http_north, '_send_payloads', return_value=mock_coro()) as patch_send_payload:
        is_data_sent, new_last_object_id, num_sent = await http_north.plugin_send(data=data, payload=payload, stream_id=3)
        assert (True, 1, 2) == (is_data_sent, new_last_object_id, num_sent)
    args, kwargs = patch_send_payload.call_args
    assert (payload, ) == args


@pytest.allure.feature("unit")
@pytest.allure.story("plugin", "north", "http")
@pytest.mark.asyncio
async def test_plugin_shutdown(loop):
    async def mock_coro():
        return ""

    data = {'applyFilter': {'default': 'False', 'type': 'boolean', 'description': 'Whether to apply filter before processing the data', 'value': 'False'}, 'shutdown_wait_time': {'default': '10', 'type': 'integer', 'description': 'how long (x seconds) the plugin should wait for pending tasks to complete or cancel otherwise', 'value': '10'}, 'sending_process_instance': SendingProcess(), '_CONFIG_CATEGORY_NAME': 'SEND_PR_3', 'enable': {'default': 'True', 'type': 'boolean', 'description': 'A switch that can be used to enable or disable execution of the sending process.', 'value': 'True'}, 'source': {'default': 'readings', 'type': 'string', 'description': 'Defines the source of the data to be sent on the stream, this may be one of either readings, statistics or audit.', 'value': 'readings'}, 'north': {'default': 'omf', 'type': 'string', 'description': 'The name of the north to use to translate the readings into the output format and send them', 'value': 'omf'}, 'stream_id': {'default': '3', 'type': 'integer', 'description': 'Stream ID', 'value': '3'}, 'blockSize': {'default': '5000', 'type': 'integer', 'description': 'The size of a block of readings to send in each transmission.', 'value': '5000'}, 'plugin': {'default': 'http_north', 'type': 'string', 'description': 'HTTP North Plugin', 'value': 'http_north'}, 'filterRule': {'default': '.[]', 'type': 'string', 'description': 'JQ formatted filter to apply (applicable if applyFilter is True)', 'value': '.[]'}, 'duration': {'default': '60', 'type': 'integer', 'description': 'How long the sending process should run (in seconds) before stopping.', 'value': '60'}, 'url': {'default': 'http://localhost:8118/ingress/messages', 'type': 'string', 'description': 'URI to accept data', 'value': 'http://localhost:8118/ingress/messages'}, 'sleepInterval': {'default': '5', 'type': 'integer', 'description': 'A period of time, expressed in seconds, to wait between attempts to send readings when there are no readings to be sent.', 'value': '5'}}
    http_north.http_north = HttpNorthPlugin()
    http_north.http_north.event_loop = loop
    with patch.object(http_north.http_north, 'cancel_tasks', return_value=mock_coro()) as patch_cancel:
        http_north.plugin_shutdown(data)
    assert 1 == patch_cancel.call_count
