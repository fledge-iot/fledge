# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import json
import logging
import datetime
import uuid

from aiohttp import web

from fledge.common import logger
from fledge.common.configuration_manager import ConfigurationManager
from fledge.common.storage_client.exceptions import StorageServerError
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.common.web.middleware import has_permission
from fledge.services.core import connect
from fledge.services.core import server
from fledge.services.core.scheduler.entities import Schedule, ManualSchedule
from fledge.services.core.api.control_service.exceptions import *


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2021 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -----------------------------------------------------------------------
    | GET POST            | /fledge/control/script                        |
    | GET PUT DELETE      | /fledge/control/script/{script_name}          |
    | GET                 | /fledge/control/script/schedule               |
    | POST                | /fledge/control/script/{script_name}/schedule |
    -----------------------------------------------------------------------
"""

_logger = logger.setup(__name__, level=logging.INFO)


def setup(app):
    # schedules
    app.router.add_route('GET', '/fledge/control/script/schedule', get_all_schedules)
    app.router.add_route('GET', '/fledge/control/script/{script_name}/schedule', get_schedule_by_name)
    app.router.add_route('POST', '/fledge/control/script/{script_name}/schedule', add_schedule_and_configuration)

    # CRUD's
    app.router.add_route('POST', '/fledge/control/script', add)
    app.router.add_route('GET', '/fledge/control/script', get_all)
    app.router.add_route('GET', '/fledge/control/script/{script_name}', get_by_name)
    app.router.add_route('PUT', '/fledge/control/script/{script_name}', update)
    app.router.add_route('DELETE', '/fledge/control/script/{script_name}', delete)


async def get_all_schedules(request: web.Request) -> web.Response:
    """ Get list of automation script type schedule

    :Example:
        curl -H "authorization: $AUTH_TOKEN" -sX GET http://localhost:8081/fledge/control/script/schedule
    """
    schedule_list = await server.Server.scheduler.get_schedules()
    schedules = []
    for sch in schedule_list:
        if sch.process_name == "automation_script":
            schedules.append({
                'id': str(sch.schedule_id),
                'name': sch.name,
                'processName': sch.process_name,
                'type': Schedule.Type(int(sch.schedule_type)).name,
                'repeat': 0,
                'time': 0,
                'day': sch.day,
                'exclusive': sch.exclusive,
                'enabled': sch.enabled
            })
    return web.json_response({'schedules': schedules})


async def get_schedule_by_name(request: web.Request) -> web.Response:
    """ Get script schedule by name

    :Example:
        curl -H "authorization: $AUTH_TOKEN" -sX GET http://localhost:8081/fledge/control/script/testScript/schedule
    """
    name = request.match_info.get('script_name', None)
    schedule = {}
    try:
        schedule_list = await server.Server.scheduler.get_schedules()
        for sch in schedule_list:
            if sch.name == name and sch.process_name == "automation_script":
                schedule = {
                    'id': str(sch.schedule_id),
                    'name': sch.name,
                    "processName": sch.process_name,
                    'type': Schedule.Type(int(sch.schedule_type)).name,
                    'repeat': 0,
                    'time': 0,
                    'day': sch.day,
                    'exclusive': sch.exclusive,
                    'enabled': sch.enabled
                }
                break
        if not schedule:
            raise ValueError('No schedule found for {} script.'.format(name))
    except ValueError as err:
        msg = str(err)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response(schedule)


@has_permission("admin")
async def add_schedule_and_configuration(request: web.Request) -> web.Response:
    """ Create a schedule and configuration category for the task
       :Example:
           curl -H "authorization: $AUTH_TOKEN" -sX POST http://localhost:8081/fledge/control/script/testScript/schedule
           curl -H "authorization: $AUTH_TOKEN" -sX POST http://localhost:8081/fledge/control/script/testScript/schedule -d '{"parameters": {"foobar": "0.8"}}'
       """
    params = None
    try:
        data = await request.json()
        params = data.get('parameters')
        if params is None:
            msg = "parameters field is required."
            return web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
        if not isinstance(params, dict):
            msg = "parameters must be a dictionary."
            return web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
        if not params:
            msg = "parameters cannot be an empty."
            return web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except Exception:
        pass
    try:
        name = request.match_info.get('script_name', None)
        storage = connect.get_storage_async()
        payload = PayloadBuilder().SELECT("name", "steps", "acl").WHERE(['name', '=', name]).payload()
        result = await storage.query_tbl_with_payload('control_script', payload)
        if 'rows' in result:
            if result['rows']:
                write_steps, macros_used_in_write_steps = _validate_write_steps(result['rows'][0]['steps'])
                if not write_steps:
                    msg = 'write steps KV pair is missing for {} script.'.format(name)
                    return web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
                if params is not None:
                    for pk, pv in params.items():
                        if pk not in macros_used_in_write_steps:
                            msg = '{} param is not found in write steps for {} script.'.format(pk, name)
                            return web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
                        if not isinstance(pv, str):
                            msg = 'Value should be in string for {} param.'.format(pk)
                            return web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
                if params is not None:
                    for w in write_steps:
                        for k, v in w['values'].items():
                            if any(p in v for p in params):
                                # Amend parameters to the existing dict
                                w['values'][v[1:-1]] = w['values'].pop(k)
                                w['values'][v[1:-1]] = params[v[1:-1]]
                # Check if schedule exists for an automation task
                schedule_list = await server.Server.scheduler.get_schedules()
                for sch in schedule_list:
                    if sch.name == name and sch.process_name == "automation_script":
                        msg = '{} schedule already exists.'.format(name)
                        return web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
                # Create configuration category for a task
                cf_mgr = ConfigurationManager(connect.get_storage_async())
                category_value = {"write": {"default": json.dumps(write_steps),
                                            "description": "Dispatcher write operation using automation script",
                                            "type": "string"}}
                category_desc = "{} configuration for automation script task".format(name)
                cat_name = "{}-automation-script".format(name)
                await cf_mgr.create_category(category_name=cat_name, category_description=category_desc,
                                             category_value=category_value, keep_original_items=True, display_name=name)
                # Create Parent-child relation
                await cf_mgr.create_child_category("dispatcher", [cat_name])
                # Create schedule for an automation script
                manual_schedule = ManualSchedule()
                manual_schedule.name = name
                manual_schedule.process_name = 'automation_script'
                manual_schedule.repeat = datetime.timedelta(seconds=0)
                manual_schedule.enabled = True
                manual_schedule.exclusive = True
                await server.Server.scheduler.save_schedule(manual_schedule)
                # Set the schedule id
                schedule_id = manual_schedule.schedule_id
                # Add schedule_id to the schedule queue
                await server.Server.scheduler.queue_task(schedule_id)
            else:
                raise NameNotFoundError('Script with name {} is not found.'.format(name))
        else:
            raise StorageServerError(result)
    except StorageServerError as err:
        msg = "Storage error: {}".format(str(err))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    except (ValueError, NameNotFoundError) as err:
        msg = str(err)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except (KeyError, RuntimeError) as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        msg = "Schedule and configuration is created for an automation script with name {}".format(name)
        return web.json_response({"message": msg})


async def get_all(request: web.Request) -> web.Response:
    """ Get list of all scripts

    :Example:
        curl -H "authorization: $AUTH_TOKEN" -sX GET http://localhost:8081/fledge/control/script
    """
    storage = connect.get_storage_async()
    cf_mgr = ConfigurationManager(storage)
    payload = PayloadBuilder().SELECT("name", "steps", "acl").payload()
    result = await storage.query_tbl_with_payload('control_script', payload)
    schedule_list = await server.Server.scheduler.get_schedules()
    scripts = []
    for row in result['rows']:
        # Add configuration to script
        cat_name = "{}-automation-script".format(row['name'])
        get_category = await cf_mgr.get_category_all_items(cat_name)
        row['configuration'] = {}
        if get_category is not None:
            row['configuration'] = {"categoryName": cat_name}
            row['configuration'].update(get_category)
        # Add schedule to script
        for sch in schedule_list:
            row['schedule'] = {}
            if sch.name == row['name'] and sch.process_name == "automation_script":
                row['schedule'] = {
                    'id': str(sch.schedule_id),
                    'name': sch.name,
                    'processName': sch.process_name,
                    'type': Schedule.Type(int(sch.schedule_type)).name,
                    'repeat': 0,
                    'time': 0,
                    'day': sch.day,
                    'exclusive': sch.exclusive,
                    'enabled': sch.enabled
                }
                break
        scripts.append(row)
    return web.json_response({"scripts": scripts})


async def get_by_name(request: web.Request) -> web.Response:
    """ Get a named script

    :Example:
        curl -H "authorization: $AUTH_TOKEN" -sX GET http://localhost:8081/fledge/control/script/testScript
    """
    try:
        name = request.match_info.get('script_name', None)
        storage = connect.get_storage_async()
        cf_mgr = ConfigurationManager(storage)
        payload = PayloadBuilder().SELECT("name", "steps", "acl").WHERE(['name', '=', name]).payload()
        result = await storage.query_tbl_with_payload('control_script', payload)
        if 'rows' in result:
            if result['rows']:
                rows = result['rows'][0]
                rows['configuration'] = {}
                rows['schedule'] = {}
                try:
                    # Add configuration to script
                    cat_name = "{}-automation-script".format(rows['name'])
                    get_category = await cf_mgr.get_category_all_items(cat_name)
                    if get_category is not None:
                        rows['configuration'] = {"categoryName": cat_name}
                        rows['configuration'].update(get_category)
                    # Add schedule to script
                    sch = await server.Server.scheduler.get_schedule_by_name(rows['name'])
                    rows['schedule'] = {
                        'id': str(sch.schedule_id),
                        'name': sch.name,
                        'processName': sch.process_name,
                        'type': Schedule.Type(int(sch.schedule_type)).name,
                        'repeat': 0,
                        'time': 0,
                        'day': sch.day,
                        'exclusive': sch.exclusive,
                        'enabled': sch.enabled
                    }
                except:
                    pass
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
        return web.json_response(rows)


@has_permission("admin")
async def add(request: web.Request) -> web.Response:
    """ Add a script

    :Example:
        curl -H "authorization: $AUTH_TOKEN" -sX POST http://localhost:8081/fledge/control/script -d '{"name": "testScript", "steps": [{"write": {"order": 0, "service": "modbus1", "values": {"speed": "$requestedSpeed$", "fan": "1200"}, "condition": {"key": "requestedSpeed", "condition": "<", "value": "2000"}}}, {"delay": {"order": 1, "duration": 1500}}]}'
        curl -H "authorization: $AUTH_TOKEN" -sX POST http://localhost:8081/fledge/control/script -d '{"name": "test", "steps": [], "acl": "testACL"}'
    """
    try:
        data = await request.json()
        name = data.get('name', None)
        steps = data.get('steps', None)
        acl = data.get('acl', None)
        if name is None:
            raise ValueError('Script name is required.')
        else:
            if not isinstance(name, str):
                raise TypeError('Script name must be a string.')
            name = name.strip()
            if name == "":
                raise ValueError('Script name cannot be empty.')
        if steps is None:
            raise ValueError('steps parameter is required.')
        if not isinstance(steps, list):
            raise ValueError('steps must be a list.')
        if acl is not None:
            if not isinstance(acl, str):
                raise ValueError('ACL name must be a string.')
            acl = acl.strip()
        _steps = _validate_steps_and_convert_to_str(steps)
        result = {}
        storage = connect.get_storage_async()
        # Check duplicate script record
        payload = PayloadBuilder().SELECT("name").WHERE(['name', '=', name]).payload()
        get_control_script_name_result = await storage.query_tbl_with_payload('control_script', payload)
        if get_control_script_name_result['count'] == 0:
            payload = PayloadBuilder().INSERT(name=name, steps=_steps).payload()
            if acl is not None:
                # Check the existence of valid ACL record
                acl_payload = PayloadBuilder().SELECT("name").WHERE(['name', '=', acl]).payload()
                acl_result = await storage.query_tbl_with_payload('control_acl', acl_payload)
                if 'rows' in acl_result:
                    if acl_result['rows']:
                        payload = PayloadBuilder().INSERT(name=name, steps=_steps, acl=acl).payload()
                    else:
                        raise NameNotFoundError('ACL with name {} is not found.'.format(acl))
                else:
                    raise StorageServerError(acl_result)
            # Insert the script record
            insert_control_script_result = await storage.insert_into_tbl("control_script", payload)
            if 'response' in insert_control_script_result:
                if insert_control_script_result['response'] == "inserted":
                    result = {"name": name, "steps": json.loads(_steps)}
                    if acl is not None:
                        # Append ACL into response if acl exists in payload
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
        return web.json_response(result)


@has_permission("admin")
async def update(request: web.Request) -> web.Response:
    """ Update a script
    Only the steps & ACL parameters can be updated

    :Example:
        curl -H "authorization: $AUTH_TOKEN" -sX PUT http://localhost:8081/fledge/control/script/testScript -d '{"steps": []}'
        curl -H "authorization: $AUTH_TOKEN" -sX PUT http://localhost:8081/fledge/control/script/test -d '{"steps": [{"delay": {"order": 0, "duration": 12}}], "acl": "testACL"}'
    """
    try:
        name = request.match_info.get('script_name', None)
        data = await request.json()
        steps = data.get('steps', None)
        acl = data.get('acl', None)
        if steps is None and acl is None:
            raise ValueError("Nothing to update for the given payload.")
        if steps is not None and not isinstance(steps, list):
            raise ValueError('steps must be a list.')
        if acl is not None:
            if not isinstance(acl, str):
                raise ValueError('ACL must be a string.')
            acl = acl.strip()
        set_values = {}
        if steps is not None:
            set_values["steps"] = _validate_steps_and_convert_to_str(steps)
        storage = connect.get_storage_async()
        # Check existence of script record
        payload = PayloadBuilder().SELECT("name").WHERE(['name', '=', name]).payload()
        result = await storage.query_tbl_with_payload('control_script', payload)
        message = ""
        if 'rows' in result:
            if result['rows']:
                if acl is not None:
                    if len(acl):
                        # Check the existence of valid ACL record
                        acl_payload = PayloadBuilder().SELECT("name").WHERE(['name', '=', acl]).payload()
                        acl_result = await storage.query_tbl_with_payload('control_acl', acl_payload)
                        if 'rows' in acl_result:
                            if not acl_result['rows']:
                                raise NameNotFoundError('ACL with name {} is not found.'.format(acl))
                        else:
                            raise StorageServerError(acl_result)
                    set_values["acl"] = acl
                # Update script record
                update_query = PayloadBuilder()
                update_query.SET(**set_values).WHERE(['name', '=', name])
                update_result = await storage.update_tbl("control_script", update_query.payload())
                if 'response' in update_result:
                    if update_result['response'] == "updated":
                        message = "Control script {} updated successfully.".format(name)
                else:
                    raise StorageServerError(update_result)
            else:
                raise NameNotFoundError('No such {} script found.'.format(name))
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
async def delete(request: web.Request) -> web.Response:
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
                try:
                    # Delete automation script category and schedule
                    cf_mgr = ConfigurationManager(connect.get_storage_async())
                    cat_name = "{}-automation-script".format(name)
                    await cf_mgr.delete_category_and_children_recursively(cat_name)
                    schedules_list = await server.Server.scheduler.get_schedules()
                    for sch in schedules_list:
                        if sch.name == name and sch.process_name == "automation_script":
                            schedule_id = str(sch.schedule_id)
                            await server.Server.scheduler.disable_schedule(uuid.UUID(schedule_id))
                            await server.Server.scheduler.delete_schedule(uuid.UUID(schedule_id))
                            break
                except:
                    pass
                payload = PayloadBuilder().WHERE(['name', '=', name]).payload()
                delete_result = await storage.delete_from_tbl("control_script", payload)
                if 'response' in delete_result:
                    if delete_result['response'] == "deleted":
                        message = "{} script deleted successfully.".format(name)
                else:
                    raise StorageServerError(delete_result)
            else:
                raise NameNotFoundError('No such {} script found.'.format(name))
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


def _validate_write_steps(steps: list) -> tuple:
    write_step_values = []
    macro_step_values = []
    for k in steps:
        for k1, v1 in k.items():
            if k1 == 'write':
                for k2, v2 in v1['values'].items():
                    if v2.startswith("$") and v2.endswith("$"):
                        macro_step_values.append(v2[1:-1])
                write_step_values.append(v1)
    return write_step_values, macro_step_values


def _validate_steps_and_convert_to_str(payload: list) -> str:
    """
    NOTE: We cannot really check the internal KV pairs in steps as they related to configuration of plugin.
          And only do the type check of step and for each item it should have order KV pair along its unique value.

          Also steps supported types are hardcoded at the moment, we may add new API to get the types
          so that any client can use from there itself.
          For example:
          GUI client has also prepared this list by their own to show down in the dropdown.
          Therefore if any new/update type is introduced with the current scenario both sides needs to be changed
    """
    steps_supported_types = ["configure", "delay", "operation", "script", "write"]
    unique_order_items = []
    if payload:
        for p in payload:
            if isinstance(p, dict):
                for k, v in p.items():
                    if k not in steps_supported_types:
                        raise TypeError('{} is an invalid step. Supported step types are {} '
                                        'with case-sensitive.'.format(k, steps_supported_types))
                    else:
                        if isinstance(v, dict):
                            if 'order' not in v:
                                raise ValueError('order key is missing for {} step.'.format(k))
                            else:
                                if isinstance(v['order'], int):
                                    if v['order'] not in unique_order_items:
                                        unique_order_items.append(v['order'])
                                    else:
                                        raise ValueError('order with value {} is also found in {}. '
                                                         'It should be unique for each step item.'.format(
                                            v['order'], k))
                                else:
                                    raise TypeError('order should be an integer for {} step.'.format(k))
                        else:
                            raise ValueError("For {} step nested elements should be in dictionary.".format(k))
            else:
                raise ValueError('Steps should be in list of dictionaries.')
    # Convert steps payload list into string
    return json.dumps(payload)
