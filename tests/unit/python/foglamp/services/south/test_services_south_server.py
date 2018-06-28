# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import asyncio
import copy
import sys
from unittest.mock import MagicMock, Mock, call, patch
import pytest

from foglamp.services.south import server as South
from foglamp.services.south.server import Server
from foglamp.common.storage_client.storage_client import StorageClientAsync
from foglamp.services.common.microservice import FoglampMicroservice
from foglamp.services.south.ingest import Ingest

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_TEST_CONFIG = {
    'plugin': {
        'description': 'Python module name of the plugin to load',
        'type': 'string',
        'default': 'test'
    }
}
plugin_attrs = {
    'plugin_info.return_value': {
        'name': 'CoAP Server',
        'version': '1.0',
        'mode': 'async',
        'type': 'south',
        'interface': '1.0',
        'config': {
            'plugin': {
                'description': 'Python module name of the plugin to load',
                'type': 'string',
                'default': 'test',
                'value': 'test',
            },
            'port': {
                'description': 'Port to listen on',
                'type': 'integer',
                'default': '5683',
                'value': '5683',
            },
            'uri': {
                'description': 'URI to accept data on',
                'type': 'string',
                'default': 'sensor-values',
                'value': 'sensor-values',
            }
        }
    },
    'plugin_init.return_value': {
        'config': {
            'plugin': {
                'description': 'Python module name of the plugin to load',
                'type': 'string',
                'default': 'test',
                'value': 'test',
            },
            'port': {
                'description': 'Port to listen on',
                'type': 'integer',
                'default': '5683',
                'value': '5683',
            },
            'uri': {
                'description': 'URI to accept data on',
                'type': 'string',
                'default': 'sensor-values',
                'value': 'sensor-values',
            }
        }
    },
    'plugin_start.return_value': "",
    # We are forcing RuntimeError as poll plugin runs an infinite loop and as such this will tested indirectly
    'plugin_poll.side_effect': RuntimeError,
    'plugin_shutdown.return_value': "",
    'plugin_reconfigure.return_value': {"restart": "yes"}
}


@asyncio.coroutine
def mock_coro():
    yield from false_coro()


async def false_coro():
    return True


@pytest.allure.feature("unit")
@pytest.allure.story("south")
class TestServicesSouthServer:
    def south_fixture(self, mocker):
        def cat_get():
            config = _TEST_CONFIG
            config['plugin']['value'] = config['plugin']['default']
            return config

        mocker.patch.object(FoglampMicroservice, "__init__", return_value=None)

        south_server = Server()
        south_server._storage = MagicMock(spec=StorageClientAsync)

        attrs = {
                    'create_configuration_category.return_value': None,
                    'get_configuration_category.return_value': cat_get(),
                    'register_interest.return_value': {'id': 1234, 'message': 'all ok'}
        }
        south_server._core_microservice_management_client = Mock()
        south_server._core_microservice_management_client.configure_mock(**attrs)

        mocker.patch.object(south_server, '_name', 'test')

        ingest_start = mocker.patch.object(Ingest, 'start', return_value=mock_coro())
        log_exception = mocker.patch.object(South._LOGGER, "exception")
        log_info = mocker.patch.object(South._LOGGER, "info")

        return cat_get, south_server, ingest_start, log_exception, log_info

    @pytest.mark.asyncio
    async def test__start_async_plugin(self, mocker, loop):
        # GIVEN
        cat_get, south_server, ingest_start, log_exception, log_info = self.south_fixture(mocker)
        mock_plugin = MagicMock()
        attrs = copy.deepcopy(plugin_attrs)
        attrs['plugin_info.return_value']['mode'] = 'async'
        mock_plugin.configure_mock(**attrs)
        sys.modules['foglamp.plugins.south.test.test'] = mock_plugin

        # WHEN
        await south_server._start(loop)
        await asyncio.sleep(.5)

        # THEN
        assert 1 == ingest_start.call_count
        ingest_start.assert_called_with(south_server)
        assert 1 == log_info.call_count
        assert 0 == log_exception.call_count
        assert south_server._task_main.done() is True

    @pytest.mark.asyncio
    async def test__start_async_plugin_bad_plugin_value(self, mocker, loop):
        # GIVEN
        mocker.patch.object(FoglampMicroservice, "__init__", return_value=None)

        south_server = Server()
        south_server._storage = MagicMock(spec=StorageClientAsync)

        mocker.patch.object(south_server, '_name', 'test')
        mocker.patch.object(south_server, '_stop', return_value=mock_coro())

        log_exception = mocker.patch.object(South._LOGGER, "exception")

        # WHEN
        await south_server._start(loop)
        await asyncio.sleep(.5)

        # THEN
        log_exception.assert_called_with('Failed to initialize plugin {}'.format(south_server._name))

    @pytest.mark.asyncio
    async def test__start_async_plugin_bad_plugin_name(self, mocker, loop):
        # GIVEN
        cat_get, south_server, ingest_start, log_exception, log_info = self.south_fixture(mocker)
        mocker.patch.object(south_server, '_stop', return_value=mock_coro())
        sys.modules['foglamp.plugins.south.test.test'] = None

        # WHEN
        with patch.object(South._LOGGER, 'error') as log_error:
            await south_server._start(loop)
            await asyncio.sleep(.5)
        assert 1 == log_error.call_count
        log_error.assert_called_once_with('Unable to load module |{}| for device plugin |{}| - error details |{}|'
                                          .format(south_server._name, south_server._name, south_server._name))

        # THEN
        assert 1 == log_exception.call_count
        log_exception.assert_called_with('Failed to initialize plugin {}'.format(south_server._name))

    @pytest.mark.asyncio
    async def test__start_async_plugin_bad_plugin_type(self, mocker, loop):
        # GIVEN
        cat_get, south_server, ingest_start, log_exception, log_info = self.south_fixture(mocker)
        mocker.patch.object(south_server, '_stop', return_value=mock_coro())
        mock_plugin = MagicMock()
        attrs = copy.deepcopy(plugin_attrs)
        attrs['plugin_info.return_value']['mode'] = 'async'
        attrs['plugin_info.return_value']['type'] = 'bad'
        mock_plugin.configure_mock(**attrs)
        sys.modules['foglamp.plugins.south.test.test'] = mock_plugin

        # WHEN
        with patch.object(South._LOGGER, 'error') as log_error:
            await south_server._start(loop)
            await asyncio.sleep(.5)
        assert 1 == log_error.call_count
        log_error.assert_called_once_with('cannot proceed the execution, only the type -south- is allowed'
                                          ' - plugin name |{}| plugin type |bad|'.format(south_server._name))

        # THEN
        log_exception.assert_called_with('Failed to initialize plugin {}'.format(south_server._name))

    @pytest.mark.asyncio
    async def test__start_poll_plugin(self, loop, mocker):
        # GIVEN
        cat_get, south_server, ingest_start, log_exception, log_info = self.south_fixture(mocker)
        # Mocking _stop() required as we are testing poll_plugin indirectly
        mocker.patch.object(south_server, '_stop', return_value=mock_coro())
        mock_plugin = MagicMock()
        attrs = copy.deepcopy(plugin_attrs)
        attrs['plugin_info.return_value']['mode'] = 'poll'
        mock_plugin.configure_mock(**attrs)
        sys.modules['foglamp.plugins.south.test.test'] = mock_plugin

        # WHEN
        South._MAX_RETRY_POLL = 1
        await south_server._start(loop)
        await asyncio.sleep(.5)

        # THEN
        assert 1 == ingest_start.call_count
        ingest_start.assert_called_with(south_server)
        assert 1 == log_info.call_count
        assert 1 == log_exception.call_count
        assert south_server._task_main.done() is False  # because of exception occurred

    @pytest.mark.asyncio
    async def test__exec_plugin_async(self, loop, mocker):
        # GIVEN
        cat_get, south_server, ingest_start, log_exception, log_info = self.south_fixture(mocker)
        mock_plugin = MagicMock()
        attrs = copy.deepcopy(plugin_attrs)
        attrs['plugin_info.return_value']['mode'] = 'async'
        mock_plugin.configure_mock(**attrs)
        sys.modules['foglamp.plugins.south.test.test'] = mock_plugin

        # WHEN
        # We need to run _start() in order to initialize self._plugin
        await south_server._start(loop)
        await asyncio.sleep(.5)

        # This line is redundant as it has already been executed above
        await south_server._exec_plugin_async()

        # THEN
        assert 2 == log_info.call_count
        log_info.assert_called_with('Started South Plugin: {}'.format(south_server._name))

    @pytest.mark.asyncio
    async def test__exec_plugin_poll(self, loop, mocker):
        # GIVEN
        cat_get, south_server, ingest_start, log_exception, log_info = self.south_fixture(mocker)
        # Mocking _stop() required as we are testing poll_plugin indirectly
        mocker.patch.object(south_server, '_stop', return_value=mock_coro())
        mock_plugin = MagicMock()
        attrs = copy.deepcopy(plugin_attrs)
        attrs['plugin_info.return_value']['mode'] = 'poll'
        mock_plugin.configure_mock(**attrs)
        sys.modules['foglamp.plugins.south.test.test'] = mock_plugin

        # WHEN
        # We need to run _start() in order to initialize self._plugin
        South._MAX_RETRY_POLL = 1
        South._TIME_TO_WAIT_BEFORE_RETRY = .1
        await south_server._start(loop)
        await asyncio.sleep(.5)

        # This line is redundant as it has already been executed above
        await south_server._exec_plugin_poll()

        # THEN
        assert 2 == log_info.call_count
        log_info.assert_called_with('Started South Plugin: {}'.format(south_server._name))

    @pytest.mark.asyncio
    async def test__exec_plugin_poll_exceed_retries(self, loop, mocker):
        # GIVEN
        cat_get, south_server, ingest_start, log_exception, log_info = self.south_fixture(mocker)
        mocker.patch.object(south_server, '_stop', return_value=mock_coro())
        mock_plugin = MagicMock()
        attrs = copy.deepcopy(plugin_attrs)
        attrs['plugin_info.return_value']['mode'] = 'poll'
        mock_plugin.configure_mock(**attrs)
        sys.modules['foglamp.plugins.south.test.test'] = mock_plugin

        # WHEN
        # We need to run _start() in order to initialize self._plugin
        South._MAX_RETRY_POLL = 1
        South._TIME_TO_WAIT_BEFORE_RETRY = .1
        await south_server._start(loop)
        await asyncio.sleep(.5)
        await south_server._exec_plugin_poll()

        # THEN
        # Count is 2 and 4 because above method is executed twice
        assert 2 == log_info.call_count
        assert 4 == log_exception.call_count
        calls = [call('Max retries exhausted in starting South plugin: test'),
                 call('Failed to poll for plugin test, retry count: 2'),
                 call('Max retries exhausted in starting South plugin: test'),
                 call('Failed to poll for plugin test, retry count: 2')]
        log_exception.assert_has_calls(calls, any_order=True)

    @pytest.mark.asyncio
    async def test_run(self, mocker):
        """Not fit for Unit test"""
        pass

    @pytest.mark.asyncio
    async def test__stop(self, loop, mocker):
        # GIVEN
        cat_get, south_server, ingest_start, log_exception, log_info = self.south_fixture(mocker)
        mocker.patch.object(Ingest, 'stop', return_value=mock_coro())
        mock_plugin = MagicMock()
        attrs = copy.deepcopy(plugin_attrs)
        attrs['plugin_info.return_value']['mode'] = 'async'
        mock_plugin.configure_mock(**attrs)
        sys.modules['foglamp.plugins.south.test.test'] = mock_plugin

        # WHEN
        # We need to initialize and start plugin in order to stop it
        await south_server._start(loop)
        await asyncio.sleep(.1)
        South._CLEAR_PENDING_TASKS_TIMEOUT = 1
        await south_server._stop(loop)

        # THEN
        assert 3 == log_info.call_count
        calls = [call('Started South Plugin: {}'.format(south_server._name)),
                 call('Stopped the Ingest server.'),
                 call('Stopping South service event loop, for plugin test.')]
        log_info.assert_has_calls(calls, any_order=True)
        assert 0 == log_exception.call_count

    @pytest.mark.asyncio
    async def test__stop_plugin_stop_error(self, loop, mocker):
        # GIVEN
        cat_get, south_server, ingest_start, log_exception, log_info = self.south_fixture(mocker)
        mocker.patch.object(Ingest, 'stop', return_value=mock_coro())
        mock_plugin = MagicMock()
        attrs = copy.deepcopy(plugin_attrs)
        attrs['plugin_info.return_value']['mode'] = 'async'
        attrs['plugin_shutdown.side_effect'] = RuntimeError
        mock_plugin.configure_mock(**attrs)
        sys.modules['foglamp.plugins.south.test.test'] = mock_plugin

        # WHEN
        # We need to initialize and start plugin in order to stop it
        await south_server._start(loop)
        await asyncio.sleep(.5)
        South._CLEAR_PENDING_TASKS_TIMEOUT = 1
        await south_server._stop(loop)

        # THEN
        assert 3 == log_info.call_count
        calls = [call('Started South Plugin: {}'.format(south_server._name)),
                 call('Stopped the Ingest server.'),
                 call('Stopping South service event loop, for plugin test.')]
        log_info.assert_has_calls(calls, any_order=True)
        assert 1 == log_exception.call_count

    @pytest.mark.asyncio
    async def test_shutdown(self, loop, mocker):
        # GIVEN
        cat_get, south_server, ingest_start, log_exception, log_info = self.south_fixture(mocker)
        mocker.patch.object(south_server, '_stop', return_value=mock_coro())
        mocker.patch.object(south_server, 'unregister_service_with_core', return_value=True)

        # WHEN
        await south_server.shutdown(request=None)

        # THEN
        assert 1 == log_info.call_count
        log_info.assert_called_with('Stopping South Service plugin {}'.format(south_server._name))

    @pytest.mark.asyncio
    async def test_shutdown_error(self, loop, mocker):
        # GIVEN
        cat_get, south_server, ingest_start, log_exception, log_info = self.south_fixture(mocker)
        mocker.patch.object(south_server, '_stop', return_value=mock_coro(), side_effect=RuntimeError)
        mocker.patch.object(south_server, 'unregister_service_with_core', return_value=True)

        # WHEN
        from aiohttp.web_exceptions import HTTPInternalServerError
        with pytest.raises(HTTPInternalServerError):
            await south_server.shutdown(request=None)

        # THEN
        assert 1 == log_info.call_count
        log_info.assert_called_with('Stopping South Service plugin {}'.format(south_server._name))
        assert 1 == log_exception.call_count
        log_exception.assert_called_with('Error in stopping South Service plugin {}, '.format(south_server._name))

    @pytest.mark.asyncio
    async def test_change(self, loop, mocker):
        # GIVEN
        cat_get, south_server, ingest_start, log_exception, log_info = self.south_fixture(mocker)
        mock_plugin = MagicMock()
        attrs = copy.deepcopy(plugin_attrs)
        attrs['plugin_info.return_value']['mode'] = 'async'
        mock_plugin.configure_mock(**attrs)
        sys.modules['foglamp.plugins.south.test.test'] = mock_plugin

        # WHEN
        await south_server._start(loop)
        await asyncio.sleep(.5)
        await south_server.change(request=None)

        # THEN
        assert 4 == log_info.call_count
        calls = [call('Started South Plugin: test'),
                 call('Configuration has changed for South plugin test'),
                 call('Reconfiguration done for South plugin test'),
                 call('Started South Plugin: test')]
        log_info.assert_has_calls(calls, any_order=True)

    @pytest.mark.asyncio
    async def test_change_error(self, loop, mocker):
        # GIVEN
        from foglamp.services.south import exceptions
        cat_get, south_server, ingest_start, log_exception, log_info = self.south_fixture(mocker)
        mock_plugin = MagicMock()
        attrs = copy.deepcopy(plugin_attrs)
        attrs['plugin_info.return_value']['mode'] = 'async'
        attrs['plugin_reconfigure.side_effect'] = exceptions.DataRetrievalError
        mock_plugin.configure_mock(**attrs)
        sys.modules['foglamp.plugins.south.test.test'] = mock_plugin

        # WHEN
        with pytest.raises(TypeError):
            await south_server._start(loop)
            await asyncio.sleep(.5)
            await south_server.change(request=None)

        # THEN
        assert 2 == log_info.call_count
        calls = [call('Started South Plugin: test'),
                 call('Configuration has changed for South plugin test')]
        log_info.assert_has_calls(calls, any_order=True)

        assert 1 == log_exception.call_count
        calls = [call('Data retrieval error in plugin test during reconfigure')]
        log_exception.assert_has_calls(calls, any_order=True)

