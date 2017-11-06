# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""FogLAMP device server"""

import asyncio
import signal
from aiohttp import web
import http.client
import json

from foglamp import configuration_manager
from foglamp import logger
from foglamp.device.ingest import Ingest
from foglamp.microservice_management import routes
from foglamp.web import middleware


__author__ = "Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_LOGGER = logger.setup(__name__, level=20)


class Server:

    _core_management_host = None
    _core_management_port = None
    """ address of core microservice management api """

    _plugin_name = None  # type:str
    """"The name of the plugin"""
    
    _plugin = None
    """The plugin's module'"""

    _plugin_data = None
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
    """ id for this microsrvice """

    @classmethod
    async def _stop(cls, loop):
        if cls._plugin is not None:
            try:
                cls._plugin.plugin_shutdown(cls._plugin_data)
            except Exception:
                _LOGGER.exception("Unable to shut down plugin '{}'".format(cls._plugin_name))
            finally:
                cls._plugin = None
                cls._plugin_data = None

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
    async def _start(cls, loop)->None:
        error = None
        try:
            config = {}
            await configuration_manager.create_category(cls._plugin_name, config,
                                                        '{} Device'.format(cls._plugin_name), True)

            config = await configuration_manager.get_category_all_items(cls._plugin_name)

            try:
                plugin_module_name = config['plugin']['value']
            except KeyError:
                _LOGGER.warning("Unable to obtain configuration of module for plugin {}".format(cls._plugin_name))
                raise

            try:
                cls._plugin = __import__("foglamp.device.{}_device".format(plugin_module_name), fromlist=[''])
            except Exception:
                error = 'Unable to load module {} for device plugin {}'.format(plugin_module_name,
                                                                               cls._plugin_name)
                raise

            default_config = cls._plugin.plugin_info()['config']

            await configuration_manager.create_category(cls._plugin_name, default_config,
                                                        '{} Device'.format(cls._plugin_name))

            config = await configuration_manager.get_category_all_items(cls._plugin_name)

            # TODO: Register for config changes

            cls._plugin_data = cls._plugin.plugin_init(config)
            cls._plugin.plugin_run(cls._plugin_data)

            await Ingest.start(cls._core_management_host,cls._core_management_port)
        except Exception:
            if error is None:
                error = 'Failed to initialize plugin {}'.format(cls._plugin_name)
            _LOGGER.exception(error)
            print(error)
            asyncio.ensure_future(cls._stop(loop))

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
        coro = loop.create_server(cls._microservice_management_handler, '0.0.0.0', 0)
        cls._microservice_management_server = loop.run_until_complete(coro)
        cls._microservice_management_host, cls._microservice_management_port = cls._microservice_management_server.sockets[0].getsockname()
        _LOGGER.info('Device - Management API started on http://%s:%s', cls._microservice_management_host, cls._microservice_management_port)


    @classmethod
    def _get_service_registration_payload(cls):
        service_registration_payload = {
                "name"            : cls._plugin_name,
                "type"            : "Southbound",
                "management_port" : int(cls._microservice_management_port),
                "service_port"    : 0,
                "address"         : "127.0.0.1",
                "protocol"        : "http"
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
        cls._microservice_id = response["id"]
        _LOGGER.info('Device - Registered Service %s', response["id"])



    @classmethod
    def start(cls, plugin, core_mgt_host, core_mgt_port):
        """Starts the device server

        Args:
            plugin: Specifies which device plugin to start
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
