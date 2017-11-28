# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Common FoglampMicroservice Class"""

import asyncio
from aiohttp import web
import http.client
import json
from foglamp.services.common.microservice_management import routes
from foglamp.common.process import FoglampProcess
from foglamp.common.web import middleware


__author__ = "Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

class FoglampMicroservice(FoglampProcess):
    """ FoglampMicroservice class for all non-core python microservices
        All microservices will inherit from FoglampMicroservice and implement pure virtual method run()
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
            self._make_microservice_management_app()
        except Exception:
            #_LOGGER.exception("Unable to create microservice management app")
            raise
        try:
            loop = asyncio.get_event_loop()
            self._run_microservice_management_app(loop)
        except Exception:
            #_LOGGER.exception("Unable to run microservice management app")
            raise
        try:
            self.register_service(self._get_service_registration_payload())
        except Exception:
            #_LOGGER.exception("Unable to register")
            raise

    def _make_microservice_management_app(self):
        # create web server application
        self._microservice_management_app = web.Application(middlewares=[middleware.error_middleware])
        # register supported urls
        routes.setup(self._microservice_management_app)
        # create http protocol factory for handling requests
        self._microservice_management_handler = self._microservice_management_app.make_handler()

    @classmethod
    def _run_microservice_management_app(self, loop):
        # run microservice_management_app
        core = loop.create_server(self._microservice_management_handler, '0.0.0.0', 0)
        self._microservice_management_server = loop.run_until_complete(core)
        self._microservice_management_host, self._microservice_management_port = \
            self._microservice_management_server.sockets[0].getsockname()
        #_LOGGER.info('Device - Management API started on http://%s:%s',
        #             self._microservice_management_host,
        #             self._microservice_management_port)


    @classmethod
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

