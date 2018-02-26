# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Unit test for foglamp.plugins.south.http_south.http_south"""
import copy
import json
import asyncio
from unittest import mock
from unittest.mock import call, patch
import pytest
import aiohttp.web_exceptions
from aiohttp.test_utils import make_mocked_request
from aiohttp.streams import StreamReader
from multidict import CIMultiDict
from foglamp.plugins.south.http_south import http_south
from foglamp.plugins.south.http_south.http_south import HttpSouthIngest, Ingest, _DEFAULT_CONFIG as config

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_CONFIG_CATEGORY_NAME = 'HTTP_SOUTH'
_CONFIG_CATEGORY_DESCRIPTION = 'South Plugin HTTP Listener'
_NEW_CONFIG = {
    'plugin': {
        'description': 'South Plugin HTTP Listener',
        'type': 'string',
        'default': 'http_south'
    },
    'port': {
        'description': 'Port to listen on',
        'type': 'integer',
        'default': '1234',
    },
    'host': {
        'description': 'Address to accept data on',
        'type': 'string',
        'default': 'localhost',
    },
    'uri': {
        'description': 'URI to accept data on',
        'type': 'string',
        'default': 'sensor-reading',
    }
}


def mock_request(data, loop):
    payload = StreamReader(loop=loop)
    payload.feed_data(data.encode())
    payload.feed_eof()

    protocol = mock.Mock()
    app = mock.Mock()
    headers = CIMultiDict([('CONTENT-TYPE', 'application/json')])
    req = make_mocked_request('POST', '/sensor-reading', headers=headers,
                              protocol=protocol, payload=payload, app=app)
    return req


@pytest.allure.feature("unit")
@pytest.allure.story("plugin", "south", "http")
def test_plugin_info():
    assert http_south.plugin_info() == {
        'name': 'http_south',
        'version': '1.0',
        'mode': 'async',
        'type': 'south',
        'interface': '1.0',
        'config': config
    }


@pytest.allure.feature("unit")
@pytest.allure.story("plugin", "south", "http")
def test_plugin_init():
    assert http_south.plugin_init(config) == config


@pytest.allure.feature("unit")
@pytest.allure.story("plugin", "south", "http")
@pytest.mark.asyncio
async def test_plugin_start(mocker, unused_port, loop):
    # GIVEN
    port = {
        'description': 'Port to listen on',
        'type': 'integer',
        'default': str(unused_port()),
    }
    mocker.patch.dict(config, {'port': port})
    config['port']['value'] = config['port']['default']
    config['host']['value'] = config['host']['default']
    config['uri']['value'] = config['uri']['default']

    # WHEN
    loop.call_soon(http_south.plugin_start(config))
    await asyncio.sleep(.33)  # Allow ensure_future task to complete

    # THEN
    assert isinstance(config['app'], aiohttp.web.Application)
    assert isinstance(config['handler'], aiohttp.web_server.Server)
    assert isinstance(config['server'], asyncio.base_events.Server)


@pytest.allure.feature("unit")
@pytest.allure.story("plugin", "south", "http")
@pytest.mark.asyncio
async def test_plugin_start_exception(unused_port, mocker, loop):
    # GIVEN
    port = {
        'description': 'Port to listen on',
        'type': 'integer',
        'default': str(unused_port()),
    }
    mocker.patch.dict(config, {'port': port})
    log_exception = mocker.patch.object(http_south._LOGGER, "exception")

    # WHEN
    loop.call_soon(http_south.plugin_start(config))
    await asyncio.sleep(.33)  # Allow ensure_future task to complete

    # THEN
    assert 1 == log_exception.call_count
    log_exception.assert_called_with("'value'")


@pytest.allure.feature("unit")
@pytest.allure.story("plugin", "south", "http")
def test_plugin_reconfigure(mocker, unused_port):
    # GIVEN
    port = {
        'description': 'Port to listen on',
        'type': 'integer',
        'default': str(unused_port()),
    }
    mocker.patch.dict(config, {'port': port})
    config['port']['value'] = config['port']['default']
    config['host']['value'] = config['host']['default']
    config['uri']['value'] = config['uri']['default']
    pstop = mocker.patch.object(http_south, '_plugin_stop', return_value=True)
    log_info = mocker.patch.object(http_south._LOGGER, "info")

    # WHEN
    new_config = http_south.plugin_reconfigure(config, _NEW_CONFIG)

    # THEN
    assert _NEW_CONFIG == new_config
    assert "yes" == new_config["restart"]
    assert 2 == log_info.call_count
    assert 1 == pstop.call_count
    # TODO: log_info.assert_called_with('Restarting HTTP_SOUTH plugin due to change in configuration keys [uri, port, host]')


@pytest.allure.feature("unit")
@pytest.allure.story("plugin", "south", "http")
def test_plugin_reconfigure_else(mocker, unused_port):
    # GIVEN
    port = {
        'description': 'Port to listen on',
        'type': 'integer',
        'default': str(unused_port()),
    }
    mocker.patch.dict(config, {'port': port})
    config['port']['value'] = config['port']['default']
    config['host']['value'] = config['host']['default']
    config['uri']['value'] = config['uri']['default']
    config2 = copy.deepcopy(config)
    pstop = mocker.patch.object(http_south, '_plugin_stop', return_value=True)

    # WHEN
    new_config = http_south.plugin_reconfigure(config, config2)

    # THEN
    assert 0 == pstop.call_count
    assert "no" == new_config["restart"]


@pytest.allure.feature("unit")
@pytest.allure.story("plugin", "south", "http")
@pytest.mark.asyncio
async def test_plugin__stop(mocker, unused_port, loop):
    # GIVEN
    port = {
        'description': 'Port to listen on',
        'type': 'integer',
        'default': str(unused_port()),
    }
    mocker.patch.dict(config, {'port': port})
    config['port']['value'] = config['port']['default']
    config['host']['value'] = config['host']['default']
    config['uri']['value'] = config['uri']['default']
    log_exception = mocker.patch.object(http_south._LOGGER, "exception")
    log_info = mocker.patch.object(http_south._LOGGER, "info")

    # WHEN
    loop.call_soon(http_south.plugin_start(config))
    await asyncio.sleep(.33)  # Allow ensure_future task to complete
    http_south._plugin_stop(config)

    # THEN
    assert 1 == log_info.call_count
    calls = [call('Stopping South HTTP plugin.')]
    log_info.assert_has_calls(calls, any_order=True)
    assert 0 == log_exception.call_count


@pytest.allure.feature("unit")
@pytest.allure.story("plugin", "south", "http")
@pytest.mark.asyncio
async def test_plugin_shutdown(mocker, unused_port, loop):
    # GIVEN
    port = {
        'description': 'Port to listen on',
        'type': 'integer',
        'default': str(unused_port()),
    }
    mocker.patch.dict(config, {'port': port})
    config['port']['value'] = config['port']['default']
    config['host']['value'] = config['host']['default']
    config['uri']['value'] = config['uri']['default']
    log_exception = mocker.patch.object(http_south._LOGGER, "exception")
    log_info = mocker.patch.object(http_south._LOGGER, "info")

    # WHEN
    loop.call_soon(http_south.plugin_start(config))
    await asyncio.sleep(.33)  # Allow ensure_future task to complete
    http_south.plugin_shutdown(config)

    # THEN
    assert 2 == log_info.call_count
    calls = [call('Stopping South HTTP plugin.'),
             call('South HTTP plugin shut down.')]
    log_info.assert_has_calls(calls, any_order=True)
    assert 0 == log_exception.call_count


@pytest.allure.feature("unit")
@pytest.allure.story("plugin", "south", "http")
@pytest.mark.asyncio
async def test_plugin_shutdown_error(mocker, unused_port, loop):
    # GIVEN
    port = {
        'description': 'Port to listen on',
        'type': 'integer',
        'default': str(unused_port()),
    }
    mocker.patch.dict(config, {'port': port})
    config['port']['value'] = config['port']['default']
    config['host']['value'] = config['host']['default']
    config['uri']['value'] = config['uri']['default']
    log_exception = mocker.patch.object(http_south._LOGGER, "exception")
    log_info = mocker.patch.object(http_south._LOGGER, "info")

    # WHEN
    loop.call_soon(http_south.plugin_start(config))
    await asyncio.sleep(.33)  # Allow ensure_future task to complete
    server = config['server']
    mocker.patch.object(server, 'wait_closed', side_effect=Exception)
    with pytest.raises(Exception):
        http_south.plugin_shutdown(config)

    # THEN
    assert 1 == log_info.call_count
    calls = [call('Stopping South HTTP plugin.')]
    log_info.assert_has_calls(calls, any_order=True)
    assert 1 == log_exception.call_count


@pytest.allure.feature("unit")
@pytest.allure.story("services", "south", "ingest")
class TestHttpSouthIngest(object):
    """Unit tests foglamp.plugins.south.http_south.http_south.HttpSouthIngest
    """
    @pytest.mark.asyncio
    async def test_render_post_reading_ok(self, loop):
        data = """{
            "timestamp": "2017-01-02T01:02:03.23232Z-05:00",
            "asset": "sensor1",
            "key": "80a43623-ebe5-40d6-8d80-3f892da9b3b4",
            "readings": {
                "velocity": "500",
                "temperature": {
                    "value": "32",
                    "unit": "kelvin"
                }
            }
        }"""
        with patch.object(Ingest, 'increment_discarded_readings', return_value=True) as ingest_discarded:
            with patch.object(Ingest, 'add_readings', return_value=asyncio.sleep(.1)) as ingest_add_readings:
                with patch.object(Ingest, 'is_available', return_value=True) as ingest_is_available:
                    request = mock_request(data, loop)
                    r = await HttpSouthIngest.render_post(request)
                    retval = json.loads(r.body.decode())
                    # Assert the POST request response
                    assert 200 == r.status
                    assert 'success' == retval['result']
            assert 0 == ingest_discarded.call_count
            assert 1 == ingest_add_readings.call_count
            assert 1 == ingest_is_available.call_count

    @pytest.mark.asyncio
    async def test_render_post_sensor_values_ok(self, loop):
        data = """{
            "timestamp": "2017-01-02T01:02:03.23232Z-05:00",
            "asset": "sensor1",
            "key": "80a43623-ebe5-40d6-8d80-3f892da9b3b4",
            "sensor_values": {
                "velocity": "500",
                "temperature": {
                    "value": "32",
                    "unit": "kelvin"
                }
            }
        }"""
        with patch.object(Ingest, 'increment_discarded_readings', return_value=True) as ingest_discarded:
            with patch.object(Ingest, 'add_readings', return_value=asyncio.sleep(.1)) as ingest_add_readings:
                with patch.object(Ingest, 'is_available', return_value=True) as ingest_is_available:
                    request = mock_request(data, loop)
                    r = await HttpSouthIngest.render_post(request)
                    retval = json.loads(r.body.decode())
                    # Assert the POST request response
                    assert 200 == r.status
                    assert 'success' == retval['result']
            assert 0 == ingest_discarded.call_count
            assert 1 == ingest_add_readings.call_count
            assert 1 == ingest_is_available.call_count

    @pytest.mark.asyncio
    async def test_render_post_payload_not_dict(self, loop):
        data = "blah"
        with patch.object(Ingest, 'increment_discarded_readings', return_value=True) as ingest_discarded:
            with patch.object(Ingest, 'is_available', return_value=True) as ingest_is_available:
                with pytest.raises(aiohttp.web_exceptions.HTTPBadRequest) as ex:
                    request = mock_request(data, loop)
                    r = await HttpSouthIngest.render_post(request)
                    assert 400 == r.status
                assert str(ex).endswith('Payload must be a dictionary')
            assert 1 == ingest_discarded.call_count
            assert 1 == ingest_is_available.call_count

    @pytest.mark.asyncio
    async def test_render_post_reading_is_available_false(self, loop):
        data = """{
            "timestamp": "2017-01-02T01:02:03.23232Z-05:00",
            "asset": "sensor1",
            "key": "80a43623-ebe5-40d6-8d80-3f892da9b3b4",
            "readings": {
                "velocity": "500",
                "temperature": {
                    "value": "32",
                    "unit": "kelvin"
                }
            }
        }"""
        with patch.object(Ingest, 'increment_discarded_readings', return_value=True) as ingest_discarded:
            with patch.object(Ingest, 'is_available', return_value=False) as ingest_is_available:
                with pytest.raises(aiohttp.web_exceptions.HTTPInternalServerError) as ex:
                    request = mock_request(data, loop)
                    r = await HttpSouthIngest.render_post(request)
                    assert 400 == r.status
                assert str(ex).endswith("{'busy': True}")
            assert 1 == ingest_discarded.call_count
            assert 1 == ingest_is_available.call_count

    @pytest.mark.asyncio
    async def test_render_post_reading_missing_delimiter(self, loop):
        data = """{
            "timestamp": "2017-01-02T01:02:03.23232Z-05:00",
            "asset": "sensor1",
            "key": "80a43623-ebe5-40d6-8d80-3f892da9b3b4",
            "readings": {
                "velocity": "500",
                "temperature": {
                    "value": "32",
                    "unit": "kelvin"
                }
        }"""
        with patch.object(Ingest, 'increment_discarded_readings', return_value=True) as ingest_discarded:
            with patch.object(Ingest, 'is_available', return_value=True) as ingest_is_available:
                with pytest.raises(aiohttp.web_exceptions.HTTPBadRequest) as ex:
                    request = mock_request(data, loop)
                    r = await HttpSouthIngest.render_post(request)
                    assert 400 == r.status
                assert str(ex).endswith('Payload must be a dictionary')
            assert 1 == ingest_discarded.call_count
            assert 1 == ingest_is_available.call_count

    @pytest.mark.asyncio
    async def test_render_post_reading_not_dict(self, loop):
        data = """{
            "timestamp": "2017-01-02T01:02:03.23232Z-05:00",
            "asset": "sensor2",
            "key": "80a43623-ebe5-40d6-8d80-3f892da9b3b4",
            "readings": "500"
        }"""
        with patch.object(Ingest, 'increment_discarded_readings', return_value=True) as ingest_discarded:
            with patch.object(Ingest, 'is_available', return_value=True) as ingest_is_available:
                with pytest.raises(aiohttp.web_exceptions.HTTPBadRequest) as ex:
                    request = mock_request(data, loop)
                    r = await HttpSouthIngest.render_post(request)
                    assert 400 == r.status
                assert str(ex).endswith("readings must be a dictionary")
            assert 1 == ingest_discarded.call_count
            assert 1 == ingest_is_available.call_count
