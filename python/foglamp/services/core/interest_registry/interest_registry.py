import uuid
from foglamp.common import logger
from foglamp.services.core.interest_registry.interest_record import InterestRecord
from foglamp.services.core.interest_registry import exceptions as interest_registry_exceptions

_NOTIFY_CHANGE_CALLBACK = "foglamp.services.core.interest_registry.change_callback"
class InterestRegistrySingleton(object):
    _shared_state = {}
    def __init__(self):
        self.__dict__ = self._shared_state

class InterestRegistry(InterestRegistrySingleton):
    _registered_interests = list()
    def __init__(self, configuration_manager):
        InterestRegistrySingleton.__init__(self)
        self._configuration_manager = configuration_manager
    
    def filter(self, **kwargs):
        # OR based filter
        interest_records = None
#        for k, v in kwargs.items():
#            if v:
#                interest_records = [s for s in self._registered_interests if getattr(s, k, None) == v]
        interest_records = [s for s in self._registered_interests if all(getattr(s, k, None) == v for k, v in kwargs.items() if v is not None)]
        return interest_records

    def get(self, registration_id=None, category_name=None, microservice_uuid=None):
        interest_records = self.filter(_registration_id=registration_id, _category_name=category_name, _microservice_uuid=microservice_uuid)
        if len(interest_records) == 0:
            raise interest_registry_exceptions.DoesNotExist
        return interest_records


    def register(self, microservice_uuid, category_name):
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

        self._configuration_manager.register_interest(category_name, _NOTIFY_CHANGE_CALLBACK)

        registration_id = str(uuid.uuid4())
        registered_interest = InterestRecord(registration_id, microservice_uuid, category_name)
        self._registered_interests.append(registered_interest)
        return registration_id

    def unregister(self, category_name, callback):
        pass
        """Unregisters an interest in any changes to the category_value associated with category_name

        Keyword Arguments:
        category_name -- name of the category_name of interest (required)
        callback -- module with implementation of run(category_name) to be called when change is made to category_value

        Return Values:
        None

        Side Effects:
        Unregisters an interest in any changes to the category_value of a given category_name with the associated callback.
        This interest is maintained in memory only, and not persisted in storage.

        Restrictions and Usage:
        A particular category_name may have multiple registered interests, aka multiple callbacks associated with a single category_name.
        One or more category_names may use the same callback when a change is made to the corresponding category_value.
        """
