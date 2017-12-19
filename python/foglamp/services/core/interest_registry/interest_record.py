
class InterestRecord(object):
    def __init__(self, registration_id, microservice_uuid, category_name):
        self._registration_id = registration_id
        self._microservice_uuid = microservice_uuid
        self._category_name = category_name

    def __repr__(self):
        template = 'interest registration id={s._registration_id}: <microservice uuid={s._microservice_uuid}, category_name={s._category_name}>'
        return template.format(s=self)

    def __str__(self):
        return self.__repr__()


