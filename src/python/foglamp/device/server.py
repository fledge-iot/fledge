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

_LOGGER = logger.setup(__name__)


class Server:

    _core_management_host = None
    _core_management_port = None
    """ address of service management api """

    _plugin_name = None  # type:str
    """"The name of the plugin"""
    
    _plugin = None
    """The plugin's module'"""

    _plugin_data = None
    """The value that is returned by the plugin_init"""

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
    async def _start(cls, plugin: str, core_mgt_host, core_mgt_port, loop)->None:
        error = None
        cls.plugin_name = plugin

        cls._core_management_host = core_mgt_host
        cls._core_management_port = core_mgt_port

        try:
            category = plugin
            config = {}
            await configuration_manager.create_category(category, config,
                                                        '{} Device'.format(plugin), True)

            config = await configuration_manager.get_category_all_items(category)

            try:
                plugin_module = config['plugin']['value']
            except KeyError:
                _LOGGER.warning("Unable to obtain configuration of module for plugin {}".format(plugin))
                raise

            try:
                cls._plugin = __import__("foglamp.device.{}_device".format(plugin_module), fromlist=[''])
            except Exception:
                error = 'Unable to load module {} for device plugin {}'.format(plugin_module,
                                                                               plugin)
                raise

            default_config = cls._plugin.plugin_info()['config']

            await configuration_manager.create_category(category, default_config,
                                                        '{} Device'.format(plugin))

            config = await configuration_manager.get_category_all_items(category)

            # TODO: Register for config changes

            cls._plugin_data = cls._plugin.plugin_init(config)
            cls._plugin.plugin_run(cls._plugin_data)

            await Ingest.start(core_mgt_host, core_mgt_port)
        except Exception:
            if error is None:
                error = 'Failed to initialize plugin {}'.format(plugin)
            _LOGGER.exception(error)
            print(error)
            asyncio.ensure_future(cls._stop(loop))

    @classmethod
    def start(cls, plugin, core_mgt_host, core_mgt_port):
        """Starts the device server

        Args:
            plugin: Specifies which device plugin to start
        """
        loop = asyncio.get_event_loop()

        # Register signal handlers
        # Registering SIGTERM causes an error at shutdown. See
        # https://github.com/python/asyncio/issues/396
        for signal_name in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                signal_name,
                lambda: asyncio.ensure_future(cls._stop(loop)))

        microservice_management_app = web.Application(middlewares=[middleware.error_middleware])
        routes.setup(microservice_management_app)

        microservice_management_handler = microservice_management_app.make_handler()
        coro = loop.create_server(microservice_management_handler, '0.0.0.0', 0)
        # added coroutine
        microservice_management_server = loop.run_until_complete(coro)

        microservice_management_address, microservice_management_port = microservice_management_server.sockets[0].getsockname()
        _LOGGER.warning('Device - Management API started on http://%s:%s', microservice_management_address, microservice_management_port)

        conn = http.client.HTTPConnection("{0}:{1}".format(core_mgt_host, core_mgt_port))
        
        service_registration_payload = {
                "name"            : plugin,
                "type"            : "Southbound",
                "management_port" : int(microservice_management_port),
                "service_port"    : 0,
                "address"         : "127.0.0.1",
                "protocol"        : "http"
            }

        conn.request(method='POST', url='/foglamp/service', body=json.dumps(service_registration_payload))
        r = conn.getresponse()

        if r.status in range(400, 500):
            _LOGGER.error("Client error code: %d", r.status)
        if r.status in range(500, 600):
            _LOGGER.error("Server error code: %d", r.status)

        res = r.read().decode()
        conn.close()
        response = json.loads(res)
        _LOGGER.warning('Device - Registered Service %s', response["id"])

        asyncio.ensure_future(cls._start(plugin, core_mgt_host, core_mgt_port, loop))
        loop.run_forever()
