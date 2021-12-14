# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import json
from aiohttp import web

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
        curl -sX POST http://localhost:8081/fledge/control/script -d '{"name": "testScript", "steps": []}'
        curl -sX POST http://localhost:8081/fledge/control/script -d '{"name": "test", "steps": [], "acl": "testACL"}'
    """
    try:
        data = await request.json()
        name = data.get('name', None)
        steps = data.get('steps', None)
        acl = data.get('acl', None)
        if name is None:
            raise ValueError('name param is required')
        if name is not None and name.strip() == "":
            raise ValueError('name cannot be empty')
        if steps is None:
            raise ValueError('steps param is required')
        if not isinstance(steps, list):
            raise ValueError('steps must be a list')
        if acl is not None and acl.strip() == "":
            raise ValueError('ACL cannot be empty')
    except (TypeError, ValueError) as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({"message": "To be Implemented"})


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

