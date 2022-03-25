# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import json
import logging
from aiohttp import web


from fledge.common import logger
from fledge.common.configuration_manager import ConfigurationManager
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
    | PUT DELETE          | /fledge/service/{service_name}/ACL   |
    --------------------------------------------------------------
"""

_logger = logger.setup(__name__, level=logging.INFO)


async def get_all_acls(request: web.Request) -> web.Response:
    """ Get list of all access control lists in the system

    :Example:
        curl -H "authorization: $AUTH_TOKEN" -sX GET http://localhost:8081/fledge/ACL
    """
    storage = connect.get_storage_async()
    payload = PayloadBuilder().SELECT("name", "service", "url").payload()
    result = await storage.query_tbl_with_payload('control_acl', payload)
    # TODO: FOGL-6258 Add users list in response where they are used
    return web.json_response({"acls": result['rows']})


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
                raise NameNotFoundError('ACL with name {} is not found.'.format(name))
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
         curl -H "authorization: $AUTH_TOKEN" -sX POST http://localhost:8081/fledge/ACL -d '{"name": "testACL",
         "service": [{"name": "IEC-104"}, {"type": "notification"}], "url": [{"url": "/fledge/south/operation",
         "acl": [{"type": "Northbound"}]}]}'
    """
    try:
        data = await request.json()
        name = data.get('name', None)
        service = data.get('service', None)
        url = data.get('url', None)
        if name is None:
            raise ValueError('ACL name is required.')
        else:
            if not isinstance(name, str):
                raise TypeError('ACL name must be a string.')
            name = name.strip()
            if name == "":
                raise ValueError('ACL name cannot be empty.')
        if service is None:
            raise ValueError('service parameter is required.')
        if not isinstance(service, list):
            raise TypeError('service must be a list.')
        # check each item in list is an object of, either 'type'|<service type> or 'name'|<service name> value pair
        if url is None:
            raise ValueError('url parameter is required.')
        if not isinstance(url, list):
            raise TypeError('url must be a list.')
        # check URLs list has objects with URL and a list of ACL where each acl item here is an object of
        # 'type'|<service type> value pair
        result = {}
        storage = connect.get_storage_async()
        payload = PayloadBuilder().SELECT("name").WHERE(['name', '=', name]).payload()
        get_control_acl_name_result = await storage.query_tbl_with_payload('control_acl', payload)
        if get_control_acl_name_result['count'] == 0:
            services = json.dumps(service)
            urls = json.dumps(url)
            payload = PayloadBuilder().INSERT(name=name, service=services, url=urls).payload()
            insert_control_acl_result = await storage.insert_into_tbl("control_acl", payload)
            if 'response' in insert_control_acl_result:
                if insert_control_acl_result['response'] == "inserted":
                    result = {"name": name, "service": json.loads(services), "url": json.loads(urls)}
            else:
                raise StorageServerError(insert_control_acl_result)
        else:
            msg = 'ACL with name {} already exists.'.format(name)
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
    """ Update an access control list
    Only the service and URL parameters can be updated. 

    :Example:
        curl -H "authorization: $AUTH_TOKEN" -sX PUT http://localhost:8081/fledge/ACL/testACL -d '{"service": [{"name": "Sinusoid"}]}'
        curl -H "authorization: $AUTH_TOKEN" -sX PUT http://localhost:8081/fledge/ACL/testACL -d '{"service": [],
        "url": [{"url": "/fledge/south/operation", "acl": [{"type": "Southbound"}]}]}'
    """
    try:
        name = request.match_info.get('acl_name', None)
        
        data = await request.json()
        service = data.get('service', None)
        url = data.get('url', None)
        if service is None and url is None:
            raise ValueError("Nothing to update for the given payload.")

        if service is not None and not isinstance(service, list):
            raise TypeError('service must be a list.')
        if url is not None and not isinstance(url, list):
            raise TypeError('url must be a list.')
        storage = connect.get_storage_async()
        payload = PayloadBuilder().SELECT("name").WHERE(['name', '=', name]).payload()
        result = await storage.query_tbl_with_payload('control_acl', payload)
        message = ""
        if 'rows' in result:
            if result['rows']:
                update_query = PayloadBuilder()
                
                set_values = {}
                if service is not None:
                    set_values["service"] = json.dumps(service)
                if url is not None:
                    set_values["url"] = json.dumps(url)
                
                update_query.SET(**set_values).WHERE(['name', '=', name])

                update_result = await storage.update_tbl("control_acl", update_query.payload())
                if 'response' in update_result:
                    if update_result['response'] == "updated":
                        message = "ACL {} updated successfully.".format(name)
                else:
                    raise StorageServerError(update_result)
            else:
                raise NameNotFoundError('ACL with name {} is not found.'.format(name))
        else:
            raise StorageServerError(result)
    except StorageServerError as err:
        message = "Storage error: {}".format(str(err))
        raise web.HTTPInternalServerError(reason=message, body=json.dumps({"message": message}))
    except NameNotFoundError as err:
        message = str(err)
        raise web.HTTPNotFound(reason=message, body=json.dumps({"message": message}))
    except (TypeError, ValueError) as err:
        message = str(err)
        raise web.HTTPBadRequest(reason=message, body=json.dumps({"message": message}))
    except Exception as ex:
        message = str(ex)
        raise web.HTTPInternalServerError(reason=message, body=json.dumps({"message": message}))
    else:
        return web.json_response({"message": message})


@has_permission("admin")
async def delete_acl(request: web.Request) -> web.Response:
    """ Delete an access control list. Only ACL's that have no users can be deleted

    :Example:
        curl -H "authorization: $AUTH_TOKEN" -sX DELETE http://localhost:8081/fledge/ACL/testACL
    """
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
                raise NameNotFoundError('ACL with name {} is not found.'.format(name))
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


@has_permission("admin")
async def attach_acl_to_service(request: web.Request) -> web.Response:
    """ Attach ACL to a service. A service may only have single ACL associated with it

    :Example:
        curl -H "authorization: $AUTH_TOKEN" -sX PUT http://localhost:8081/fledge/service/Sine/ACL -d '{"acl_name": "testACL"}'
    """
    try:
        svc_name = request.match_info.get('service_name', None)
        storage = connect.get_storage_async()
        payload = PayloadBuilder().SELECT(["id", "enabled"]).WHERE(['schedule_name', '=', svc_name]).payload()
        # check service name existence
        get_schedules_result = await storage.query_tbl_with_payload('schedules', payload)
        if 'count' in get_schedules_result:
            if get_schedules_result['count'] == 0:
                raise NameNotFoundError('{} service does not exist.'.format(svc_name))
        else:
            raise StorageServerError(get_schedules_result)
        data = await request.json()
        acl_name = data.get('acl_name', None)
        if acl_name is not None:
            if not isinstance(acl_name, str):
                raise ValueError('ACL must be a string')
            if acl_name.strip() == "":
                raise ValueError('ACL cannot be empty')
        else:
            raise ValueError('acl name is missing in given payload request')
        acl_name = acl_name.strip()
        # check ACL name existence
        payload = PayloadBuilder().SELECT("name", "service", "url").WHERE(['name', '=', acl_name]).payload()
        get_acl_result = await storage.query_tbl_with_payload('control_acl', payload)
        if 'count' in get_acl_result:
            if get_acl_result['count'] == 0:
                raise NameNotFoundError('{} ACL does not exist'.format(acl_name))
        else:
            raise StorageServerError(get_acl_result)
        # check ACL existence with service
        cf_mgr = ConfigurationManager(storage)
        security_cat_name = "{}Security".format(svc_name)
        category = await cf_mgr.get_category_all_items(security_cat_name)
        if category is None or category == {}:
            # Create {service_name}Security category and having value with AuthenticationCaller Global switch &
            # ACL info attached (name is excluded from the ACL dict)
            category_desc = "Security category for {} service".format(svc_name)
            del get_acl_result['rows'][0]['name']
            category_value = {
                'AuthenticatedCaller':
                    {
                        'description': 'Caller authorisation is needed',
                        'type': 'boolean',
                        'default': 'false',
                        'displayName': 'Enable caller authorisation'
                    },
                'ACL':
                    {
                        'description': 'Service ACL for {}'.format(svc_name),
                        'type': 'JSON',
                        'displayName': 'Service ACL',
                        'default': json.dumps(get_acl_result['rows'][0])
                    }
            }
            await cf_mgr.create_category(category_name=security_cat_name, category_description=category_desc,
                                         category_value=category_value)
            add_child_result = await cf_mgr.create_child_category(svc_name, [security_cat_name])
            if security_cat_name not in add_child_result['children']:
                raise StorageServerError(add_child_result)
        else:
            raise ValueError('A {} service has already ACL attached'.format(svc_name))
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
        return web.json_response({"message": "{} ACL attached to {} service successfully".format(acl_name, svc_name)})


@has_permission("admin")
async def detach_acl_from_service(request: web.Request) -> web.Response:
    """ Detach ACL from a service

    :Example:
        curl -H "authorization: $AUTH_TOKEN" -sX DELETE http://localhost:8081/fledge/service/Sine/ACL
    """
    try:
        svc_name = request.match_info.get('service_name', None)
        storage = connect.get_storage_async()
        payload = PayloadBuilder().SELECT(["id", "enabled"]).WHERE(['schedule_name', '=', svc_name]).payload()
        # check service name existence
        get_schedules_result = await storage.query_tbl_with_payload('schedules', payload)
        if 'count' in get_schedules_result:
            if get_schedules_result['count'] == 0:
                raise NameNotFoundError('{} service does not exist.'.format(svc_name))
        else:
            raise StorageServerError(get_schedules_result)
        cf_mgr = ConfigurationManager(storage)
        security_cat_name = "{}Security".format(svc_name)
        # Check {service_name}Security existence
        category = await cf_mgr.get_category_all_items(security_cat_name)
        if category is not None:
            # Delete {service_name}Security category
            category_desc = "Security category for {} service".format(svc_name)
            category_value = {}
            await cf_mgr.create_category(category_name=security_cat_name,
                                         category_description=category_desc,
                                         category_value=category_value)

            message = "ACL detached from {} service successfully".format(svc_name)
        else:
            raise ValueError("Nothing to delete as there is no ACL attached with {} service".format(svc_name))
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
