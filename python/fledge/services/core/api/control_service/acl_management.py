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
    --------------------------------------------------------------
    | GET POST            | /fledge/ACL                          |
    | GET PUT DELETE      | /fledge/ACL/{acl_name}               |
    --------------------------------------------------------------
"""

_logger = logger.setup(__name__, level=logging.INFO)
FORBIDDEN_MSG = 'resource you were trying to reach is absolutely forbidden for some reason'


async def get_all_acls(request: web.Request) -> web.Response:
    """ Get list of all access control lists in the system

    :Example:
        curl -H "authorization: $AUTH_TOKEN" -sX GET http://localhost:8081/fledge/ACL
    """
    storage = connect.get_storage_async()
    payload = PayloadBuilder().SELECT("name", "service", "url").payload()
    result = await storage.query_tbl_with_payload('control_acl', payload)
    all_acls = [key for key in result['rows']]
    # TODO: Add users list in response where they are used
    return web.json_response({"acls": all_acls})


async def get_acl(request: web.Request) -> web.Response:
    """ Get the details of access control list by name

    :Example:
        curl -H "authorization: $AUTH_TOKEN" -sX GET http://localhost:8081/fledge/ACL/testACL
    """
    try:
        name = request.match_info.get('acl_name', None)
        storage = connect.get_storage_async()
        payload = PayloadBuilder().SELECT("name", "service", "url").WHERE(['name', '=', name]).payload()
        result = await storage.query_tbl_with_payload('control_acl', payload)
        if 'rows' in result:
            if result['rows']:
                acl_info = result['rows'][0]
            else:
                raise NameNotFoundError('No such {} ACL found'.format(name))
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
        return web.json_response(acl_info)


@has_permission("admin")
async def add_acl(request: web.Request) -> web.Response:
    """ Create a new access control list

    :Example:
         curl -H "authorization: $AUTH_TOKEN" -sX POST http://localhost:8081/fledge/ACL -d '{"name": "testACL", "service": {"name": "IEC-104", "type": "notification"}, "url": {"URL": "/fledge/south/operation"}}'
    """
    if request.is_auth_optional:
        msg = "Add ACL: {}".format(FORBIDDEN_MSG)
        _logger.warning(msg)
        raise web.HTTPForbidden(reason=msg, body=json.dumps({"message": msg}))
    try:
        data = await request.json()
        name = data.get('name', None)
        service = data.get('service', None)
        url = data.get('url', None)
        if name is None:
            raise ValueError('name param is required')
        if name is not None:
            if not isinstance(name, str):
                raise TypeError('name must be a string')
            name = name.strip()
            if name == "":
                raise ValueError('name cannot be empty')
        if service is None:
            raise ValueError('service param is required')
        if not isinstance(service, dict):
            raise TypeError('service must be a dictionary')
        if url is None:
            raise ValueError('url param is required')
        if not isinstance(url, dict):
            raise TypeError('url must be a dictionary')
        result = {}
        storage = connect.get_storage_async()
        payload = PayloadBuilder().SELECT("name").WHERE(['name', '=', name]).payload()
        get_control_acl_name_result = await storage.query_tbl_with_payload('control_acl', payload)
        if get_control_acl_name_result['count'] == 0:
            payload = PayloadBuilder().INSERT(name=name, service=service, url=url).payload()
            insert_control_acl_result = await storage.insert_into_tbl("control_acl", payload)
            if 'response' in insert_control_acl_result:
                if insert_control_acl_result['response'] == "inserted":
                    result = {"name": name, "service": service, "url": url}
            else:
                raise StorageServerError(insert_control_acl_result)
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
        return web.json_response(result)


@has_permission("admin")
async def update_acl(request: web.Request) -> web.Response:
    """ Update an access control list. Only the set of service and URL's can be updated

    :Example:
        curl -H "authorization: $AUTH_TOKEN" -sX PUT http://localhost:8081/fledge/ACL/testACL -d '{"service": {"name": "Sinusoid"}}'
        curl -H "authorization: $AUTH_TOKEN" -sX PUT http://localhost:8081/fledge/ACL/testACL -d '{"service": {}, "url": {"URL": "/fledge/south/operation"}}'
    """
    if request.is_auth_optional:
        msg = "Update ACL: {}".format(FORBIDDEN_MSG)
        _logger.warning(msg)
        raise web.HTTPForbidden(reason=msg, body=json.dumps({"message": msg}))
    try:
        name = request.match_info.get('acl_name', None)
        data = await request.json()
        service = data.get('service', None)
        url = data.get('url', None)
        if service is None and url is None:
            raise ValueError("Nothing to update in a given payload. Only service and url can be updated")
        if service is not None and not isinstance(service, dict):
            raise TypeError('service must be a dictionary')
        if url is not None and not isinstance(url, dict):
            raise TypeError('url must be a dictionary')
        storage = connect.get_storage_async()
        payload = PayloadBuilder().SELECT("name").WHERE(['name', '=', name]).payload()
        result = await storage.query_tbl_with_payload('control_acl', payload)
        message = ""
        if 'rows' in result:
            if result['rows']:
                if service is not None and url is not None:
                    update_payload = PayloadBuilder().SET(service=service, url=url).WHERE(
                        ['name', '=', name]).payload()
                elif service is not None:
                    update_payload = PayloadBuilder().SET(service=service).WHERE(['name', '=', name]).payload()
                else:
                    update_payload = PayloadBuilder().SET(url=url).WHERE(['name', '=', name]).payload()
                update_result = await storage.update_tbl("control_acl", update_payload)
                if 'response' in update_result:
                    if update_result['response'] == "updated":
                        message = "Record updated successfully for {} ACL".format(name)
                else:
                    raise StorageServerError(update_result)
            else:
                raise NameNotFoundError('No such {} ACL found'.format(name))
        else:
            raise StorageServerError(result)
    except StorageServerError as err:
        msg = "Storage error: {}".format(str(err))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    except NameNotFoundError as err:
        msg = str(err)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except (TypeError, ValueError) as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({"message": message})


@has_permission("admin")
async def delete_acl(request: web.Request) -> web.Response:
    """ Delete an access control list. Only ACL's that have no users can be deleted

    :Example:
        curl -H "authorization: $AUTH_TOKEN" -sX DELETE http://localhost:8081/fledge/ACL/testACL
    """
    if request.is_auth_optional:
        msg = "Delete ACL: {}".format(FORBIDDEN_MSG)
        _logger.warning(msg)
        raise web.HTTPForbidden(reason=msg, body=json.dumps({"message": msg}))
    try:
        name = request.match_info.get('acl_name', None)
        storage = connect.get_storage_async()
        payload = PayloadBuilder().SELECT("name").WHERE(['name', '=', name]).payload()
        result = await storage.query_tbl_with_payload('control_acl', payload)
        message = ""
        if 'rows' in result:
            if result['rows']:
                payload = PayloadBuilder().WHERE(['name', '=', name]).payload()
                # TODO: delete only that have no users
                delete_result = await storage.delete_from_tbl("control_acl", payload)
                if 'response' in delete_result:
                    if delete_result['response'] == "deleted":
                        message = "{} ACL deleted successfully".format(name)
                else:
                    raise StorageServerError(delete_result)
            else:
                raise NameNotFoundError('No such {} ACL found'.format(name))
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
