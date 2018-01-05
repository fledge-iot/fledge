# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Services Registry class"""

import uuid
from foglamp.common import logger
from foglamp.common.service_record import ServiceRecord
from foglamp.services.core.service_registry import exceptions as service_registry_exceptions

__author__ = "Praveen Garg, Amarendra Kumar Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class ServiceRegistry:

    _registry = list()
    # INFO - level 20
    _logger = logger.setup(__name__, level=20)

    @classmethod
    def register(cls, name, s_type, address, port, management_port,  protocol='http'):
        """ registers the service instance
       
        :param name: name of the service
        :param s_type: a valid service type; e.g. Storage, Core, Southbound
        :param address: any IP or host address
        :param port: a valid positive integer
        :param management_port: a valid positive integer for management operations e.g. ping, shutdown
        :param protocol: defaults to http
        :return: registered services' uuid
        """

        try:
            cls.get(name=name)
        except service_registry_exceptions.DoesNotExist:
            pass
        else:
            raise service_registry_exceptions.AlreadyExistsWithTheSameName

        if port is not None and cls.check_address_and_port(address, port):
            raise service_registry_exceptions.AlreadyExistsWithTheSameAddressAndPort

        if cls.check_address_and_mgt_port(address, management_port):
            raise service_registry_exceptions.AlreadyExistsWithTheSameAddressAndManagementPort

        if port is not None and (not isinstance(port, int)):
            raise service_registry_exceptions.NonNumericPortError
        if not isinstance(management_port, int):
            raise service_registry_exceptions.NonNumericPortError

        service_id = str(uuid.uuid4())
        registered_service = ServiceRecord(service_id, name, s_type, protocol, address, port, management_port)
        cls._registry.append(registered_service)
        cls._logger.info("Registered {}".format(str(registered_service)))
        return service_id

    @classmethod
    def unregister(cls, service_id):
        """ deregisters the service instance

        :param service_id: a uuid of registered service
        :return: service_id on successful deregistration
        """
        services = cls.get(idx=service_id)
        cls._registry.remove(services[0])
        cls._logger.info("Unregistered {}".format(str(services[0])))
        return service_id

    @classmethod
    def all(cls):
        return cls._registry

    @classmethod
    def filter(cls, **kwargs):
        # OR based filter
        services = cls._registry
        for k, v in kwargs.items():
            if v:
                services = [s for s in cls._registry if getattr(s, k, None) == v]
        return services

    @classmethod
    def get(cls, idx=None, name=None, s_type=None):
        services = cls.filter(_id=idx, _name=name, _type=s_type)
        if len(services) == 0:
            raise service_registry_exceptions.DoesNotExist
        return services

    @classmethod
    def check_address_and_port(cls, address, port):
        # AND based check
        # ugly hack! <Make filter to support AND | OR>
        services = [s for s in cls._registry if getattr(s, "_address") == address and getattr(s, "_port") == port]
        if len(services) == 0:
            return False
        return True

    @classmethod
    def check_address_and_mgt_port(cls, address, m_port):
        # AND based check
        # ugly hack! <Make filter to support AND | OR>
        services = [s for s in cls._registry if getattr(s, "_address") == address
                    and getattr(s, "_management_port") == m_port]
        if len(services) == 0:
            return False
        return True

    @classmethod
    def filter_by_name_and_type(cls, name, s_type):
        # AND based check
        # ugly hack! <Make filter to support AND | OR>
        services = [s for s in cls._registry if getattr(s, "_name") == name and getattr(s, "_type") == s_type]
        if len(services) == 0:
            raise service_registry_exceptions.DoesNotExist
        return services
