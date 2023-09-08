# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import json
from aiohttp import web
from enum import IntEnum

from fledge.common.logger import FLCoreLogger
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.services.core import connect, server


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2023 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_logger = FLCoreLogger().get_logger(__name__)

_help = """
    Two types of users: Control Administrator and Control Requestor
    Control Administrator:
                          - has access rights to create a control entrypoint.
                          - must be a user with role of admin or control
    Control Requestor:
                      - can make requests to defined control entrypoint but cannot create new entrypoints.
                      - any user role can make request to control entrypoint but the username must match one in list
                       of users given when entrypoint was created.
    -----------------------------------------------------------------------------------------------------------------
    | GET POST                       |        /fledge/control/manage                                                 |
    | GET PUT DELETE                 |        /fledge/control/manage/{name}                                          |
    | PUT                            |        /fledge/control/request/{name}                                          |
    ------------------------------------------------------------------------------------------------------------------
"""


def setup(app):
    app.router.add_route('POST', '/fledge/control/manage', create)
    app.router.add_route('GET', '/fledge/control/manage', get_all)
    app.router.add_route('GET', '/fledge/control/manage/{name}', get_by_name)
    app.router.add_route('PUT', '/fledge/control/manage/{name}', update)
    app.router.add_route('DELETE', '/fledge/control/manage/{name}', delete)
    app.router.add_route('PUT', '/fledge/control/request/{name}', update_request)


class EntryPointType(IntEnum):
    WRITE = 0
    OPERATION = 1


class Destination(IntEnum):
    BROADCAST = 0
    SERVICE = 1
    ASSET = 2
    SCRIPT = 3


async def _get_type(identifier):
    if isinstance(identifier, str):
        type_converted = [ept.value for ept in EntryPointType if ept.name.lower() == identifier]
    else:
        type_converted = [ept.name.lower() for ept in EntryPointType if ept.value == identifier]
    return type_converted[0]


async def _get_destination(identifier):
    if isinstance(identifier, str):
        dest_converted = [d.value for d in Destination if d.name.lower() == identifier]
    else:
        dest_converted = [d.name.lower() for d in Destination if d.value == identifier]
    return dest_converted[0]


async def _check_parameters(payload, skip_required=False):
    if not skip_required:
        required_keys = {"name", "description", "type", "destination"}
        if not all(k in payload.keys() for k in required_keys):
            raise KeyError("{} required keys are missing in request payload.".format(required_keys))
    final = {}
    name = payload.get('name', None)
    if name is not None:
        if not isinstance(name, str):
            raise ValueError('Control entrypoint name should be in string.')
        name = name.strip()
        if len(name) == 0:
            raise ValueError('Control entrypoint name cannot be empty.')
        final['name'] = name
    description = payload.get('description', None)
    if description is not None:
        if not isinstance(description, str):
            raise ValueError('Control entrypoint description should be in string.')
        description = description.strip()
        if len(description) == 0:
            raise ValueError('Control entrypoint description cannot be empty.')
        final['description'] = description
    _type = payload.get('type', None)
    if _type is not None:
        if not isinstance(_type, str):
            raise ValueError('Control entrypoint type should be in string.')
        _type = _type.strip()
        if len(_type) == 0:
            raise ValueError('Control entrypoint type cannot be empty.')
        ept_names = [ept.name.lower() for ept in EntryPointType]
        if _type not in ept_names:
            raise ValueError('Possible types are: {}'.format(ept_names))
        if _type == EntryPointType.OPERATION.name.lower():
            operation_name = payload.get('operation_name', None)
            if operation_name is not None:
                if not isinstance(operation_name, str):
                    raise ValueError('Control entrypoint operation name should be in string.')
                operation_name = operation_name.strip()
                if len(operation_name) == 0:
                    raise ValueError('Control entrypoint operation name cannot be empty.')
            else:
                raise KeyError('operation_name KV pair is missing')
            final['operation_name'] = operation_name
        final['type'] = await _get_type(_type)

    destination = payload.get('destination', None)
    if destination is not None:
        if not isinstance(destination, str):
            raise ValueError('Control entrypoint destination should be in string.')
        destination = destination.strip()
        if len(destination) == 0:
            raise ValueError('Control entrypoint destination cannot be empty.')
        dest_names = [d.name.lower() for d in Destination]
        if destination not in dest_names:
            raise ValueError('Possible destination values are: {}'.format(dest_names))

        destination_idx = await _get_destination(destination)
        final['destination'] = destination_idx

        # only if non-zero
        final['destination_arg'] = ''
        if destination_idx:
            destination_arg = payload.get(destination, None)
            if destination_arg is not None:
                if not isinstance(destination_arg, str):
                    raise ValueError('Control entrypoint destination argument should be in string.')
                destination_arg = destination_arg.strip()
                if len(destination_arg) == 0:
                    raise ValueError('Control entrypoint destination argument cannot be empty.')
                final[destination] = destination_arg
                final['destination_arg'] = destination
            else:
                raise KeyError('{} destination argument is missing.'.format(destination))
    anonymous = payload.get('anonymous', None)
    if anonymous is not None:
        if not isinstance(anonymous, bool):
            raise ValueError('anonymous should be a bool.')
        anonymous = 't' if anonymous else 'f'
        final['anonymous'] = anonymous
    constants = payload.get('constants', None)
    if constants is not None:
        if not isinstance(constants, dict):
            raise ValueError('constants should be dictionary.')
        if not constants and  _type == EntryPointType.WRITE.name.lower():
            raise ValueError('constants should not be empty.')
        final['constants'] = constants
    else:
        if _type == EntryPointType.WRITE.name.lower():
            raise ValueError("For type write constants must have passed in payload and cannot have empty value.")

    variables = payload.get('variables', None)
    if variables is not None:
        if not isinstance(variables, dict):
            raise ValueError('variables should be a dictionary.')
        if not variables and _type == EntryPointType.WRITE.name.lower():
            raise ValueError('variables should not be empty.')
        final['variables'] = variables
    else:
        if _type == EntryPointType.WRITE.name.lower():
            raise ValueError("For type write variables must have passed in payload and cannot have empty value.")

    allow = payload.get('allow', None)
    if allow is not None:
        if not isinstance(allow, list):
            raise ValueError('allow should be an array of list of users.')
        # FIXME: get usernames validation
        final['allow'] = allow
    return final


async def create(request: web.Request) -> web.Response:
    """Create a control entrypoint
     :Example:
         curl -sX POST http://localhost:8081/fledge/control/manage -d '{"name": "SetLatheSpeed", "description": "Set the speed of the lathe", "type": "write", "destination": "asset", "asset": "lathe", "constants": {"units": "spin"}, "variables": {"rpm": "100"}, "allow":["AJ"], "anonymous": "reject"}'
     """
    try:
        data = await request.json()
        payload = await _check_parameters(data)
        name = payload['name']
        storage = connect.get_storage_async()
        result = await storage.query_tbl("control_api")
        entrypoints = [r['name'] for r in result['rows']]
        if name in entrypoints:
            raise ValueError('{} control entrypoint is already in use.'.format(name))
        # add common data keys in control_api table
        control_api_column_name = {"name": name,
                                   "description": payload['description'],
                                   "type": payload['type'],
                                   "operation_name": payload['operation_name'] if payload['type'] == 1 else "",
                                   "destination": payload['destination'],
                                   "destination_arg": payload[
                                       payload['destination_arg']] if payload['destination'] else "",
                                   "anonymous": payload['anonymous']
                                   }
        api_insert_payload = PayloadBuilder().INSERT(**control_api_column_name).payload()
        insert_api_result = await storage.insert_into_tbl("control_api", api_insert_payload)
        if insert_api_result['rows_affected'] == 1:
            # add if any params data keys in control_api_parameters table
            if 'constants' in payload:
                for k, v in payload['constants'].items():
                    control_api_params_column_name = {"name": name, "parameter": k, "value": v, "constant": 't'}
                    api_params_insert_payload = PayloadBuilder().INSERT(**control_api_params_column_name).payload()
                    await storage.insert_into_tbl("control_api_parameters", api_params_insert_payload)
            if 'variables' in payload:
                for k, v in payload['variables'].items():
                    control_api_params_column_name = {"name": name, "parameter": k, "value": v, "constant": 'f'}
                    api_params_insert_payload = PayloadBuilder().INSERT(**control_api_params_column_name).payload()
                    await storage.insert_into_tbl("control_api_parameters", api_params_insert_payload)
            # add if any users in control_api_acl table
            for u in payload['allow']:
                control_acl_column_name = {"name": name, "user": u}
                acl_insert_payload = PayloadBuilder().INSERT(**control_acl_column_name).payload()
                await storage.insert_into_tbl("control_api_acl", acl_insert_payload)
    except (KeyError, ValueError) as err:
        msg = str(err)
        raise web.HTTPBadRequest(body=json.dumps({"message": msg}), reason=msg)
    except Exception as ex:
        msg = str(ex)
        _logger.error(ex, "Failed to create control entrypoint.")
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({"message": "{} control entrypoint has been created successfully.".format(name)})


async def get_all(request: web.Request) -> web.Response:
    """Get a list of all control entrypoints
     :Example:
         curl -sX GET http://localhost:8081/fledge/control/manage
     """
    storage = connect.get_storage_async()
    result = await storage.query_tbl("control_api")
    entrypoint = []
    for r in result["rows"]:
        """permitted: means user is able to make the API call
        This is on the basis of anonymous flag if true then permitted true
        If anonymous flag is false then list of allowed users to determine if the specific user can make the call
        """
        # TODO: verify the user when anonymous is false and set permitted value based on it
        entrypoint.append({"name": r['name'], "description": r['description'],
                           "permitted": True if r['anonymous'] == 't' else False})
    return web.json_response({"controls": entrypoint})


async def get_by_name(request: web.Request) -> web.Response:
    """Get a control entrypoint by name
    :Example:
        curl -sX GET http://localhost:8081/fledge/control/manage/SetLatheSpeed
    """
    # TODO: forbidden when permitted is false on the basis of anonymous
    name = request.match_info.get('name', None)
    try:
        storage = connect.get_storage_async()
        payload = PayloadBuilder().WHERE(["name", '=', name]).payload()
        result = await storage.query_tbl_with_payload("control_api", payload)
        if not result['rows']:
            raise KeyError('{} control entrypoint not found.'.format(name))
        response = result['rows'][0]
        response['type'] = await _get_type(response['type'])
        response['destination'] = await _get_destination(response['destination'])
        if response['destination'] != "broadcast":
            response[response['destination']] = response['destination_arg']
        del response['destination_arg']
        param_result = await storage.query_tbl_with_payload("control_api_parameters", payload)
        constants = {}
        variables = {}
        if param_result['rows']:
            for r in param_result['rows']:
                if r['constant'] == 't':
                    constants[r['parameter']] = r['value']
                else:
                    variables[r['parameter']] = r['value']
            response['constants'] = constants
            response['variables'] = variables
        else:
            response['constants'] = constants
            response['variables'] = variables
        response['allow'] = ""
        acl_result = await storage.query_tbl_with_payload("control_api_acl", payload)
        if acl_result['rows']:
            users = []
            for r in acl_result['rows']:
                users.append(r['user'])
            response['allow'] = users
    except ValueError as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except KeyError as err:
        msg = str(err)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        _logger.error(ex, "Failed to fetch details of {} entrypoint.".format(name))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response(response)


async def delete(request: web.Request) -> web.Response:
    """Delete a control entrypoint
    :Example:
        curl -sX DELETE http://localhost:8081/fledge/control/manage/SetLatheSpeed
    """
    name = request.match_info.get('name', None)
    try:
        storage = connect.get_storage_async()
        payload = PayloadBuilder().WHERE(["name", '=', name]).payload()
        result = await storage.query_tbl_with_payload("control_api", payload)
        if not result['rows']:
            raise KeyError('{} control entrypoint not found.'.format(name))
        await storage.delete_from_tbl("control_api_acl", payload)
        await storage.delete_from_tbl("control_api_parameters", payload)
        await storage.delete_from_tbl("control_api", payload)
    except ValueError as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except KeyError as err:
        msg = str(err)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        _logger.error(ex, "Failed to delete of {} entrypoint.".format(name))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({"message": "{} control entrypoint has been deleted successfully.".format(name)})


async def update(request: web.Request) -> web.Response:
    """Update a control entrypoint
    :Example:
        curl -sX PUT http://localhost:8081/fledge/control/manage/SetLatheSpeed -d '{"name": "Changed"}'
    """
    name = request.match_info.get('name', None)
    try:
        storage = connect.get_storage_async()
        payload = PayloadBuilder().WHERE(["name", '=', name]).payload()
        result = await storage.query_tbl_with_payload("control_api", payload)
        if not result['rows']:
            raise KeyError('{} control entrypoint not found.'.format(name))
        data = await request.json()
        columns = await _check_parameters(data, skip_required=True)
        # TODO: rename
        if 'name' in columns:
            del columns['name']
        # TODO:  "constants", "variables", "allow"
        possible_keys = {"name", "description", "type", "operation_name", "destination", "destination_arg", "anonymous"}
        if 'type' in columns:
            columns['operation_name'] = columns['operation_name'] if columns['type'] == 1 else ""
        if 'destination_arg' in columns:
            dest = await _get_destination(columns['destination'])
            columns['destination_arg'] = columns[dest] if columns['destination'] else ""
        entries_to_remove = set(columns) - set(possible_keys)
        for k in entries_to_remove:
            del columns[k]
        payload = PayloadBuilder().SET(**columns).WHERE(['name', '=', name]).payload()
        await storage.update_tbl("control_api", payload)
    except Exception as ex:
        msg = str(ex)
        _logger.error(ex, "Failed to update the details of {} entrypoint.".format(name))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({"message": "{} control entrypoint has been updated successfully.".format(name)})


async def update_request(request: web.Request) -> web.Response:
    """API control entry  points can be called with PUT operation to URL form
    :Example:
        curl -sX PUT http://localhost:8081/fledge/control/request/SetLatheSpeed -d '{"distance": "13"}'
    """
    name = request.match_info.get('name', None)
    try:
        storage = connect.get_storage_async()
        payload = PayloadBuilder().WHERE(["name", '=', name]).payload()
        result = await storage.query_tbl_with_payload("control_api", payload)
        if not result['rows']:
            raise KeyError('{} control entrypoint not found.'.format(name))
        result = await storage.query_tbl_with_payload("control_api_parameters", payload)
        if request.user is not None:
            # Admin and Control roles can always call entrypoints. But for a user it must match in list of allowed users
            if request.user["role_id"] not in (1, 5):
                acl_result = await storage.query_tbl_with_payload("control_api_acl", payload)
                allowed_user = [r['user'] for r in acl_result['rows']]
                if request.user["uname"] not in allowed_user:
                    raise ValueError("Operation is not allowed for the {} user.".format(request.user['uname']))
        data = await request.json()
        payload = {"updates": []}
        for k, v in data.items():
            for r in result['rows']:
                if r['parameter'] == k:
                    if isinstance(v, str):
                        payload_item = PayloadBuilder().SET(value=v).WHERE(["name", "=", name]).AND_WHERE(["parameter", "=", k]).payload()
                        payload['updates'].append(json.loads(payload_item))
                        break
                    else:
                        raise ValueError("Value should be in string for {} parameter.".format(k))
        await storage.update_tbl("control_api_parameters", json.dumps(payload))
    except ValueError as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        _logger.error(ex, "Failed to update the control request details of {} entrypoint.".format(name))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({"message": "{} control entrypoint URL called.".format(name)})
