# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from unittest.mock import patch
import pytest

from foglamp.tasks.north.sending_process import SendingProcess
from foglamp.plugins.north.http_north import http_north
from foglamp.plugins.north.http_north.http_north import HttpNorthPlugin

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


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
        is_data_sent, new_last_object_id, num_sent = http_north.plugin_send(data=data, payload=payload, stream_id=3)
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
