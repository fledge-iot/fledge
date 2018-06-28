# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Storage layer python client
"""

__author__ = "Praveen Garg, Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

import aiohttp
import http.client
import json
from abc import ABC, abstractmethod

from foglamp.common import logger
from foglamp.common.service_record import ServiceRecord
from foglamp.common.storage_client.exceptions import *
from foglamp.common.storage_client.utils import Utils

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


class StorageClientAsync(AbstractStorage):
    def __init__(self, core_management_host, core_management_port, svc=None):
        try:
            if svc:
                self.service = svc
            else:
                self.connect(core_management_host, core_management_port)

            self.base_url = '{}:{}'.format(self.service._address, self.service._port)
            self.management_api_url = '{}:{}'.format(self.service._address, self.service._management_port)
        except Exception:
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
        if not isinstance(svc, ServiceRecord):
            w_msg = 'Storage should be a valid FogLAMP micro-service instance'
            _LOGGER.warning(w_msg)
            raise InvalidServiceInstance

        if not getattr(svc, "_type") == "Storage":
            w_msg = 'Storage should be a valid *Storage* micro-service instance'
            _LOGGER.warning(w_msg)
            raise InvalidServiceInstance

        self.__service = svc

    def _get_storage_service(self, host, port):
        """ get Storage service """

        conn = http.client.HTTPConnection("{0}:{1}".format(host, port))
        # TODO: need to set http / https based on service protocol

        conn.request('GET', url='/foglamp/service?name=FogLAMP%20Storage')
        r = conn.getresponse()

        if r.status in range(400, 500):
            _LOGGER.error("Get Service: Client error code: %d, %s", r.status.r.reason)
        if r.status in range(500, 600):
            _LOGGER.error("Get Service: Server error code: %d, %s", r.status, r.reason)

        res = r.read().decode()
        conn.close()
        response = json.loads(res)
        svc = response["services"][0]
        return svc

    def connect(self, core_management_host, core_management_port):
        svc = self._get_storage_service(host=core_management_host, port=core_management_port)
        if len(svc) == 0:
            raise InvalidServiceInstance
        self.service = ServiceRecord(s_id=svc["id"], s_name=svc["name"], s_type=svc["type"], s_port=svc["service_port"],
                                     m_port=svc["management_port"], s_address=svc["address"],
                                     s_protocol=svc["protocol"])

        return self

    def disconnect(self):
        pass

    # FIXME: As per JIRA-615 strict=false at python side (interim solution)
    # fix is required at storage layer (error message with escape sequence using a single quote)
    async def insert_into_tbl(self, tbl_name, data):
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
        if not tbl_name:
            raise ValueError("Table name is missing")

        if not data:
            raise ValueError("Data to insert is missing")

        if not Utils.is_json(data):
            raise TypeError("Provided data to insert must be a valid JSON")

        post_url = '/storage/table/{tbl_name}'.format(tbl_name=tbl_name)
        url = 'http://' + self.base_url + post_url
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as resp:
                status_code = resp.status
                jdoc = await resp.json()
                if status_code not in range(200, 209):
                    _LOGGER.info("POST %s, with payload: %s", post_url, data)
                    _LOGGER.error("Error code: %d, reason: %s, details: %s", resp.status, resp.reason, jdoc)
                    raise StorageServerError(code=resp.status, reason=resp.reason, error=jdoc)

        return jdoc

    async def update_tbl(self, tbl_name, data):
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
        if not tbl_name:
            raise ValueError("Table name is missing")

        if not data:
            raise ValueError("Data to update is missing")

        if not Utils.is_json(data):
            raise TypeError("Provided data to update must be a valid JSON")

        put_url = '/storage/table/{tbl_name}'.format(tbl_name=tbl_name)

        url = 'http://' + self.base_url + put_url
        async with aiohttp.ClientSession() as session:
            async with session.put(url, data=data) as resp:
                status_code = resp.status
                jdoc = await resp.json()
                if status_code not in range(200, 209):
                    _LOGGER.info("PUT %s, with payload: %s", put_url, data)
                    _LOGGER.error("Error code: %d, reason: %s, details: %s", resp.status, resp.reason, jdoc)
                    raise StorageServerError(code=resp.status, reason=resp.reason, error=jdoc)

        return jdoc

    async def delete_from_tbl(self, tbl_name, condition=None):
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

        if not tbl_name:
            raise ValueError("Table name is missing")

        del_url = '/storage/table/{tbl_name}'.format(tbl_name=tbl_name)

        if condition and (not Utils.is_json(condition)):
            raise TypeError("condition payload must be a valid JSON")

        url = 'http://' + self.base_url + del_url
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, data=condition) as resp:
                status_code = resp.status
                jdoc = await resp.json()
                if status_code not in range(200, 209):
                    _LOGGER.info("DELETE %s, with payload: %s", del_url, condition if condition else '')
                    _LOGGER.error("Error code: %d, reason: %s, details: %s", resp.status, resp.reason, jdoc)
                    raise StorageServerError(code=resp.status, reason=resp.reason, error=jdoc)

        return jdoc

    async def query_tbl(self, tbl_name, query=None):
        """ Simple SELECT query for the specified table with optional query params

        :param tbl_name:
        :param query: query params in format k1=v1&k2=v2
        :return:

        :Example:
            curl -X GET http://0.0.0.0:8080/storage/table/statistics_history
            curl -X GET http://0.0.0.0:8080/storage/table/statistics_history?key=PURGE
        """
        if not tbl_name:
            raise ValueError("Table name is missing")

        get_url = '/storage/table/{tbl_name}'.format(tbl_name=tbl_name)

        if query:  # else SELECT * FROM <tbl_name>
            get_url += '?{}'.format(query)

        url = 'http://' + self.base_url + get_url
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                status_code = resp.status
                jdoc = await resp.json()
                if status_code not in range(200, 209):
                    _LOGGER.info("GET %s", get_url)
                    _LOGGER.error("Error code: %d, reason: %s, details: %s", resp.status, resp.reason, jdoc)
                    raise StorageServerError(code=resp.status, reason=resp.reason, error=jdoc)

        return jdoc

    async def query_tbl_with_payload(self, tbl_name, query_payload):
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
        if not tbl_name:
            raise ValueError("Table name is missing")

        if not query_payload:
            raise ValueError("Query payload is missing")

        if not Utils.is_json(query_payload):
            raise TypeError("Query payload must be a valid JSON")

        put_url = '/storage/table/{tbl_name}/query'.format(tbl_name=tbl_name)

        url = 'http://' + self.base_url + put_url
        async with aiohttp.ClientSession() as session:
            async with session.put(url, data=query_payload) as resp:
                status_code = resp.status
                jdoc = await resp.json()
                if status_code not in range(200, 209):
                    _LOGGER.info("PUT %s, with query payload: %s", put_url, query_payload)
                    _LOGGER.error("Error code: %d, reason: %s, details: %s", resp.status, resp.reason, jdoc)
                    raise StorageServerError(code=resp.status, reason=resp.reason, error=jdoc)

        return jdoc


class ReadingsStorageClientAsync(StorageClientAsync):
    """ Readings table operations """
    _base_url = ""

    def __init__(self, core_mgt_host, core_mgt_port, svc=None):
        super().__init__(core_management_host=core_mgt_host, core_management_port=core_mgt_port, svc=svc)
        self.__class__._base_url = self.base_url

    async def append(self, readings):
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

        if not readings:
            raise ValueError("Readings payload is missing")

        if not Utils.is_json(readings):
            raise TypeError("Readings payload must be a valid JSON")

        url = 'http://' + self._base_url + '/storage/reading'
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=readings) as resp:
                status_code = resp.status
                jdoc = await resp.json()
                if status_code not in range(200, 209):
                    _LOGGER.error("POST url %s with payload: %s, Error code: %d, reason: %s, details: %s",
                                  '/storage/reading', readings, resp.status, resp.reason, jdoc)
                    raise StorageServerError(code=resp.status, reason=resp.reason, error=jdoc)

        return jdoc

    async def fetch(self, reading_id, count):
        """

        :param reading_id: the first reading ID in the block that is retrieved
        :param count: the number of readings to return, if available
        :return:
        :Example:
            curl -X  GET http://0.0.0.0:8080/storage/reading?id=2&count=3

        """

        if reading_id is None:
            raise ValueError("first reading id to retrieve the readings block is required")

        if count is None:
            raise ValueError("count is required to retrieve the readings block")

        try:
            count = int(count)
        except ValueError:
            raise

        get_url = '/storage/reading?id={}&count={}'.format(reading_id, count)
        url = 'http://' + self._base_url + get_url
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                status_code = resp.status
                jdoc = await resp.json()
                if status_code not in range(200, 209):
                    _LOGGER.error("GET url: %s, Error code: %d, reason: %s, details: %s", url, resp.status,
                                  resp.reason, jdoc)
                    raise StorageServerError(code=resp.status, reason=resp.reason, error=jdoc)

        return jdoc

    async def query(self, query_payload):
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

        if not query_payload:
            raise ValueError("Query payload is missing")

        if not Utils.is_json(query_payload):
            raise TypeError("Query payload must be a valid JSON")

        url = 'http://' + self._base_url + '/storage/reading/query'
        async with aiohttp.ClientSession() as session:
            async with session.put(url, data=query_payload) as resp:
                status_code = resp.status
                jdoc = await resp.json()
                if status_code not in range(200, 209):
                    _LOGGER.error("PUT url %s with query payload: %s, Error code: %d, reason: %s, details: %s",
                                  '/storage/reading/query', query_payload, resp.status, resp.reason, jdoc)
                    raise StorageServerError(code=resp.status, reason=resp.reason, error=jdoc)

        return jdoc

    async def purge(self, age=None, sent_id=0, size=None, flag=None):
        """ Purge readings based on the age of the readings

        :param age: the maximum age of data to retain, expressed in hours
        :param sent_id: the id of the last reading to be sent out of FogLAMP
        :param size: the maximum size of data to retain, expressed in Kbytes
        :param flag: define what to do about unsent readings. Valid options are retain or purge
        :return: a JSON with the number of readings removed, the number of unsent readings removed
            and the number of readings that remain
        :Example:
            curl -X PUT "http://0.0.0.0:<storage_service_port>/storage/reading/purge?age=<age>&sent=<reading id>&flags=<flags>"
            curl -X PUT "http://0.0.0.0:<storage_service_port>/storage/reading/purge?age=24&sent=2&flags=PURGE"
            curl -X PUT "http://0.0.0.0:<storage_service_port>/storage/reading/purge?size=1024&sent=0&flags=PURGE"
        """

        valid_flags = ['retain', 'purge']

        if flag and flag.lower() not in valid_flags:
            raise InvalidReadingsPurgeFlagParameters

        if age and size:
            raise PurgeOnlyOneOfAgeAndSize

        if not age and not size:
            raise PurgeOneOfAgeAndSize

        # age should be int
        # size should be int
        # sent_id should again be int
        try:
            if age is not None:
                _age = int(age)

            if size is not None:
                _size = int(size)

            _sent_id = int(sent_id)
        except ValueError:
            raise

        if age:
            put_url = '/storage/reading/purge?age={}&sent={}'.format(_age, _sent_id)
        if size:
            put_url = '/storage/reading/purge?size={}&sent={}'.format(_size, _sent_id)
        if flag:
            put_url += "&flags={}".format(flag.lower())

        url = 'http://' + self._base_url + put_url
        async with aiohttp.ClientSession() as session:
            async with session.put(url, data=None) as resp:
                status_code = resp.status
                jdoc = await resp.json()
                if status_code not in range(200, 209):
                    _LOGGER.error("PUT url %s, Error code: %d, reason: %s, details: %s", put_url, resp.status,
                                  resp.reason, jdoc)
                    raise StorageServerError(code=resp.status, reason=resp.reason, error=jdoc)

        return jdoc
