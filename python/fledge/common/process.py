# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

"""Common FledgeProcess Class"""

from abc import ABC, abstractmethod
import argparse
import time
from fledge.common.storage_client.storage_client import StorageClientAsync, ReadingsStorageClientAsync
from fledge.common import logger
from fledge.common.microservice_management_client.microservice_management_client import MicroserviceManagementClient

__author__ = "Ashwin Gopalakrishnan, Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_logger = logger.setup(__name__)


class ArgumentParserError(Exception):
    """ Override default exception to not terminate application """

    def __init__(self, message):
        self.message = message

    def __str__(self):
        fmt = '%(message)s'
        return fmt % dict(message=self.message)


class SilentArgParse(argparse.ArgumentParser):
    def error(self, message):
        """ Override default error functionality to not terminate application """
        raise ArgumentParserError(message)


class FledgeProcess(ABC):
    """ FledgeProcess for all non-core python processes.

    All processes will inherit from FledgeProcess and must implement pure virtual method run()
    """

    _core_management_host = None
    """ string containing core's micro-service management host """

    _core_management_port = None
    """ int containing core's micro-service management port """

    _name = None
    """ name of process """

    _core_microservice_management_client = None
    """ MicroserviceManagementClient instance """

    _readings_storage_async = None
    """ fledge.common.storage_client.storage_client.ReadingsStorageClientAsync """

    _storage_async = None
    """ async fledge.common.storage_client.storage_client.StorageClientAsync """

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
            parser = SilentArgParse()
            parser.add_argument("--name", required=True)
            parser.add_argument("--address", required=True)
            parser.add_argument("--port", required=True, type=int)
            namespace, args = parser.parse_known_args()
            self._name = getattr(namespace, 'name')
            self._core_management_host = getattr(namespace, 'address')
            self._core_management_port = getattr(namespace, 'port')
            r = range(1, 65536)
            if self._core_management_port not in r:
                raise ArgumentParserError("Invalid Port: {}".format(self._core_management_port))
            for item in args:
                if item.startswith('--'):
                    kv = item.split('=')
                    if len(kv) == 2:
                        if len(kv[1].strip()) == 0:
                            raise ArgumentParserError("Invalid value {} for optional arg {}".format(kv[1], kv[0]))

        except ArgumentParserError as ex:
            _logger.error("Arg parser error: %s", str(ex))
            raise

        self._core_microservice_management_client = MicroserviceManagementClient(self._core_management_host,
                                                                                 self._core_management_port)

        self._readings_storage_async = ReadingsStorageClientAsync(self._core_management_host,
                                                                  self._core_management_port)
        self._storage_async = StorageClientAsync(self._core_management_host, self._core_management_port)

    # pure virtual method run() to be implemented by child class
    @abstractmethod
    def run(self):
        pass

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

