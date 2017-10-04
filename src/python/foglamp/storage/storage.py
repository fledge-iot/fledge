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
from foglamp.storage.utils import Utils

_LOGGER = logger.setup(__name__)


class AbstractStorage(ABC):
    """ abstract class for storage client """

    def __init__(self):
        super().__init__()

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
        # discover the Storage type the service: how do we know the instance name?
        # with type there can be multiple instances (as allowed)
        # TODO: (Praveen) do via http
        try:
            storage_services = Service.Instances.get(name="store")
            self.service = storage_services[0]
            self.base_url = '{}:{}'.format(self.service._address, self.service._port)
        except Service.DoesNotExist:
            raise InvalidServiceInstance

    @property
    def base_url(self):
        return self.__base_url

    @base_url.setter
    def base_url(self, url):
        self.__base_url = url

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

        self.__service = svc

    def check_service_availibility(self):
        """ ping Storage service """

        print("Connecting to service: %s", self.service.__repr__)
        conn = http.client.HTTPConnection(self.base_url)
        # TODO: need to set http / https based on service protocol

        get_url = '/storage/ping'
        conn.request('GET', url=get_url)
        r = conn.getresponse()

        # TODO: log error with message if status is 4xx or 5xx
        if r.status in range(400, 500):
            _LOGGER.error("Client error code: %d", r.status)
        if r.status in range(500, 600):
            _LOGGER.error("Server error code: %d", r.status)

        res = r.read().decode()
        conn.close()
        return json.loads(res)

    def connect(self):
        return self

    def disconnect(self):
        pass

    def insert_into_tbl(self, tbl_name, data):
        """ insert json payload into given table

        :param tbl_name:
        :param data: JSON payload
        :return:

        :Example:
            curl -X POST http://0.0.0.0:8080/storage/table/statistics_history -d @payload2.json
            @payload2.json content:
            
            {
                "key" : "SENT_test",
                "history_ts" : "now()",
                "value" : 1
            }
        """
        conn = http.client.HTTPConnection(self.base_url)
        # TODO: need to set http / https based on service protocol

        post_url = '/storage/table/{tbl_name}'.format(tbl_name=tbl_name)
        if not data:
            raise ValueError("Data to insert is missing")

        if not Utils.is_json(data):
            raise TypeError("Provided data to insert must be a valid JSON")

        conn.request('POST', url=post_url, body=data)
        r = conn.getresponse()

        # TODO: log error with message if status is 4xx or 5xx
        if r.status in range(400, 500):
            _LOGGER.error("Client error code: %d", r.status)
        if r.status in range(500, 600):
            _LOGGER.error("Server error code: %d", r.status)

        res = r.read().decode()
        conn.close()
        return json.loads(res)

    def update_tbl(self, tbl_name, data):
        """ update json payload for specified condition into given table

        :param tbl_name:
        :param data: JSON payload
        :return:

        :Example:
            curl -X PUT http://0.0.0.0:8080/storage/table/statistics_history -d @payload3.json
            @payload3.json content:
            {
                "condition" : {
                    "column" : "key",
                    "condition" : "=",
                    "value" : "SENT_test"
                },
                "values" : {
                    "value" : 44444
                }
            }
        """
        conn = http.client.HTTPConnection(self.base_url)
        # TODO: need to set http / https based on service protocol
        put_url = '/storage/table/{tbl_name}'.format(tbl_name=tbl_name)

        if not data:
            raise ValueError("Data to update is missing")

        if not Utils.is_json(data):
            raise TypeError("Provided data to update must be a valid JSON")

        conn.request('PUT', url=put_url, body=data)
        r = conn.getresponse()

        # TODO: log error with message if status is 4xx or 5xx
        if r.status in range(400, 500):
            _LOGGER.error("Client error code: %d", r.status)
        if r.status in range(500, 600):
            _LOGGER.error("Server error code: %d", r.status)

        res = r.read().decode()
        conn.close()
        return json.loads(res)

    def delete_from_tbl(self, tbl_name, condition=None):
        """ Delete for specified condition from given table

        :param tbl_name:
        :param condition: JSON payload
        :return:

        :Example:
            curl -X DELETE http://0.0.0.0:8080/storage/table/statistics_history -d @payload_del.json
            @payload_del.json content:
            "condition" : {
                    "column" : "key",
                    "condition" : "=",
                    "value" : "SENT_test"
            }
        """
        conn = http.client.HTTPConnection(self.base_url)
        # TODO: need to set http / https based on service protocol
        del_url = '/storage/table/{tbl_name}'.format(tbl_name=tbl_name)

        if condition and (not Utils.is_json(condition)):
            raise TypeError("condition payload must be a valid JSON")

        conn.request('DELETE', url=del_url, body=condition)
        r = conn.getresponse()

        # TODO: log error with message if status is 4xx or 5xx
        if r.status in range(400, 500):
            _LOGGER.error("Client error code: %d", r.status)
        if r.status in range(500, 600):
            _LOGGER.error("Server error code: %d", r.status)

        res = r.read().decode()
        conn.close()
        return json.loads(res)

    def query_tbl(self, tbl_name, query=None):
        """ Simple SELECT query for the specified table with optional query params

        :param tbl_name:
        :param query: query params in format k1=v1&k2=v2
        :return:

        :Example:
            curl -X GET http://0.0.0.0:8080/storage/table/statistics_history
            curl -X GET http://0.0.0.0:8080/storage/table/statistics_history?key=PURGE
        """
        conn = http.client.HTTPConnection(self.base_url)
        # TODO: need to set http / https based on service protocol

        get_url = '/storage/table/{tbl_name}'.format(tbl_name=tbl_name)

        if query:  # else SELECT * FROM <tbl_name>
            get_url += '?{}'.format(query)

        conn.request('GET', url=get_url)
        r = conn.getresponse()

        # TODO: log error with message if status is 4xx or 5xx
        if r.status in range(400, 500):
            _LOGGER.error("Client error code: %d", r.status)
        if r.status in range(500, 600):
            _LOGGER.error("Server error code: %d", r.status)

        res = r.read().decode()
        conn.close()
        return json.loads(res)

    def query_tbl_with_payload(self, tbl_name, query_payload):
        """ Complex SELECT query for the specified table with a payload

        :param tbl_name:
        :param query_payload: payload in valid JSON format
        :return:

        :Example:
            curl -X PUT http://0.0.0.0:8080/storage/table/statistics_history/query -d @payload.json
            @payload.json content:
            "where" : {
                    "column" : "key",
                    "condition" : "=",
                    "value" : "SENT_test"
            }
        """
        conn = http.client.HTTPConnection(self.base_url)
        # TODO: need to set http / https based on service protocol
        put_url = '/storage/table/{tbl_name}/query'.format(tbl_name=tbl_name)

        conn.request('PUT', url=put_url, body=query_payload)
        r = conn.getresponse()

        # TODO: log error with message if status is 4xx or 5xx
        if r.status in range(400, 500):
            _LOGGER.error("Client error code: %d", r.status)
        if r.status in range(500, 600):
            _LOGGER.error("Server error code: %d", r.status)

        res = r.read().decode()
        conn.close()
        return json.loads(res)


class Readings(Storage):
    """ Readings table operations """

    _base_url = ""

    def __init__(self):
        super().__init__()
        # FIXME: WTH?
        self.__class__._base_url = self.base_url

    @classmethod
    def append(cls, readings):
        """
        :param readings:
        :return:

        :Example:
            curl -X POST http://0.0.0.0:8080/storage/reading -d @payload.json

            {
              "readings" : [
                {
                  "asset_code": "MyAsset",
                  "read_key" : "5b3be500-ff95-41ae-b5a4-cc99d08bef40",
                  "reading" : { "rate" : 18.4 },
                  "user_ts" : "2017-09-21 15:00:09.025655"
                },
                {
                "asset_code": "MyAsset",
                "read_key" : "5b3be500-ff95-41ae-b5a4-cc99d18bef40",
                "reading" : { "rate" : 45.1 },
                "user_ts" : "2017-09-21 15:03:09.025655"
                }
              ]
            }

        """

        conn = http.client.HTTPConnection(cls._base_url)
        # TODO: need to set http / https based on service protocol

        if not readings:
            raise ValueError("Readings payload is missing")

        if not Utils.is_json(readings):
            raise TypeError("Readings payload must be a valid JSON")

        conn.request('POST', url='/storage/reading', body=readings)
        r = conn.getresponse()

        # TODO: log error with message if status is 4xx or 5xx
        if r.status in range(400, 500):
            _LOGGER.error("Client error code: %d", r.status)
        if r.status in range(500, 600):
            _LOGGER.error("Server error code: %d", r.status)

        res = r.read().decode()
        conn.close()
        return json.loads(res)

    @classmethod
    def fetch(cls, reading_id, count):
        """

        :param reading_id: the first reading ID in the block that is retrieved
        :param count: the number of readings to return, if available
        :return:
        :Example:
            curl -X  GET http://0.0.0.0:8080/storage/reading?id=2&count=3

        """

        conn = http.client.HTTPConnection(cls._base_url)
        # TODO: need to set http / https based on service protocol

        get_url = '/storage/reading?id={}&count={}'.format(reading_id, count)

        conn.request('GET', url=get_url)
        r = conn.getresponse()

        # TODO: log error with message if status is 4xx or 5xx
        if r.status in range(400, 500):
            _LOGGER.error("Client error code: %d", r.status)
        if r.status in range(500, 600):
            _LOGGER.error("Server error code: %d", r.status)

        res = r.read().decode()
        conn.close()
        return json.loads(res)

    @classmethod
    def query(cls, query_payload):
        """

        :param query_payload:
        :return:
        :Example:
            curl -X PUT http://0.0.0.0:8080/storage/reading/query -d @payload.json

            @payload.json content:
            {
              "where" : {
                "column" : "asset_code",
                "condition" : "=",
                "value" : "MyAsset"
                }
            }
        """
        conn = http.client.HTTPConnection(cls._base_url)
        # TODO: need to set http / https based on service protocol

        conn.request('PUT', url='/storage/reading/query', body=query_payload)
        r = conn.getresponse()

        # TODO: log error with message if status is 4xx or 5xx
        if r.status in range(400, 500):
            _LOGGER.error("Client error code: %d", r.status)
        if r.status in range(500, 600):
            _LOGGER.error("Server error code: %d", r.status)

        res = r.read().decode()
        conn.close()
        return json.loads(res)

    @classmethod
    def purge(cls, age, sent_id, flag=None):
        """ Purge readings based on the age of the readings

        :param age: the maximum age of data to retain, expressed in hours
        :param sent_id: the id of the last reading to be sent out of FogLAMP
        :param flag: define what to do about unsent readings. Valid options are retain or purge
        :return: a JSON with the number of readings removed, the number of unsent readings removed
            and the number of readings that remain
        :Example:
            curl -X PUT http://0.0.0.0:8080/storage/reading/purge?age=24&sent=2&flags=PURGE
            curl -X PUT <base url>?/storage/reading/purge?age=<age>&sent=<reading id>&flags=<flags>

        """
        # TODO: flagS should be flag?

        valid_flags = ['retain', 'purge']

        if flag and flag.lower() not in valid_flags:
            raise InvalidReadingsPurgeFlagParameters

        # age should be int
        # sent_id should again be int
        try:
            _age = int(age)
            _sent_id = int(sent_id)
        except TypeError:
            raise

        conn = http.client.HTTPConnection(cls._base_url)
        # TODO: need to set http / https based on service protocol

        put_url = '/storage/reading/purge?age={}&sent={}'.format(_age, _sent_id)
        if flag:
            put_url += "&flags={}".format(flag.lower())

        conn.request('PUT', url=put_url, body=None)
        r = conn.getresponse()

        # TODO: log error with message if status is 4xx or 5xx
        if r.status in range(400, 500):
            _LOGGER.error("Client error code: %d", r.status)
        if r.status in range(500, 600):
            _LOGGER.error("Server error code: %d", r.status)

        # NOTE: If the data could not be deleted because of a conflict,
        #       then the error “409 Conflict” will be returned.
        res = r.read().decode()
        conn.close()
        return json.loads(res)
