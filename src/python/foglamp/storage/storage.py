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
import http.client
import json

from foglamp import logger
from foglamp.core.service_registry.service_registry import Service
from foglamp.storage.exceptions import *

_LOGGER = logger.setup(__name__)


class AbstractStorage(ABC):

    """ abstract class for storage client
    """

    def __init__(self, service):
        self.service = service
        super(AbstractStorage, self).__init__()

    @property
    def service(self):
        return self.__service

    @service.setter
    def service(self, svc):
        if not isinstance(svc, Service):
            w_msg = 'Storage should be a valid FogLAMP micro-service instance'
            _LOGGER.warning(w_msg)
            raise InvalidServiceInstance

        if not getattr(svc, "_type") == "Storage":
            w_msg = 'Storage should be a valid *Storage* micro-service instance'
            _LOGGER.warning(w_msg)
            raise InvalidServiceInstance
        # ignore inspection
        self.__service = svc

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

    def __init__(self):
        # TODO: (Praveen) do via http
        try:
            storage_services = Service.Instances.get(name="store")
            self.service = storage_services[0]
            self.base_url = '{}:{}'.format(self.service._address, self.service._port)
        except Service.DoesNotExist:
            raise InvalidServiceInstance

    def connect(self):
        # TODO: (Praveen) connect to storage service
        print("Connecting to service: %s", self.service.__repr__)
        return self

    def disconnect(self):
        # TODO: (Praveen) disconnect storage service
        print("Disconnecting service")

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

    def query_tbl(self, tbl_name, query=None):
        conn = http.client.HTTPConnection(self.base_url)
        # TODO: need to set http / https based on service protocol

        get_url = '/storage/table/{tbl_name}'.format(tbl_name=tbl_name, q=query)
        if query:
            get_url += '?{}'.format(query)

        # remove this print
        print(get_url)
        conn.request('GET', url=get_url)
        r = conn.getresponse()
        # remove this assert
        assert 200 == r.status
        res = r.read().decode()
        conn.close()
        return json.loads(res)

    def query_tbl_with_payload(self, tbl_name, query_payload):
        conn = http.client.HTTPConnection(self.base_url)
        # TODO: need to set http / https based on service protocol
        q_tbl_url = '/storage/table/{tbl_name}/query'.format(tbl_name=tbl_name)
        # remove this print
        print(q_tbl_url)
        conn.request('PUT', url=q_tbl_url, body=query_payload)
        r = conn.getresponse()
        # remove this print
        print(r.status)
        res = r.read().decode()
        conn.close()
        return json.loads(res)


class Readings(object):
    """ Readings table operations"""

    _TABLE = 'readings'

    @classmethod
    def append(cls, conn, readings):
        print("append", readings)
        conn.insert_into_tbl(cls._TABLE, readings)

    @classmethod
    def fetch(cls, reading_id, size):
        pass

    @classmethod
    def query(cls, query):
        pass

    # TODO: these value shall be picked from purge config and passed to it?
    @classmethod
    def purge(cls, age, sent_id, purge_unsent=False):
        pass
