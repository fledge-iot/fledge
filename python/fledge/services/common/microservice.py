# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

"""Common FledgeMicroservice Class"""

from aiohttp import web
from fledge.services.common.microservice_management import routes
from fledge.common import logger
from fledge.common.process import FledgeProcess
from fledge.common.web import middleware
from abc import abstractmethod
import time
import json
import asyncio

__author__ = "Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_logger = logger.setup(__name__)


class FledgeMicroservice(FledgeProcess):
    """ FledgeMicroservice class for all non-core python microservices
        All microservices will inherit from FledgeMicroservice and implement pure virtual method run()
    """
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

    _type = None
    """ microservice type """

    _protocol = "http"
    """ communication protocol """

    def __init__(self):
        super().__init__()
        try:
            # Configuration handled through the Configuration Manager
            default_config = {
                'local_services': {
                    'description': 'Restrict microservices to localhost',
                    'type': 'boolean',
                    'default': 'false',
                    'displayName': 'Restrict Microservices To Local'
                }
            }

            loop = asyncio.get_event_loop()

            category = "Security"
            config = default_config
            config_descr = 'Microservices Security'
            config_payload = json.dumps({
                "key": category,
                "description": config_descr,
                "value": config,
                "keep_original_items": True
            })
            self._core_microservice_management_client.create_configuration_category(config_payload)
            self._core_microservice_management_client.create_child_category("General", ["Security"])
            config = self._core_microservice_management_client.get_configuration_category(category_name=category)
            is_local_services = True if config['local_services']['value'].lower() == 'true' else False
            host = '127.0.0.1' if is_local_services is True else '0.0.0.0'

            self._make_microservice_management_app()
            self._run_microservice_management_app(loop, host)
            res = self.register_service_with_core(self._get_service_registration_payload())
            self._microservice_id = res["id"]
        except Exception as ex:
            _logger.exception('Unable to intialize FledgeMicroservice due to exception %s', str(ex))
            raise

    def _make_microservice_management_app(self):
        # create web server application
        self._microservice_management_app = web.Application(middlewares=[middleware.error_middleware])
        # register supported urls
        routes.setup(self._microservice_management_app, self)
        # create http protocol factory for handling requests
        self._microservice_management_handler = self._microservice_management_app.make_handler()

    def _run_microservice_management_app(self, loop, host='127.0.0.1'):
        # run microservice_management_app
        coro = loop.create_server(self._microservice_management_handler, host, 0)
        self._microservice_management_server = loop.run_until_complete(coro)
        self._microservice_management_host, self._microservice_management_port = \
            self._microservice_management_server.sockets[0].getsockname()

    def _get_service_registration_payload(self):
        service_registration_payload = {
                "name": self._name,
                "type": self._type,
                "management_port": int(self._microservice_management_port),
                "service_port": int(self._microservice_management_port),
                "address": self._microservice_management_host,
                "protocol": self._protocol
            }
        return service_registration_payload

    @abstractmethod
    async def shutdown(self, request):
        pass

    @abstractmethod
    async def change(self, request):
        pass

    async def ping(self, request):
        """ health check
    
        """
        since_started = time.time() - self._start_time
        return web.json_response({'uptime': since_started})
