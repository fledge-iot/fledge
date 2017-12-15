from enum import IntEnum
from foglamp.common import logger

__author__ = "Praveen Garg, Amarendra Kumar Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class ServiceRecord(object):

    class Type(IntEnum):
        """Enumeration for Service Types"""

        Storage = 1
        Core = 2
        Southbound = 3

    class InvalidServiceType(Exception):
        # TODO: tell allowed service types?
        pass

    __slots__ = ['_id', '_name', '_type', '_protocol', '_address', '_port', '_management_port', '_status']

    def __init__(self, s_id, s_name, s_type, s_protocol, s_address, s_port, m_port):
        self._id = s_id
        self._name = s_name
        self._type = self.valid_type(s_type)  # check with Service.Type, if not a valid type raise error
        self._protocol = s_protocol
        self._address = s_address
        self._port = None
        if s_port != None:
            self._port = int(s_port)
        self._management_port = int(m_port)
        self._status = 0
        # TODO: MUST
        # well, reserve the self PORT?

    def __repr__(self):
        template = 'service instance id={s._id}: <{s._name}, type={s._type}, protocol={s._protocol}, ' \
                   'address={s._address}, service port={s._port}, management port={s._management_port}, status={s._status}>'
        return template.format(s=self)

    def __str__(self):
        return self.__repr__()

    def valid_type(self, s_type):
        if s_type not in Service.Type.__members__:
            raise Service.InvalidServiceType
        return s_type

