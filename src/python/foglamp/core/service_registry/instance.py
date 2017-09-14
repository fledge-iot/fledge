# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Services Instances Registry module"""

import uuid
from enum import IntEnum
from foglamp import logger

__author__ = "Praveen Garg, Amarendra Kumar Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class Service(object):

    class Type(IntEnum):  # IntEnum ?
        """Enumeration for Service Types"""
        Storage = 1
        Device = 2

    __slots__ = ['_id', '_name', '_type', '_protocol', '_address', '_port']

    def __init__(self, s_id, s_name, s_type, s_protocol, s_address, s_port):
        self._id = s_id
        self._name = s_name
        self._type = self.valid_type(s_type)  # check with Service.Type, if not a valid type raise error
        self._protocol = s_protocol
        self._address = s_address
        self._port = int(s_port)
        # TODO: MUST
        # well, reserve the core api PORT
        # or keep core service registered as default

    def __repr__(self):
        template = 'service instance id={s._id}: <{s._name}, type={s._type}, protocol={s._protocol}, ' \
                   'address={s._address}, port={s._port}>'
        return template.format(s=self)

    def __str__(self):
        return self.__repr__()

    def valid_type(self, s_type):
        if s_type not in Service.Type.__members__:
            raise Service.InvalidServiceType
        return s_type

    class DoesNotExist(BaseException):
        pass

    class AlreadyExistsWithTheSameName(BaseException):
        pass

    class AlreadyExistsWithTheSameAddressAndPort(BaseException):
        pass

    class InvalidServiceType(BaseException):
        # TODO: tell allowed service types?
        pass

    class NonNumericPortError(TypeError):
        # TypeError('Service port can be a positive integer only')
        pass

    class ReservedPortError(ValueError):
        pass

    class Instances:
        _registry = list()
        # INFO - level 20
        _logger = logger.setup(__name__, level=20)

        @classmethod
        def register(cls, name, s_type, address, port, protocol='http'):
            """ registers the service instance
           
            :param name: name of the service
            :param s_type: a valid service type; e.g. Storage, Device
            :param address: any IP or host address
            :param port: a valid postive integer
            :param protocol: defaults to http
            :return: registered services' uuid
            """

            try:
                cls.get(name=name)
            except Service.DoesNotExist:
                pass
            else:
                raise Service.AlreadyExistsWithTheSameName

            if cls.check_address_and_port(address, port):
                raise Service.AlreadyExistsWithTheSameAddressAndPort
            if not isinstance(port, int):
                raise Service.NonNumericPortError
            if int(port) == 8082:
                raise Service.ReservedPortError

            service_id = str(uuid.uuid4())
            registered_service = Service(service_id, name, s_type, protocol, address, port)
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
                raise Service.DoesNotExist
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
        def filter_by_name_and_type(cls, name, s_type):
            # AND based check
            # ugly hack! <Make filter to support AND | OR>
            services = [s for s in cls._registry if getattr(s, "_name") == name and getattr(s, "_type") == s_type]
            if len(services) == 0:
                raise Service.DoesNotExist
            return services
