# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import asyncio
import time
import json
import requests
import pytest
from aiohttp import web


__author__ = "Praveen Garg, Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# Module attributes
__DB_NAME = "foglamp"
BASE_URL = 'http://localhost:8082/foglamp'
headers = {"Content-Type": 'application/json'}


class TestMicroServicesRestapi:
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

        assert 200 == r.status_code

        service_id = retval["id"]

        assert data["name"] == retval["name"]

        r = requests.delete(BASE_URL + '/service/'+service_id)
        retval = dict(r.json())

        assert 200 == r.status_code
        assert service_id == retval["id"]
        assert "Service unresistered" == retval["message"]

    @pytest.mark.asyncio
    async def test_get(self):
        data = {"type": "Storage", "name": "Storage Services 3", "address": "127.0.0.1", "port": "8091"}
        r = requests.post(BASE_URL + '/service', data=json.dumps(data), headers=headers)
        retval = dict(r.json())
        storage_service_id = retval["id"]

        assert 200 == r.status_code

        data = {"type": "Device", "name": "Storage Services 3", "address": "127.0.0.1", "port": "8091"}
        r = requests.post(BASE_URL + '/service', data=json.dumps(data), headers=headers)
        retval = dict(r.json())
        storage_service_id = retval["id"]

        assert 200 == r.status_code

        assert data["name"] == retval["name"]

        r = requests.delete(BASE_URL + '/service/'+storage_service_id)
