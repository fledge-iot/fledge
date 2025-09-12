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
    """Used to information regarding a registered microservice."""

    class Status(IntEnum):
        """Enumeration for Service Status"""

        Running = 1
        Shutdown = 2
        Failed = 3
        Unresponsive = 4
        Restart = 5


    class InvalidServiceStatus(Exception):
        # TODO: tell allowed service status?
        pass

    __slots__ = ['_id', '_name', '_type', '_protocol', '_address', '_port', '_management_port', '_status', '_debug']

    def __init__(self, s_id, s_name, s_type, s_protocol, s_address, s_port, m_port):
        self._id = s_id
        self._name = s_name
        self._type = s_type
        self._protocol = s_protocol
        self._address = s_address
        self._port = None
        if s_port is not None:
            self._port = int(s_port)
        self._management_port = int(m_port)
        self._status = ServiceRecord.Status.Running
        self._debug = {}

    def __repr__(self):
        template = 'service instance id={s._id}: <{s._name}, type={s._type}, protocol={s._protocol}, ' \
                   'address={s._address}, service port={s._port}, management port={s._management_port}, ' \
                   'status={s._status}>'
        return template.format(s=self)

    def __str__(self):
        return self.__repr__()

