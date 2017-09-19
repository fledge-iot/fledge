# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Storage layer python client
"""

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

from abc import ABC, abstractmethod

from foglamp import logger
from foglamp.core.service_registry.service_registry import Service

_LOGGER = logger.setup(__name__)


class AbstractStorage(ABC):
    """ abstract class for storage client
    """

    def __init__(self, service):
        self._service = service
        super(AbstractStorage, self).__init__()

    @property
    def service(self):
        return self._service

    @service.setter
    def service(self, svc):
        if not isinstance(svc, Service):
            w_msg = 'Storage should be a valid FogLAMP micro-service instance'
            _LOGGER.warning(w_msg)
            raise TypeError(w_msg)

    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def disconnect(self):
        pass

    # Allow with context

    def __enter__(self):
        return self.connect()

    def __exit__(self, *args):
        self.disconnect()


class Storage(AbstractStorage):

    def connect(self):
        # TODO: (Praveen) connect to storage service
        print(("Connecting to service: %s", self._service.__repr__))
        return self

    def disconnect(self):
        # TODO: (Praveen) disconnect storage service
        print("Disconnecting service")
        pass

    # TODO: check, is it assumed on bootstrapping init data will also be in
    # the same way as \i ddl?
    # or each service will do it individually as needed the same way as config?
    def insert_into_tbl(self, tbl_name, data):
        print(tbl_name, data)
        pass

    def update_tbl(self, tbl_name, data):
        pass

    def delete_from_tbl(self, tbl_name):
        pass

    def query_tbl(self, tbl_name):
        pass


class Readings(object):

    @staticmethod
    def append(conn, readings):
        print("append", readings)
        conn.insert_into_tbl("foglamp.readings", readings)
        pass

    @staticmethod
    def fetch(reading_id, size):
        pass

    @staticmethod
    def query(query):
        pass

    # TODO: these value shall be picked by purge and passed to it?
    @staticmethod
    def purge(age, sent_id, purge_unsent=False):
        pass
