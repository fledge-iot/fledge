from foglamp.common.storage_client.storage_client import ReadingsStorageClient, StorageClient
from abc import ABC, abstractmethod
import argparse
import http.client
import json

__author__ = "Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

class ArgumentParserError(Exception):
    pass

class FoglampProcess(ABC):
    _core_management_host = None
    _core_management_port = None
    _name = None
    _m_client = None
    _readings_storage = None
    _storage = None


    def __init__(self):
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
        self._m_client.register_service(service_registration_payload)


    class MicroserviceManagementClient(object):
        _management_client_conn = None

        def __init__(self,core_management_host, core_management_port):
            self._management_client_conn = http.client.HTTPConnection("{0}:{1}".format(core_management_host, core_management_port))

        def register_service(self, service_registration_payload):
            # register with core
            self._management_client_conn.request(method='POST', url='/foglamp/service', body=json.dumps(service_registration_payload))
            r = self._management_client_conn.getresponse()
            if r.status in range(400, 500):
                # _LOGGER.error("Client error code: %d", r.status)
                r.raise_for_status()
            if r.status in range(500, 600):
                # _LOGGER.error("Server error code: %d", r.status)
                r.raise_for_status()
            res = r.read().decode()
            self._management_client_conn.close()
            response = json.loads(res)
            try:
                cls._microservice_id = response["id"]
                # _LOGGER.info('Device - Registered Service %s', response["id"])
            except:
                pass
                #_LOGGER.error("Device - Could not register")

        def unregister_service(self):
            pass
        def register_interest(self):
            pass
        def unregister_interest(self):
            pass
        def get_services(self):
            pass


