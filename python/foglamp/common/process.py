# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Common FoglampProcess Class"""

from abc import ABC, abstractmethod
import argparse
import http.client
import json
import time

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
    
    _start_time = None
    """ time at which this python process started """

    def __init__(self):
        """ All processes must have these three command line arguments passed:

        --address [core microservice management host]
        --port [core microservice management port]
        --name [process name]
        """
        
        self._start_time = time.time()

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

        return self._m_client.register_service(service_registration_payload)

    def unregister_service(self):
        """ UnRegister, with core, this process as a microservice.
        """
        return self._m_client.unregister_service(self.microservice_id)

    def get_service(self, name=None, _type=None):
        return self._m_client.get_services(name, _type)

    def register_interest(self):
        # cat name
        # callback module
        # self.microservice_id
        raise NotImplementedError

    def deregister_interest(self):
        # cat name
        # self.microservice_id
        raise NotImplementedError

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
                response["id"]
            except KeyError:
                error = response["error"]
                _logger.exception("Could not register the microservice, From request %s, Got error %s", json.dumps(service_registration_payload), error)
            except Exception as ex:
                _logger.exception("Could not register the microservice, From request %s, Reason: %s", json.dumps(service_registration_payload), str(ex))
                raise

            return response

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
                response["id"]
                # assert microservice_id = response["id"]
                # assert "Service unregistered" == response["message"]
            except KeyError:
                error = response["error"]
                _logger.exception("Could not un-register the micro-service having uuid %s, "
                                  "Got error: %s", microservice_id, error)
            except Exception as ex:
                _logger.exception("Could not un-register the micro-service having uuid %s, "
                                  "Reason: %s", microservice_id, str(ex))
                raise

            return response

        def register_interest(self):
            # TODO
            # check with python/foglamp/services/common/microservice_management/service_registry/service_registry.py
            # And routing problem
            pass

        def unregister_interest(self):
            # TODO
            # check with python/foglamp/services/common/microservice_management/service_registry/service_registry.py
            # And routing problem
            pass

        def get_services(self, name=None, _type=None):
            url = '/foglamp/service'
            if _type:
                url = '{}?type={}'.format(url, _type)
            if name:
                url = '{}?name={}'.format(url, name)
            if name and _type:
                url = '{}?name={}&type={}'.format(url, name, _type)
            self._management_client_conn.request(method='GET', url=url)
            r = self._management_client_conn.getresponse()
            if r.status in range(400, 500):
                r.raise_for_status()
            if r.status in range(500, 600):
                r.raise_for_status()
            res = r.read().decode()
            self._management_client_conn.close()
            response = json.loads(res)
            try:
                response["services"]
            except KeyError:
                error = response["error"]
                _logger.exception("Could not find the micro-service for request url %s, Got error: %s", url, error)
            except Exception as ex:
                _logger.exception("Could not find the micro-service for request url %s, Reason: %s", url, str(ex))
                raise

            return response
