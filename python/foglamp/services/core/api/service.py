# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import datetime
from aiohttp import web
from foglamp.services.core.service_registry.service_registry import ServiceRegistry
from foglamp.common.storage_client.payload_builder import PayloadBuilder
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.services.core import server
from foglamp.services.core import connect
from foglamp.services.core.scheduler.entities import StartUpSchedule

__author__ = "Mark Riddoch, Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -------------------------------------------------------------------------------
    | POST            | /foglamp/service                                          |
    | GET             | /foglamp/service                                          |
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
                    'name' : service_record._name,
                    'type' : service_record._type,
                    'address' : service_record._address,
                    'management_port' : service_record._management_port,
                    'service_port' : service_record._port,
                    'protocol' : service_record._protocol,
                    'status': 'running'
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

        name = data.get('name', None)
        plugin = data.get('plugin', None)
        service_type = data.get('type', None)
        if name is None:
            raise web.HTTPBadRequest(reason='Missing name property in payload.')
        if plugin is None:
            raise web.HTTPBadRequest(reason='Missing plugin property in payload.')
        if service_type is None:
            raise web.HTTPBadRequest(reason='Missing type property in payload.')
        if not service_type in ['south', 'north']:
            raise web.HTTPBadRequest(reason='Only north and south types are supported.')

        storage = connect.get_storage()

        # Check that the process is not already registered
        payload = PayloadBuilder().SELECT("name").WHERE(['name', '=', name]).payload()
        result = storage.query_tbl_with_payload('scheduled_processes', payload)
        count = result['count']
        if count != 0:
            raise web.HTTPBadRequest(reason='A service with that name already exists')

        # First create the scheduled process entry for our new service
        if service_type == 'south':
            script = '["services/south"]'
        if service_type == 'north':
            script = '["services/north"]'
        payload = PayloadBuilder().INSERT(name=name, script=script).payload()
        try:
            res = storage.insert_into_tbl("scheduled_processes", payload)
        except Exception as ins_ex:
            raise web.HTTPInternalServerError(reason='Failed to created scheduled process. {}'.format(str(ins_ex)))

        # Now create a configuration category with the minimum to load the plugin
        # TODO It would be better to load the default configuration from the plugin
        # and use this, however we should extract the plugin loading code so that is shared
        new_category = {"plugin":
                            {"type": "string",
                             "default": plugin,
                             "description": "Python module name of the plugin to load"}
                       }
        category_desc = '{} service configuration'.format(name)
        config_mgr = ConfigurationManager(storage)
        await config_mgr.create_category(category_name=name, category_description=category_desc,
                                     category_value=new_category, keep_original_items=False)

        # Check that the process is not already registered
        payload = PayloadBuilder().SELECT("schedule_name").WHERE(['schedule_name', '=', name]).payload()
        result = storage.query_tbl_with_payload('schedules', payload)
        count = result['count']
        if count != 0:
            raise web.HTTPBadRequest(reason='A schedule with that name already exists')

        # Finally add a schedule to run the new service at startup
        schedule = StartUpSchedule()
        schedule.name = name
        schedule.process_name = name
        schedule.repeat = datetime.timedelta(0)
        schedule.exclusive = True
        schedule.enabled = False
        # Save schedule
        await server.Server.scheduler.save_schedule(schedule)
        schedule = await server.Server.scheduler.get_schedule_by_name(name)

        return web.json_response({'name': name, 'id': str(schedule.schedule_id)})

    except ValueError as ex:
        raise web.HTTPNotFound(reason=str(ex))

