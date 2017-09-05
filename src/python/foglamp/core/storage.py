# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import asyncio
import time
import json
import requests
from aiohttp import web


__author__ = "Praveen Garg, Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# Module attributes
__DB_NAME = "foglamp"
BASE_URL = 'http://localhost:8082/foglamp'
headers = {"Content-Type": 'application/json'}
__start_time = time.time()

# We cannot assign value to a module variable in a method
__storage_service_id = list()


async def ping(request):
    since_started = time.time() - __start_time

    return web.json_response({'uptime': since_started})

async def start(request):
    """
    Start Storage service

    :Example: curl  -X POST  http://localhost:8082/foglamp/storage
    """
    if len(__storage_service_id):
        raise ValueError("Storage Service already started with id {}".format(__storage_service_id[0]))

    try:
        # TODO: Will this data come from Configuration Manager?
        data = {"type": "Storage", "name": "Storage Services", "address": "127.0.0.1", "port": "8090"}

        r = requests.post(BASE_URL + '/service', data=json.dumps(data), headers=headers)
        retval = dict(r.json())

        assert 200 == r.status_code
        __storage_service_id.append(retval['id'])

        _response = {
            'id': retval['id'],
            'message': retval['message']
        }

        return web.json_response(_response)
    except ValueError as ex:
        raise web.HTTPNotFound(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason='FogLAMP has encountered an internal error', text=str(ex))

async def stop(request):
    """
    Stop Storage service

    :Example: curl  -X DELETE  http://localhost:8082/foglamp/storage
    """

    try:
        if not __storage_service_id:
            raise ValueError("No Storage Service started yet")

        r = requests.delete(BASE_URL + '/service/'+__storage_service_id)
        retval = dict(r.json())

        assert 200 == r.status_code

        _response = {
            'id': retval['id'],
            'message': retval['message']
        }

        return web.json_response(_response)
    except ValueError as ex:
        raise web.HTTPNotFound(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason='FogLAMP has encountered an internal error', text=str(ex))


async def restart(request):
    __start_time = time.time()
