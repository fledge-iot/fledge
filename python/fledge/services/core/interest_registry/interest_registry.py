# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

"""Interest Registry Class"""

import uuid
from fledge.common.configuration_manager import ConfigurationManager
from fledge.common import logger
from fledge.services.core.interest_registry.interest_record import InterestRecord
from fledge.services.core.interest_registry import exceptions as interest_registry_exceptions

__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_LOGGER = logger.setup(__name__)
NOTIFY_CHANGE_CALLBACK = "fledge.services.core.interest_registry.change_callback"


class InterestRegistrySingleton(object):
    """This class is used to provide singlton functionality to InterestRegistry
    """

    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state


class InterestRegistry(InterestRegistrySingleton):
    """Used by core to manage microservices' interests in configuration changes.

    Inherits from InterestRegistrySingleton to make it a singleton

    """

    _registered_interests = None
    """ maintains the list of InterestRecord objects """

    _configuration_manager = None
    """ ConfigurationManager used by InterestRegistry """

    def __init__(self, configuration_manager=None):
        """ Used to create InterestRegistry object

        Args:
            configuration_manager (ConfigurationManager): configuration_manager instance to use

        """

        InterestRegistrySingleton.__init__(self)
        if self._configuration_manager is None:
            if not isinstance(configuration_manager, ConfigurationManager):
                raise TypeError('Must be a valid ConfigurationManager object')
            self._configuration_manager = configuration_manager
        if self._registered_interests is None:
            self._registered_interests = list()
    
    def and_filter(self, **kwargs):
        """ Used to filter InterestRecord objects based on attribute values.
        """
        interest_records = None
        interest_records = [s for s in self._registered_interests if all(getattr(s, k, None) == v for k, v in kwargs.items() if v is not None)]
        return interest_records

    def get(self, registration_id=None, category_name=None, microservice_uuid=None):
        """ Used to filter InterestRecord objects based on attribute values.
        Args:
            registration_id (str): registration_id uuid as a string (optional)
            category_name (str): category of interest (optional)
            microservice_uuid (str): interested party - microservice uuid as a string (optional)
        """
        interest_records = self.and_filter(_registration_id=registration_id, _category_name=category_name, _microservice_uuid=microservice_uuid)
        if len(interest_records) == 0:
            raise interest_registry_exceptions.DoesNotExist
        return interest_records

    def register(self, microservice_uuid, category_name):
        """ Used to add an entry to the InterestRegistry
        Args:
            category_name (str): category of interest (required)
            microservice_uuid (str): interested party - microservice_uuid as a string (required)
        Note:
            category_name, microservice_uuid pair must be unique
        Returns:
            registration id of new InterestRegistration entry
        Raises:
            fledge.services.core.interest_registry.exceptions.ErrorInterestRegistrationAlreadyExists
                in the event that the microservice_uuid, category_name pair is already registered
        """
        if microservice_uuid is None:
            raise ValueError('Failed to register interest. microservice_uuid cannot be None')
        if category_name is None:
            raise ValueError('Failed to register interest. category_name cannot be None')

        try:
            self.get(microservice_uuid=microservice_uuid, category_name=category_name)
        except interest_registry_exceptions.DoesNotExist:
            pass
        else:
            raise interest_registry_exceptions.ErrorInterestRegistrationAlreadyExists

        # register callback with configuration manager
        self._configuration_manager.register_interest(category_name, NOTIFY_CHANGE_CALLBACK)
        # get registration_id
        registration_id = str(uuid.uuid4())
        # create new InterestRecord
        registered_interest = InterestRecord(registration_id, microservice_uuid, category_name)
        # add interest record to list of registered interests
        self._registered_interests.append(registered_interest)

        return registration_id

    def unregister(self, registration_id):
        """ Used to remove an entry from the InterestRegistry
        Args:
            registration_id (str): id (uuid as a string) of InterestRegistration entry to remove
        Returns:
            registration id of removed interest record
        Raises:
            fledge.services.core.interest_registry.exceptions.DoesNotExist
                in the event that the registration id does not have a corresponding entry in the registry
        """
        # remove entry from list in InterestRegistry
        try: 
            registered_interests = self.get(registration_id=registration_id)
            interest_record = registered_interests[0]
            self._registered_interests.remove(registered_interests[0])
        except interest_registry_exceptions.DoesNotExist:
            raise
        # remove entry from configuration manager if no registered interests exist for this category_name
        try: 
            registered_interests = self.get(category_name=interest_record._category_name)
        except interest_registry_exceptions.DoesNotExist:
            self._configuration_manager.unregister_interest(interest_record._category_name, NOTIFY_CHANGE_CALLBACK)
        _LOGGER.info("Unregistered interest with id {}".format(str(registered_interests[0])))
        return registration_id


