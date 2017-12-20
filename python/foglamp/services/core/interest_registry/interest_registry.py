import uuid
from foglamp.common import logger
from foglamp.services.core.interest_registry.interest_record import InterestRecord
from foglamp.services.core.interest_registry import exceptions as interest_registry_exceptions
_LOGGER = logger.setup(__name__)
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
    
    def and_filter(self, **kwargs):
        interest_records = None
        interest_records = [s for s in self._registered_interests if all(getattr(s, k, None) == v for k, v in kwargs.items() if v is not None)]
        return interest_records

    def get(self, registration_id=None, category_name=None, microservice_uuid=None):
        interest_records = self.and_filter(_registration_id=registration_id, _category_name=category_name, _microservice_uuid=microservice_uuid)
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

    def unregister(self, registration_id):
        registered_interests = self.get(registration_id=registration_id)
        self._registered_interests.remove(registered_interests[0])
        _LOGGER.info("Unregistered interest with id {}".format(str(registered_interests[0])))
        return registration_id


