# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import datetime
from aiohttp import web
from foglamp.common.service_record import ServiceRecord
from foglamp.services.core.service_registry.service_registry import ServiceRegistry
from foglamp.common.storage_client.payload_builder import PayloadBuilder
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.services.core import server
from foglamp.services.core import connect
from foglamp.services.core.scheduler.entities import StartUpSchedule

__author__ = "Mark Riddoch, Ashwin Gopalakrishnan, Amarendra K Sinha"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -------------------------------------------------------------------------------
    | GET POST            | /foglamp/service                                      |
    -------------------------------------------------------------------------------
"""


#################################
#  Service
#################################


def get_service_records():
    sr_list = list()
    for service_record in ServiceRegistry.all():
        sr_list.append(
            {
                'name': service_record._name,
                'type': service_record._type,
                'address': service_record._address,
                'management_port': service_record._management_port,
                'service_port': service_record._port,
                'protocol': service_record._protocol,
                'status': ServiceRecord.Status(int(service_record._status)).name.lower()
            })
    recs = {'services' : sr_list}
    return recs


async def get_health(request):
    """
    Args:
        request:

    Returns:
            health of all registered services

    :Example:
            curl -X GET http://localhost:8081/foglamp/service
    """
    response = get_service_records()
    return web.json_response(response)


async def add_service(request):
    """
    Create a new service to run a specific plugin

    :Example:
             curl -X POST /foglamp/service -d '{"name": "furnace4", "type": "south", "plugin": "dht11"}'
    """

    try:
        data = await request.json()
        if not isinstance(data, dict):
            raise ValueError('Data payload must be a dictionary')

        name = data.get('name', None)
        plugin = data.get('plugin', None)
        service_type = data.get('type', None)
        enabled = data.get('enabled', None)

        if name is None:
            raise web.HTTPBadRequest(reason='Missing name property in payload.')
        if plugin is None:
            raise web.HTTPBadRequest(reason='Missing plugin property in payload.')
        if service_type is None:
            raise web.HTTPBadRequest(reason='Missing type property in payload.')
        if not service_type in ['south', 'north']:
            raise web.HTTPBadRequest(reason='Only north and south types are supported.')
        if enabled is not None:
            if enabled not in ['t', 'f', 'true', 'false', 0, 1]:
                raise web.HTTPBadRequest(reason='Only "t", "f", "true", "false" are allowed for value of enabled.')
        is_enabled = True if ((type(enabled) is str and enabled.lower() in ['t', 'true']) or (
            (type(enabled) is bool and enabled is True))) else False

        storage = connect.get_storage_async()

        # Check that the process name is not already registered
        payload = PayloadBuilder().SELECT("name").WHERE(['name', '=', name]).payload()
        result = await storage.query_tbl_with_payload('scheduled_processes', payload)
        count = result['count']
        if count != 0:
            raise web.HTTPBadRequest(reason='A service with that name already exists')

        # Check that the schedule name is not already registered
        payload = PayloadBuilder().SELECT("schedule_name").WHERE(['schedule_name', '=', name]).payload()
        result = await storage.query_tbl_with_payload('schedules', payload)
        count = result['count']
        if count != 0:
            raise web.HTTPBadRequest(reason='A schedule with that name already exists')

        # First create the scheduled process entry for our new service
        if service_type == 'south':
            script = '["services/south"]'
            plugin_module_path = "foglamp.plugins.south"
        if service_type == 'north':
            script = '["services/north"]'
            plugin_module_path = "foglamp.plugins.north"
        payload = PayloadBuilder().INSERT(name=name, script=script).payload()
        try:
            res = await storage.insert_into_tbl("scheduled_processes", payload)
        except Exception as ins_ex:
            raise web.HTTPInternalServerError(reason='Failed to created scheduled process. {}'.format(str(ins_ex)))

        # Now load the plugin to fetch its configuration
        try:
            # "plugin_module_path" is fixed by design. It is MANDATORY to keep the plugin in the exactly similar named
            # folder, within the plugin_module_path.
            import_file_name = "{path}.{dir}.{file}".format(path=plugin_module_path, dir=plugin, file=plugin)
            _plugin = __import__(import_file_name, fromlist=[''])

            # Fetch configuration from the configuration defined in the plugin
            plugin_info = _plugin.plugin_info()
            plugin_config = plugin_info['config']

            # Create a configuration category from the configuration defined in the plugin
            category_desc = plugin_config['plugin']['description']
            config_mgr = ConfigurationManager(storage)
            await config_mgr.create_category(category_name=name,
                                             category_description=category_desc,
                                             category_value=plugin_config,
                                             keep_original_items=True)
        except ImportError as ex:
            raise web.HTTPInternalServerError(reason='Plugin "{}" import problem from path "{}". {}'.format(plugin, plugin_module_path, str(ex)))
        except Exception as ex:
            raise web.HTTPInternalServerError(reason='Failed to create plugin configuration. {}'.format(str(ex)))

        # Next add a schedule to run the new service at startup
        schedule = StartUpSchedule()  # TODO: For North plugin also?
        schedule.name = name
        schedule.process_name = name
        schedule.repeat = datetime.timedelta(0)
        schedule.exclusive = True
        schedule.enabled = False  # if "enabled" is supplied, it gets activated in save_schedule() via is_enabled flag

        # Save schedule
        await server.Server.scheduler.save_schedule(schedule, is_enabled)
        schedule = await server.Server.scheduler.get_schedule_by_name(name)

        return web.json_response({'name': name, 'id': str(schedule.schedule_id)})

    except ValueError as ex:
        raise web.HTTPNotFound(reason=str(ex))

