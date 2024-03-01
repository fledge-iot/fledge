#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

"""Core server module"""

import asyncio
import os
import logging
import subprocess
import sys
import ssl
import time
import uuid
from aiohttp import web
import aiohttp
import json
import signal
from datetime import datetime, timedelta
import jwt

from fledge.common import logger
from fledge.common.alert_manager import AlertManager
from fledge.common.audit_logger import AuditLogger
from fledge.common.configuration_manager import ConfigurationManager
from fledge.common.storage_client.exceptions import *
from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.common.storage_client.storage_client import ReadingsStorageClientAsync
from fledge.common.web import middleware

from fledge.services.core import routes as admin_routes
from fledge.services.core.api import configuration as conf_api
from fledge.services.common.microservice_management import routes as management_routes

from fledge.common.service_record import ServiceRecord
from fledge.services.core.service_registry.service_registry import ServiceRegistry
from fledge.services.core.service_registry import exceptions as service_registry_exceptions
from fledge.services.core.interest_registry.interest_registry import InterestRegistry
from fledge.services.core.interest_registry import exceptions as interest_registry_exceptions
from fledge.services.core.scheduler.scheduler import Scheduler
from fledge.services.core.service_registry.monitor import Monitor
from fledge.services.common.service_announcer import ServiceAnnouncer
from fledge.services.core.user_model import User
from fledge.common.storage_client import payload_builder
from fledge.services.core.asset_tracker.asset_tracker import AssetTracker
from fledge.services.core.api import asset_tracker as asset_tracker_api
from fledge.common.web.ssl_wrapper import SSLVerifier
from fledge.services.core.api import exceptions as api_exception
from fledge.services.core.api.control_service import acl_management as acl_management


__author__ = "Amarendra K. Sinha, Praveen Garg, Terris Linenbach, Massimiliano Pinto, Ashish Jabble"
__copyright__ = "Copyright (c) 2017-2021 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_logger = logger.setup(__name__, level=logging.INFO)

# FLEDGE_ROOT env variable
_FLEDGE_DATA = os.getenv("FLEDGE_DATA", default=None)
_FLEDGE_ROOT = os.getenv("FLEDGE_ROOT", default='/usr/local/fledge')
_SCRIPTS_DIR = os.path.expanduser(_FLEDGE_ROOT + '/scripts')

# PID dir and filename
_FLEDGE_PID_DIR = "/var/run"
_FLEDGE_PID_FILE = "fledge.core.pid"


SSL_PROTOCOLS = (asyncio.sslproto.SSLProtocol,)

# TODO generate secret at build time
SERVICE_JWT_SECRET = 'f0gl@mp+Fl3dG3'
SERVICE_JWT_ALGORITHM = 'HS256'
SERVICE_JWT_EXP_DELTA_SECONDS = 30*60  # 30 minutes
SERVICE_JWT_AUDIENCE = 'Fledge'

# aiohttp client’s maximum size in a request, in bytes.
# If a POST request exceeds this value, it raises an HTTPRequestEntityTooLarge exception.
AIOHTTP_CLIENT_MAX_SIZE = 4*1024**3  # allowed up to 4GB


def ignore_aiohttp_ssl_eror(loop):
    """Ignore aiohttp #3535 / cpython #13548 issue with SSL data after close

    There is an issue in Python 3.7 up to 3.7.3 that over-reports a
    ssl.SSLError fatal error. See GitHub issues aio-libs/aiohttp#3535 and
    python/cpython#13548.

    Given a loop, this sets up an exception handler that ignores this specific
    exception, but passes everything else on to the previous exception handler
    this one replaces.

    Checks for fixed Python versions, disabling itself when running on 3.7.4+
    or 3.8.

    """
    if sys.version_info >= (3, 7, 4):
        return

    orig_handler = loop.get_exception_handler()

    def ignore_ssl_error(loop, context):
        if context.get("message") in {
            "SSL error in data received",
            "SSL handshake failed"
        }:
            # validate we have the right exception, transport and protocol
            exception = context.get('exception')
            protocol = context.get('protocol')
            if (
                isinstance(exception, ssl.SSLError)
                and exception.reason == 'SSLV3_ALERT_CERTIFICATE_UNKNOWN'
                and isinstance(protocol, SSL_PROTOCOLS)
            ):
                if loop.get_debug():
                    asyncio.log.logger.debug('Ignoring asyncio SSL SSLV3_ALERT_CERTIFICATE_UNKNOWN error')
                return
        if orig_handler is not None:
            orig_handler(loop, context)
        else:
            loop.default_exception_handler(context)

    loop.set_exception_handler(ignore_ssl_error)


class Server:
    """ Fledge core server.

     Starts the Fledge REST server, storage and scheduler
    """

    scheduler = None
    """ fledge.core.Scheduler """

    service_monitor = None
    """ fledge.microservice_management.service_registry.Monitor """

    _service_name = 'Fledge'
    """ The name of this Fledge service """

    _service_description = 'Fledge REST Services'
    """ The description of this Fledge service """

    _SERVICE_DEFAULT_CONFIG = {
        'name': {
            'description': 'Name of this Fledge service',
            'type': 'string',
            'default': 'Fledge',
            'displayName': 'Name',
            'order': '1',
            'mandatory': "true"
        },
        'description': {
            'description': 'Description of this Fledge service',
            'type': 'string',
            'default': 'Fledge administrative API',
            'displayName': 'Description',
            'order': '2'
        }
    }

    _MANAGEMENT_SERVICE = '_fledge-manage._tcp.local.'
    """ The management service we advertise """

    _ADMIN_API_SERVICE = '_fledge-admin._tcp.local.'
    """ The admin REST service we advertise """

    _USER_API_SERVICE = '_fledge-user._tcp.local.'
    """ The user REST service we advertise """

    _API_PROXIES = {}
    """ Proxy map for interfacing admin/user's REST API endpoints to Micro-services' service API endpoints """

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
    """ Fledge REST API port """

    is_rest_server_http_enabled = True
    """ a Flag to decide to enable Fledge REST API on HTTP on restart """

    is_auth_required = False
    """ a var to decide to make authentication mandatory / optional for Fledge Admin/ User REST API"""

    auth_method = 'any'

    cert_file_name = ''
    """ cert file name """

    _REST_API_DEFAULT_CONFIG = {
        'enableHttp': {
            'description': 'Enable HTTP (disable to use HTTPS)',
            'type': 'boolean',
            'default': 'true',
            'displayName': 'Enable HTTP',
            'order': '1'
        },
        'httpPort': {
            'description': 'Port to accept HTTP connections on',
            'type': 'integer',
            'default': '8081',
            'displayName': 'HTTP Port',
            'order': '2'
        },
        'httpsPort': {
            'description': 'Port to accept HTTPS connections on',
            'type': 'integer',
            'default': '1995',
            'displayName': 'HTTPS Port',
            'order': '3',
            'validity': 'enableHttp=="false"'
        },
        'certificateName': {
            'description': 'Certificate file name',
            'type': 'string',
            'default': 'fledge',
            'displayName': 'Certificate Name',
            'order': '4',
            'validity': 'enableHttp=="false"'
        },
        'authentication': {
            'description': 'API Call Authentication',
            'type': 'enumeration',
            'options': ['mandatory', 'optional'],
            'default': 'optional',
            'displayName': 'Authentication',
            'order': '5'
        },
        'authMethod': {
            'description': 'Authentication method',
            'type': 'enumeration',
            'options': ["any", "password", "certificate"],
            'default': 'any',
            'displayName': 'Authentication method',
            'order': '6'
        },
        'authCertificateName': {
            'description': 'Auth Certificate name',
            'type': 'string',
            'default': 'ca',
            'displayName': 'Auth Certificate',
            'order': '7'
        },
        'allowPing': {
            'description': 'Allow access to ping, regardless of the authentication required and'
                           ' authentication header',
            'type': 'boolean',
            'default': 'true',
            'displayName': 'Allow Ping',
            'order': '8'
        },
        'passwordChange': {
            'description': 'Number of days after which passwords must be changed',
            'type': 'integer',
            'default': '0',
            'displayName': 'Password Expiry Days',
            'order': '9'
        },
        'authProviders': {
            'description': 'Authentication providers to use for the interface (JSON array object)',
            'type': 'JSON',
            'default': '{"providers": ["username", "ldap"] }',
            'displayName': 'Auth Providers',
            'order': '10'
        },
    }

    _LOGGING_DEFAULT_CONFIG = {
        'logLevel': {
            'description': 'Minimum logging level reported for Core server',
            'type': 'enumeration',
            'displayName': 'Minimum Log Level',
            'options': ['debug', 'info', 'warning', 'error', 'critical'],
            'default': 'warning',
            'order': '1'
        }
    }

    _log_level = _LOGGING_DEFAULT_CONFIG['logLevel']['default']
    """ Common logging level for Core """

    _start_time = time.time()
    """ Start time of core process """

    _storage_client = None
    """ Storage client to storage service """

    _storage_client_async = None
    """ Async Storage client to storage service """

    _readings_client_async = None
    """ Async Readings client to storage service """

    _configuration_manager = None
    """ Instance of configuration manager (singleton) """

    _interest_registry = None
    """ Instance of interest registry (singleton) """

    _audit = None
    """ Instance of audit logger(singleton) """

    _pidfile = None
    """ The PID file name """

    _asset_tracker = None
    """ Asset tracker """

    _alert_manager = None
    """ Alert Manager """

    running_in_safe_mode = False
    """ Fledge running in Safe mode """

    _package_cache_manager = None
    """ Package Cache Manager """

    _INSTALLATION_DEFAULT_CONFIG = {
        'maxUpdate': {
            'description': 'Maximum updates per day',
            'type': 'integer',
            'default': '1',
            'displayName': 'Maximum Update',
            'order': '1',
            'minimum': '1',
            'maximum': '8'
        },
        'maxUpgrade': {
            'description': 'Maximum upgrades per day',
            'type': 'integer',
            'default': '1',
            'displayName': 'Maximum Upgrade',
            'order': '3',
            'minimum': '1',
            'maximum': '8',
            'validity': 'upgradeOnInstall == "true"'
        },
        'upgradeOnInstall': {
            'description': 'Run upgrade prior to installing new software',
            'type': 'boolean',
            'default': 'false',
            'displayName': 'Upgrade on Install',
            'order': '2'
        },
        'listAvailablePackagesCacheTTL': {
            'description': 'Caching of fetch available packages time to live in minutes',
            'type': 'integer',
            'default': '15',
            'displayName': 'Available Packages Cache',
            'order': '4',
            'minimum': '0'
        }
    }

    service_app, service_server, service_server_handler = None, None, None
    core_app, core_server, core_server_handler = None, None, None

    @classmethod
    def get_certificates(cls):
        # TODO: FOGL-780
        if _FLEDGE_DATA:
            certs_dir = os.path.expanduser(_FLEDGE_DATA + '/etc/certs')
        else:
            certs_dir = os.path.expanduser(_FLEDGE_ROOT + '/data/etc/certs')

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
        $ openssl rsa -passin pass:x -in server.pass.key -out fledge.key
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

        Put these in $FLEDGE_DATA/etc/certs, $FLEDGE_ROOT/data/etc/certs or /usr/local/fledge/data/etc/certs

        """
        cert = certs_dir + '/{}.cert'.format(cls.cert_file_name)
        key = certs_dir + '/{}.key'.format(cls.cert_file_name)

        if not os.path.isfile(cert) or not os.path.isfile(key):
            _logger.warning("%s certificate files are missing. Hence using default certificate.", cls.cert_file_name)
            cert = certs_dir + '/fledge.cert'
            key = certs_dir + '/fledge.key'
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

            await cls._configuration_manager.create_category(category, config, 'Fledge Admin and User REST API', True, display_name="Admin API")
            config = await cls._configuration_manager.get_category_all_items(category)

            try:
                cls.is_auth_required = True if config['authentication']['value'] == "mandatory" else False
            except KeyError:
                _logger.error("error in retrieving authentication info")
                raise

            try:
                cls.auth_method = config['authMethod']['value']
            except KeyError:
                _logger.error("error in retrieving authentication method info")
                raise

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
        except Exception as ex:
            _logger.exception(ex)
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
            await cls._configuration_manager.create_category(category, config, 'Fledge Service', True, display_name='Fledge Service')
            config = await cls._configuration_manager.get_category_all_items(category)

            try:
                cls._service_name = config['name']['value']
            except KeyError:
                cls._service_name = 'Fledge'
            try:
                cls._service_description = config['description']['value']
            except KeyError:
                cls._service_description = 'Fledge REST Services'
        except Exception as ex:
            _logger.exception(ex)
            raise

    @classmethod
    async def installation_config(cls):
        """
        Get the installation level configuration
        """
        try:
            config = cls._INSTALLATION_DEFAULT_CONFIG
            category = 'Installation'

            if cls._configuration_manager is None:
                _logger.error("No configuration manager available")
            await cls._configuration_manager.create_category(category, config, 'Installation', True,
                                                             display_name='Installation')
            await cls._configuration_manager.get_category_all_items(category)

            cls._package_cache_manager = {"update": {"last_accessed_time": ""},
                                          "upgrade": {"last_accessed_time": ""}, "list": {"last_accessed_time": ""}}
        except Exception as ex:
            _logger.exception(ex)
            raise

    @classmethod
    async def core_logger_setup(cls):
        """ Get the logging level configuration """
        try:
            config = cls._LOGGING_DEFAULT_CONFIG
            category = 'LOGGING'
            description = "Logging Level of Core Server"
            if cls._configuration_manager is None:
                cls._configuration_manager = ConfigurationManager(cls._storage_client_async)
            await cls._configuration_manager.create_category(category, config, description, True,
                                                             display_name='Logging')
            config = await cls._configuration_manager.get_category_all_items(category)
            cls._log_level = config['logLevel']['value']
            from fledge.common.logger import FLCoreLogger
            FLCoreLogger().set_level(cls._log_level)
        except Exception as ex:
            _logger.exception(ex)
            raise

    @staticmethod
    def _make_app(auth_required=True, auth_method='any'):
        """Creates the REST server

        :rtype: web.Application
        """
        mwares = [middleware.error_middleware]

        # Maintain this order. Middlewares are executed in reverse order.
        if auth_method != "any":
            if auth_method == "certificate":
                mwares.append(middleware.certificate_login_middleware)
            else:  # password
                mwares.append(middleware.password_login_middleware)

        if not auth_required:
            mwares.append(middleware.optional_auth_middleware)
        else:
            mwares.append(middleware.auth_middleware)

        app = web.Application(middlewares=mwares, client_max_size=AIOHTTP_CLIENT_MAX_SIZE)
        # aiohttp web server logging level always set to warning
        web.access_logger.setLevel(logging.WARNING)
        admin_routes.setup(app)
        return app

    @classmethod
    def _make_core_app(cls):
        """Creates the Service management REST server Core a.k.a. service registry

        :rtype: web.Application
        """
        app = web.Application(middlewares=[middleware.error_middleware], client_max_size=AIOHTTP_CLIENT_MAX_SIZE)
        # aiohttp web server logging level always set to warning
        web.access_logger.setLevel(logging.WARNING)
        management_routes.setup(app, cls, True)
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
        _logger.info("Starting scheduler ...")
        cls.scheduler = Scheduler(cls._host, cls.core_management_port, cls.running_in_safe_mode)
        await cls.scheduler.start()

    @staticmethod
    def __start_storage(host, m_port):
        _logger.info("Start storage, from directory {}".format(_SCRIPTS_DIR))
        try:
            cmd_with_args = ['./services/storage', '--address={}'.format(host),
                             '--port={}'.format(m_port)]
            subprocess.call(cmd_with_args, cwd=_SCRIPTS_DIR)
        except Exception as ex:
            _logger.exception(ex)

    @classmethod
    async def _start_storage(cls, loop):
        if loop is None:
            loop = asyncio.get_event_loop()
        # callback with args
        loop.call_soon(cls.__start_storage, cls._host, cls.core_management_port)

    @classmethod
    async def _get_storage_client(cls):
        storage_service = None
        while storage_service is None and cls._storage_client_async is None:
            try:
                found_services = ServiceRegistry.get(name="Fledge Storage")
                storage_service = found_services[0]
                cls._storage_client_async = StorageClientAsync(cls._host, cls.core_management_port, svc=storage_service)
            except (service_registry_exceptions.DoesNotExist, InvalidServiceInstance, StorageServiceUnavailable, Exception) as ex:
                await asyncio.sleep(5)
        while cls._readings_client_async is None:
            try:
                cls._readings_client_async = ReadingsStorageClientAsync(cls._host, cls.core_management_port, svc=storage_service)
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
        """ Get the full path of Fledge PID file """
        if _FLEDGE_DATA is None:
            path = _FLEDGE_ROOT + "/data"
        else:
            path = _FLEDGE_DATA
        return path + _FLEDGE_PID_DIR + "/" + _FLEDGE_PID_FILE

    @classmethod
    def _pidfile_exists(cls):
        """ Check whether the PID file exists """
        try:
            fh = open(cls._pidfile, 'r')
            fh.close()
            return True
        except (FileNotFoundError, IOError, TypeError):
            return False

    @classmethod
    def _remove_pid(cls):
        """ Remove PID file """
        try:
            os.remove(cls._pidfile)
            _logger.info("Fledge PID file [" + cls._pidfile + "] removed.")
        except Exception as ex:
            _logger.error("Fledge PID file remove error: [" + ex.__class__.__name__ + "], (" + format(str(ex)) + ")")

    @classmethod
    def _write_pid(cls, api_address, api_port):
        """ Write data into PID file """
        try:
            # Get PID file path
            cls._pidfile = cls.pid_filename()

            # Check for existing PID file and log a message """
            if cls._pidfile_exists() is True:
                _logger.warn("A Fledge PID file has been found: [" + \
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
                errmsg = "Fledge PID file create error: [" + ex.__class__.__name__ + "], (" + format(str(ex)) + ")"
                _logger.error(errmsg)
                raise

            # Build the JSON object to write into PID file
            info_data = {'processID': pid,\
                         'adminAPI': {\
                             "protocol": "HTTP" if cls.is_rest_server_http_enabled else "HTTPS",\
                             "addresses": [api_address],\
                             "port": api_port}\
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
    def _reposition_streams_table(cls, loop):

        _logger.info("'fledge.readings' is stored in memory and a restarted has occurred, "
                     "force reset of 'fledge.streams' last_objects")

        configuration = loop.run_until_complete(cls._storage_client_async.query_tbl('configuration'))
        rows = configuration['rows']
        if len(rows) > 0:
            streams_id = []
            # Identifies the sending process handling the readings table
            for _item in rows:
                try:
                    if _item['value']['source']['value'] is not None:
                        if _item['value']['source']['value'] == "readings":
                            # Sending process in C++
                            try:
                                streams_id.append(_item['value']['streamId']['value'])
                            except KeyError:
                                # Sending process in Python
                                try:
                                    streams_id.append(_item['value']['stream_id']['value'])
                                except KeyError:
                                    pass
                except KeyError:
                    pass

            # Reset identified rows of the streams table
            if len(streams_id) >= 0:
                for _stream_id in streams_id:

                    # Checks if there is the row in the Stream table to avoid an error during the update
                    where = 'id={0}'.format(_stream_id)
                    streams = loop.run_until_complete(cls._readings_client_async.query_tbl('streams', where))
                    rows = streams['rows']

                    if len(rows) > 0:
                        payload = payload_builder.PayloadBuilder().SET(last_object=0, ts='now()')\
                            .WHERE(['id', '=', _stream_id]).payload()
                        loop.run_until_complete(cls._storage_client_async.update_tbl("streams", payload))

    @classmethod
    def _check_readings_table(cls, loop):
        # check readings table has any row
        select_query_payload = payload_builder.PayloadBuilder().SELECT("id").LIMIT(1).payload()
        result = loop.run_until_complete(cls._readings_client_async.query(select_query_payload))
        readings_row_exists = len(result['rows'])
        if readings_row_exists == 0:
            # check streams table has any row
            s_result = loop.run_until_complete(cls._storage_client_async.query_tbl_with_payload('streams',
                                                                                                select_query_payload))
            streams_row_exists = len(s_result['rows'])
            if streams_row_exists:
                cls._reposition_streams_table(loop)
        else:
            _logger.info("'fledge.readings' is not empty; 'fledge.streams' last_objects reset is not required")

    @classmethod
    async def _config_parents(cls):
        # Create the parent category for all general configuration categories
        try:
            await cls._configuration_manager.create_category("General", {}, 'General', True)
            await cls._configuration_manager.create_child_category("General", ["service", "rest_api", "Installation"])
        except KeyError:
            _logger.error('Failed to create General parent configuration category for service')
            raise

        # Create the parent category for all advanced configuration categories
        try:
            await cls._configuration_manager.create_category("Advanced", {}, 'Advanced', True)
            await cls._configuration_manager.create_child_category("Advanced", ["SMNTR", "SCHEDULER", "LOGGING"])
        except KeyError:
            _logger.error('Failed to create Advanced parent configuration category for service')
            raise

        # Create the parent category for all Utilities configuration categories
        try:
            await cls._configuration_manager.create_category("Utilities", {}, "Utilities", True)
        except KeyError:
            _logger.error('Failed to create Utilities parent configuration category for task')
            raise

    @classmethod
    async def _start_asset_tracker(cls):
        cls._asset_tracker = AssetTracker(cls._storage_client_async)
        await cls._asset_tracker.load_asset_records()

    @classmethod
    async def _get_alerts(cls):
        cls._alert_manager = AlertManager(cls._storage_client_async)
        await cls._alert_manager.get_all()

    @classmethod
    def _start_core(cls, loop=None):
        if cls.running_in_safe_mode:
            _logger.info("Starting in SAFE MODE ...")
        else:
            _logger.info("Starting ...")
        try:
            host = cls._host

            cls.core_app = cls._make_core_app()
            cls.core_server, cls.core_server_handler = cls._start_app(loop, cls.core_app, host, 0)
            address, cls.core_management_port = cls.core_server.sockets[0].getsockname()
            _logger.info('Management API started on http://%s:%s', address, cls.core_management_port)
            # see http://<core_mgt_host>:<core_mgt_port>/fledge/service for registered services
            # start storage
            loop.run_until_complete(cls._start_storage(loop))

            # get storage client
            loop.run_until_complete(cls._get_storage_client())

            if not cls.running_in_safe_mode:
                # If readings table is empty, set last_object of all streams to 0
                cls._check_readings_table(loop)

            # obtain configuration manager and interest registry
            cls._configuration_manager = ConfigurationManager(cls._storage_client_async)
            cls._interest_registry = InterestRegistry(cls._configuration_manager)

            # Logging category
            loop.run_until_complete(cls.core_logger_setup())

            # start scheduler
            # see scheduler.py start def FIXME
            # scheduler on start will wait for storage service registration
            #
            # NOTE: In safe mode, the scheduler will be in restricted mode,
            # and only API operations and current state will be accessible (No jobs / processes will be triggered)
            #
            loop.run_until_complete(cls._start_scheduler())

            # start monitor
            loop.run_until_complete(cls._start_service_monitor())

            loop.run_until_complete(cls.rest_api_config())
            cls.service_app = cls._make_app(auth_required=cls.is_auth_required, auth_method=cls.auth_method)

            # ssl context
            ssl_ctx = None
            if not cls.is_rest_server_http_enabled:
                cert, key = cls.get_certificates()
                _logger.info('Loading certificates %s and key %s', cert, key)

                # Verification handling of a tls cert
                with open(cert, 'r') as tls_cert_content:
                    tls_cert = tls_cert_content.read()
                SSLVerifier.set_user_cert(tls_cert)
                if SSLVerifier.is_expired():
                    msg = 'Certificate `{}` expired on {}'.format(cls.cert_file_name, SSLVerifier.get_enddate())
                    _logger.error(msg)

                    if cls.running_in_safe_mode:
                        cls.is_rest_server_http_enabled = True
                        # TODO: Should cls.rest_server_port be set to configured http port, as is_rest_server_http_enabled has been set to True?
                        msg = "Running in safe mode withOUT https on port {}".format(cls.rest_server_port)
                        _logger.info(msg)
                    else:
                        msg = 'Start in safe-mode to fix this problem!'
                        _logger.warning(msg)
                        raise SSLVerifier.VerificationError(msg)
                else:
                    ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                    ssl_ctx.load_cert_chain(cert, key)

            # Get the service data and advertise the management port of the core
            # to allow other microservices to find Fledge
            loop.run_until_complete(cls.service_config())
            _logger.info('Announce management API service')
            cls.management_announcer = ServiceAnnouncer("core-{}".format(cls._service_name), cls._MANAGEMENT_SERVICE, cls.core_management_port,
                                                        ['The Fledge Core REST API'])

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

            # Installation category
            loop.run_until_complete(cls.installation_config())

            # Create the configuration category parents
            loop.run_until_complete(cls._config_parents())

            if not cls.running_in_safe_mode:
                # Start asset tracker
                loop.run_until_complete(cls._start_asset_tracker())

                # Start Alert Manager
                loop.run_until_complete(cls._get_alerts())

                # If dispatcher installation:
                # a) not found then add it as a StartUp service
                # b) found then check the status of its schedule and take action
                is_dispatcher = loop.run_until_complete(cls.is_dispatcher_running(cls._storage_client_async))
                if not is_dispatcher:
                    _logger.info("Dispatcher service installation found on the system, but not in running state. "
                                 "Therefore, starting the service...")
                    loop.run_until_complete(cls.add_and_enable_dispatcher())
                    _logger.info("Dispatcher service started.")
                # dryrun execution of all the tasks that are installed but have schedule type other than STARTUP
                schedule_list = loop.run_until_complete(cls.scheduler.get_schedules())
                for sch in schedule_list:
                    # STARTUP type schedules and special FledgeUpdater schedule process name exclusion to avoid dryrun
                    if int(sch.schedule_type) != 1 and sch.process_name != "FledgeUpdater":
                        schedule_row = cls.scheduler._ScheduleRow(
                            id=sch.schedule_id,
                            name=sch.name,
                            type=sch.schedule_type,
                            time=(sch.time.hour * 60 * 60 + sch.time.minute * 60 + sch.time.second) if sch.time else 0,
                            day=sch.day,
                            repeat=sch.repeat,
                            repeat_seconds=sch.repeat.total_seconds() if sch.repeat else 0,
                            exclusive=sch.exclusive,
                            enabled=sch.enabled,
                            process_name=sch.process_name)
                        loop.run_until_complete(cls.scheduler._start_task(schedule_row, dryrun=True))
            # Everything is complete in the startup sequence, write the audit log entry
            cls._audit = AuditLogger(cls._storage_client_async)
            audit_msg = {"message": "Running in safe mode"} if cls.running_in_safe_mode else None
            loop.run_until_complete(cls._audit.information('START', audit_msg))
            if sys.version_info >= (3, 7, 1):
                ignore_aiohttp_ssl_eror(loop)
            loop.run_forever()
        except SSLVerifier.VerificationError as e:
            sys.stderr.write('Error: ' + format(str(e)) + "\n")
            loop.run_until_complete(cls.stop_storage())
            sys.exit(1)
        except (OSError, RuntimeError, TimeoutError) as e:
            sys.stderr.write('Error: ' + format(str(e)) + "\n")
            sys.exit(1)
        except Exception as e:
            sys.stderr.write('Error: ' + format(str(e)) + "\n")
            sys.exit(1)

    @classmethod
    def _register_core(cls, host, mgt_port, service_port):
        core_service_id = ServiceRegistry.register(name="Fledge Core", s_type="Core", address=host,
                                                     port=service_port, management_port=mgt_port)

        return core_service_id

    @classmethod
    def start(cls, is_safe_mode=False):
        """Starts Fledge"""
        #
        # is_safe_mode: When True, It prevents the start of any services or tasks other than the storage layer.
        # Starting Fledge in this way would mean only the core and storage services would be running.
        # And Scheduler will be running in restricted mode.
        #
        cls.running_in_safe_mode = is_safe_mode
        loop = asyncio.get_event_loop()
        cls._start_core(loop=loop)

    @classmethod
    async def _stop(cls):
        """Stops Fledge"""
        try:
            # stop monitor
            await cls.stop_service_monitor()

            # stop the scheduler
            await cls._stop_scheduler()

            await cls.stop_microservices()

            # poll microservices for unregister
            await cls.poll_microservices_unregister()

            # stop the REST api (exposed on service port)
            await cls.stop_rest_server()

            # Must write the audit log entry before we stop the storage service
            cls._audit = AuditLogger(cls._storage_client_async)
            audit_msg = {"message": "Exited from safe mode"} if cls.running_in_safe_mode else None
            await cls._audit.information('FSTOP', audit_msg)

            # stop storage
            await cls.stop_storage()

            # stop core management api
            # loop.stop does it all

            # Remove PID file
            cls._remove_pid()
        except Exception:
            raise

    @classmethod
    async def stop_rest_server(cls):
        # Delete all user tokens
        await User.Objects.delete_all_user_tokens()
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
            found_services = ServiceRegistry.get(name="Fledge Storage")
        except service_registry_exceptions.DoesNotExist:
            raise

        svc = found_services[0]
        if svc is None:
            _logger.info("Fledge Storage shut down requested, but could not be found.")
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
                if fs._name in ("Fledge Storage", "Fledge Core"):
                    continue
                if fs._status not in [ServiceRecord.Status.Running, ServiceRecord.Status.Unresponsive]:
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
            _logger.exception(ex)

    @classmethod
    async def _request_microservice_shutdown(cls, svc):
        """ request service's shutdown """
        management_api_url = 'http://{}:{}/fledge/service/shutdown'.format(svc._address, svc._management_port)
        # TODO: need to set http / https based on service protocol
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
                    _logger.info("Shutdown scheduled for %s service %s. %s", svc._type, svc._name, response['message'])
                except KeyError:
                    raise

    @classmethod
    async def poll_microservices_unregister(cls):
        """ poll microservice shutdown endpoint for non core micro-services"""

        def get_process_id(name):
            """Return process ids found by (partial) name or regex."""
            child = subprocess.Popen(['pgrep', '-f', 'name={}'.format(name)], stdout=subprocess.PIPE, shell=False)
            response = child.communicate()[0]
            return [int(_pid) for _pid in response.split()]

        try:
            shutdown_threshold = 0
            found_services = ServiceRegistry.get()
            _service_shutdown_threshold = 5 * (len(found_services) - 2)
            while True:
                services_to_stop = list()
                for fs in found_services:
                    if fs._name in ("Fledge Storage", "Fledge Core"):
                        continue
                    if fs._status not in [ServiceRecord.Status.Running, ServiceRecord.Status.Unresponsive]:
                        continue
                    services_to_stop.append(fs)
                if len(services_to_stop) == 0:
                    _logger.info("All microservices, except Core and Storage, have been shutdown.")
                    return
                if shutdown_threshold > _service_shutdown_threshold:
                    for fs in services_to_stop:
                        pids = get_process_id(fs._name)
                        for pid in pids:
                            _logger.error("Microservice:%s status: %s has NOT been shutdown. Killing it...", fs._name, fs._status)
                            os.kill(pid, signal.SIGKILL)
                            _logger.info("KILLED Microservice:%s...", fs._name)
                    return
                await asyncio.sleep(2)
                shutdown_threshold += 2
                found_services = ServiceRegistry.get()

        except service_registry_exceptions.DoesNotExist:
            pass
        except Exception as ex:
            _logger.exception(ex)

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
        return web.json_response({'uptime': int(since_started)})

    @classmethod
    async def register(cls, request):
        """ Register a service

        :Example:
            curl -d '{"type": "Storage", "name": "Storage Services", "address": "127.0.0.1", "service_port": 8090,
                "management_port": 1090, "protocol": "https"}' -X POST http://localhost:<core mgt port>/fledge/service
            curl -d '{"type": "N1", "name": "Micro Service", "address": "127.0.0.1", "service_port": 9091,
                "management_port": 1090, "protocol": "https", "token": "SVCNAME_ABCDE"}' -X POST
                http://localhost:<core mgt port>/fledge/service
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
            token = data.get('token', None)

            if not (service_name.strip() or service_type.strip() or service_address.strip()
                    or service_management_port.strip() or not service_management_port.isdigit()):
                raise web.HTTPBadRequest(reason='One or more values for type/name/address/management port missing')

            if service_port is not None:
                if not (isinstance(service_port, int)):
                    raise web.HTTPBadRequest(reason="Service's service port can be a positive integer only")

            if not isinstance(service_management_port, int):
                raise web.HTTPBadRequest(reason='Service management port can be a positive integer only')

            if token is None and ServiceRegistry.getStartupToken(service_name) is not None:
                raise web.HTTPBadRequest(body=json.dumps({"message": 'Required registration token is missing.'}))

            # If token, then check single use token verification; if bad then return 4XX
            if token is not None:
                if not isinstance(token, str):
                    msg = 'Token can be a string only'
                    raise web.HTTPBadRequest(reason=msg)

                # Check startup token exists
                if ServiceRegistry.checkStartupToken(service_name, token) == False:
                    msg = 'Token for the service was not found'
                    raise web.HTTPBadRequest(reason=msg)

            try:
                registered_service_id = ServiceRegistry.register(service_name, service_type, service_address,
                                                                 service_port, service_management_port,
                                                                 service_protocol, token)
                try:
                    if not cls._storage_client_async is None:
                        cls._audit = AuditLogger(cls._storage_client_async)
                        await cls._audit.information('SRVRG', {'name': service_name})
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

            bearer_token = ''
            # Create a JWT token if startup token exists
            if token is not None:
                # Set JWT bearer token
                # Set expiration now + delta seconds
                exp = int(time.time()) + SERVICE_JWT_EXP_DELTA_SECONDS
                # Add public token claims
                claims = {
                             'aud': service_type,
                             'sub': service_name,
                             'iss': SERVICE_JWT_AUDIENCE,
                             'exp': exp
                         }

                # Create JWT token
                bearer_token = jwt.encode(claims, SERVICE_JWT_SECRET, SERVICE_JWT_ALGORITHM) if token is not None else ""

                # Add the bearer token for that service being registered
                ServiceRegistry.addBearerToken(service_name, bearer_token)

            # Prepare response JSON
            _response = {
                'id': registered_service_id,
                'message': "Service registered successfully",
                'bearer_token': bearer_token
            }

            _logger.debug("For service: {} SERVER RESPONSE: {}".format(service_name, _response))

            return web.json_response(_response)

        except ValueError as err:
            msg = str(err)
            raise web.HTTPNotFound(reason=msg, body=json.dumps(msg))

    @classmethod
    async def unregister(cls, request):
        """ Unregister a service

        :Example:
            curl -X DELETE  http://localhost:<core mgt port>/fledge/service/dc9bfc01-066a-4cc0-b068-9c35486db87f
        """

        try:
            service_id = request.match_info.get('service_id', None)

            try:
                services = ServiceRegistry.get(idx=service_id)
            except service_registry_exceptions.DoesNotExist:
                raise ValueError('Service with {} does not exist'.format(service_id))

            ServiceRegistry.unregister(service_id)

            if cls._storage_client_async is not None and services[0]._name not in ("Fledge Storage", "Fledge Core"):
                try:
                    cls._audit = AuditLogger(cls._storage_client_async)
                    await cls._audit.information('SRVUN', {'name': services[0]._name})
                except Exception as ex:
                    _logger.exception(ex)

            _resp = {'id': str(service_id), 'message': 'Service unregistered'}

            return web.json_response(_resp)
        except ValueError as ex:
            raise web.HTTPNotFound(reason=str(ex))

    @classmethod
    async def restart_service(cls, request):
        """ Restart a service

        :Example:
            curl -X PUT  http://localhost:<core mgt port>/fledge/service/dc9bfc01-066a-4cc0-b068-9c35486db87f/restart
        """
        try:
            service_id = request.match_info.get('service_id', None)
            try:
                services = ServiceRegistry.get(idx=service_id)
            except service_registry_exceptions.DoesNotExist:
                raise ValueError('Service with {} does not exist'.format(service_id))

            ServiceRegistry.restart(service_id)
            if cls._storage_client_async is not None and services[0]._name not in ("Fledge Storage", "Fledge Core"):
                try:
                    cls._audit = AuditLogger(cls._storage_client_async)
                    await cls._audit.information('SRVRS', {'name': services[0]._name})
                except Exception as ex:
                    _logger.exception(ex)
                """ Special Case:
                    For BucketStorage type we have used proxy map for interfacing REST API endpoints 
                    to Microservice service API endpoints. Therefore we need to clear the proxy map on restart.
                """
                if services[0]._type == "BucketStorage":
                    cls._API_PROXIES = {}
        except ValueError as err:
            msg = str(err)
            raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
        except Exception as ex:
            msg = str(ex)
            raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
        else:
            _resp = {'id': str(service_id), 'message': 'Service restart requested'}
            return web.json_response(_resp)

    @classmethod
    async def get_service(cls, request):
        """ Returns a list of all services or as per name &|| type filter

        :Example:
            curl -X GET  http://localhost:<core mgt port>/fledge/service
            curl -X GET  http://localhost:<core mgt port>/fledge/service?name=X&type=Storage
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
            svc["status"] = ServiceRecord.Status(int(service._status)).name.lower()
            if service._port:
                svc["service_port"] = service._port
            services.append(svc)

        return web.json_response({"services": services})

    @classmethod
    async def get_auth_token(cls, request: web.Request) -> web.Response:
        """ get auth token
            :Example:
                curl -sX GET -H "{'Authorization': 'Bearer ..'}" http://localhost:<core mgt port>/fledge/service/authtoken
        """
        async def cert_login(ca_cert):
            certs_dir = _FLEDGE_DATA + '/etc/certs' if _FLEDGE_DATA else _FLEDGE_ROOT + "/data/etc/certs"
            ca_cert_file = "{}/{}.cert".format(certs_dir, ca_cert)
            SSLVerifier.set_ca_cert(ca_cert_file)
            # FIXME: allow to supply content and any cert name as placed with configured CA sign
            with open('{}/{}'.format(certs_dir, "admin.cert"), 'r') as content_file:
                cert_content = content_file.read()
            SSLVerifier.set_user_cert(cert_content)
            SSLVerifier.verify()
            username = SSLVerifier.get_subject()['commonName']
            _uid, _token, _is_admin = await User.Objects.certificate_login(username, host)
            return _token

        try:
            cfg_mgr = ConfigurationManager(cls._storage_client_async)
            category_info = await cfg_mgr.get_category_all_items('rest_api')
            is_auth_optional = True if category_info['authentication']['value'].lower() == 'optional' else False

            if is_auth_optional:
                raise api_exception.AuthenticationIsOptional

            auth_method = category_info['authMethod']['value']
            ca_cert_name = category_info['authCertificateName']['value']

            try:
                auth_header = request.headers.get('Authorization', None)
            except:
                raise api_exception.VerificationFailed
            else:
                if auth_header is None:
                    raise api_exception.VerificationFailed
                if not "Bearer " in auth_header:
                    raise api_exception.VerificationFailed
                # check bearer token with service registry for given service
                ##
                # the lines below are repated many times, make it a def for common usage/check
                parts = auth_header.split("Bearer ")
                if len(parts) != 2:
                    msg = "Bearer token is missing"
                    raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
                bearer_token = parts[1]
                # Validate token and get public claims
                claims = cls.validate_token(bearer_token)
                if claims.get('error'):
                    msg = "Service '" + str(claims['sub']) + "' not registered"
                    raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))

                if bearer_token != ServiceRegistry.getBearerToken(claims['sub']):
                    # add WARN log (audit?) for this attempt?!
                    raise api_exception.VerificationFailed
                else:
                    # add debug log for successful token verification
                    pass
                ##

            peername = request.transport.get_extra_info('peername')
            host = '0.0.0.0'
            if peername is not None:
                host, _ = peername

            # TODO: restrict host to 0.0.0.0, 127.0.0.1 or localhost?

            if auth_method == 'certificate':
                token = await cert_login(ca_cert_name)
            elif auth_method == 'password':
                # Super admin user always exists on the system
                # these can be configured diff for a/per services if required
                payload = payload_builder.PayloadBuilder().SELECT("uname", "pwd").WHERE(['id', '=', 1]).payload()
                result = await cls._storage_client_async.query_tbl_with_payload('users', payload)
                uid, token, is_admin = await User.Objects.login("admin", result['rows'][0]['pwd'], host)
            else:
                # For auth method "any" we can use either login with cert or password
                token = await cert_login(ca_cert_name)
                # TODO: if cert does not exist then may try with password
        except api_exception.AuthenticationIsOptional as err:
            msg = str(err)
            raise web.HTTPPreconditionFailed(reason=msg, body=json.dumps({"message": msg}))
        except api_exception.VerificationFailed:
            raise web.HTTPUnauthorized(body=json.dumps({"message": 'Required authorization token is missing or invalid.'}))
        except Exception as ex:
            msg = str(ex)
            raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
        return web.json_response({"token": token})

    @classmethod
    async def shutdown(cls, request):
        """ Shutdown the core microservice and its components

        :return: JSON payload with message key
        :Example:
            curl -X POST http://localhost:<core mgt port>/fledge/service/shutdown
        """
        try:
            await cls._stop()
            loop = request.loop
            # allow some time
            await asyncio.sleep(2.0, loop=loop)
            _logger.info("Stopping the Fledge Core event loop. Good Bye!")
            loop.stop()

            return web.json_response({'message': 'Fledge stopped successfully. '
                                                 'Wait for few seconds for process cleanup.'})
        except TimeoutError as err:
            raise web.HTTPInternalServerError(reason=str(err))
        except Exception as ex:
            raise web.HTTPInternalServerError(reason=str(ex))

    @classmethod
    async def restart(cls, request):
        """ Restart the core microservice and its components """
        try:
            await cls._stop()
            loop = request.loop
            # allow some time
            await asyncio.sleep(2.0, loop=loop)
            _logger.info("Stopping the Fledge Core event loop. Good Bye!")
            loop.stop()

            if 'safe-mode' in sys.argv:
                sys.argv.remove('safe-mode')
                sys.argv.append('')

            python3 = sys.executable
            os.execl(python3, python3, *sys.argv)

            return web.json_response({'message': 'Fledge stopped successfully. '
                                                 'Wait for few seconds for restart.'})
        except TimeoutError as err:
            raise web.HTTPInternalServerError(reason=str(err))
        except Exception as ex:
            raise web.HTTPInternalServerError(reason=str(ex))

    @classmethod
    async def register_interest(cls, request):
        """ Register an interest in a configuration category

        :Example:
            curl -d '{"category": "COAP", "service": "x43978x8798x"}' -X POST http://localhost:<core mgt port>/fledge/interest
        """

        try:
            data = await request.json()
            category_name = data.get('category', None)
            microservice_uuid = data.get('service', None)

            try:
                value = data.get('child', None)
                if value is not None:

                    if value == "True":
                        child_subscribe = True
                    else:
                        child_subscribe = False
                else:
                    child_subscribe = False

            except:
                child_subscribe = False

            if microservice_uuid is not None:
                try:
                    assert uuid.UUID(microservice_uuid)
                except:
                    raise ValueError('Invalid microservice id {}'.format(microservice_uuid))

            if child_subscribe:

                try:
                    registered_interest_id = cls._interest_registry.register_child(microservice_uuid, category_name)
                except interest_registry_exceptions.ErrorInterestRegistrationAlreadyExists:
                    raise web.HTTPBadRequest(reason='An InterestRecord already exists by microservice_uuid {} for category_name {}'.format(microservice_uuid, category_name))

                if not registered_interest_id:
                    raise web.HTTPBadRequest(reason='Interest by microservice_uuid {} for category_name {} could not be registered'.format(microservice_uuid, category_name))

                _response = {
                    'id': registered_interest_id,
                    'message': "Interest registered successfully"
                }


            else:
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

        except ValueError as ex:
            raise web.HTTPBadRequest(reason=str(ex))

        return web.json_response(_response)

    @classmethod
    async def unregister_interest(cls, request):
        """ Unregister an interest

        :Example:
            curl -X DELETE  http://localhost:<core mgt port>/fledge/interest/dc9bfc01-066a-4cc0-b068-9c35486db87f
        """

        try:
            interest_registration_id = request.match_info.get('interest_id', None)

            try:
                assert uuid.UUID(interest_registration_id)
            except:
                raise web.HTTPBadRequest(reason="Invalid registration id {}".format(interest_registration_id))

            try:
                cls._interest_registry.get(registration_id=interest_registration_id)
            except interest_registry_exceptions.DoesNotExist:
                raise ValueError('InterestRecord with registration_id {} does not exist'.format(interest_registration_id))

            cls._interest_registry.unregister(interest_registration_id)

            _resp = {'id': str(interest_registration_id), 'message': 'Interest unregistered'}

        except ValueError as ex:
            raise web.HTTPNotFound(reason=str(ex))

        return web.json_response(_resp)

    @classmethod
    async def get_interest(cls, request):
        """ Returns a list of all interests or of the selected interest

        :Example:
                curl -X GET  http://localhost:{core_mgt_port}/fledge/interest
                curl -X GET  http://localhost:{core_mgt_port}/fledge/interest?microserviceid=X&category=Y
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

    @classmethod
    async def get_track(cls, request):
        res = await asset_tracker_api.get_asset_tracker_events(request)
        return res

    @classmethod
    async def add_track(cls, request):

        data = await request.json()

        if not isinstance(data, dict):
            raise ValueError('Data payload must be a dictionary')

        jsondata = data.get("data")

        try:
            if jsondata is None:

                result = await cls._asset_tracker.add_asset_record(asset=data.get("asset"),
                                                                   plugin=data.get("plugin"),
                                                                   service=data.get("service"),
                                                                   event=data.get("event"))
            else:
                result = await cls._asset_tracker.add_asset_record(asset=data.get("asset"),
                                                                   plugin=data.get("plugin"),
                                                                   service=data.get("service"),
                                                                   event=data.get("event"),
                                                                   jsondata=data.get("data"))

        except (TypeError, StorageServerError) as ex:
            raise web.HTTPBadRequest(reason=str(ex))
        except ValueError as ex:
            raise web.HTTPNotFound(reason=str(ex))
        except Exception as ex:
            raise web.HTTPInternalServerError(reason=ex)

        return web.json_response(result)

    @classmethod
    async def enable_disable_schedule(cls, request: web.Request) -> web.Response:
        data = await request.json()
        try:
            schedule_id = request.match_info.get('schedule_id', None)
            is_enabled = data.get('value', False)
            if is_enabled:
                status, reason = await cls.scheduler.enable_schedule(uuid.UUID(schedule_id))
            else:
                status, reason = await cls.scheduler.disable_schedule(uuid.UUID(schedule_id))
        except (TypeError, ValueError, KeyError) as err:
            raise web.HTTPBadRequest(reason=str(err), body=json.dumps({'message': str(err)}))
        except Exception as ex:
            raise web.HTTPInternalServerError(reason=str(ex), body=json.dumps({'message': str(ex)}))
        else:
            schedule = {
                'scheduleId': schedule_id,
                'status': status,
                'message': reason
            }
            return web.json_response(schedule)

    @classmethod
    async def refresh_cache(cls, request: web.Request) -> web.Response:
        from fledge.services.core.api.plugins import common

        data = await request.json()
        try:
            # At the moment only case to clear cache for available plugins
            # We may add with action & key combination basis later on
            common._get_available_packages.cache_clear()
            cls._package_cache_manager['list']['last_accessed_time'] = ""
        except (TypeError, ValueError, KeyError) as err:
            raise web.HTTPBadRequest(reason=str(err), body=json.dumps({'message': str(err)}))
        except Exception as ex:
            raise web.HTTPInternalServerError(reason=str(ex), body=json.dumps({'message': str(ex)}))
        else:
            return web.json_response({"message": "Refresh cache is completed"})

    @classmethod
    async def get_configuration_categories(cls, request):
        res = await conf_api.get_categories(request)
        return res

    @classmethod
    async def create_configuration_category(cls, request):
        request.is_core_mgt = True
        res = await conf_api.create_category(request)
        return res

    @classmethod
    async def delete_configuration_category(cls, request):
        res = await conf_api.delete_category(request)
        return res

    @classmethod
    async def create_child_category(cls, request):
        res = await conf_api.create_child_category(request)
        return res

    @classmethod
    async def get_child_category(cls, request):
        res = await conf_api.get_child_category(request)
        return res

    @classmethod
    async def get_configuration_category(cls, request):
        request.is_core_mgt = True
        res = await conf_api.get_category(request)
        return res

    @classmethod
    async def get_configuration_item(cls, request):
        request.is_core_mgt = True
        res = await conf_api.get_category_item(request)
        return res

    @classmethod
    async def update_configuration_item(cls, request):
        request.is_core_mgt = True
        res = await conf_api.set_configuration_item(request)
        return res

    @classmethod
    async def delete_configuration_item(cls, request):
        request.is_core_mgt = True
        res = await conf_api.delete_configuration_item_value(request)
        return res

    @classmethod
    async def add_audit(cls, request):
        data = await request.json()
        if not isinstance(data, dict):
            raise ValueError('Data payload must be a dictionary')

        try:
            code = data.get("source")
            level = data.get("severity")
            message = data.get("details")

            # Add audit entry code and message for the given level
            await getattr(cls._audit, str(level).lower())(code, message)

            # Set timestamp for return message
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

            # Return JSON message
            message = {'timestamp': str(timestamp),
                       'source': code,
                       'severity': level,
                       'details': message
                      }

        except (TypeError, StorageServerError) as ex:
            raise web.HTTPBadRequest(reason=str(ex))
        except ValueError as ex:
            raise web.HTTPNotFound(reason=str(ex))
        except Exception as ex:
            raise web.HTTPInternalServerError(reason=ex)

        return web.json_response(message)

    @classmethod
    async def verify_token(cls, request):
        """ Endpoint for verifycation of service bearer token received at registration time

        :Example:
            curl -H 'Authorization: Bearer evZGdrdmV.4dWFsY2dsaHVyZ.mFxdmdybXB5dXduaXJvc3g='
            -X POST http://localhost:<core mngmt port>/fledge/service/verity_token

        Authorization header must contain the Bearer token to verify
        No post data

        Note: token will be verified for the service name in token claim 'sub'
        """

        try:
            return web.json_response(cls.get_token_common(request))
        except Exception as e:
            msg = str(e)
            raise web.HTTPBadRequest(reason=msg, body=json.dumps({"error": msg}))

    @classmethod
    def validate_token(cls, token):
        """ Validate service bearer token
        """
        try:
            ret = jwt.decode(token, SERVICE_JWT_SECRET, algorithms=[SERVICE_JWT_ALGORITHM],
                             options={"verify_signature": True, "verify_aud": False, "verify_exp": True})
            return ret
        except Exception as e:
            return {'error': str(e)}

    @classmethod
    async def refresh_token(cls, request):
        """ Endpoint for refresh of service bearer token received at registration time

        :Example:
            curl -X POST
             -H 'Authorization: Bearer evZGdrdmV.4dWFsY2dsaHVyZ.mFxdmdybXB5dXduaXJvc3g='
             http://localhost:<core mngmt port>/fledge/service/refresh_token

        Authorization header must contain the Bearer token
        No post data

        Note: token will be refreshed for the service it belongs to
        """

        try:
            claims = cls.get_token_common(request)
            # Expiration set to now + delta
            claims['exp'] = int(time.time()) + SERVICE_JWT_EXP_DELTA_SECONDS
            bearer_token = jwt.encode(claims, SERVICE_JWT_SECRET, SERVICE_JWT_ALGORITHM)

            # Replace bearer_token for the service
            ServiceRegistry.addBearerToken(claims['sub'], bearer_token)
            ret = {'bearer_token': bearer_token}

            return web.json_response(ret)

        except Exception as e:
            msg = str(e)
            raise web.HTTPBadRequest(reason=msg, body=json.dumps({"error": msg}))

    @classmethod
    async def is_dispatcher_running(cls, storage):
        from fledge.services.core.api import service as service_api
        from fledge.common.storage_client.payload_builder import PayloadBuilder

        # Find the dispatcher service installation
        get_svc = service_api.get_service_installed()
        # if installation found:
        if 'dispatcher' in get_svc:
            payload = PayloadBuilder().SELECT("id", "schedule_name", "process_name", "enabled").payload()
            res = await storage.query_tbl_with_payload('schedules', payload)
            for sch in res['rows']:
                if sch['process_name'] == 'dispatcher_c' and sch['enabled'] == 'f':
                    _logger.info("Dispatcher service found but not in enabled state. "
                                 "Therefore, {} schedule name is enabled".format(sch['schedule_name']))
                    # reset process_script priority for the service
                    cls.scheduler._process_scripts['dispatcher_c'] = (
                        cls.scheduler._process_scripts['dispatcher_c'][0], 999)
                    await cls.scheduler.enable_schedule(uuid.UUID(sch["id"]))
                    return True
                elif sch['process_name'] == 'dispatcher_c' and sch['enabled'] == 't':
                    # As such no action required for the case
                    return True
            # If installation not found:
            return False
        return True

    @classmethod
    async def add_and_enable_dispatcher(cls):
        import datetime as dt
        from fledge.services.core.scheduler.entities import StartUpSchedule

        name = "dispatcher"
        process_name = 'dispatcher_c'
        is_enabled = True
        schedule = StartUpSchedule()
        schedule.name = name
        schedule.process_name = process_name
        schedule.repeat = dt.timedelta(0)
        schedule.exclusive = True
        schedule.enabled = False
        # Save schedule
        await cls.scheduler.save_schedule(schedule, is_enabled)

    @classmethod
    def get_token_common(cls, request):
        """ Get Bearer Token from request
            validate it and return token claims
        """
        auth_header = request.headers.get('Authorization', None)
        if auth_header is None:
            msg = "Authorization header is missing"
            raise web.HTTPBadRequest(reason=msg, body=json.dumps({"error": msg}))

        if not "Bearer " in auth_header:
            msg = "Invalid Authorization token"
            # FIXME: raise UNAUTHORISED here and among other places
            #   and JSON body to have message key
            raise web.HTTPBadRequest(reason=msg, body=json.dumps({"error": msg}))

        parts = auth_header.split("Bearer ")
        if len(parts) != 2:
            msg = "bearer token is missing"
            raise web.HTTPBadRequest(reason=msg, body=json.dumps({"error": msg}))

        bearer_token = parts[1]

        try:
            # Validate token and get public claims
            claims = cls.validate_token(bearer_token)
            if claims.get('error') is None:
                # Check input token exists in system for the service name given in claims['sub']
                foundToken = ServiceRegistry.getBearerToken(claims['sub'])
                if foundToken is None:
                    msg = "service '" + str(claims['sub']) + "' not registered"
                    raise web.HTTPBadRequest(reason=msg, body=json.dumps({"error": msg}))

                # Check input token is associated with service in claims['sub']
                if foundToken != bearer_token:
                    msg = "bearer token does not belong to service '" + str(claims['sub']) + "'"
                    raise web.HTTPBadRequest(reason=msg, body=json.dumps({"error": msg}))

                # Success
                return claims

            else:
                msg = claims.get('error')
                raise web.HTTPBadRequest(reason=msg, body=json.dumps({"error": msg}))

        except Exception as e:
            msg = str(e)
            raise web.HTTPBadRequest(reason=msg, body=json.dumps({"error": msg}))

    @classmethod
    async def get_control_acl(cls, request):
        request.is_core_mgt = True
        res = await acl_management.get_acl(request)
        return res

    @classmethod
    async def get_alert(cls, request):
        name = request.match_info.get('key', None)
        try:
            alert = await cls._alert_manager.get_by_key(name)
        except KeyError as err:
            msg = str(err.args[0])
            return web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
        except Exception as ex:
            msg = str(ex)
            _logger.error(ex, "Failed to get an alert.")
            raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
        else:
            return web.json_response({"alert": alert})

    @classmethod
    async def add_alert(cls, request):
        try:
            data = await request.json()
            key = data.get("key")
            message = data.get("message")
            urgency = data.get("urgency")
            if any(elem is None for elem in [key, message, urgency]):
                msg = 'key, message, urgency post params are required to raise an alert.'
                return web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
            if not all(isinstance(i, str) for i in [key, message, urgency]):
                msg = 'key, message, urgency KV pair must be passed as string.'
                return web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
            urgency = urgency.lower().capitalize()
            if urgency not in cls._alert_manager.urgency:
                msg = 'Urgency value should be from list {}'.format(list(cls._alert_manager.urgency.keys()))
                return web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
            key_exists = [a for a in cls._alert_manager.alerts if a['key'] == key]
            if key_exists:
                # Delete existing key
                await cls._alert_manager.delete(key)
            param = {"key": key, "message": message, "urgency": cls._alert_manager.urgency[urgency]}
            response = await cls._alert_manager.add(param)
            if response is None:
                raise Exception
        except Exception as ex:
            msg = str(ex)
            _logger.error(ex, "Failed to add an alert.")
            raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
        else:
            response['alert']['urgency'] = cls._alert_manager._urgency_name_by_value(response['alert']['urgency'])
            return web.json_response(response)
