# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import copy
import json
from aiohttp import web

from fledge.common.audit_logger import AuditLogger
from fledge.common.configuration_manager import ConfigurationManager
from fledge.common.logger import FLCoreLogger
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.common.storage_client.exceptions import StorageServerError
from fledge.services.core import connect, server

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2023 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_logger = FLCoreLogger().get_logger(__name__)

_help = """
    -----------------------------------------------------------------------------------
    | GET POST                   |        /fledge/control/pipeline                    |
    | GET PUT DELETE             |        /fledge/control/pipeline/{id}               |
    | GET                        |        /fledge/control/lookup                      |
    -----------------------------------------------------------------------------------
"""


def setup(app):
    app.router.add_route('GET', '/fledge/control/lookup', get_lookup)
    app.router.add_route('POST', '/fledge/control/pipeline', create)
    app.router.add_route('GET', '/fledge/control/pipeline', get_all)
    app.router.add_route('GET', '/fledge/control/pipeline/{id}', get_by_id)
    app.router.add_route('PUT', '/fledge/control/pipeline/{id}', update)
    app.router.add_route('DELETE', '/fledge/control/pipeline/{id}', delete)


async def get_lookup(request: web.Request) -> web.Response:
    """List of supported control source and destinations

    :Example:
        curl -sX GET http://localhost:8081/fledge/control/lookup
        curl -sX GET http://localhost:8081/fledge/control/lookup?type=source
        curl -sX GET http://localhost:8081/fledge/control/lookup?type=destination
    """
    try:
        _type = request.query.get('type')
        if _type is None or not _type:
            lookup = await _get_all_lookups()
            response = {'controlLookup': lookup}
        else:
            table_name = None
            if _type == "source":
                table_name = "control_source"
            elif _type == "destination":
                table_name = "control_destination"
            if table_name:
                lookup = await _get_all_lookups(table_name)
                response = lookup
            else:
                lookup = await _get_all_lookups()
                response = {'controlLookup': lookup}
    except Exception as ex:
        msg = str(ex)
        _logger.error(ex, "Failed to get all control lookups.")
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response(response)


async def create(request: web.Request) -> web.Response:
    """Create a control pipeline. It's name must be unique and there must be no other pipelines with the same
    source or destination

    :Example:
        curl -sX POST http://localhost:8081/fledge/control/pipeline -d '{"name": "wildcard", "enabled": true, "execution": "shared", "source": {"type": 1}, "destination": {"type": 1}}'
        curl -sX POST http://localhost:8081/fledge/control/pipeline -d '{"name": "pump", "enabled": true, "execution": "shared", "source": {"type": 2, "name": "pump"}}'
        curl -sX POST http://localhost:8081/fledge/control/pipeline -d '{"name": "broadcast", "enabled": true, "execution": "exclusive", "destination": {"type": 5}}'
        curl -sX POST http://localhost:8081/fledge/control/pipeline -d '{"name": "opcua_pump", "enabled": true, "execution": "shared", "source": {"type": 2, "name": "opcua"}, "destination": {"type": 3, "name": "pump1"}}'
        curl -sX POST http://localhost:8081/fledge/control/pipeline -d '{"name": "opcua_pump1", "enabled": true, "execution": "exclusive", "source": {"type": 2, "name": "southOpcua"}, "destination": {"type": 2, "name": "northOpcua"}, "filters": ["Filter1"]}'
        curl -sX POST http://localhost:8081/fledge/control/pipeline -d '{"name": "Test", "enabled": false, "filters": ["Filter1", "Filter2"]}'
    """
    try:
        data = await request.json()
        # Create entry in control_pipelines table
        column_names = await _check_parameters(data, request)
        source_type = column_names.get("stype")
        if source_type is None:
            column_names['stype'] = 0
            column_names['sname'] = ''
        des_type = column_names.get("dtype")
        if des_type is None:
            column_names['dtype'] = 0
            column_names['dname'] = ''
        payload = PayloadBuilder().INSERT(**column_names).payload()
        storage = connect.get_storage_async()
        insert_result = await storage.insert_into_tbl("control_pipelines", payload)
        pipeline_name = column_names['name']
        pipeline_filter = data.get('filters', None)
        if insert_result['response'] == "inserted" and insert_result['rows_affected'] == 1:
            source = {'type': column_names["stype"], 'name': column_names["sname"]}
            destination = {'type': column_names["dtype"], 'name': column_names["dname"]}
            final_result = await _pipeline_in_use(pipeline_name, source, destination, info=True)
            final_result['source'] = {"type": await _get_lookup_value('source', final_result["stype"]),
                                      "name": final_result['sname']}
            final_result['destination'] = {"type": await _get_lookup_value('destination', final_result["dtype"]),
                                           "name": final_result['dname']}
            final_result.pop('stype', None)
            final_result.pop('sname', None)
            final_result.pop('dtype', None)
            final_result.pop('dname', None)
            final_result['enabled'] = False if final_result['enabled'] == 'f' else True
            final_result['filters'] = []
            if pipeline_filter:
                go_ahead = await _check_filters(storage, pipeline_filter)
                if go_ahead:
                    filters = await _update_filters(storage, final_result['id'], pipeline_name, pipeline_filter)
                    final_result['filters'] = filters
        else:
            raise StorageServerError
    except StorageServerError as serr:
        msg = serr.error
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": "Storage error: {}".format(msg)}))
    except KeyError as err:
        msg = str(err)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except ValueError as err:
        msg = str(err)
        raise web.HTTPBadRequest(body=json.dumps({"message": msg}), reason=msg)
    except Exception as ex:
        msg = str(ex)
        _logger.error(ex, "Failed to create pipeline: {}.".format(data.get('name')))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        # CTPAD audit trail entry
        audit = AuditLogger(storage)
        await audit.information('CTPAD', final_result)
        return web.json_response(final_result)


async def get_all(request: web.Request) -> web.Response:
    """List of all control pipelines within the system

    :Example:
        curl -sX GET http://localhost:8081/fledge/control/pipeline
    """
    try:
        storage = connect.get_storage_async()
        result = await storage.query_tbl("control_pipelines")
        control_pipelines = []
        source_lookup = await _get_all_lookups("control_source")
        des_lookup = await _get_all_lookups("control_destination")
        for r in result["rows"]:
            source_name = [s['name'] for s in source_lookup if r['stype'] == s['cpsid']]
            des_name = [s['name'] for s in des_lookup if r['dtype'] == s['cpdid']]
            temp = {
                'id': r['cpid'],
                'name': r['name'],
                'source': {
                    'type': ''.join(source_name), 'name': r['sname']} if r['stype'] else {'type': '', 'name': ''},
                'destination': {
                    'type': ''.join(des_name), 'name': r['dname']} if r['dtype'] else {'type': '', 'name': ''},
                'enabled': False if r['enabled'] == 'f' else True,
                'execution': r['execution']
            }
            result = await _get_table_column_by_value("control_filters", "cpid", r['cpid'])
            temp.update({'filters': [r['fname'] for r in result["rows"]]})
            control_pipelines.append(temp)
    except Exception as ex:
        msg = str(ex)
        _logger.error(ex, "Failed to get all pipelines.")
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({'pipelines': control_pipelines})


async def get_by_id(request: web.Request) -> web.Response:
    """Fetch the pipeline within the system

    :Example:
        curl -sX GET http://localhost:8081/fledge/control/pipeline/2
    """
    cpid = request.match_info.get('id', None)
    try:
        pipeline = await _get_pipeline(cpid)
    except ValueError as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except KeyError as err:
        msg = str(err)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        _logger.error(ex, "Failed to fetch details of pipeline having ID: <{}>.".format(cpid))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response(pipeline)


async def update(request: web.Request) -> web.Response:
    """Update an existing pipeline within the system

    :Example:
        curl -sX PUT http://localhost:8081/fledge/control/pipeline/1 -d '{"filters": ["F3", "F2"]}'
        curl -sX PUT http://localhost:8081/fledge/control/pipeline/13 -d '{"name": "Changed"}'
        curl -sX PUT http://localhost:8081/fledge/control/pipeline/9 -d '{"enabled": false, "execution": "exclusive", "filters": [], "source": {"type": 1, "name": "Universal"}, "destination": {"type": 4, "name": "TestScript"}}'
    """
    cpid = request.match_info.get('id', None)
    try:
        pipeline = await _get_pipeline(cpid)
        data = await request.json()
        data['old_pipeline_name'] = pipeline['name']
        columns = await _check_parameters(data, request)
        storage = connect.get_storage_async()
        if columns:
            payload = PayloadBuilder().SET(**columns).WHERE(['cpid', '=', cpid]).payload()
            await storage.update_tbl("control_pipelines", payload)
        filters = data.get('filters', None)
        if filters is not None:
            # Case: When filters payload is empty then remove all filters
            if not filters:
                await _remove_filters(storage, pipeline['filters'], cpid, pipeline['name'])
            else:
                go_ahead = await _check_filters(storage, filters) if filters else True
                if go_ahead:
                    if filters:
                        result_filters = await _get_table_column_by_value("control_filters", "cpid", cpid)
                        db_filters = None
                        if result_filters['rows']:
                            db_filters = [r['fname'].replace("ctrl_{}_".format(pipeline['name']), ''
                                                             ) for r in result_filters['rows']]
                        await _update_filters(storage, cpid, pipeline['name'], filters, db_filters)
                else:
                    raise ValueError('Filters do not exist as per the given list {}'.format(filters))
    except ValueError as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except KeyError as err:
        msg = str(err)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        _logger.error(ex, "Failed to update pipeline having ID: <{}>.".format(cpid))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        # CTPCH audit trail entry
        audit = AuditLogger(storage)
        updated_pipeline = await _get_pipeline(cpid)
        await audit.information('CTPCH', {"pipeline": updated_pipeline, "old_pipeline": pipeline})
        return web.json_response(
            {"message": "Control Pipeline with ID:<{}> has been updated successfully.".format(cpid)})


async def delete(request: web.Request) -> web.Response:
    """Delete an existing pipeline within the system.
    Also remove the filters along with configuration that are part of pipeline

    :Example:
        curl -sX DELETE http://localhost:8081/fledge/control/pipeline/1
    """
    cpid = request.match_info.get('id', None)
    try:
        storage = connect.get_storage_async()
        pipeline = await _get_pipeline(cpid)
        # Remove filters if exists and also delete the entry from control_filter table
        await _remove_filters(storage, pipeline['filters'], cpid, pipeline['name'])
        # Delete entry from control_pipelines
        payload = PayloadBuilder().WHERE(['cpid', '=', pipeline['id']]).payload()
        await storage.delete_from_tbl("control_pipelines", payload)
    except KeyError as err:
        msg = str(err)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except ValueError as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        _logger.error(ex, "Failed to delete pipeline having ID: <{}>.".format(cpid))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        message = {"message": "Control Pipeline with ID:<{}> has been deleted successfully.".format(cpid)}
        audit_details = message
        audit_details["name"] = pipeline['name']
        # CTPDL audit trail entry
        audit = AuditLogger(storage)
        await audit.information('CTPDL', audit_details)
        return web.json_response(message)


async def _get_all_lookups(tbl_name=None):
    storage = connect.get_storage_async()
    if tbl_name:
        res = await storage.query_tbl(tbl_name)
        lookup = res["rows"]
        return lookup
    result = await storage.query_tbl("control_source")
    source_lookup = result["rows"]
    result = await storage.query_tbl("control_destination")
    des_lookup = result["rows"]
    return {"source": source_lookup, "destination": des_lookup}


async def _get_table_column_by_value(table, column_name, column_value, limit=None):
    storage = connect.get_storage_async()
    if table == "control_filters":
        payload = PayloadBuilder().WHERE([column_name, '=', column_value]).ORDER_BY(["forder", "asc"]).payload()
    else:
        payload = PayloadBuilder().WHERE([column_name, '=', column_value]).payload()
    if limit is not None:
        payload = PayloadBuilder().WHERE([column_name, '=', column_value]).LIMIT(limit).payload()
    result = await storage.query_tbl_with_payload(table, payload)
    return result


async def _get_pipeline(cpid, filters=True):
    result = await _get_table_column_by_value("control_pipelines", "cpid", cpid)
    rows = result["rows"]
    if not rows:
        raise KeyError("Pipeline having ID: {} not found.".format(cpid))
    r = rows[0]
    pipeline = {
        'id': r['cpid'],
        'name': r['name'],
        'source': {'type': await _get_lookup_value("source", r['stype']), 'name': r['sname']
                   } if r['stype'] else {'type': '', 'name': ''},
        'destination': {'type': await _get_lookup_value("destination", r['dtype']), 'name': r['dname']
                        } if r['dtype'] else {'type': '', 'name': ''},
        'enabled': False if r['enabled'] == 'f' else True,
        'execution': r['execution']
    }
    if filters:
        # update filters in pipeline
        result = await _get_table_column_by_value("control_filters", "cpid", pipeline['id'])
        pipeline['filters'] = [r['fname'] for r in result["rows"]]
    return pipeline


async def _pipeline_in_use(name, source, destination, info=False):
    result = await _get_table_column_by_value("control_pipelines", "name", name)
    rows = result["rows"]
    row = None
    new_data = {'source': source if source else {'type': 0, 'name': ''},
                'destination': destination if destination else {'type': 0, 'name': ''}
                }
    is_matched = False
    for r in rows:
        db_data = {'source': {'type': r['stype'], 'name': r['sname']},
                   'destination': {'type': r['dtype'], 'name': r['dname']}}
        if json.dumps(db_data, sort_keys=True) == json.dumps(new_data, sort_keys=True):
            is_matched = True
            r["id"] = r['cpid']
            r.pop('cpid', None)
            row = r
            break
    return row if info else is_matched


async def _get_lookup_value(_type, value):
    if _type == "source":
        tbl_name = "control_source"
        key_name = 'cpsid'
    else:
        tbl_name = "control_destination"
        key_name = 'cpdid'
    lookup = await _get_all_lookups(tbl_name)
    name = [lu['name'] for lu in lookup if value == lu[key_name]]
    return ''.join(name)


async def _check_parameters(payload, request):
    column_names = {}
    # name
    name = payload.get('name', None)
    if name is not None:
        if not isinstance(name, str):
            raise ValueError('Pipeline name should be in string.')
        name = name.strip()
        if len(name) == 0:
            raise ValueError('Pipeline name cannot be empty.')
        cpid = request.match_info.get('id', None)
        old_name = payload.get('old_pipeline_name', None)
        await _check_unique_pipeline(name, old_name, cpid)
        column_names['name'] = name
    # enabled
    enabled = payload.get('enabled', None)
    if enabled is not None:
        if not isinstance(enabled, bool):
            raise ValueError('Enabled should be a bool.')
        column_names['enabled'] = 't' if enabled else 'f'
    # execution
    execution = payload.get('execution', None)
    if execution is not None:
        if not isinstance(execution, str):
            raise ValueError('Execution should be in string.')
        execution = execution.strip()
        if len(execution) == 0:
            raise ValueError('Execution value cannot be empty.')
        if execution.lower() not in ["shared", "exclusive"]:
            raise ValueError('Execution model value either shared or exclusive.')
        column_names['execution'] = execution
    # source
    source = payload.get('source', None)
    if source is not None:
        if not isinstance(source, dict):
            raise ValueError('Source should be passed with type and name.')
        if len(source):
            source_type = source.get("type")
            source_name = source.get("name")
            if source_type is not None:
                if not isinstance(source_type, int):
                    raise ValueError("Source type should be an integer value.")
                stype = await _get_lookup_value("source", source_type)
                if not stype:
                    raise ValueError("Invalid source type found.")
            else:
                raise ValueError('Source type is missing.')
            # Note: when source type is Any or API; no name is applied
            if source_type not in (1, 3):
                if source_name is not None:
                    if not isinstance(source_name, str):
                        raise ValueError("Source name should be a string value.")
                    source_name = source_name.strip()
                    if len(source_name) == 0:
                        raise ValueError('Source name cannot be empty.')
                    await _validate_lookup_name("source", source_type, source_name)
                    column_names["stype"] = source_type
                    column_names["sname"] = source_name
                else:
                    raise ValueError('Source name is missing.')
            else:
                source_name = ''
                if source_type == 3:
                    source_name = request.user["uname"] if hasattr(request, "user") and request.user else "anonymous"
                source = {'type': source_type, 'name': source_name}
                column_names["stype"] = source_type
                column_names["sname"] = source_name
        else:
            column_names["stype"] = 0
            column_names["sname"] = ""
    # destination
    destination = payload.get('destination', None)
    if destination is not None:
        if not isinstance(destination, dict):
            raise ValueError('Destination should be passed with type and name.')
        if len(destination):
            des_type = destination.get("type")
            des_name = destination.get("name")
            if des_type is not None:
                if not isinstance(des_type, int):
                    raise ValueError("Destination type should be an integer value.")
                dtype = await _get_lookup_value("destination", des_type)
                if not dtype:
                    raise ValueError("Invalid destination type found.")
            else:
                raise ValueError('Destination type is missing.')
            # Note: when destination type is Any or Broadcast; no name is applied
            if des_type not in (1, 5):
                if des_name is not None:
                    if not isinstance(des_name, str):
                        raise ValueError("Destination name should be a string value.")
                    des_name = des_name.strip()
                    if len(des_name) == 0:
                        raise ValueError('Destination name cannot be empty.')
                    await _validate_lookup_name("destination", des_type, des_name)
                    column_names["dtype"] = des_type
                    column_names["dname"] = des_name
                else:
                    raise ValueError('Destination name is missing.')
            else:
                des_name = ''
                destination = {'type': des_type, 'name': des_name}
                column_names["dtype"] = des_type
                column_names["dname"] = des_name
        else:
            column_names["dtype"] = 0
            column_names["dname"] = ""
    if source is not None and destination is not None:
        error_msg = "Pipeline is not allowed with same type of source and destination."
        # Service
        if source_type == 2 and des_type == 2:
            schedules = await server.Server.scheduler.get_schedules()
            south_schedules = [sch.name for sch in schedules if sch.schedule_type == 1 and sch.process_name == "south_c"]
            north_schedules = [sch.name for sch in schedules if
                               sch.schedule_type == 1 and sch.process_name == "north_C"]
            if (source_name in south_schedules and des_name in south_schedules) or (
                    source_name in north_schedules and des_name in north_schedules):
                raise ValueError(error_msg)
        # Script
        if source_type == 6 and des_type == 4:
            raise ValueError(error_msg)
    # filters
    filters = payload.get('filters', None)
    if filters is not None:
        if not isinstance(filters, list):
            raise ValueError('Pipeline filters should be passed in list.')
    return column_names


async def _validate_lookup_name(lookup_name, _type, value):
    storage = connect.get_storage_async()
    config_mgr = ConfigurationManager(storage)

    async def get_schedules():
        schedules = await server.Server.scheduler.get_schedules()
        if _type == 5:
            # Verify against all type of schedules
            if not any(sch.name == value for sch in schedules):
                raise ValueError("'{}' not a valid schedule name.".format(value))
        else:
            # Verify against STARTUP type schedule and having South, North based service
            if not any(sch.name == value for sch in schedules
                       if sch.schedule_type == 1 and sch.process_name in ('south_c', 'north_C')):
                raise ValueError("'{}' not a valid service.".format(value))

    async def get_control_scripts():
        script_payload = PayloadBuilder().SELECT("name").payload()
        scripts = await storage.query_tbl_with_payload('control_script', script_payload)
        if not any(s['name'] == value for s in scripts['rows']):
            raise ValueError("'{}' not a valid script name.".format(value))

    async def get_assets():
        asset_payload = PayloadBuilder().DISTINCT(["asset"]).payload()
        assets = await storage.query_tbl_with_payload('asset_tracker', asset_payload)
        if not any(ac['asset'] == value for ac in assets['rows']):
            raise ValueError("'{}' not a valid asset name.".format(value))

    async def get_notifications():
        all_notifications = await config_mgr._read_all_child_category_names("Notifications")
        if not any(notify['child'] == value for notify in all_notifications):
            raise ValueError("'{}' not a valid notification instance name.".format(value))

    if (lookup_name == "source" and _type == 2) or (lookup_name == 'destination' and _type == 2):
        # Verify schedule name in startup type and south, north based schedules
        await get_schedules()
    elif (lookup_name == "source" and _type == 6) or (lookup_name == 'destination' and _type == 4):
        # Verify control script name
        await get_control_scripts()
    elif lookup_name == "source" and _type == 4:
        # Verify notification instance name
        await get_notifications()
    elif lookup_name == "source" and _type == 5:
        # Verify schedule name in all type of schedules
        await get_schedules()
    elif lookup_name == "destination" and _type == 3:
        # Verify asset name
        await get_assets()
    else:
        """No validation required for source id 1(Any) & destination id 4(Broadcast)"""
        pass


async def _remove_filters(storage, filters, cp_id, cp_name=None):
    cf_mgr = ConfigurationManager(storage)
    if filters:
        for f in filters:
            # Delete entry from control_filter table
            payload = PayloadBuilder().WHERE(['cpid', '=', cp_id]).AND_WHERE(['fname', '=', f]).payload()
            await storage.delete_from_tbl("control_filters", payload)

            # Delete filter from filters table
            filter_name = f.replace("ctrl_{}_".format(cp_name), '')
            payload = PayloadBuilder().WHERE(['name', '=', filter_name]).payload()
            await storage.delete_from_tbl("filters", payload)

            # Delete the filters category
            await cf_mgr.delete_category_and_children_recursively(f)
            await cf_mgr.delete_category_and_children_recursively(filter_name)


async def _check_filters(storage, cp_filters):
    is_exist = False
    filters_result = await storage.query_tbl("filters")
    if filters_result['rows']:
        filters_instances_list = [f['name'] for f in filters_result['rows']]
        check_if = all(f in filters_instances_list for f in cp_filters)
        if check_if:
            is_exist = True
        else:
            _logger.warning("Filters do not exist as per the given {} payload..".format(cp_filters))
    else:
        _logger.warning("No filter instances exists in the system.")
    return is_exist


async def _update_filters(storage, cp_id, cp_name, cp_filters, db_filters=None):
    if db_filters is None:
        db_filters = []
    cf_mgr = ConfigurationManager(storage)
    new_filters = []
    children = []

    insert_filters = set(cp_filters) - set(db_filters)
    update_filters = set(cp_filters) & set(db_filters)
    delete_filters = set(db_filters) - set(cp_filters)

    if insert_filters:
        for fid, fname in enumerate(insert_filters, start=1):
            # get plugin config of filter
            category_value = await cf_mgr.get_category_all_items(category_name=fname)
            cat_value = copy.deepcopy(category_value)
            if cat_value is None:
                raise ValueError(
                    "{} category does not exist during {} control pipeline filter.".format(
                        fname, cp_name))
            # Copy value in default and remove value KV pair for creating new category
            for k, v in cat_value.items():
                v['default'] = v['value']
                v.pop('value', None)
            # Create category
            cat_name = "ctrl_{}_{}".format(cp_name, fname)
            await cf_mgr.create_category(category_name=cat_name,
                                         category_description="Filter of {} control pipeline.".format(
                                             cp_name),
                                         category_value=cat_value,
                                         keep_original_items=True)
            new_category = await cf_mgr.get_category_all_items(cat_name)
            if new_category is None:
                raise KeyError("No such {} category found.".format(new_category))
            # Create entry in control_filters table
            column_names = {"cpid": cp_id, "forder": fid, "fname": cat_name}
            payload = PayloadBuilder().INSERT(**column_names).payload()
            await storage.insert_into_tbl("control_filters", payload)
            new_filters.append(cat_name)
            children.append(cat_name)
            children.extend([fname])
        try:
            # Create parent-child relation with Dispatcher service
            await cf_mgr.create_child_category("dispatcher", children)
        except:
            pass
    if update_filters:
        # only order
        for fid, fname in enumerate(cp_filters, start=1):
            payload = PayloadBuilder().SET(forder=fid).WHERE(["fname", "=", "ctrl_{}_{}".format(cp_name, fname)]).AND_WHERE(["cpid", "=", cp_id]).payload()
            await storage.update_tbl("control_filters", payload)
    if delete_filters:
        del_filters = ["ctrl_{}_{}".format(cp_name, f) for f in list(delete_filters)]
        await _remove_filters(storage, del_filters, cp_id, cp_name)
    return new_filters


async def _check_unique_pipeline(name, old_name=None, cpid=None):
    """Disallow pipeline name cases:
       a) If given pipeline name already exists in DB.
       b) If given pipeline has already attached filters.
    """
    if cpid is not None:
        if name != old_name:
            pipeline_filter_result = await _get_table_column_by_value("control_filters", "cpid", cpid, limit=1)
            if pipeline_filter_result['rows']:
                raise ValueError('Filters are attached. Pipeline name cannot be changed.')
            pipeline_result = await _get_table_column_by_value("control_pipelines", "name", name, limit=1)
            if pipeline_result['rows']:
                raise ValueError('{} pipeline already exists, name cannot be changed.'.format(name))
    else:
        pipeline_result = await _get_table_column_by_value("control_pipelines", "name", name, limit=1)
        if pipeline_result['rows']:
            raise ValueError('{} pipeline already exists with the same name.'.format(name))
