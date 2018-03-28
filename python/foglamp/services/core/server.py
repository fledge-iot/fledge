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

import ssl
import time
import uuid
from aiohttp import web
import aiohttp
import json

from foglamp.common import logger
from foglamp.common.audit_logger import AuditLogger
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.common.web import middleware
from foglamp.common.storage_client.exceptions import *
from foglamp.common.storage_client.storage_client import StorageClient

from foglamp.services.core import routes as admin_routes
from foglamp.services.common.microservice_management import routes as management_routes

from foglamp.services.core.service_registry.service_registry import ServiceRegistry
from foglamp.services.core.service_registry import exceptions as service_registry_exceptions
from foglamp.services.core.interest_registry.interest_registry import InterestRegistry
from foglamp.services.core.interest_registry import exceptions as interest_registry_exceptions
from foglamp.services.core.scheduler.scheduler import Scheduler
from foglamp.services.core.service_registry.monitor import Monitor
from foglamp.services.common.service_announcer import ServiceAnnouncer
from foglamp.services.core.user_model import User


__author__ = "Amarendra K. Sinha, Praveen Garg, Terris Linenbach, Massimiliano Pinto"
__copyright__ = "Copyright (c) 2017-2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_logger = logger.setup(__name__, level=20)

# FOGLAMP_ROOT env variable
_FOGLAMP_DATA = os.getenv("FOGLAMP_DATA", default=None)
_FOGLAMP_ROOT = os.getenv("FOGLAMP_ROOT", default='/usr/local/foglamp')
_SCRIPTS_DIR = os.path.expanduser(_FOGLAMP_ROOT + '/scripts')

# PID dir and filename
_FOGLAMP_PID_DIR= "/var/run"
_FOGLAMP_PID_FILE = "foglamp.core.pid"

class Server:
    """ FOGLamp core server.

     Starts the FogLAMP REST server, storage and scheduler
    """

    scheduler = None
    """ foglamp.core.Scheduler """

    service_monitor = None
    """ foglamp.microservice_management.service_registry.Monitor """

    _service_name = 'FogLAMP'
    """ The name of this FogLAMP service """

    _service_description = 'FogLAMP REST Services'
    """ The description of this FogLAMP service """

    _SERVICE_DEFAULT_CONFIG = {
        'name': {
            'description': 'The name of this FogLAMP service',
            'type': 'string',
            'default': 'FogLAMP'
        },
        'description': {
            'description': 'The description of this FogLAMP service',
            'type': 'string',
            'default': 'The FogLAMP administrative API'
        }
    }

    _MANAGEMENT_SERVICE = '_foglamp-manage._tcp'
    """ The management service we advertise """

    _ADMIN_API_SERVICE = '_foglamp-admin._tcp'
    """ The admin REST service we advertise """

    _USER_API_SERVICE = '_foglamp-user._tcp'
    """ The user REST service we advertise """

    admin_announcer = None
    """ The Announcer for the Admin API """

    user_announcer = None
    """ The Announcer for the Admin API """

    management_announcer = None
    """ The Announcer for the management API """

    _host = '0.0.0.0'
    """ Host IP of core """

    core_management_port = 0
    """ Microservice management port of core """

    rest_server_port = 0
    """ FogLAMP REST API port """

    is_rest_server_http_enabled = False
    """ a Flag to decide to enable FogLAMP REST API on HTTP on restart """

    is_auth_required = True
    """ a var to decide to make authentication mandatory / optional for FogLAMP Admin/ User REST API"""

    cert_file_name = ''
    """ cert file name """

    _REST_API_DEFAULT_CONFIG = {
        'httpPort': {
            'description': 'The port to accept HTTP connections on',
            'type': 'integer',
            'default': '8081'
        },
        'httpsPort': {
            'description': 'The port to accept HTTPS connections on',
            'type': 'integer',
            'default': '1995'
        },
        'enableHttp': {
            'description': 'Enable or disable the connection via HTTP',
            'type': 'boolean',
            'default': 'false'
        },
        'authProviders': {
            'description': 'A JSON object which is an array of authentication providers to use '
                           'for the interface',
            'type': 'JSON',
            'default': '{"providers": ["username", "ldap"] }'
        },
        'certificateName': {
            'description': 'Certificate file name',
            'type': 'string',
            'default': 'foglamp'
        },
        'authentication': {
            'description': 'To make the authentication mandatory or optional for API calls',
            'type': 'string',
            'default': 'optional'
        },
        'allowPing': {
            'description': 'To allow access to the ping, regardless of the authentication required and'
                           ' authentication header',
            'type': 'boolean',
            'default': 'true'
        }
    }

    _start_time = time.time()
    """ Start time of core process """

    _storage_client = None
    """ Storage client to storage service """

    _configuration_manager = None
    """ Instance of configuration manager (singleton) """

    _interest_registry = None
    """ Instance of interest registry (singleton) """

    _audit = None
    """ Instance of audit logger(singleton) """

    _pidfile = None
    """ The PID file name """

    service_app, service_server, service_server_handler = None, None, None
    core_app, core_server, core_server_handler = None, None, None

    @classmethod
    def get_certificates(cls):
        # TODO: FOGL-780
        if _FOGLAMP_DATA:
            certs_dir = os.path.expanduser(_FOGLAMP_DATA + '/etc/certs')
        else:
            certs_dir = os.path.expanduser(_FOGLAMP_ROOT + '/data/etc/certs')

        """ Generated using      
                $ openssl version
                OpenSSL 1.0.2g  1 Mar 2016
                 
        The openssl library is required to generate your own certificate. Run the following command in your local environment to see if you already have openssl installed installed.
        
        $ which openssl
        /usr/bin/openssl
        
        If the which command does not return a path then you will need to install openssl yourself:
        
        $ apt-get install openssl
        
        Generate private key and certificate signing request:
        
        A private key and certificate signing request are required to create an SSL certificate.
        When the openssl req command asks for a “challenge password”, just press return, leaving the password empty. 
        This password is used by Certificate Authorities to authenticate the certificate owner when they want to revoke 
        their certificate. Since this is a self-signed certificate, there’s no way to revoke it via CRL(Certificate Revocation List).
        
        $ openssl genrsa -des3 -passout pass:x -out server.pass.key 2048
        ...
        $ openssl rsa -passin pass:x -in server.pass.key -out foglamp.key
        writing RSA key
        $ rm server.pass.key
        $ openssl req -new -key server.key -out server.csr
        ...
        Country Name (2 letter code) [AU]:US
        State or Province Name (full name) [Some-State]:California
        ...
        A challenge password []:
        ...
       
        Generate SSL certificate:
       
        The self-signed SSL certificate is generated from the server.key private key and server.csr files.
        
        $ openssl x509 -req -sha256 -days 365 -in server.csr -signkey server.key -out server.cert
        
        The server.cert file is the certificate suitable for use along with the server.key private key.
        
        Put these in $FOGLAMP_DATA/etc/certs, $FOGLAMP_ROOT/data/etc/certs or /usr/local/foglamp/data/etc/certs
        
        """
        cert = certs_dir + '/{}.cert'.format(cls.cert_file_name)
        key = certs_dir + '/{}.key'.format(cls.cert_file_name)

        if not os.path.isfile(cert) or not os.path.isfile(key):
            _logger.warning("%s certificate files are missing. Hence using default certificate.", cls.cert_file_name)
            cert = certs_dir + '/foglamp.cert'
            key = certs_dir + '/foglamp.key'
            if not os.path.isfile(cert) or not os.path.isfile(key):
                _logger.error("Certificates are missing")
                raise RuntimeError

        return cert, key

    @classmethod
    async def rest_api_config(cls):
        """

        :return: port and TLS enabled info
        """
        try:
            config = cls._REST_API_DEFAULT_CONFIG
            category = 'rest_api'

            await cls._configuration_manager.create_category(category, config, 'The FogLAMP Admin and User REST API', True)
            config = await cls._configuration_manager.get_category_all_items(category)

            try:
                cls.cert_file_name = config['certificateName']['value']
            except KeyError:
                _logger.error("error in retrieving certificateName info")
                raise

            try:
                cls.is_rest_server_http_enabled = False if config['enableHttp']['value'] == 'false' else True
            except KeyError:
                cls.is_rest_server_http_enabled = False

            try:
                port_from_config = config['httpPort']['value'] if cls.is_rest_server_http_enabled \
                    else config['httpsPort']['value']
                cls.rest_server_port = int(port_from_config)
            except KeyError:
                _logger.error("error in retrieving port info")
                raise
            except ValueError:
                _logger.error("error in parsing port value, received %s with type %s",
                              port_from_config, type(port_from_config))
                raise

            try:
                cls.is_auth_required = True if config['authentication']['value'] == "mandatory" else False
            except KeyError:
                _logger.error("error in retrieving authentication info")
                raise

        except Exception as ex:
            _logger.exception(str(ex))
            raise

    @classmethod
    async def service_config(cls):
        """
        Get the service level configuration
        """
        try:
            config = cls._SERVICE_DEFAULT_CONFIG
            category = 'service'

            if cls._configuration_manager is None:
                _logger.error("No configuration manager available")
            await cls._configuration_manager.create_category(category, config, 'The FogLAMP service configuration', True)
            config = await cls._configuration_manager.get_category_all_items(category)

            try:
                cls._service_name = config['name']['value']
            except KeyError:
                cls._service_name = 'FogLAMP'
            try:
                cls._service_description = config['description']['value']
            except KeyError:
                cls._service_description = 'FogLAMP REST Services'

        except Exception as ex:
            _logger.exception(str(ex))
            raise

    @staticmethod
    def _make_app(auth_required=True):
        """Creates the REST server

        :rtype: web.Application
        """
        app = web.Application(middlewares=[middleware.error_middleware, middleware.auth_middleware])
        if not auth_required:
            app = web.Application(middlewares=[middleware.error_middleware, middleware.optional_auth_middleware])
        admin_routes.setup(app)
        return app

    @classmethod
    def _make_core_app(cls):
        """Creates the Service management REST server Core a.k.a. service registry

        :rtype: web.Application
        """
        app = web.Application(middlewares=[middleware.error_middleware])
        management_routes.setup(app, cls)
        return app

    @classmethod
    async def _start_service_monitor(cls):
        """Starts the micro-service monitor"""
        cls.service_monitor = Monitor()
        await cls.service_monitor.start()
        _logger.info("Services monitoring started ...")

    @classmethod
    async def stop_service_monitor(cls):
        """Stops the micro-service monitor"""
        await cls.service_monitor.stop()
        _logger.info("Services monitoring stopped.")

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
    async def _get_storage_client(cls):
        storage_service = None
        while storage_service is None and cls._storage_client is None:
            try:
                found_services = ServiceRegistry.get(name="FogLAMP Storage")
                storage_service = found_services[0]
                cls._storage_client = StorageClient(cls._host, cls.core_management_port, svc=storage_service)
            except (service_registry_exceptions.DoesNotExist, InvalidServiceInstance, StorageServiceUnavailable, Exception) as ex:
                await asyncio.sleep(5)

    @classmethod
    def _start_app(cls, loop, app, host, port, ssl_ctx=None):
        if loop is None:
            loop = asyncio.get_event_loop()

        handler = app.make_handler()
        coro = loop.create_server(handler, host, port, ssl=ssl_ctx)
        # added coroutine
        server = loop.run_until_complete(coro)
        return server, handler

    @staticmethod
    def pid_filename():
        """ Get the full path of FogLAMP PID file """
        if _FOGLAMP_DATA is None:
            path = _FOGLAMP_ROOT + "/data"
        else:
            path = _FOGLAMP_DATA
        return path + _FOGLAMP_PID_DIR + "/" + _FOGLAMP_PID_FILE 

    @classmethod
    def _pidfile_exists(cls):
        """ Check whether the PID file exists """
        try:
            fh = open(cls._pidfile,'r')
            fh.close()
            return True
        except (FileNotFoundError, IOError, TypeError):
            return False

    @classmethod
    def _remove_pid(cls):
        """ Remove PID file """
        try:
            os.remove(cls._pidfile)
            _logger.info("FogLAMP PID file [" + cls._pidfile + "] removed.")
        except Exception as ex:
            _logger.error("FogLAMP PID file remove error: [" + ex.__class__.__name__ + "], (" + format(str(ex)) + ")")

    @classmethod
    def _write_pid(cls, api_address, api_port):
        """ Write data into PID file """
        try:
            # Get PID file path
            cls._pidfile = cls.pid_filename()

            # Check for existing PID file and log a message """
            if cls._pidfile_exists() is True:
                _logger.warn("A FogLAMP PID file has been found: [" + \
                             cls._pidfile + "] found, ignoring it.")

            # Get the running script PID
            pid = os.getpid()

            # Open for writing and truncate existing file
            fh = None
            try:
                fh = open(cls._pidfile, 'w+')
            except FileNotFoundError:
                try:
                    os.makedirs(os.path.dirname(cls._pidfile))
                    _logger.info("The PID directory [" + os.path.dirname(cls._pidfile) + "] has been created")
                    fh = open(cls._pidfile, 'w+')
                except Exception as ex:
                    errmsg = "PID dir create error: [" + ex.__class__.__name__ + "], (" + format(str(ex)) + ")"
                    _logger.error(errmsg)
                    raise
            except Exception as ex:
                errmsg = "FogLAMP PID file create error: [" + ex.__class__.__name__ + "], (" + format(str(ex)) + ")"
                _logger.error(errmsg)
                raise

            # Build the JSON object to write into PID file
            info_data = {'processID' : pid,\
                         'adminAPI' : {\
                             "protocol": "HTTP" if cls.is_rest_server_http_enabled else "HTTPS",\
                             "addresses": [api_address],\
                             "port": api_port }\
                        }

            # Write data into PID file
            fh.write(json.dumps(info_data))

            # Close the PID file
            fh.close()
            _logger.info("PID [" + str(pid) + "] written in [" + cls._pidfile + "]")
        except Exception as e:
            sys.stderr.write('Error: ' + format(str(e)) + "\n")
            sys.exit(1)

    @classmethod
    def _start_core(cls, loop=None):
        _logger.info("start core")

        try:
            host = cls._host

            cls.core_app = cls._make_core_app()
            cls.core_server, cls.core_server_handler = cls._start_app(loop, cls.core_app, host, 0)
            address, cls.core_management_port = cls.core_server.sockets[0].getsockname()
            _logger.info('Management API started on http://%s:%s', address, cls.core_management_port)
            # see http://<core_mgt_host>:<core_mgt_port>/foglamp/service for registered services

            # start storage
            loop.run_until_complete(cls._start_storage(loop))
            
            # get storage client
            loop.run_until_complete(cls._get_storage_client())
            
            # obtain configuration manager and interest registry
            cls._configuration_manager = ConfigurationManager(cls._storage_client)
            cls._interest_registry = InterestRegistry(cls._configuration_manager)

            # start scheduler
            # see scheduler.py start def FIXME
            # scheduler on start will wait for storage service registration
            loop.run_until_complete(cls._start_scheduler())

            # start monitor
            loop.run_until_complete(cls._start_service_monitor())

            loop.run_until_complete(cls.rest_api_config())
            cls.service_app = cls._make_app(auth_required=cls.is_auth_required)
            # ssl context
            ssl_ctx = None
            if not cls.is_rest_server_http_enabled:
                # ensure TLS 1.2 and SHA-256
                # handle expiry?
                ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                cert, key = cls.get_certificates()
                _logger.info('Loading certificates %s and key %s', cert, key)
                ssl_ctx.load_cert_chain(cert, key)

            # Get the service data and advertise the management port of the core
            # to allow other microservices to find FogLAMP
            loop.run_until_complete(cls.service_config())
            _logger.info('Announce management API service')
            cls.management_announcer = ServiceAnnouncer('core.{}'.format(cls._service_name), cls._MANAGEMENT_SERVICE, cls.core_management_port,
                                                        ['The FogLAMP Core REST API'])

            cls.service_server, cls.service_server_handler = cls._start_app(loop, cls.service_app, host, cls.rest_server_port, ssl_ctx=ssl_ctx)
            address, service_server_port = cls.service_server.sockets[0].getsockname()

            # Write PID file with REST API details
            cls._write_pid(address, service_server_port)

            _logger.info('REST API Server started on %s://%s:%s', 'http' if cls.is_rest_server_http_enabled else 'https',
                         address, service_server_port)

            # All services are up so now we can advertise the Admin and User REST API's
            cls.admin_announcer = ServiceAnnouncer(cls._service_name, cls._ADMIN_API_SERVICE, service_server_port,
                                                   [cls._service_description])
            cls.user_announcer = ServiceAnnouncer(cls._service_name, cls._USER_API_SERVICE, service_server_port,
                                                  [cls._service_description])
            # register core
            # a service with 2 web server instance,
            # registering now only when service_port is ready to listen the request
            # TODO: if ssl then register with protocol https
            cls._register_core(host, cls.core_management_port, service_server_port)

            # Everything is complete in the startup sequence, write the audit log entry
            cls._audit = AuditLogger(cls._storage_client)
            loop.run_until_complete(cls._audit.information('START', None))

            loop.run_forever()

        except (OSError, RuntimeError, TimeoutError) as e:
            sys.stderr.write('Error: ' + format(str(e)) + "\n")
            sys.exit(1)
        except Exception as e:
            sys.stderr.write('Error: ' + format(str(e)) + "\n")
            sys.exit(1)

    @classmethod
    def _register_core(cls, host, mgt_port, service_port):
        core_service_id = ServiceRegistry.register(name="FogLAMP Core", s_type="Core", address=host,
                                                     port=service_port, management_port=mgt_port)

        return core_service_id

    @classmethod
    def start(cls):
        """Starts FogLAMP"""
        loop = asyncio.get_event_loop()
        cls._start_core(loop=loop)

    @classmethod
    async def _stop(cls):
        """Stops FogLAMP"""
        try:
            # stop the scheduler
            await cls._stop_scheduler()

            # I assume it will be by scheduler
            await cls.stop_microservices()

            # stop monitor
            await cls.stop_service_monitor()

            # stop the REST api (exposed on service port)
            await cls.stop_rest_server()

            # Must write the audit log entry before we stop the storage service
            cls._audit = AuditLogger(cls._storage_client)
            await cls._audit.information('FSTOP', None)

            # stop storage
            await cls.stop_storage()

            # stop core management api
            # loop.stop does it all

            # Remove PID file
            cls._remove_pid()
        except Exception:
            raise

    @classmethod
    def stop(cls, loop=None):
        if loop is None:
            loop = asyncio.get_event_loop()
        loop.run_until_complete(cls._stop())
        loop.stop()

    @classmethod
    async def stop_rest_server(cls):
        # Delete all user tokens
        User.Objects.delete_all_user_tokens()
        cls.service_server.close()
        await cls.service_server.wait_closed()
        await cls.service_app.shutdown()
        await cls.service_server_handler.shutdown(60.0)
        await cls.service_app.cleanup()
        _logger.info("Rest server stopped.")

    @classmethod
    async def stop_storage(cls):
        """Stops Storage service """

        try:
            found_services = ServiceRegistry.get(name="FogLAMP Storage")
        except service_registry_exceptions.DoesNotExist:
            raise

        svc = found_services[0]
        if svc is None:
            _logger.info("FogLAMP Storage shut down requested, but could not be found.")
            return
        await cls._request_microservice_shutdown(svc)

    @classmethod
    async def stop_microservices(cls):
        """ call shutdown endpoint for non core micro-services

        There are 3 types of services
           - Core
           - Storage
           - Southbound
        """
        try:
            found_services = ServiceRegistry.get()
            services_to_stop = list()

            for fs in found_services:
                if fs._name in ("FogLAMP Storage", "FogLAMP Core"):
                    continue
                services_to_stop.append(fs)

            if len(services_to_stop) == 0:
                _logger.info("No service found except the core, and(or) storage.")
                return

            tasks = [cls._request_microservice_shutdown(svc) for svc in services_to_stop]
            await asyncio.wait(tasks)
        except service_registry_exceptions.DoesNotExist:
            pass
        except Exception as ex:
            _logger.exception(str(ex))

    @classmethod
    async def _request_microservice_shutdown(cls, svc):
        """ request service's shutdown """
        management_api_url = 'http://{}:{}/foglamp/service/shutdown'.format(svc._address, svc._management_port)
        # TODO: need to set http / https based on service protocol
        _logger.info("Shutting down the %s service %s ...", svc._type, svc._name)
        headers = {'content-type': 'application/json'}
        async with aiohttp.ClientSession() as session:
            async with session.post(management_api_url, data=None, headers=headers) as resp:
                result = await resp.text()
                status_code = resp.status
                if status_code in range(400, 500):
                    _logger.error("Bad request error code: %d, reason: %s", status_code, resp.reason)
                    raise web.HTTPBadRequest(reason=resp.reason)
                if status_code in range(500, 600):
                    _logger.error("Server error code: %d, reason: %s", status_code, resp.reason)
                    raise web.HTTPInternalServerError(reason=resp.reason)
                try:
                    response = json.loads(result)
                    response['message']
                    _logger.info("Successfully shut down the %s service %s.", svc._type, svc._name)
                except KeyError:
                    raise

    @classmethod
    async def _stop_scheduler(cls):
        try:
            await cls.scheduler.stop()
        except TimeoutError as e:
            _logger.exception('Unable to stop the scheduler')
            raise e

    @classmethod
    async def ping(cls, request):
        """ health check
        """
        since_started = time.time() - cls._start_time
        return web.json_response({'uptime': since_started})

    @classmethod
    async def register(cls, request):
        """ Register a service

        :Example:
            curl -d '{"type": "Storage", "name": "Storage Services", "address": "127.0.0.1", "service_port": 8090,
                "management_port": 1090, "protocol": "https"}' -X POST http://localhost:<core mgt port>/foglamp/service

            service_port in payload is optional
        """

        try:
            data = await request.json()

            service_name = data.get('name', None)
            service_type = data.get('type', None)
            service_address = data.get('address', None)
            service_port = data.get('service_port', None)
            service_management_port = data.get('management_port', None)
            service_protocol = data.get('protocol', 'http')

            if not (service_name.strip() or service_type.strip() or service_address.strip()
                    or service_management_port.strip() or not service_management_port.isdigit()):
                raise web.HTTPBadRequest(reason='One or more values for type/name/address/management port missing')

            if service_port is not None:
                if not (isinstance(service_port, int)):
                    raise web.HTTPBadRequest(reason="Service's service port can be a positive integer only")

            if not isinstance(service_management_port, int):
                raise web.HTTPBadRequest(reason='Service management port can be a positive integer only')

            try:
                registered_service_id = ServiceRegistry.register(service_name, service_type, service_address,
                                                                   service_port, service_management_port, service_protocol)
                try:
                    if not cls._storage_client is None:
                        cls._audit = AuditLogger(cls._storage_client)
                        await cls._audit.information('SRVRG', { 'name' : service_name})
                except Exception as ex:
                    _logger.info("Failed to audit registration: %s", str(ex))
            except service_registry_exceptions.AlreadyExistsWithTheSameName:
                raise web.HTTPBadRequest(reason='A Service with the same name already exists')
            except service_registry_exceptions.AlreadyExistsWithTheSameAddressAndPort:
                raise web.HTTPBadRequest(reason='A Service is already registered on the same address: {} and '
                                                'service port: {}'.format(service_address, service_port))
            except service_registry_exceptions.AlreadyExistsWithTheSameAddressAndManagementPort:
                raise web.HTTPBadRequest(reason='A Service is already registered on the same address: {} and '
                                                'management port: {}'.format(service_address, service_management_port))

            if not registered_service_id:
                raise web.HTTPBadRequest(reason='Service {} could not be registered'.format(service_name))

            _response = {
                'id': registered_service_id,
                'message': "Service registered successfully"
            }

            return web.json_response(_response)

        except ValueError as ex:
            raise web.HTTPNotFound(reason=str(ex))

    @classmethod
    async def unregister(cls, request):
        """ Unregister a service

        :Example:
            curl -X DELETE  http://localhost:<core mgt port>/foglamp/service/dc9bfc01-066a-4cc0-b068-9c35486db87f
        """

        try:
            service_id = request.match_info.get('service_id', None)

            if not service_id:
                raise web.HTTPBadRequest(reason='Service id is required')

            try:
                services = ServiceRegistry.get(idx=service_id)
            except service_registry_exceptions.DoesNotExist:
                raise web.HTTPNotFound(reason='Service with {} does not exist'.format(service_id))

            ServiceRegistry.unregister(service_id)

            if cls._storage_client is not None and services[0]._name not in ("FogLAMP Storage", "FogLAMP Core"):
                try:
                    cls._audit = AuditLogger(cls._storage_client)
                    await cls._audit.information('SRVUN', { 'name' : services[0]._name })
                except Exception as ex:
                    _logger.exception(str(ex))

            _resp = {'id': str(service_id), 'message': 'Service unregistered'}

            return web.json_response(_resp)
        except ValueError as ex:
            raise web.HTTPNotFound(reason=str(ex))

    @classmethod
    async def get_service(cls, request):
        """ Returns a list of all services or as per name &|| type filter

        :Example:
            curl -X GET  http://localhost:<core mgt port>/foglamp/service
            curl -X GET  http://localhost:<core mgt port>/foglamp/service?name=X&type=Storage
        """
        service_name = request.query['name'] if 'name' in request.query else None
        service_type = request.query['type'] if 'type' in request.query else None

        try:
            if not service_name and not service_type:
                services_list = ServiceRegistry.all()
            elif service_name and not service_type:
                services_list = ServiceRegistry.get(name=service_name)
            elif not service_name and service_type:
                services_list = ServiceRegistry.get(s_type=service_type)
            else:
                services_list = ServiceRegistry.filter_by_name_and_type(
                        name=service_name, s_type=service_type
                    )
        except service_registry_exceptions.DoesNotExist as ex:
            if not service_name and not service_type:
                msg = 'No service found'
            elif service_name and not service_type:
                msg = 'Service with name {} does not exist'.format(service_name)
            elif not service_name and service_type:
                msg = 'Service with type {} does not exist'.format(service_type)
            else:
                msg = 'Service with name {} and type {} does not exist'.format(service_name, service_type)

            raise web.HTTPNotFound(reason=msg)

        services = []
        for service in services_list:
            svc = dict()
            svc["id"] = service._id
            svc["name"] = service._name
            svc["type"] = service._type
            svc["address"] = service._address
            svc["management_port"] = service._management_port
            svc["protocol"] = service._protocol
            svc["status"] = service._status
            if service._port:
                svc["service_port"] = service._port
            services.append(svc)

        return web.json_response({"services": services})

    @classmethod
    async def shutdown(cls, request):
        """ Shutdown the core microservice and its components

        :return: JSON payload with message key
        :Example:
            curl -X POST http://localhost:<core mgt port>/foglamp/service/shutdown
        """
        try:

            await cls._stop()
            loop = asyncio.get_event_loop()
            # allow some time
            await asyncio.sleep(2.0)
            _logger.info("Stopping the FogLAMP Core event loop. Good Bye!")
            loop.stop()

            return web.json_response({'message': 'FogLAMP stopped successfully. '
                                                 'Wait for few seconds for process cleanup.'})
        except TimeoutError as err:
            raise web.HTTPInternalServerError(reason=str(err))
        except Exception as ex:
            raise web.HTTPException(reason=str(ex))

    @classmethod
    async def register_interest(cls, request):
        """ Register an interest in a configuration category

        :Example:
            curl -d '{"category": "COAP", "service": "x43978x8798x"}' -X POST http://localhost:<core mgt port>/foglamp/interest
        """

        try:
            data = await request.json()
            category_name = data.get('category', None)
            microservice_uuid = data.get('service', None)
            if microservice_uuid is not None:
                try:
                    assert uuid.UUID(microservice_uuid)
                except:
                    raise web.HTTPBadRequest(reason="Invalid microservice id {}".format(microservice_uuid))

            try:
                registered_interest_id = cls._interest_registry.register(microservice_uuid, category_name)
            except interest_registry_exceptions.ErrorInterestRegistrationAlreadyExists:
                raise web.HTTPBadRequest(reason='An InterestRecord already exists by microservice_uuid {} for category_name {}'.format(microservice_uuid, category_name))

            if not registered_interest_id:
                raise web.HTTPBadRequest(reason='Interest by microservice_uuid {} for category_name {} could not be registered'.format(microservice_uuid, category_name))

            _response = {
                'id': registered_interest_id,
                'message': "Interest registered successfully"
            }

            return web.json_response(_response)

        except ValueError as ex:
            raise web.HTTPBadRequest(reason=str(ex))

    @classmethod
    async def unregister_interest(cls, request):
        """ Unregister an interest

        :Example:
            curl -X DELETE  http://localhost:<core mgt port>/foglamp/interest/dc9bfc01-066a-4cc0-b068-9c35486db87f
        """

        try:
            interest_registration_id = request.match_info.get('interest_id', None)

            if not interest_registration_id:
                raise web.HTTPBadRequest(reason='Registration id is required')
            else:
                try:
                    assert uuid.UUID(interest_registration_id)
                except:
                    raise web.HTTPBadRequest(reason="Invalid registration id {}".format(interest_registration_id))

            try:
                cls._interest_registry.get(registration_id=interest_registration_id)
            except interest_registry_exceptions.DoesNotExist:
                raise web.HTTPNotFound(reason='InterestRecord with registration_id {} does not exist'.format(interest_registration_id))

            cls._interest_registry.unregister(interest_registration_id)

            _resp = {'id': str(interest_registration_id), 'message': 'Interest unregistered'}

            return web.json_response(_resp)
        except ValueError as ex:
            raise web.HTTPNotFound(reason=str(ex))

    @classmethod
    async def get_interest(cls, request):
        """ Returns a list of all interests or of the selected interest

        :Example:
                curl -X GET  http://localhost:{core_mgt_port}/foglamp/interest
                curl -X GET  http://localhost:{core_mgt_port}/foglamp/interest?microserviceid=X&category=Y
        """
        category = request.query['category'] if 'category' in request.query else None
        microservice_id = request.query['microserviceid'] if 'microserviceid' in request.query else None
        if microservice_id is not None:
            try:
                assert uuid.UUID(microservice_id)
            except:
                raise web.HTTPBadRequest(reason="Invalid microservice id {}".format(microservice_id))

        try:
            if not category and not microservice_id:
                interest_list = cls._interest_registry.get()
            elif category and not microservice_id:
                interest_list = cls._interest_registry.get(category_name=category)
            elif not category and microservice_id:
                interest_list = cls._interest_registry.get(microservice_uuid=microservice_id)
            else:
                interest_list = cls._interest_registry.get(category_name=category, microservice_uuid=microservice_id)
        except interest_registry_exceptions.DoesNotExist as ex:
            if not category and not microservice_id:
                msg = 'No interest registered'
            elif category and not microservice_id:
                msg = 'No interest registered for category {}'.format(category)
            elif not category and microservice_id:
                msg = 'No interest registered microservice id {}'.format(microservice_id)
            else:
                msg = 'No interest registered for category {} and microservice id {}'.format(category, microservice_id)

            raise web.HTTPNotFound(reason=msg)

        interests = []
        for interest in interest_list:
            d = dict()
            d["registrationId"] = interest._registration_id
            d["category"] = interest._category_name
            d["microserviceId"] = interest._microservice_uuid
            interests.append(d)

        return web.json_response({"interests": interests})

    @classmethod
    async def change(cls, request):
        pass
