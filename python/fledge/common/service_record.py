# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

"""Service Record Class"""

from enum import IntEnum

__author__ = "Praveen Garg, Amarendra Kumar Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class ServiceRecord(object):
    """Used to information regarding a registered microservice.
    """

    class Type(IntEnum):
        """Enumeration for Service Types"""

        Storage = 1
        Core = 2
        Southbound = 3
        Notification = 4
        Management = 5
        Northbound = 6
        Dispatcher = 7

    class Status(IntEnum):
        """Enumeration for Service Status"""

        Running = 1
        Shutdown = 2
        Failed = 3
        Unresponsive = 4

    class InvalidServiceType(Exception):
        # TODO: tell allowed service types?
        pass

    class InvalidServiceStatus(Exception):
        # TODO: tell allowed service status?
        pass

    __slots__ = ['_id', '_name', '_type', '_protocol', '_address', '_port', '_management_port', '_status', '_token']

    def __init__(self, s_id, s_name, s_type, s_protocol, s_address, s_port, m_port, s_token=None):
        self._id = s_id
        self._name = s_name
        self._type = self.valid_type(s_type)  # check with ServiceRecord.Type, if not a valid type raise error
        self._protocol = s_protocol
        self._address = s_address
        self._port = None
        if s_port is not None:
            self._port = int(s_port)
        self._management_port = int(m_port)
        self._status = ServiceRecord.Status.Running
        self._token = s_token if s_token is not None else None

    def __repr__(self):
        template = 'service instance id={s._id}: <{s._name}, type={s._type}, protocol={s._protocol}, ' \
                   'address={s._address}, service port={s._port}, management port={s._management_port}, ' \
                   'status={s._status}, token={s._token}>'
        return template.format(s=self)

    def __str__(self):
        return self.__repr__()

    def valid_type(self, s_type):
        if s_type not in ServiceRecord.Type.__members__:
            raise ServiceRecord.InvalidServiceType
        return s_type
