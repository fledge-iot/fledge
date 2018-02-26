# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Unit test for foglamp.plugins.south.coap_listen.coap_listen.py"""
import copy
import json
import pytest
import asyncio
import cbor2
import aiocoap.error
from aiocoap import message, numbers
from unittest.mock import call, patch
from foglamp.plugins.south.coap_listen import coap_listen
from foglamp.plugins.south.coap_listen.coap_listen import CoAPIngest, Ingest, _DEFAULT_CONFIG as config

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_NEW_CONFIG = {
    'plugin': {
        'description': 'Python module name of the plugin to load',
        'type': 'string',
        'default': 'coap_listen'
    },
    'port': {
        'description': 'Port to listen on',
        'type': 'integer',
        'default': '1234',
    },
    'uri': {
        'description': 'URI to accept data on',
        'type': 'string',
        'default': 'sensor-values',
    }
}


@pytest.allure.feature("unit")
@pytest.allure.story("plugin", "south", "coap")
def test_plugin_info():
    assert coap_listen.plugin_info() == {
        'name': 'CoAP Server',
        'version': '1.0',
        'mode': 'async',
        'type': 'south',
        'interface': '1.0',
        'config': config
    }


@pytest.allure.feature("unit")
@pytest.allure.story("plugin", "south", "coap")
def test_plugin_init(mocker):
    assert coap_listen.plugin_init(config) == config


@pytest.allure.feature("unit")
@pytest.allure.story("plugin", "south", "coap")
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
    config['uri']['value'] = config['uri']['default']

    log_info = mocker.patch.object(coap_listen._LOGGER, "info")
    assert coap_listen.aiocoap_ctx is None

    # WHEN
    loop.call_soon(coap_listen.plugin_start(config))
    await asyncio.sleep(.5)  # required to allow ensure_future task to complete

    # THEN
    assert coap_listen.aiocoap_ctx is not None
    assert 1 == log_info.call_count
    calls = [
        call('CoAP listener started on port {} with uri {}'.format(config['port']['value'], config['uri']['value']))]
    log_info.assert_has_calls(calls, any_order=True)


@pytest.allure.feature("unit")
@pytest.allure.story("plugin", "south", "coap")
def test_plugin_reconfigure(mocker, unused_port):
    # GIVEN
    port = {
        'description': 'Port to listen on',
        'type': 'integer',
        'default': str(unused_port()),
    }
    mocker.patch.dict(config, {'port': port})
    config['port']['value'] = config['port']['default']
    config['uri']['value'] = config['uri']['default']
    pstop = mocker.patch.object(coap_listen, '_plugin_stop', return_value=True)
    log_info = mocker.patch.object(coap_listen._LOGGER, "info")

    # WHEN
    new_config = coap_listen.plugin_reconfigure(config, _NEW_CONFIG)

    # THEN
    assert _NEW_CONFIG == new_config
    assert new_config["restart"] == "yes"
    assert 2 == log_info.call_count
    assert 1 == pstop.call_count
    # TODO: log_info.assert_called_with('Restarting HTTP_SOUTH plugin due to change in configuration keys [uri, port, host]')


@pytest.allure.feature("unit")
@pytest.allure.story("plugin", "south", "coap")
def test_plugin_reconfigure_else(mocker, unused_port):
    # GIVEN
    port = {
        'description': 'Port to listen on',
        'type': 'integer',
        'default': str(unused_port()),
    }
    mocker.patch.dict(config, {'port': port})
    config['port']['value'] = config['port']['default']
    config['uri']['value'] = config['uri']['default']
    config2 = copy.deepcopy(config)
    pstop = mocker.patch.object(coap_listen, '_plugin_stop', return_value=True)
    log_info = mocker.patch.object(coap_listen._LOGGER, "info")

    # WHEN
    new_config = coap_listen.plugin_reconfigure(config, config2)

    # THEN
    assert new_config["restart"] == "no"
    assert 1 == log_info.call_count
    assert 0 == pstop.call_count


@pytest.allure.feature("unit")
@pytest.allure.story("plugin", "south", "coap")
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
    config['uri']['value'] = config['uri']['default']
    log_exception = mocker.patch.object(coap_listen._LOGGER, "exception")
    log_info = mocker.patch.object(coap_listen._LOGGER, "info")

    # WHEN
    loop.call_soon(coap_listen.plugin_start(config))
    await asyncio.sleep(.5)  # required to allow ensure_future task to complete
    coap_listen._plugin_stop(config)

    # THEN
    assert 2 == log_info.call_count
    calls = [call('CoAP listener started on port {} with uri sensor-values'.format(config['port']['value'])),
             call('Stopping South COAP plugin...')]
    log_info.assert_has_calls(calls, any_order=True)
    assert 0 == log_exception.call_count


@pytest.allure.feature("unit")
@pytest.allure.story("plugin", "south", "coap")
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
    config['uri']['value'] = config['uri']['default']
    log_exception = mocker.patch.object(coap_listen._LOGGER, "exception")
    log_info = mocker.patch.object(coap_listen._LOGGER, "info")

    # WHEN
    loop.call_soon(coap_listen.plugin_start(config))
    await asyncio.sleep(.5)  # required to allow ensure_future task to complete
    coap_listen.plugin_shutdown(config)

    # THEN
    assert 3 == log_info.call_count
    calls = [call('CoAP listener started on port {} with uri sensor-values'.format(config['port']['value'])),
             call('Stopping South COAP plugin...'),
             call('COAP plugin shut down.')]
    log_info.assert_has_calls(calls, any_order=True)
    assert 0 == log_exception.call_count


@pytest.allure.feature("unit")
@pytest.allure.story("services", "south", "ingest")
class TestCoapSouthIngest(object):
    """Unit tests foglamp.plugins.south.coap_listen.coap_listen.CoAPIngest
    """

    @pytest.mark.asyncio
    async def test_render_post_ok(self, loop):
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
                with patch.object(Ingest, 'is_available', return_value=True) as is_ingest_available:
                    request = message.Message(payload=cbor2.dumps(json.loads(data)), code=numbers.codes.Code.POST)
                    r = await CoAPIngest.render_post(request)
                    assert numbers.codes.Code.VALID == r.code
                    assert '' == r.payload.decode()
            assert 0 == ingest_discarded.call_count
            assert 1 == ingest_add_readings.call_count
            assert 1 == is_ingest_available.call_count

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
                with patch.object(Ingest, 'is_available', return_value=True) as is_ingest_available:
                    request = message.Message(payload=cbor2.dumps(json.loads(data)), code=numbers.codes.Code.POST)
                    r = await CoAPIngest.render_post(request)
                    assert numbers.codes.Code.VALID == r.code
                    assert '' == r.payload.decode()
            assert 0 == ingest_discarded.call_count
            assert 1 == ingest_add_readings.call_count
            assert 1 == is_ingest_available.call_count

    @pytest.mark.asyncio
    async def test_render_post_is_available_false(self, loop):
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
        with patch.object(coap_listen._LOGGER, "exception") as log_exception:
            with patch.object(Ingest, 'increment_discarded_readings', return_value=True) as ingest_discarded:
                with patch.object(Ingest, 'is_available', return_value=False) as is_ingest_available:
                    with pytest.raises(aiocoap.error.ConstructionRenderableError) as excinfo:
                        request = message.Message(payload=cbor2.dumps(json.loads(data)), code=numbers.codes.Code.POST)
                        r = await CoAPIngest.render_post(request)
                    assert str(excinfo).endswith('{"busy": true}')
                assert 1 == ingest_discarded.call_count
                assert 1 == is_ingest_available.call_count
                assert 1 == log_exception.call_count

    @pytest.mark.asyncio
    async def test_render_post_reading_not_dict(self, loop):
        data = """{
            "timestamp": "2017-01-02T01:02:03.23232Z-05:00",
            "asset": "sensor2",
            "key": "80a43623-ebe5-40d6-8d80-3f892da9b3b4",
            "readings": "500"
        }"""
        with patch.object(coap_listen._LOGGER, "exception") as log_exception:
            with patch.object(Ingest, 'increment_discarded_readings', return_value=True) as ingest_discarded:
                with patch.object(Ingest, 'is_available', return_value=True) as is_ingest_available:
                    with pytest.raises(aiocoap.error.BadRequest) as excinfo:
                        request = message.Message(payload=cbor2.dumps(json.loads(data)), code=numbers.codes.Code.POST)
                        r = await CoAPIngest.render_post(request)
                    assert str(excinfo).endswith('readings must be a dictionary')
                assert 1 == ingest_discarded.call_count
                assert 1 == is_ingest_available.call_count
                assert 1 == log_exception.call_count
