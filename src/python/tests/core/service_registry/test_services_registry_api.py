# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import json
import requests
import pytest
import uuid


__author__ = "Amarendra Kumar Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

pytestmark = pytest.mark.asyncio

# Module attributes
__DB_NAME = "foglamp"
BASE_URL = 'http://localhost:8082/foglamp'
headers = {'Content-Type': 'application/json'}


@pytest.allure.feature("service-registry", "api")
class TestServicesRegistryApi:

    def setup_method(self, method):
        """clean up registry storage"""

        l = requests.get(BASE_URL + '/service')
        res = dict(l.json())
        t = res["services"]
        for s in t:
            requests.delete(BASE_URL + '/service/' + s["id"])

    def teardown_method(self, method):
        """clean up registry storage"""

        l = requests.get(BASE_URL + '/service')
        res = dict(l.json())
        t = res["services"]
        for s in t:
            requests.delete(BASE_URL + '/service/' + s["id"])

    async def test_register(self):
        data = {"type": "Storage", "name": "Storage Services 1", "address": "127.0.0.1", "port": 8090}

        r = requests.post(BASE_URL + '/service', data=json.dumps(data), headers=headers)
        res = dict(r.json())

        assert 200 == r.status_code
        assert str(uuid.UUID(res["id"], version=4)) == res["id"]
        assert "Service registered successfully" == res["message"]

    async def test_register_dup_name(self):
        data = {"type": "Storage", "name": "name-dup", "address": "127.0.0.1", "port": 9001}

        r = requests.post(BASE_URL + '/service', data=json.dumps(data), headers=headers)
        res = dict(r.json())

        assert 200 == r.status_code
        assert str(uuid.UUID(res["id"], version=4)) == res["id"]

        r = requests.post(BASE_URL + '/service', data=json.dumps(data), headers=headers)
        res = dict(r.json())

        assert 200 == r.status_code
        assert "Service with the same name already exists" == res["error"]

    async def test_register_dup_address_port(self):
        data = {"type": "Storage", "name": "name-1", "address": "127.0.0.1", "port": 9001}

        r = requests.post(BASE_URL + '/service', data=json.dumps(data), headers=headers)
        res = dict(r.json())

        assert 200 == r.status_code
        assert str(uuid.UUID(res["id"], version=4)) == res["id"]

        data = {"type": "Storage", "name": "name-2", "address": "127.0.0.1", "port": 9001}
        r = requests.post(BASE_URL + '/service', data=json.dumps(data), headers=headers)
        res = dict(r.json())

        assert 200 == r.status_code
        assert "Service with the same address and port already exists" == res["error"]

    async def test_register_invalid_port(self):
        data = {"type": "Storage", "name": "Storage Services 2", "address": "127.0.0.1", "port": "80a1"}

        r = requests.post(BASE_URL + '/service', data=json.dumps(data), headers=headers)
        res = dict(r.json())

        assert 200 == r.status_code
        assert "Service port can be a positive integer only" == res["error"]

    async def test_unregister(self):
        data = {"type": "Storage", "name": "Storage Services 2", "address": "127.0.0.1", "port": 8091}

        r = requests.post(BASE_URL + '/service', data=json.dumps(data), headers=headers)
        res = dict(r.json())

        assert 200 == r.status_code
        service_id = res["id"]

        r = requests.delete(BASE_URL + '/service/'+service_id)
        retval = dict(r.json())

        assert 200 == r.status_code
        assert service_id == retval["id"]
        assert "Service unregistered" == retval["message"]

    async def test_unregister_non_existing(self):
        r = requests.delete(BASE_URL + '/service/any')
        res = dict(r.json())

        assert 200 == r.status_code
        assert "Service with {} does not exist".format("any") == res["error"]

    async def test_get(self):
        data1 = {"type": "Storage", "name": "Storage Services x", "address": "127.0.0.1", "port": 8091}
        r = requests.post(BASE_URL + '/service', data=json.dumps(data1), headers=headers)
        assert 200 == r.status_code
        retval = dict(r.json())
        storage_service_id = retval["id"]

        # Create another service
        data2 = {"type": "Device", "name": "Device Services y", "address": "127.0.0.1", "port": 8092, "protocol": "https"}
        r = requests.post(BASE_URL + '/service', data=json.dumps(data2), headers=headers)
        assert 200 == r.status_code
        res = dict(r.json())
        device_service_id = res["id"]

        # data1 and data2 also ensure diff |address AND port| combinations work!
        l = requests.get(BASE_URL + '/service')
        assert 200 == l.status_code

        retval = dict(l.json())
        svc = retval["services"]
        assert 2 == len(svc)

        data1_svc = data2_svc = None
        for s in svc:
            if s["id"] == storage_service_id:
                data1_svc = s
            if s["id"] == device_service_id:
                data2_svc = s

        assert data1_svc is not None
        assert data1["name"] == data1_svc["name"]
        assert data1["type"] == data1_svc["type"]
        assert data1["address"] == data1_svc["address"]
        assert data1["port"] == data1_svc["port"]
        # check default protocol
        assert "http" == data1_svc["protocol"]

        assert data2_svc is not None
        assert data2["name"] == data2_svc["name"]
        assert data2["type"] == data2_svc["type"]
        assert data2["address"] == data2_svc["address"]
        assert data2["port"] == data2_svc["port"]
        assert data2["protocol"] == data2_svc["protocol"]

    async def test_get_by_name(self):
        data = {"type": "Storage", "name": "Storage Services A", "address": "127.0.0.1", "port": 8091}
        r = requests.post(BASE_URL + '/service', data=json.dumps(data), headers=headers)
        assert 200 == r.status_code

        l = requests.get(BASE_URL + '/service?name={}'.format(data["name"]))
        assert 200 == l.status_code

        res = dict(l.json())
        svc = res["services"]
        assert 1 == len(svc)

        assert data["name"] == svc[0]["name"]
        assert data["type"] == svc[0]["type"]
        assert data["address"] == svc[0]["address"]
        assert data["port"] == svc[0]["port"]

    async def test_get_by_type(self):
        data = {"type": "Device", "name": "Storage Services A", "address": "127.0.0.1", "port": 8091}
        r = requests.post(BASE_URL + '/service', data=json.dumps(data), headers=headers)
        assert 200 == r.status_code

        l = requests.get(BASE_URL + '/service?type={}'.format(data["type"]))
        assert 200 == l.status_code

        res = dict(l.json())
        svc = res["services"]
        assert 1 == len(svc)

        assert data["name"] == svc[0]["name"]
        assert data["type"] == svc[0]["type"]
        assert data["address"] == svc[0]["address"]
        assert data["port"] == svc[0]["port"]

    async def test_get_by_name_and_type(self):
        data0 = {"type": "Device", "name": "D Services", "address": "127.0.0.1", "port": 8091}
        r = requests.post(BASE_URL + '/service', data=json.dumps(data0), headers=headers)
        assert 200 == r.status_code

        data1 = {"type": "Storage", "name": "S Services", "address": "127.0.0.1", "port": 8092}
        r = requests.post(BASE_URL + '/service', data=json.dumps(data1), headers=headers)
        assert 200 == r.status_code

        l = requests.get(BASE_URL + '/service?type={}&name={}'.format(data0["type"], data1["name"]))
        assert 200 == l.status_code

        res = dict(l.json())
        svc = res["services"]
        assert 0 == len(svc)

        l = requests.get(BASE_URL + '/service?type={}&name={}'.format(data0["type"], data0["name"]))
        assert 200 == l.status_code

        res = dict(l.json())
        svc = res["services"]
        assert 1 == len(svc)

        assert data0["name"] == svc[0]["name"]
        assert data0["type"] == svc[0]["type"]
