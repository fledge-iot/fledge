#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Core server module"""

import asyncio
import os
import subprocess
import sys
import http.client
import json
import ssl
from aiohttp import web

from foglamp.common import logger
from foglamp.common.web import middleware
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.common.storage_client.storage_client import StorageClient

from foglamp.services.core import routes as admin_routes
from foglamp.services.core.scheduler.scheduler import Scheduler

from foglamp.services.common.microservice_management import routes as management_routes
from foglamp.services.common.microservice_management.service_registry.instance import Service
from foglamp.services.common.microservice_management.service_registry.monitor import Monitor
from foglamp.services.common.service_announcer import ServiceAnnouncer


__author__ = "Amarendra K. Sinha, Praveen Garg, Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_logger = logger.setup(__name__, level=20)

# FOGLAMP_ROOT env variable
_FOGLAMP_DATA = os.getenv("FOGLAMP_DATA", default=None)
_FOGLAMP_ROOT = os.getenv("FOGLAMP_ROOT", default='/usr/local/foglamp')
_SCRIPTS_DIR = os.path.expanduser(_FOGLAMP_ROOT + '/scripts')


class Server:
    """ FOGLamp core server.

     Starts the FogLAMP REST server, storage and scheduler
    """

    scheduler = None
    """ foglamp.core.Scheduler """

    service_monitor = None
    """ foglamp.microservice_management.service_registry.Monitor """

    admin_announcer = None
    """ The Announcer for the Admin API """

    user_announcer = None
    """ The Announcer for the Admin API """

    management_announcer = None
    """ The Announcer for the management API """

    _host = '0.0.0.0'
    core_management_port = 0

    _REST_API_DEFAULT_CONFIG = {
        'port': {
            'description': 'REST API service port',
            'type': 'integer',
            'default': '8081'
        },
        'isTlsEnabled': {
            'description': 'if True run on https',
            'type': 'boolean',
            'default': 'true'
        }
    }

    @classmethod
    async def rest_api_config(cls, storage_client):
        """

        :return: port and TLS enabled info
        """
        try:
            config = cls._REST_API_DEFAULT_CONFIG
            category = 'rest_api'

            cfg_manager = ConfigurationManager(storage_client)
            await cfg_manager.create_category(category, config, 'The FogLAMP Admin and User REST API', True)
            config = await cfg_manager.get_category_all_items(category)

            try:
                port = config['port']['value']
            except KeyError:
                _logger.error("error in retrieving port info")
                raise
            try:
                is_tls_enabled = config['isTlsEnabled']['value']
                is_tls_enabled = False if is_tls_enabled == 'false' else True
            except KeyError:
                is_tls_enabled = True

            return port, is_tls_enabled

        except Exception as ex:
            _logger.exception(str(ex))
            raise

    @staticmethod
    def _make_app():
        """Creates the REST server

        :rtype: web.Application
        """
        app = web.Application(middlewares=[middleware.error_middleware])
        admin_routes.setup(app)
        return app

    @staticmethod
    def _make_core_app():
        """Creates the Service management REST server Core a.k.a. service registry

        :rtype: web.Application
        """
        app = web.Application(middlewares=[middleware.error_middleware])
        management_routes.setup(app, is_core=True)
        return app

    @classmethod
    async def _start_service_monitor(cls):
        """Starts the micro-service monitor"""
        cls.service_monitor = Monitor()
        await cls.service_monitor.start()

    @classmethod
    async def stop_service_monitor(cls):
        """Stops the micro-service monitor"""
        await cls.service_monitor.stop()

    @classmethod
    async def _start_scheduler(cls):
        """Starts the scheduler"""
        _logger.info("start scheduler")
        cls.scheduler = Scheduler(cls._host, cls.core_management_port)
        await cls.scheduler.start()

    @staticmethod
    def __start_storage(host, m_port):
        _logger.info("start storage, from directory %s", _SCRIPTS_DIR)
        try:
            cmd_with_args = ['./services/storage', '--address={}'.format(host),
                             '--port={}'.format(m_port)]
            subprocess.call(cmd_with_args, cwd=_SCRIPTS_DIR)
        except Exception as ex:
            _logger.exception(str(ex))

    @classmethod
    async def _start_storage(cls, loop):
        if loop is None:
            loop = asyncio.get_event_loop()
            # callback with args
        loop.call_soon(cls.__start_storage, cls._host, cls.core_management_port)

    @classmethod
    def _start_app(cls, loop, app, host, port, ssl_ctx=None):
        if loop is None:
            loop = asyncio.get_event_loop()

        handler = app.make_handler()
        coro = loop.create_server(handler, host, port, ssl=ssl_ctx)
        # added coroutine
        server = loop.run_until_complete(coro)
        return server, handler

    @classmethod
    def _start_core(cls, loop=None):
        _logger.info("start core")

        try:
            host = cls._host

            core_app = cls._make_core_app()
            core_server, core_server_handler = cls._start_app(loop, core_app, host, 0)
            address, cls.core_management_port = core_server.sockets[0].getsockname()
            _logger.info('Management API started on http://%s:%s', address, cls.core_management_port)
            # see http://<core_mgt_host>:<core_mgt_port>/foglamp/service for registered services

            _logger.info('Announce management API service')
            cls.management_announcer = ServiceAnnouncer('FogLAMP-Core', '_foglamp_core._tcp', cls.core_management_port,
                                                    ['The FogLAMP Core REST API'])

            # start storage
            loop.run_until_complete(cls._start_storage(loop))
            # start scheduler
            # see scheduler.py start def FIXME
            # scheduler on start will wait for storage service registration
            loop.run_until_complete(cls._start_scheduler())

            # start monitor
            loop.run_until_complete(cls._start_service_monitor())

            service_app = cls._make_app()

            storage_client = StorageClient(address, cls.core_management_port)

            rest_service_port, is_tls_enabled = loop.run_until_complete(cls.rest_api_config(storage_client))

            # ssl context
            ssl_ctx = None
            if is_tls_enabled:
                # ensure TLS 1.2 and SHA-256
                # handle expiry?
                ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                cert, key = cls.get_certificates()
                _logger.info('Loading certificates %s and key %s', cert, key)
                ssl_ctx.load_cert_chain(cert, key)

            service_server, service_server_handler = cls._start_app(loop, service_app,
                                                                    host, rest_service_port, ssl_ctx=ssl_ctx)
            address, service_server_port = service_server.sockets[0].getsockname()
            _logger.info('Admin API Server started on http://%s:%s', address, service_server_port)

            cls.admin_announcer = ServiceAnnouncer('FogLAMP', '_foglamp._tcp', service_server_port, ['The FogLAMP Admin REST API'])
            cls.user_announcer = ServiceAnnouncer('FogLAMP', '_foglamp_app._tcp', service_server_port,
                                              ['The FogLAMP Application  REST API'])
            # register core
            # a service with 2 web server instance,
            # registering now only when service_port is ready to listen the request
            # TODO: if ssl then register with protocol https
            cls._register_core(host, cls.core_management_port, rest_service_port)
            print("(Press CTRL+C to quit)")

            try:
                loop.run_forever()
            except KeyboardInterrupt:
                pass
            finally:
                # graceful-shutdown
                # http://aiohttp.readthedocs.io/en/stable/web.html
                # TODO: FOGL-653 shutdown implementation
                # stop the scheduler
                loop.run_until_complete(cls._stop_scheduler())

                # stop monitor
                loop.run_until_complete(cls.stop_service_monitor())

                # stop the REST api (exposed on service port)
                service_server.close()
                loop.run_until_complete(service_server.wait_closed())
                loop.run_until_complete(service_app.shutdown())
                loop.run_until_complete(service_server_handler.shutdown(60.0))
                loop.run_until_complete(service_app.cleanup())

                # stop storage
                cls.stop_storage()

                # stop core management api
                core_server.close()
                loop.run_until_complete(core_server.wait_closed())
                loop.run_until_complete(core_app.shutdown())
                loop.run_until_complete(core_server_handler.shutdown(60.0))
                loop.run_until_complete(core_app.cleanup())

                loop.close()
        except (OSError, RuntimeError, TimeoutError) as e:
            sys.stderr.write('Error: ' + format(str(e)) + "\n")
            sys.exit(1)
        except Exception as e:
            sys.stderr.write('Error: ' + format(str(e)) + "\n")
            sys.exit(1)

    @classmethod
    def _register_core(cls, host, mgt_port, service_port):
        core_service_id = Service.Instances.register(name="FogLAMP Core", s_type="Core", address=host,
                                                     port=service_port, management_port=mgt_port)

        return core_service_id

    @classmethod
    def start(cls):
        """Starts the server"""

        loop = asyncio.get_event_loop()
        cls._start_core(loop=loop)

    @classmethod
    def stop_storage(cls):
        """ stop Storage service """

        # TODO: FOGL-653 shutdown implementation
        # remove me, and allow this call in service registry API

        found_services = Service.Instances.get(name="FogLAMP Storage")
        svc = found_services[0]
        if svc is None:
            return

        management_api_url = '{}:{}'.format(svc._address, svc._management_port)

        conn = http.client.HTTPConnection(management_api_url)
        # TODO: need to set http / https based on service protocol

        conn.request('POST', url='/foglamp/service/shutdown', body=None)
        r = conn.getresponse()

        # TODO: FOGL-615
        # log error with message if status is 4xx or 5xx
        if r.status in range(400, 500):
            _logger.error("Client error code: %d", r.status)
        if r.status in range(500, 600):
            _logger.error("Server error code: %d", r.status)

        res = r.read().decode()
        conn.close()
        return json.loads(res)

    @classmethod
    async def _stop_scheduler(cls):
        if cls.scheduler:
            try:
                await cls.scheduler.stop()
                cls.scheduler = None
            except TimeoutError:
                _logger.exception('Unable to stop the scheduler')
                return

    @staticmethod
    def get_certificates():
        # TODO: FOGL-780
        if _FOGLAMP_DATA:
            certs_dir = os.path.expanduser(_FOGLAMP_DATA + '/etc/certs')
        else:
            certs_dir = os.path.expanduser(_FOGLAMP_ROOT + '/etc/certs')

        """ Generated using
            $ openssl version
            OpenSSL 1.0.2g  1 Mar 2016
        """
        # use pem file?
        # file name will be WHAT? *using server for now*
        cert = certs_dir + '/server.cert'
        key = certs_dir + '/server.key'
        # remove these asserts and put in try-except block with logging
        assert os.path.isfile(cert)
        assert os.path.isfile(key)

        return cert, key


def main():
    """ Processes command-line arguments
           COMMAND LINE ARGUMENTS:
               - start
               - stop

           :raises ValueError: Invalid or missing arguments provided
           """

    if len(sys.argv) == 1:
        raise ValueError("Usage: start|stop")
    elif len(sys.argv) == 2:
        command = sys.argv[1]
        if command == 'start':
            Server().start()
        elif command == 'stop':
            Server().stop_storage()
            Server().stop_service_monitor()
            # scheduler has signal binding
        else:
            raise ValueError("Unknown argument: {}".format(sys.argv[1]))
