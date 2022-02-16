# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import json
import logging

from aiohttp import web

from fledge.common import logger
from fledge.common.storage_client.exceptions import StorageServerError
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.common.web.middleware import has_permission
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
        curl -H "authorization: $AUTH_TOKEN" -sX GET http://localhost:8081/fledge/control/script
    """
    storage = connect.get_storage_async()
    payload = PayloadBuilder().SELECT("name", "steps", "acl").payload()
    result = await storage.query_tbl_with_payload('control_script', payload)
    all_scripts = []
    for key in result['rows']:
        key.update({"steps": key['steps']})
        all_scripts.append(key)

    return web.json_response({"scripts": all_scripts})


async def get_script(request: web.Request) -> web.Response:
    """ Get a named script

    :Example:
        curl -H "authorization: $AUTH_TOKEN" -sX GET http://localhost:8081/fledge/control/script/testScript
    """
    try:
        name = request.match_info.get('script_name', None)
        storage = connect.get_storage_async()
        payload = PayloadBuilder().SELECT("name", "steps", "acl").WHERE(['name', '=', name]).payload()
        result = await storage.query_tbl_with_payload('control_script', payload)
        if 'rows' in result:
            if result['rows']:
                script_info = result['rows'][0]
                script_info.update({"steps": script_info['steps']})
            else:
                raise NameNotFoundError('Script with name {} is not found.'.format(name))
        else:
            raise StorageServerError(result)
    except StorageServerError as err:
        msg = "Storage error: {}".format(str(err))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    except NameNotFoundError as err:
        msg = str(err)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response(script_info)


@has_permission("admin")
async def add_script(request: web.Request) -> web.Response:
    """ Add a script

    :Example:
        curl -H "authorization: $AUTH_TOKEN" -sX POST http://localhost:8081/fledge/control/script -d '{"name": "testScript", "steps": [{"write": {"order": 1, "service": "modbus1", "values": {"speed": "$requestedSpeed$", "fan": "1200"}, "condition": {"key": "requestedSpeed", "condition": "<", "value": "2000"}}, "delay": {"order": 2, "duration": 1500}}]}'
        curl -H "authorization: $AUTH_TOKEN" -sX POST http://localhost:8081/fledge/control/script -d '{"name": "test", "steps": [], "acl": "testACL"}'
    """
    try:
        data = await request.json()
        name = data.get('name', None)
        steps = data.get('steps', None)
        acl = data.get('acl', None)
        if name is None:
            raise ValueError('Script name is required')
        else:
            if not isinstance(name, str):
                raise TypeError('Script name must be a string')
            name = name.strip()
            if name == "":
                raise ValueError('Script name cannot be empty')
        if steps is None:
            raise ValueError('steps parameter is required')
        if not isinstance(steps, list):
            raise ValueError('steps must be a list')
        if acl is not None:
            if not isinstance(acl, str):
                raise ValueError('ACL name must be a string')
            acl = acl.strip()
            if acl == "":
                raise ValueError('ACL cannot be empty')
        result = {}
        storage = connect.get_storage_async()
        payload = PayloadBuilder().SELECT("name").WHERE(['name', '=', name]).payload()
        get_control_script_name_result = await storage.query_tbl_with_payload('control_script', payload)
        _steps = json.dumps(steps)
        if get_control_script_name_result['count'] == 0:
            payload = PayloadBuilder().INSERT(name=name, steps=_steps).payload()
            if acl is not None:
                # TODO: ACL record existence check if found then move else throw 404
                payload = PayloadBuilder().INSERT(name=name, steps=_steps, acl=acl).payload()
            insert_control_script_result = await storage.insert_into_tbl("control_script", payload)
            if 'response' in insert_control_script_result:
                if insert_control_script_result['response'] == "inserted":
                    result = {"name": name, "steps": json.loads(_steps)}
                    if acl is not None:
                        result["acl"] = acl
            else:
                raise StorageServerError(insert_control_script_result)
        else:
            msg = 'Script with name {} already exists.'.format(name)
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
        return web.json_response(result)


@has_permission("admin")
async def update_script(request: web.Request) -> web.Response:
    """ Update a script
    Only the steps & ACL parameters can be updated

    :Example:
        curl -H "authorization: $AUTH_TOKEN" -sX PUT http://localhost:8081/fledge/control/script/testScript -d '{"steps": []}'
        curl -H "authorization: $AUTH_TOKEN" -sX PUT http://localhost:8081/fledge/control/script/test -d '{"steps": [], "acl": "testACL"}'
    """
    try:
        name = request.match_info.get('script_name', None)

        data = await request.json()
        steps = data.get('steps', None)
        acl = data.get('acl', None)
        
        if steps is None and acl is None:
            raise ValueError("Nothing to update for the given payload.")
        if steps is not None and not isinstance(steps, list):
            raise ValueError('steps must be in list')
        if acl is not None:
            if not isinstance(acl, str):
                raise ValueError('ACL must be a string')
            acl = acl.strip()
            if acl == "":
                raise ValueError('ACL cannot be empty')
        storage = connect.get_storage_async()
        payload = PayloadBuilder().SELECT("name").WHERE(['name', '=', name]).payload()
        result = await storage.query_tbl_with_payload('control_script', payload)
        message = ""
        if 'rows' in result:
            if result['rows']:
                update_query = PayloadBuilder()
                set_values = {}
                if steps is not None: 
                    set_values["steps"] = json.dumps(steps)
                if acl is not None:
                    # TODO: acl existence check
                    set_values["acl"] = acl
                update_query.SET(**set_values).WHERE(['name', '=', name])
                update_result = await storage.update_tbl("control_script", update_query.payload())
                if 'response' in update_result:
                    if update_result['response'] == "updated":
                        message = "Control script {} updated successfully.".format(name)
                else:
                    raise StorageServerError(update_result)
            else:
                raise NameNotFoundError('No such {} script found'.format(name))
        else:
            raise StorageServerError(result)
    except StorageServerError as err:
        msg = "Storage error: {}".format(str(err))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    except NameNotFoundError as err:
        msg = str(err)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except ValueError as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({"message": message})


@has_permission("admin")
async def delete_script(request: web.Request) -> web.Response:
    """ Delete a script

    :Example:
        curl -H "authorization: $AUTH_TOKEN" -sX DELETE http://localhost:8081/fledge/control/script/test
    """
    try:
        name = request.match_info.get('script_name', None)
        storage = connect.get_storage_async()
        payload = PayloadBuilder().SELECT("name").WHERE(['name', '=', name]).payload()
        result = await storage.query_tbl_with_payload('control_script', payload)
        message = ""
        if 'rows' in result:
            if result['rows']:
                payload = PayloadBuilder().WHERE(['name', '=', name]).payload()
                delete_result = await storage.delete_from_tbl("control_script", payload)
                if 'response' in delete_result:
                    if delete_result['response'] == "deleted":
                        message = "{} script deleted successfully.".format(name)
                else:
                    raise StorageServerError(delete_result)
            else:
                raise NameNotFoundError('No such {} script found'.format(name))
        else:
            raise StorageServerError(result)
    except StorageServerError as err:
        msg = "Storage error: {}".format(str(err))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    except NameNotFoundError as err:
        msg = str(err)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({"message": message})
