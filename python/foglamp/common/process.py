# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Common FoglampProcess Class"""

from abc import ABC, abstractmethod
import argparse
import http.client
import json

from foglamp.common.storage_client.storage_client import ReadingsStorageClient, StorageClient
from foglamp.common import logger

__author__ = "Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_logger = logger.setup(__name__)


class ArgumentParserError(Exception):
    """ Overwrite default exception to not terminate application """
    pass


class FoglampProcess(ABC):
    """ FoglampProcess for all non-core python processes.

    All processes will inherit from FoglampProcess and must implement pure virtual method run()
    """

    _core_management_host = None
    """ string containing core's micro-service management host """

    _core_management_port = None
    """ int containing core's micro-service management port """

    _name = None
    """ name of process """

    _m_client = None
    """ MicroserviceManagementClient instance """

    _readings_storage = None
    """ foglamp.common.storage_client.storage_client.ReadingsStorageClient """

    _storage = None
    """ foglamp.common.storage_client.storage_client.StorageClient """

    def __init__(self):
        """ All processes must have these three command line arguments passed:

        --address [core microservice management host]
        --port [core microservice management port]
        --name [process name]
        """
        
        try:    
            self._core_management_host = self.get_arg_value("--address")
            self._core_management_port = self.get_arg_value("--port")
            self._name = self.get_arg_value("--name")
        except ArgumentParserError:
            raise
        if self._core_management_host is None:
            raise ValueError("--address is not specified")
        elif self._core_management_port is None:
            raise ValueError("--port is not specified")
        elif self._name is None:
            raise ValueError("--name is not specified")

        self._m_client = self.MicroserviceManagementClient(self._core_management_host,self._core_management_port)
        self._readings_storage = ReadingsStorageClient(self._core_management_host, self._core_management_port)
        self._storage = StorageClient(self._core_management_host, self._core_management_port)

    # pure virtual method run() to be implemented by child class
    @abstractmethod
    def run(self):
        pass

    def get_arg_value(self, argument_name):
        """ Parses command line arguments for a single argument of name argument_name. Returns the value of the argument specified or None if argument was not specified.

        Keyword Arguments:
        argument_name -- name of command line argument to retrieve value for
    
        Return Values:
            Argument value (as a string)
            None (if argument was not passed)
    
            Side Effects:
            None
    
            Known Exceptions:
            ArgumentParserError
        """
        class SilentArgParse(argparse.ArgumentParser):
            def error(self, message):
                raise ArgumentParserError(message)
        
        parser = SilentArgParse()
        parser.add_argument(argument_name)
        try:
            parser_result = parser.parse_known_args()
        except ArgumentParserError:
            raise
        else:
            return list(vars(parser_result[0]).values())[0]

    def register_service(self, service_registration_payload):
        """ Register, with core, this process as a microservice.

        Keyword Arguments:
            service_registration_payload -- json format dictionary

        Return Values:
            Argument value (as a string)
            None (if argument was not passed)

            Known Exceptions:
                HTTPError
        """
        self._m_client.register_service(service_registration_payload)

    class MicroserviceManagementClient(object):
        _management_client_conn = None

        def __init__(self, core_management_host, core_management_port):
            self._management_client_conn = http.client.HTTPConnection("{0}:{1}".format(core_management_host, core_management_port))

        def register_service(self, service_registration_payload):
            # register with core
            self._management_client_conn.request(method='POST', url='/foglamp/service', body=json.dumps(service_registration_payload))
            r = self._management_client_conn.getresponse()
            if r.status in range(400, 500):
                r.raise_for_status()
            if r.status in range(500, 600):
                r.raise_for_status()
            res = r.read().decode()
            self._management_client_conn.close()
            response = json.loads(res)
            try:
                cls._microservice_id = response["id"]
            except KeyError:
                _logger.exception("Could not register the microservice, From request %s", json.dumps(service_registration_payload))
                raise
            except Exception as ex:
                _logger.exception("Could not register the microservice, From request %s, Reason: %s", json.dumps(service_registration_payload), str(ex))
                raise

        def unregister_service(self, microservice_id):
            # unregister with core
            self._management_client_conn.request(method='DELETE', url='/foglamp/service/{}'.format(microservice_id))
            r = self._management_client_conn.getresponse()
            if r.status in range(400, 500):
                r.raise_for_status()
            if r.status in range(500, 600):
                r.raise_for_status()
            res = r.read().decode()
            self._management_client_conn.close()
            response = json.loads(res)
            try:
                assert microservice_id == response["id"]
                # assert "Service unregistered" == response["message"]
            except KeyError:
                _logger.exception("Could not un-register the micro-service having uuid %s", microservice_id)
                raise
            except Exception as ex:
                _logger.exception("Could not un-register the micro-service having uuid %s, Reason: %s", microservice_id, str(ex))
                raise

        def register_interest(self):
            pass

        def unregister_interest(self):
            pass

        def get_services(self, name=None, type=None):
            pass


