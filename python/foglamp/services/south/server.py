# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""FogLAMP South Microservice"""

import json
import asyncio
from foglamp.services.south import exceptions
from foglamp.common import logger
from foglamp.services.south.ingest import Ingest
from foglamp.services.common.microservice import FoglampMicroservice
from aiohttp import web

__author__ = "Terris Linenbach, Amarendra K Sinha, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_LOGGER = logger.setup(__name__)
_MAX_RETRY_POLL = 3
_TIME_TO_WAIT_BEFORE_RETRY = 2
_CLEAR_PENDING_TASKS_TIMEOUT = 5


class Server(FoglampMicroservice):
    """" Implements the South Microservice """

    _DEFAULT_CONFIG = {}  # South Server configuration which will get updated with process configuration from DB.

    _PLUGIN_MODULE_PATH = "foglamp.plugins.south"

    _MESSAGES_LIST = {
        # Information messages
        "i000000": "",
        # Warning / Error messages
        "e000000": "generic error.",
        "e000001": "cannot proceed the execution, only the type -south- is allowed "
                   "- plugin name |{0}| plugin type |{1}|",
        "e000002": "Unable to obtain configuration of module for plugin |{0}|",
        "e000003": "Unable to load module |{0}| for South plugin |{1}| - error details |{0}|",
        "e000004": "Unable to create south configuration category"
    }
    """ Messages used for Information, Warning and Error notice """

    _plugin = None
    """The plugin's module'"""

    _plugin_info = None
    """The plugin's info'"""

    _plugin_handle = None
    """The value that is returned by the plugin_init"""

    _type = "Southbound"

    _task_main = None

    def __init__(self):
        super().__init__()

    async def _start(self, loop) -> None:
        error = None
        try:
            # Configuration handling - initial configuration
            category = self._name
            config = self._DEFAULT_CONFIG
            config_descr = self._name
            config_payload = json.dumps({
                "key": category,
                "description": config_descr,
                "value": config,
                "keep_original_items": True
            })
            self._core_microservice_management_client.create_configuration_category(config_payload)
            config = self._core_microservice_management_client.get_configuration_category(category_name=category)

            try:
                plugin_module_name = config['plugin']['value']
            except KeyError:
                message = self._MESSAGES_LIST['e000002'].format(self._name)
                _LOGGER.error(message)
                raise

            try:
                import_file_name = "{path}.{dir}.{file}".format(path=self._PLUGIN_MODULE_PATH,
                                                                dir=plugin_module_name,
                                                                file=plugin_module_name)
                self._plugin = __import__(import_file_name, fromlist=[''])
            except Exception as ex:
                message = self._MESSAGES_LIST['e000003'].format(plugin_module_name, self._name, str(ex))
                _LOGGER.error(message)
                raise
            # Create the parent category for all south service
            try:
                parent_payload = json.dumps({"key": "South", "description": "South microservices", "value": {},
                                             "children": [self._name], "keep_original_items": True})
                self._core_microservice_management_client.create_configuration_category(parent_payload)
            except KeyError:
                message = self._MESSAGES_LIST['e000004'].format(self._name)
                _LOGGER.error(message)
                raise

            # Plugin initialization
            self._plugin_info = self._plugin.plugin_info()
            default_config = self._plugin_info['config']
            default_plugin_descr = self._name if (default_config['plugin']['description']).strip() == "" else \
                default_config['plugin']['description']

            # Configuration handling - updates the configuration using information specific to the plugin
            config_payload = json.dumps({
                "key": category,
                "description": default_plugin_descr,
                "value": default_config,
                "keep_original_items": True
            })
            self._core_microservice_management_client.create_configuration_category(config_payload)
            config = self._core_microservice_management_client.get_configuration_category(category_name=category)

            # Register interest with category and microservice_id
            result = self._core_microservice_management_client.register_interest(category, self._microservice_id)

            # KeyError when result (id and message) keys are not found
            registration_id = result['id']
            message = result['message']

            # Ensures the plugin type is the correct one - 'south'
            if self._plugin_info['type'] != 'south':
                message = self._MESSAGES_LIST['e000001'].format(self._name, self._plugin_info['type'])
                _LOGGER.error(message)
                raise exceptions.InvalidPluginTypeError()

            self._plugin_handle = self._plugin.plugin_init(config)

            await Ingest.start(self)

            # Executes the requested plugin type
            if self._plugin_info['mode'] == 'async':
                self._task_main = asyncio.ensure_future(self._exec_plugin_async())
            elif self._plugin_info['mode'] == 'poll':
                self._task_main = asyncio.ensure_future(self._exec_plugin_poll())
        except asyncio.CancelledError:
            pass
        except exceptions.DataRetrievalError:
            _LOGGER.exception('Data retrieval error in plugin {}'.format(self._name))
        except (Exception, KeyError) as ex:
            if error is None:
                error = 'Failed to initialize plugin {}'.format(self._name)
            _LOGGER.exception(error)
            asyncio.ensure_future(self._stop(loop))

    async def _exec_plugin_async(self) -> None:
        """Executes async type plugin
        """
        _LOGGER.info('Started South Plugin: {}'.format(self._name))
        self._plugin.plugin_start(self._plugin_handle)

    async def _exec_plugin_poll(self) -> None:
        """Executes poll type plugin
        """
        _LOGGER.info('Started South Plugin: {}'.format(self._name))
        try_count = 1
        while self._plugin and try_count <= _MAX_RETRY_POLL:
            try:
                data = self._plugin.plugin_poll(self._plugin_handle)
                if len(data) > 0:
                    if isinstance(data, list):
                        for reading in data:
                            asyncio.ensure_future(Ingest.add_readings(asset=reading['asset'],
                                                                        timestamp=reading['timestamp'],
                                                                        key=reading['key'],
                                                                        readings=reading['readings']))
                    elif isinstance(data, dict):
                        asyncio.ensure_future(Ingest.add_readings(asset=data['asset'],
                                                                  timestamp=data['timestamp'],
                                                                  key=data['key'],
                                                                  readings=data['readings']))
                # pollInterval is expressed in milliseconds
                sleep_seconds = int(self._plugin_handle['pollInterval']['value']) / 1000.0
                await asyncio.sleep(sleep_seconds)
                # If successful, then set retry count back to 1, meaning that
                # only in case of 3 successive failures, exit.
                try_count = 1
            except KeyError as ex:
                _LOGGER.exception('Key error plugin {} : {}'.format(self._name, str(ex)))
            except (Exception, RuntimeError, exceptions.DataRetrievalError) as ex:
                try_count += 1
                _LOGGER.exception('Failed to poll for plugin {}, retry count: {}'.format(self._name, try_count))
                await asyncio.sleep(_TIME_TO_WAIT_BEFORE_RETRY)
        _LOGGER.exception('Max retries exhausted in starting South plugin: {}'.format(self._name))

    def run(self):
        """Starts the South Microservice
        """
        loop = asyncio.get_event_loop()
        asyncio.ensure_future(self._start(loop))
        # This activates event loop and starts fetching events to the microservice server instance
        loop.run_forever()

    async def _stop(self, loop):
        if self._plugin is not None:
            try:
                self._plugin.plugin_shutdown(self._plugin_handle)
            except Exception as ex:
                _LOGGER.exception("Unable to stop plugin '%s' | reason: %s", self._name, str(ex))
                #  must not prevent FogLAMP shutting down cleanly via the API call.
                # raise ex
            finally:
                self._plugin = None
                self._plugin_handle = None

        try:
            await Ingest.stop()
            _LOGGER.info('Stopped the Ingest server.')
        except Exception as ex:
            _LOGGER.exception('Unable to stop the Ingest server. %s', str(ex))
            raise ex

        try:
            self._task_main.cancel()
            # Cancel all pending asyncio tasks after a timeout occurs
            done, pending = await asyncio.wait(asyncio.Task.all_tasks(), timeout=_CLEAR_PENDING_TASKS_TIMEOUT)
            for task_pending in pending:
                task_pending.cancel()
            await asyncio.sleep(2)
        except (asyncio.CancelledError, exceptions.DataRetrievalError):
            pass

        # This deactivates event loop and
        # helps aiohttp microservice server instance in graceful shutdown
        _LOGGER.info('Stopping South service event loop, for plugin {}.'.format(self._name))
        loop.stop()

    async def shutdown(self, request):
        """implementation of abstract method form foglamp.common.microservice.
        """
        _LOGGER.info('Stopping South Service plugin {}'.format(self._name))
        try:
            await self._stop(asyncio.get_event_loop())
            self.unregister_service_with_core(self._microservice_id)
        except Exception as ex:
            _LOGGER.exception('Error in stopping South Service plugin {}, {}'.format(self._name, str(ex)))
            raise web.HTTPInternalServerError(reason=str(ex))

        return web.json_response({"message": "Successfully shutdown microservice id {} at "
                                             "url http://{}:{}/foglamp/service/shutdown".format(self._microservice_id, self._microservice_management_host, self._microservice_management_port)})

    async def change(self, request):
        """implementation of abstract method form foglamp.common.microservice.
        """
        _LOGGER.info('Configuration has changed for South plugin {}'.format(self._name))

        try:
            # retrieve new configuration
            new_config = self._core_microservice_management_client.get_configuration_category(category_name=self._name)

            # plugin_reconfigure and assign new handle
            new_handle = self._plugin.plugin_reconfigure(self._plugin_handle, new_config)
            self._plugin_handle = new_handle

            _LOGGER.info('Reconfiguration done for South plugin {}'.format(self._name))
            if new_handle['restart'] == 'yes':
                self._task_main.cancel()
                # Executes the requested plugin type with new config
                if self._plugin_info['mode'] == 'async':
                    self._task_main = asyncio.ensure_future(self._exec_plugin_async())
                elif self._plugin_info['mode'] == 'poll':
                    self._task_main = asyncio.ensure_future(self._exec_plugin_poll())
                await asyncio.sleep(_TIME_TO_WAIT_BEFORE_RETRY)
        except asyncio.CancelledError:
            pass
        except exceptions.DataRetrievalError:
            _LOGGER.exception('Data retrieval error in plugin {} during reconfigure'.format(self._name))
            raise web.HTTPInternalServerError('Data retreival error in plugin {} during reconfigure'.format(self._name))

        return web.json_response({"south": "change"})
