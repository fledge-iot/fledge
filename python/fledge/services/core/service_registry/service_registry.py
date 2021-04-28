# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

"""Services Registry class"""

import uuid
import asyncio
from fledge.common import logger
from fledge.common.service_record import ServiceRecord
from fledge.services.core.service_registry import exceptions as service_registry_exceptions
from fledge.services.core.interest_registry.interest_registry import InterestRegistry

__author__ = "Praveen Garg, Amarendra Kumar Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class ServiceRegistry:

    _registry = list()
    # INFO - level 20
    _logger = logger.setup(__name__, level=20)

    @classmethod
    def register(cls, name, s_type, address, port, management_port,  protocol='http', token=None):
        """ registers the service instance
       
        :param name: name of the service
        :param s_type: a valid service type; e.g. Storage, Core, Southbound
        :param address: any IP or host address
        :param port: a valid positive integer
        :param management_port: a valid positive integer for management operations e.g. ping, shutdown
        :param protocol: defaults to http
        :param token: authentication bearer token

        :return: registered services' uuid
        """

        new_service = True
        try:
            current_service = cls.get(name=name)
        except service_registry_exceptions.DoesNotExist:
            pass
        else:
            # Re: FOGL-1123
            if current_service[0]._status in [ServiceRecord.Status.Running, ServiceRecord.Status.Unresponsive]:
                raise service_registry_exceptions.AlreadyExistsWithTheSameName
            else:
                new_service = False
                current_service_id = current_service[0]._id

        if port is not None and cls.check_address_and_port(address, port):
            raise service_registry_exceptions.AlreadyExistsWithTheSameAddressAndPort

        if cls.check_address_and_mgt_port(address, management_port):
            raise service_registry_exceptions.AlreadyExistsWithTheSameAddressAndManagementPort

        if port is not None and (not isinstance(port, int)):
            raise service_registry_exceptions.NonNumericPortError

        if not isinstance(management_port, int):
            raise service_registry_exceptions.NonNumericPortError

        if new_service is False:
            # Remove current service to enable the service to register with new management port etc
            cls.remove_from_registry(current_service_id)

        service_id = str(uuid.uuid4()) if new_service is True else current_service_id
        registered_service = ServiceRecord(service_id, name, s_type, protocol, address, port, management_port, token)
        cls._registry.append(registered_service)
        cls._logger.info("Registered {}".format(str(registered_service)))
        return service_id

    @classmethod
    def _expunge(cls, service_id, service_status):
        """ removes the service instance from action

        :param service_id: a uuid of registered service
        :param service_status: service status to be marked
        :return: service_id on successful deregistration
        """
        services = cls.get(idx=service_id)
        service_name = services[0]._name
        services[0]._status = service_status
        cls._remove_from_scheduler_records(service_name)

        # Remove interest registry records, if any
        interest_recs = InterestRegistry().get(microservice_uuid=service_id)
        for interest_rec in interest_recs:
            InterestRegistry().unregister(interest_rec._registration_id)

        return services[0]

    @classmethod
    def unregister(cls, service_id):
        """ deregisters the service instance

        :param service_id: a uuid of registered service
        :return: service_id on successful deregistration
        """
        expunged_service = cls._expunge(service_id, ServiceRecord.Status.Shutdown)
        cls._logger.info("Stopped {}".format(str(expunged_service)))
        return service_id

    @classmethod
    def mark_as_failed(cls, service_id):
        """ marks the service instance as failed

        :param service_id: a uuid of registered service
        :return: service_id on successful deregistration
        """
        expunged_service = cls._expunge(service_id, ServiceRecord.Status.Failed)
        cls._logger.info("Mark as failed {}".format(str(expunged_service)))
        return service_id

    @classmethod
    def remove_from_registry(cls, service_id):
        """ remove service_id from service_registry.

        :param service_id: a uuid of registered service
        """
        services = cls.get(idx=service_id)
        cls._registry.remove(services[0])

    @classmethod
    def _remove_from_scheduler_records(cls, service_name):
        """ removes service aka STARTUP from Scheduler internal records

        :param service_name
        :return:
        """
        if service_name in ("Fledge Storage", "Fledge Core"): return

        # Require a local import in order to avoid circular import references
        from fledge.services.core import server
        if server.Server.scheduler is None: return
        asyncio.ensure_future(server.Server.scheduler.remove_service_from_task_processes(service_name))

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
        services = [s for s in cls._registry if getattr(s, "_address") == address and getattr(s, "_port") == port and getattr(s, "_status") != ServiceRecord.Status.Failed]
        if len(services) == 0:
            return False
        return True

    @classmethod
    def check_address_and_mgt_port(cls, address, m_port):
        # AND based check
        # ugly hack! <Make filter to support AND | OR>
        services = [s for s in cls._registry if getattr(s, "_address") == address
                    and getattr(s, "_management_port") == m_port and getattr(s, "_status") != ServiceRecord.Status.Failed]
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
