# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import json
import requests
import pytest
import asyncio


__author__ = "Amarendra Kumar Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# Module attributes
__DB_NAME = "foglamp"
BASE_URL = 'http://localhost:8082/foglamp'
headers = {"Content-Type": 'application/json'}


class TestMicroServicesRestapi:
    def setup_method(self, method):
        l = requests.get(BASE_URL + '/service')
        retval = dict(l.json())
        t = retval["services"]
        if len(t):
            for s in t:
                r = requests.delete(BASE_URL + '/service/' + s["id"])
                assert 200 == r.status_code

    def teardown_method(self, method):
        pass


    @pytest.mark.asyncio
    async def test_register(self):
        data = {"type": "Storage", "name": "Storage Services 1", "address": "127.0.0.1", "port": "8090"}

        r = requests.post(BASE_URL + '/service', data=json.dumps(data), headers=headers)
        retval = dict(r.json())

        assert 200 == r.status_code
        assert data["name"] == retval["name"]
        assert data["type"] == retval["type"]
        assert data["address"] == retval["address"]
        assert data["port"] == retval["port"]
        assert "Service registered successfully" == retval["message"]

    @pytest.mark.asyncio
    async def test_unregister(self):
        data = {"type": "Storage", "name": "Storage Services 2", "address": "127.0.0.1", "port": "8091"}

        r = requests.post(BASE_URL + '/service', data=json.dumps(data), headers=headers)
        retval = dict(r.json())
        service_id = retval["id"]

        assert 200 == r.status_code

        r = requests.delete(BASE_URL + '/service/'+service_id)
        retval = dict(r.json())

        assert 200 == r.status_code
        assert service_id == retval["id"]
        assert "Service now unregistered" == retval["message"]

    @pytest.mark.asyncio
    async def test_get(self):
        data1 = {"type": "Storage", "name": "Storage Services 3", "address": "127.0.0.1", "port": "8091"}
        r = requests.post(BASE_URL + '/service', data=json.dumps(data1), headers=headers)
        retval = dict(r.json())
        storage_service_id = retval["id"]

        assert 200 == r.status_code

        # Create another service
        data2 = {"type": "Device", "name": "Device Services 4", "address": "127.0.0.1", "port": "8092"}
        r = requests.post(BASE_URL + '/service', data=json.dumps(data2), headers=headers)
        retval = dict(r.json())
        device_service_id = retval["id"]

        assert 200 == r.status_code

        l = requests.get(BASE_URL + '/service')
        retval = dict(l.json())

        t = retval["services"]

        assert 2 == len(t)

        # Cannot predict the order, hence below approach for assertion
        assert storage_service_id == t[0]["id"] or device_service_id == t[0]["id"]
        assert data1["name"] == t[0]["name"] or data2["name"] == t[0]["name"]
        assert data1["type"] == t[0]["type"] or data2["type"] == t[0]["type"]
        assert data1["address"] == t[0]["address"] or data2["address"] == t[0]["address"]
        assert data1["port"] == t[0]["port"] or data2["port"] == t[0]["port"]

        assert device_service_id == t[1]["id"] or storage_service_id == t[1]["id"]
        assert data2["name"] == t[1]["name"] or data2["name"] == t[1]["name"]
        assert data2["type"] == t[1]["type"] or data2["type"] == t[1]["type"]
        assert data2["address"] == t[1]["address"] or data2["address"] == t[1]["address"]
        assert data2["port"] == t[1]["port"] or data2["port"] == t[1]["port"]
