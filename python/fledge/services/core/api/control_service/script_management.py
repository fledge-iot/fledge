# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import json
import logging

from aiohttp import web

from fledge.common.storage_client.exceptions import StorageServerError
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.common import logger
from fledge.services.core import connect
from fledge.services.core.api.control_service.exceptions import *


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2021 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -----------------------------------------------------------------
    | GET POST            | /fledge/control/script                  |
    | GET PUT DELETE      | /fledge/control/script/{script_name}    |
    -----------------------------------------------------------------
"""

_logger = logger.setup(__name__, level=logging.INFO)


async def get_all_scripts(request: web.Request) -> web.Response:
    """ Get list of all scripts

    :Example:
        curl -sX GET http://localhost:8081/fledge/control/script
    """
    return web.json_response({"message": "To be Implemented"})


async def get_script(request: web.Request) -> web.Response:
    """ Get a named script

    :Example:
        curl -sX GET http://localhost:8081/fledge/control/script/{script_name}
    """
    try:
        name = request.match_info.get('script_name', None)
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({"message": "To be Implemented"})


async def add_script(request: web.Request) -> web.Response:
    """ Add a script

    :Example:
        curl -sX POST http://localhost:8081/fledge/control/script -d '{"name": "testScript", "steps": {"write": {"order": 1, "service": "modbus1", "values": {"speed": "$requestedSpeed$", "fan": "1200"}, "condition": {"key": "requestedSpeed", "condition": "<", "value": "2000"}}, "delay": {"order": 2, "duration": 1500}}}'
        curl -sX POST http://localhost:8081/fledge/control/script -d '{"name": "test", "steps": {}, "acl": "testACL"}'
    """
    try:
        data = await request.json()
        name = data.get('name', None)
        steps = data.get('steps', None)
        acl = data.get('acl', None)
        if name is None:
            raise ValueError('name param is required')
        name = name.strip()
        if name is not None and name == "":
            raise ValueError('name cannot be empty')
        if steps is None:
            raise ValueError('steps param is required')
        if not isinstance(steps, dict):
            raise ValueError('steps must be a dictionary')
        if acl is not None and acl.strip() == "":
            raise ValueError('ACL cannot be empty')
        storage = connect.get_storage_async()
        payload = PayloadBuilder().SELECT("name").WHERE(['name', '=', name]).payload()
        get_control_script_name_result = await storage.query_tbl_with_payload('control_script', payload)
        if get_control_script_name_result['count'] == 0:
            payload = PayloadBuilder().INSERT(name=name, steps=steps).payload()
            if acl is not None:
                payload = PayloadBuilder().INSERT(name=name, steps=steps, acl=acl.strip()).payload()
            insert_control_script_result = await storage.insert_into_tbl("control_script", payload)
            if 'response' in insert_control_script_result:
                if insert_control_script_result['response'] == "inserted":
                    result = {"name": name, "steps": steps} if acl is None else {"name": name, "steps": steps,
                                                                                 "acl": acl.strip()}
            else:
                raise StorageServerError(insert_control_script_result)
        else:
            msg = '{} name already exists.'.format(name)
            raise DuplicateNameError(msg)
    except StorageServerError as err:
        msg = "Storage error: {}".format(str(err))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    except DuplicateNameError as err:
        msg = str(err)
        raise web.HTTPConflict(reason=msg, body=json.dumps({"message": msg}))
    except (TypeError, ValueError) as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({"message": result})


async def update_script(request: web.Request) -> web.Response:
    """ Update a script

    :Example:
        curl -sX PUT http://localhost:8081/fledge/control/script/{script_name} -d '{"steps": [{}]}'
        curl -sX PUT http://localhost:8081/fledge/control/script/{script_name} -d '{"steps": [{}], "acl": "testACL"}'
    """
    try:
        name = request.match_info.get('script_name', None)
        data = await request.json()
        steps = data.get('steps', None)
        acl = data.get('acl', None)
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({"message": "To be Implemented"})


async def delete_script(request: web.Request) -> web.Response:
    """ Delete a script

    :Example:
        curl -sX DELETE http://localhost:8081/fledge/control/script/{script_name}
    """
    try:
        name = request.match_info.get('script_name', None)
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({"message": "To be Implemented"})

