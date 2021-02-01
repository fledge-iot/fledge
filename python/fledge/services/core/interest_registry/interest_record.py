# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

"""Interest Record Class"""

__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

class InterestRecord(object):
    """Stores a single interest registration for notification changes 
    """

    def __init__(self, registration_id, microservice_uuid, category_name):
        self._registration_id = registration_id
        """ interest registration id """
        
        self._microservice_uuid = microservice_uuid
        """ microservice interested in the change """
        
        self._category_name = category_name
        """ configuration category name of interest """

    def __repr__(self):
        template = 'interest registration id={s._registration_id}: <microservice uuid={s._microservice_uuid}, category_name={s._category_name}>'
        return template.format(s=self)

    def __str__(self):
        return self.__repr__()


