# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Services Instances Registry module"""

import time
import uuid
from enum import IntEnum
from foglamp import logger

__author__ = "Praveen Garg, Amarendra Kumar Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class Service:

    class Type(IntEnum):  # IntEnum ?
        """Enumeration for Service Types"""
        Storage = 1
        Device = 2

    __slots__ = ['_id', '_name', '_type', '_address', '_port']

    def __init__(self, s_id, s_name, s_type, s_address, s_port):
        self._id = s_id
        self._name = s_name
        self._type = self.valid_type(s_type)  # check with Service.Type, if not a valid type raise error
        self._address = s_address
        self._port = s_port

    def __repr__(self):
        template = 'service instance id={s._id}: <{s._name}, type={s._type}>'
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

    class InvalidServiceType(BaseException):
        # TODO: tell allowed service types?
        pass

    class Instances:
        _registry = list()
        _logger = logger.setup(__name__)

        @classmethod
        def register(cls, name, s_type, address, port):
            # TODO: Do we need to add check for an existing service with the same characteristics?
            # For example, can we have two Storage services with different names but at same address:port?
            #              can we have two Storage services with different names but at different address:port?

            service_id = uuid.uuid4()
            registered_service = Service(str(service_id), name, s_type, address, port)
            cls._registry.append(registered_service)
            cls._logger.info("Service {} registered at {}".format(str(registered_service), time.time()))
            return registered_service

        @classmethod
        def unregister(cls, service_id):
            services = cls.get(idx=service_id)
            cls._registry.remove(services[0])
            cls._logger.info("Service {} unregistered at {}".format(str(services[0]), time.time()))
            return service_id

        @classmethod
        def all(cls):
            return cls._registry

        @classmethod
        def filter(cls, **kwargs):
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



