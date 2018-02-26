# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Services Registry class"""

import uuid
import asyncio
import time
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
        service_name = services[0]._name
        cls._registry.remove(services[0])
        cls._logger.info("Unregistered {}".format(str(services[0])))
        cls._remove_from_scheduler_records(service_name)
        return service_id

    @classmethod
    def _remove_from_scheduler_records(cls, service_name):
        """ removes service aka STARTUP from Scheduler internal records

        :param service_name
        :return:
        """
        if service_name in ("FogLAMP Storage", "FogLAMP Core"):
            return

        # Require a local import in order to avoid circular import references
        from foglamp.services.core import server

        if server.Server.scheduler is None:
            return

        future = asyncio.ensure_future(server.Server.scheduler.remove_service_from_task_processes(service_name))

        def get_future_status():
            return future.done()

        this_time = time.time()
        future_status = False

        # Wait for future to be completed or timeout whichever is earlier
        while time.time() - this_time <= 5.0:
            # We need to fetch status of "future" via event loop only
            future_status = asyncio.get_event_loop().call_soon(get_future_status)
            if future_status is True:
                break

        if future_status is False:
            cls._logger.exception("Timeout exception in Scheduler cleanup during shutdown of {}".format(service_name))
            raise TimeoutError("Timeout exception in Scheduler cleanup during shutdown of {}".format(service_name))

        return

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
