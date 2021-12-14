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
    --------------------------------------------------------------
    | GET POST            | /fledge/ACL                          |
    | GET PUT DELETE      | /fledge/ACL/{acl_name}               |
    | PUT DELETE          | /fledge/service/{service_name}/ACL   |
    --------------------------------------------------------------
"""


async def get_all_acls(request: web.Request) -> web.Response:
    """ Get list of all access control lists in the systemt

    :Example:
        curl -sX GET http://localhost:8081/fledge/ACL
    """
    return web.json_response({"message": "To be Implemented"})


async def get_acl(request: web.Request) -> web.Response:
    """ Get the details of access control list by name

    :Example:
        curl -sX GET http://localhost:8081/fledge/ACL/{acl_name}
    """
    try:
        name = request.match_info.get('acl_name', None)
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({"message": "To be Implemented"})


async def add_acl(request: web.Request) -> web.Response:
    """ Create a new access control list

    :Example:
        curl -sX POST http://localhost:8081/fledge/ACL -d '{"name": "testScript", "service": [], "url": []}'
    """
    try:
        data = await request.json()
        name = data.get('name', None)
        service = data.get('service', None)
        url = data.get('url', None)
        if name is None:
            raise ValueError('name param is required')
        if name is not None and name.strip() == "":
            raise ValueError('name cannot be empty')
        if service is None:
            raise ValueError('service param is required')
        if not isinstance(service, list):
            raise ValueError('service must be a list')
        if url is None:
            raise ValueError('url param is required')
        if not isinstance(url, list):
            raise ValueError('url must be a list')
    except (TypeError, ValueError) as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({"message": "To be Implemented"})


async def update_acl(request: web.Request) -> web.Response:
    """ Update an access control list. Only the set of services and URL's can be updated

    :Example:
        curl -sX PUT http://localhost:8081/fledge/ACL/{acl_name} -d '{"services": [{}]}'
        curl -sX PUT http://localhost:8081/fledge/ACL/{acl_name} -d '{"services": [{}], "url": [{}]}'
    """
    try:
        name = request.match_info.get('acl_name', None)
        data = await request.json()
        services = data.get('services', None)
        url = data.get('url', None)
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({"message": "To be Implemented"})


async def delete_acl(request: web.Request) -> web.Response:
    """ Delete an access control list. Only ACL's that have no users can be deleted

    :Example:
        curl -sX DELETE http://localhost:8081/fledge/ACL/{acl_name}
    """
    try:
        name = request.match_info.get('acl_name', None)
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({"message": "To be Implemented"})


async def attach_acl_to_service(request: web.Request) -> web.Response:
    """ Attach ACL to a service. A service may only have single ACL associated with it

    :Example:
        curl -sX PUT http://localhost:8081/fledge/service/{service_name}/ACL -d '{"name": "testACL"}'
    """
    try:
        svc_name = request.match_info.get('service_name', None)
        data = await request.json()
        acl_name = data.get('name', None)
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({"message": "To be Implemented"})


async def detach_acl_from_service(request: web.Request) -> web.Response:
    """ Detach ACL from a service

    :Example:
        curl -sX DELETE http://localhost:8081/fledge/service/{service_name}/ACL
    """
    try:
        svc_name = request.match_info.get('service_name', None)
        data = await request.json()
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({"message": "To be Implemented"})
