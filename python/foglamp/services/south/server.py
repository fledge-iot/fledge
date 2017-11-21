# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""FogLAMP South Microservice"""

import asyncio
import signal
from aiohttp import web
import http.client
import json

from foglamp.services.south import exceptions
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.common.storage_client.storage_client import StorageClient
from foglamp.common import logger
from foglamp.services.south.ingest import Ingest
from foglamp.services.common.microservice_management import routes
from foglamp.common.web import middleware


__author__ = "Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_LOGGER = logger.setup(__name__)


class Server:
    """" Implements the South Microservice """

    # Configuration handled through the Configuration Manager
    _DEFAULT_CONFIG = {
        'plugin': {
            'description': 'Python module name of the plugin to load',
            'type': 'string',
            'default': 'coap_listen'
        }
    }

    _PLUGIN_MODULE_PATH = "foglamp.plugins.south"

    _MESSAGES_LIST = {

        # Information messages
        "i000000": "",

        # Warning / Error messages
        "e000000": "generic error.",
        "e000001": "cannot proceed the execution, only the type -device- is allowed "
                   "- plugin name |{0}| plugin type |{1}|",
        "e000002": "Unable to obtain configuration of module for plugin |{0}|",
        "e000003": "Unable to load module |{0}| for device plugin |{1}| - error details |{0}|",
    }
    """ Messages used for Information, Warning and Error notice """

    _core_management_host = None
    _core_management_port = None
    """ address of core microservice management api """

    _plugin_name = None  # type:str
    """"The name of the plugin"""
    
    _plugin = None
    """The plugin's module'"""

    _plugin_handle = None
    """The value that is returned by the plugin_init"""

    _microservice_management_app = None
    """ web application for microservice management app """

    _microservice_management_handler = None
    """ http factory for microservice management app """

    _microservice_management_server = None
    """ server for microservice management app """

    _microservice_management_host = None
    _microservice_management_port = None
    """ address for microservice management app """

    _microservice_id = None
    """ id for this microservice """

    @classmethod
    async def _stop(cls, loop):
        if cls._plugin is not None:
            try:
                cls._plugin.plugin_shutdown(cls._plugin_handle)
            except Exception:
                _LOGGER.exception("Unable to shut down plugin '{}'".format(cls._plugin_name))
            finally:
                cls._plugin = None
                cls._plugin_handle = None

        try:
            await Ingest.stop()
        except Exception:
            _LOGGER.exception('Unable to stop the Ingest server')
            return

        # Stop all pending asyncio tasks
        for task in asyncio.Task.all_tasks():
            task.cancel()

        loop.stop()

    @classmethod
    async def _start(cls, loop) -> None:
        error = None

        try:
            # Configuration handling - initial configuration
            category = cls._plugin_name

            config = cls._DEFAULT_CONFIG
            config_descr = '{} Device'.format(cls._plugin_name)

            storage = StorageClient(cls._core_management_host, cls._core_management_port, svc=None)
            cfg_manager = ConfigurationManager(storage)

            await cfg_manager.create_category(category, config, config_descr, True)

            config = await cfg_manager.get_category_all_items(category)

            try:
                plugin_module_name = config['plugin']['value']
            except KeyError:
                message = cls._MESSAGES_LIST['e000002'].format(cls._plugin_name)
                _LOGGER.error(message)
                raise

            try:
                import_file_name = "{path}.{dir}.{file}".format(path=cls._PLUGIN_MODULE_PATH,
                                                                dir=plugin_module_name,
                                                                file=plugin_module_name)
                cls._plugin = __import__(import_file_name, fromlist=[''])
            except Exception as ex:
                message = cls._MESSAGES_LIST['e000003'].format(plugin_module_name, cls._plugin_name, str(ex))
                _LOGGER.error(message)
                raise

            # Plugin initialization
            plugin_info = cls._plugin.plugin_info()
            default_config = plugin_info['config']

            # Configuration handling - updates the configuration using information specific to the plugin
            await cfg_manager.create_category(category, default_config, '{} Device'.format(cls._plugin_name))

            config = await cfg_manager.get_category_all_items(category)

            # TODO: Register for config changes

            # Ensures the plugin type is the correct one - 'device'
            if plugin_info['type'] != 'device':

                message = cls._MESSAGES_LIST['e000001'].format(cls._plugin_name, plugin_info['type'])
                _LOGGER.error(message)

                raise exceptions.InvalidPluginTypeError()

            cls._plugin_handle = cls._plugin.plugin_init(config)

            # Executes the requested plugin type
            if plugin_info['mode'] == 'async':
                await  cls._exec_plugin_async(config)

            elif plugin_info['mode'] == 'poll':
                asyncio.ensure_future(cls._exec_plugin_poll(config))

        except Exception:
            if error is None:
                error = 'Failed to initialize plugin {}'.format(cls._plugin_name)
            _LOGGER.exception(error)
            print(error)
            asyncio.ensure_future(cls._stop(loop))

    @classmethod
    async def _exec_plugin_async(cls, config) -> None:
        """Executes async type plugin  """

        cls._plugin.plugin_start(cls._plugin_handle)

        await Ingest.start(cls._core_management_host, cls._core_management_port)

    @classmethod
    async def _exec_plugin_poll(cls, config) -> None:
        """Executes poll type plugin """

        await Ingest.start(cls._core_management_host, cls._core_management_port)

        while True:
            data = await cls._plugin.plugin_poll(cls._plugin_handle)

            await Ingest.add_readings(asset=data['asset'],
                                      timestamp=data['timestamp'],
                                      key=data['key'],
                                      readings=data['readings'])

            # pollInterval is expressed in milliseconds
            sleep_seconds = int(config['pollInterval']['value']) / 1000.0
            await asyncio.sleep(sleep_seconds)

    @classmethod
    def _make_microservice_management_app(cls):
        # create web server application
        cls._microservice_management_app = web.Application(middlewares=[middleware.error_middleware])
        # register supported urls
        routes.setup(cls._microservice_management_app)
        # create http protocol factory for handling requests
        cls._microservice_management_handler = cls._microservice_management_app.make_handler()

    @classmethod
    def _run_microservice_management_app(cls, loop):
        # run microservice_management_app
        core = loop.create_server(cls._microservice_management_handler, '0.0.0.0', 0)
        cls._microservice_management_server = loop.run_until_complete(core)
        cls._microservice_management_host, cls._microservice_management_port = \
            cls._microservice_management_server.sockets[0].getsockname()
        _LOGGER.info('Device - Management API started on http://%s:%s',
                     cls._microservice_management_host,
                     cls._microservice_management_port)

    @classmethod
    def _get_service_registration_payload(cls):
        service_registration_payload = {
                "name": cls._plugin_name,
                "type": "Southbound",
                "management_port": int(cls._microservice_management_port),
                # TODO: change the handling of the service_port
                "service_port": int(cls._microservice_management_port),
                "address": "127.0.0.1",
                "protocol": "http"
            }
        return service_registration_payload

    @classmethod
    def _register_microservice(cls):
        # register with core
        conn = http.client.HTTPConnection("{0}:{1}".format(cls._core_management_host, cls._core_management_port))
        service_registration_payload = cls._get_service_registration_payload()
        conn.request(method='POST', url='/foglamp/service', body=json.dumps(service_registration_payload))
        r = conn.getresponse()
        if r.status in range(400, 500):
            _LOGGER.error("Client error code: %d", r.status)
        if r.status in range(500, 600):
            _LOGGER.error("Server error code: %d", r.status)
        res = r.read().decode()
        conn.close()
        response = json.loads(res)
        try:
            cls._microservice_id = response["id"]
            _LOGGER.info('Device - Registered Service %s', response["id"])
        except:
            _LOGGER.error("Device - Could not register")
            raise

    @classmethod
    def start(cls, plugin, core_mgt_host, core_mgt_port):
        """Starts the South Microservice

        Args:
            plugin: Specifies which device plugin to start
            core_mgt_host: IP address of the core's management API
            core_mgt_port: Port of the core's management API
        """
        cls._plugin_name = plugin
        cls._core_management_host = core_mgt_host
        cls._core_management_port = core_mgt_port

        loop = asyncio.get_event_loop()

        # Register signal handlers
        # Registering SIGTERM causes an error at shutdown. See
        # https://github.com/python/asyncio/issues/396
        for signal_name in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                signal_name,
                lambda: asyncio.ensure_future(cls._stop(loop)))

        try:
            cls._make_microservice_management_app()
        except Exception:
            _LOGGER.exception("Unable to create microservice management app")
            raise

        try:
            cls._run_microservice_management_app(loop)
        except Exception:
            _LOGGER.exception("Unable to run microservice management app")
            raise

        try:
            cls._register_microservice()
        except Exception:
            _LOGGER.exception("Unable to register")
            raise

        asyncio.ensure_future(cls._start(loop))
        loop.run_forever()
