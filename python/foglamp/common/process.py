# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Common FoglampProcess Class"""

from abc import ABC, abstractmethod
import argparse
import time

from foglamp.common.storage_client.storage_client import ReadingsStorageClient, StorageClient
from foglamp.common import logger
from foglamp.common.microservice_management_client.microservice_management_client import MicroserviceManagementClient

__author__ = "Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_logger = logger.setup(__name__)


class ArgumentParserError(Exception):
    """ Override default exception to not terminate application """
    pass


class SilentArgParse(argparse.ArgumentParser):

    def error(self, message):
        """ Override default error functionality to not terminate application """
        raise ArgumentParserError(message)

    def silent_arg_parse(self, argument_name):
        self.add_argument(argument_name)
        parser_result = self.parse_known_args()
        return list(vars(parser_result[0]).values())[0]


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

    _core_microservice_management_client = None
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

        self._core_microservice_management_client = MicroserviceManagementClient(self._core_management_host,self._core_management_port)
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
        parser = SilentArgParse()
        return parser.silent_arg_parse(argument_name)
        
    def get_services_from_core(self, name=None, _type=None):
        return self._core_microservice_management_client.get_services(name, _type)

    def register_service_with_core(self, service_registration_payload):
        """ Register a microservice with core

        Keyword Arguments:
            service_registration_payload -- json format dictionary

        Return Values:
            Argument value (as a string)
            None (if argument was not passed)

            Known Exceptions:
                HTTPError
        """

        return self._core_microservice_management_client.register_service(service_registration_payload)

    def unregister_service_with_core(self, microservice_id):
        """ Unregister a microservice with core

        Keyword Arguments:
            microservice_id (uuid as a string)
        """
        return self._core_microservice_management_client.unregister_service(microservice_id)

    def register_interest_with_core(self):
        # cat name
        # callback module
        # self.microservice_id
        raise NotImplementedError

    def unregister_interest_with_core(self):
        # cat name
        # self.microservice_id
        raise NotImplementedError

    def get_configuration_categories(self):
        """

        :return:
        """
        return self._core_microservice_management_client.get_configuration_category()

    def get_configuration_category(self, category_name=None):
        """

        :param category_name:
        :return:
        """
        return self._core_microservice_management_client.get_configuration_category(category_name)

    def get_configuration_item(self, category_name, config_item):
        """

        :param category_name:
        :param config_item:
        :return:
        """
        return self._core_microservice_management_client.get_configuration_item(category_name, config_item)

    def create_configuration_category(self, category_data):
        """

        :param category_data:
        :return:
        """
        return self._core_microservice_management_client.create_configuration_category(category_data)

    def update_configuration_item(self, category_name, config_item):
        """

        :param category_name:
        :param config_item:
        :return:
        """
        return self._core_microservice_management_client.update_configuration_item(category_name, config_item)

    def delete_configuration_item(self, category_name, config_item):
        """

        :param category_name:
        :param config_item:
        :return:
        """
        return self._core_microservice_management_client.delete_configuration_item(category_name, config_item)

