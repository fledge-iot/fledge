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
# Needs foglamp to start,
# replace 8082 with core_management_port
BASE_URL = 'http://localhost:8082/foglamp'
headers = {'Content-Type': 'application/json'}


@pytest.allure.feature("api")
@pytest.allure.story("service-registry")
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
        data = {"type": "Storage", "name": "Storage Services 1", "address": "127.0.0.1",
                "service_port": 8090, "management_port": 1090}

        r = requests.post(BASE_URL + '/service', data=json.dumps(data), headers=headers)
        res = dict(r.json())

        assert 200 == r.status_code
        print(res)
        assert str(uuid.UUID(res["id"], version=4)) == res["id"]
        assert "Service registered successfully" == res["message"]

    async def test_register_without_service_port(self):
        data = {"type": "Storage", "name": "CoAP service", "address": "127.0.0.1", "management_port": 1090}

        r = requests.post(BASE_URL + '/service', data=json.dumps(data), headers=headers)
        res = dict(r.json())

        assert 200 == r.status_code
        print(res)
        assert str(uuid.UUID(res["id"], version=4)) == res["id"]
        assert "Service registered successfully" == res["message"]

        l = requests.get(BASE_URL + '/service?name={}'.format(data["name"]))
        assert 200 == l.status_code

        res = dict(l.json())
        svc = res["services"]
        assert 1 == len(svc)

        assert data["name"] == svc[0]["name"]
        assert data["type"] == svc[0]["type"]
        assert data["address"] == svc[0]["address"]
        assert data["management_port"] == svc[0]["management_port"]

    async def test_register_dup_name(self):
        data = {"type": "Storage", "name": "name-dup", "address": "127.0.0.1", "service_port": 9001, "management_port": 1009}

        r = requests.post(BASE_URL + '/service', data=json.dumps(data), headers=headers)
        res = dict(r.json())

        assert 200 == r.status_code
        assert str(uuid.UUID(res["id"], version=4)) == res["id"]

        r = requests.post(BASE_URL + '/service', data=json.dumps(data), headers=headers)
        res = dict(r.json())

        assert 200 == r.status_code
        assert "A Service with the same name already exists" == res["error"]["message"]

    async def test_register_dup_address_and_service_port(self):
        data = {"type": "Storage", "name": "name-1", "address": "127.0.0.1", "service_port": 9001, "management_port": 1009}

        r = requests.post(BASE_URL + '/service', data=json.dumps(data), headers=headers)
        res = dict(r.json())

        assert 200 == r.status_code
        assert str(uuid.UUID(res["id"], version=4)) == res["id"]

        data = {"type": "Storage", "name": "name-2", "address": "127.0.0.1", "service_port": 9001, "management_port": 1010}
        r = requests.post(BASE_URL + '/service', data=json.dumps(data), headers=headers)
        res = dict(r.json())

        assert 200 == r.status_code
        assert "A Service is already registered on the same address: {} and service port: {}".format(
            data['address'], data['service_port']) == res["error"]["message"]

    async def test_register_invalid_port(self):
        data = {"type": "Storage", "name": "Storage Services 2", "address": "127.0.0.1", "service_port": "80a1",
                "management_port": 1009}

        r = requests.post(BASE_URL + '/service', data=json.dumps(data), headers=headers)
        res = dict(r.json())

        assert 200 == r.status_code
        assert u"Service's service port can be a positive integer only" == res["error"]["message"]

    async def test_register_dup_address_and_mgt_port(self):
        data = {"type": "Storage", "name": "name-1", "address": "127.0.0.1", "service_port": 9001, "management_port": 1009}

        r = requests.post(BASE_URL + '/service', data=json.dumps(data), headers=headers)
        res = dict(r.json())

        assert 200 == r.status_code
        assert str(uuid.UUID(res["id"], version=4)) == res["id"]

        data = {"type": "Storage", "name": "name-2", "address": "127.0.0.1", "service_port": 9002, "management_port": 1009}
        r = requests.post(BASE_URL + '/service', data=json.dumps(data), headers=headers)
        res = dict(r.json())

        assert 200 == r.status_code
        assert "A Service is already registered on the same address: {} and management port: {}".format(
            data['address'], data['management_port']) == res["error"]["message"]

    async def test_register_non_numeric_m_port(self):
        data = {"type": "Storage", "name": "Storage Services 2", "address": "127.0.0.1", "service_port": 8089,
                "management_port": "bx01"}

        r = requests.post(BASE_URL + '/service', data=json.dumps(data), headers=headers)
        res = dict(r.json())

        assert 200 == r.status_code
        assert "Service management port can be a positive integer only" == res["error"]["message"]

    async def test_unregister(self):
        data = {"type": "Storage", "name": "Storage Services 2", "address": "127.0.0.1", "service_port": 8091, "management_port": 1009}

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
        assert "Service with {} does not exist".format("any") == res["error"]["message"]

    async def test_get(self):
        data1 = {"type": "Storage", "name": "Storage Services x", "address": "127.0.0.1", "service_port": 8091, "management_port": 1091}
        r = requests.post(BASE_URL + '/service', data=json.dumps(data1), headers=headers)
        assert 200 == r.status_code
        retval = dict(r.json())
        storage_service_id = retval["id"]

        # Create another service
        data2 = {"type": "Device", "name": "Device Services y", "address": "127.0.0.1", "service_port": 8092, "management_port": 1092, "protocol": "https"}
        r = requests.post(BASE_URL + '/service', data=json.dumps(data2), headers=headers)
        assert 200 == r.status_code
        res = dict(r.json())
        device_service_id = res["id"]

        # data1 and data2 also ensure diff |address AND port, including mgt port| combinations work!
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
        assert data1["service_port"] == data1_svc["service_port"]
        assert data1["management_port"] == data1_svc["management_port"]

        # check default protocol
        assert "http" == data1_svc["protocol"]

        assert data2_svc is not None
        assert data2["name"] == data2_svc["name"]
        assert data2["type"] == data2_svc["type"]
        assert data2["address"] == data2_svc["address"]
        assert data2["service_port"] == data2_svc["service_port"]
        assert data2["protocol"] == data2_svc["protocol"]
        assert data2["management_port"] == data2_svc["management_port"]
        assert data2["protocol"] == data2_svc["protocol"]

    async def test_get_by_name(self):
        data = {"type": "Storage", "name": "Storage Services A", "address": "127.0.0.1", "service_port": 8091, "management_port": 1009}
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
        assert data["service_port"] == svc[0]["service_port"]
        assert data["management_port"] == svc[0]["management_port"]

    async def test_get_by_type(self):
        data = {"type": "Device", "name": "Storage Services A", "address": "127.0.0.1", "service_port": 8091, "management_port": 1091}
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
        assert data["service_port"] == svc[0]["service_port"]
        assert data["management_port"] == svc[0]["management_port"]

    async def test_get_by_name_and_type(self):
        data0 = {"type": "Device", "name": "D Services", "address": "127.0.0.1", "service_port": 8091, "management_port": 1091}
        r = requests.post(BASE_URL + '/service', data=json.dumps(data0), headers=headers)
        assert 200 == r.status_code

        data1 = {"type": "Storage", "name": "S Services", "address": "127.0.0.1", "service_port": 8092, "management_port": 1092}
        r = requests.post(BASE_URL + '/service', data=json.dumps(data1), headers=headers)
        assert 200 == r.status_code

        l = requests.get(BASE_URL + '/service?type={}&name={}'.format(data0["type"], data1["name"]))
        assert 200 == l.status_code

        res = dict(l.json())
        assert "Invalid service name and/or type provided" == res['error']["message"]

        l = requests.get(BASE_URL + '/service?type={}&name={}'.format(data0["type"], data0["name"]))
        assert 200 == l.status_code

        res = dict(l.json())
        svc = res["services"]
        assert 1 == len(svc)

        assert data0["name"] == svc[0]["name"]
        assert data0["type"] == svc[0]["type"]
