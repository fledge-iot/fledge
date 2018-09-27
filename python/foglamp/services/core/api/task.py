# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import datetime

from aiohttp import web

from foglamp.common import utils
from foglamp.common import logger
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.common.storage_client.payload_builder import PayloadBuilder
from foglamp.common.storage_client.exceptions import StorageServerError

from foglamp.services.core import server
from foglamp.services.core import connect
from foglamp.services.core.scheduler.entities import Schedule, TimedSchedule, IntervalSchedule, ManualSchedule
from foglamp.services.core.api import utils as apiutils

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -------------------------------------------------------------------------------
    | GET POST            | /foglamp/scheduled/task                               |
    -------------------------------------------------------------------------------
"""

_logger = logger.setup()


async def add_task(request):
    """ Create a new task to run a specific plugin

    :Example:
     curl -X POST http://localhost:8081/foglamp/scheduled/task -d
     '{
        "name": "North Readings to PI",
        "plugin": "pi_server",
        "type": "north",
        "schedule_type": 3,
        "schedule_day": 0,
        "schedule_time": 0,
        "schedule_repeat": 30,
        "schedule_enabled": true
     }'
    """

    try:
        data = await request.json()
        if not isinstance(data, dict):
            raise ValueError('Data payload must be a valid JSON')

        name = data.get('name', None)
        plugin = data.get('plugin', None)
        task_type = data.get('type', None)

        schedule_type = data.get('schedule_type', None)
        schedule_day = data.get('schedule_day', None)
        schedule_time = data.get('schedule_time', None)
        schedule_repeat = data.get('schedule_repeat', None)
        enabled = data.get('schedule_enabled', None)

        if name is None:
            raise web.HTTPBadRequest(reason='Missing name property in payload.')
        if plugin is None:
            raise web.HTTPBadRequest(reason='Missing plugin property in payload.')
        if task_type is None:
            raise web.HTTPBadRequest(reason='Missing type property in payload.')
        if utils.check_reserved(name) is False:
            raise web.HTTPBadRequest(reason='Invalid name property in payload.')
        if utils.check_reserved(plugin) is False:
            raise web.HTTPBadRequest(reason='Invalid plugin property in payload.')
        if task_type not in ['north']:
            raise web.HTTPBadRequest(reason='Only north type is supported.')

        if schedule_type is None:
            raise web.HTTPBadRequest(reason='schedule_type is mandatory')
        if not isinstance(schedule_type, int) and not schedule_type.isdigit():
            raise web.HTTPBadRequest(reason='Error in schedule_type: {}'.format(schedule_type))
        if int(schedule_type) not in list(Schedule.Type):
            raise web.HTTPBadRequest(reason='schedule_type error: {}'.format(schedule_type))
        if int(schedule_type) == Schedule.Type.STARTUP:
            raise web.HTTPBadRequest(reason='schedule_type cannot be STARTUP: {}'.format(schedule_type))

        schedule_type = int(schedule_type)

        if schedule_day is not None:
            if isinstance(schedule_day, float) or (isinstance(schedule_day, str) and (schedule_day.strip() != "" and not schedule_day.isdigit())):
                raise web.HTTPBadRequest(reason='Error in schedule_day: {}'.format(schedule_day))
        else:
            schedule_day = int(schedule_day) if schedule_day is not None else None

        if schedule_time is not None and (not isinstance(schedule_time, int) and not schedule_time.isdigit()):
            raise web.HTTPBadRequest(reason='Error in schedule_time: {}'.format(schedule_time))
        else:
            schedule_time = int(schedule_time) if schedule_time is not None else None

        if schedule_repeat is not None and (not isinstance(schedule_repeat, int) and not schedule_repeat.isdigit()):
            raise web.HTTPBadRequest(reason='Error in schedule_repeat: {}'.format(schedule_repeat))
        else:
            schedule_repeat = int(schedule_repeat) if schedule_repeat is not None else None

        if schedule_type == Schedule.Type.TIMED:
            if not schedule_time:
                raise web.HTTPBadRequest(reason='schedule_time cannot be empty/None for TIMED schedule.')
            if schedule_day is not None and (schedule_day < 1 or schedule_day > 7):
                raise web.HTTPBadRequest(reason='schedule_day {} must either be None or must be an integer, 1(Monday) '
                                                'to 7(Sunday).'.format(schedule_day))
            if schedule_time < 0 or schedule_time > 86399:
                raise web.HTTPBadRequest(reason='schedule_time {} must be an integer and in range 0-86399.'.format(schedule_time))

        if schedule_type == Schedule.Type.INTERVAL:
            if schedule_repeat is None:
                raise web.HTTPBadRequest(reason='schedule_repeat {} is required for INTERVAL schedule_type.'.format(schedule_repeat))
            elif not isinstance(schedule_repeat, int):
                raise web.HTTPBadRequest(reason='schedule_repeat {} must be an integer.'.format(schedule_repeat))

        if enabled is not None:
            if enabled not in ['true', 'false', True, False]:
                raise web.HTTPBadRequest(reason='Only "true", "false", true, false are allowed for value of enabled.')
        is_enabled = True if ((type(enabled) is str and enabled.lower() in ['true']) or (
            (type(enabled) is bool and enabled is True))) else False

        # Check if a valid plugin has been provided
        try:
            # "plugin_module_path" is fixed by design. It is MANDATORY to keep the plugin in the exactly similar named
            # folder, within the plugin_module_path.
            # if multiple plugin with same name are found, then python plugin import will be tried first
            plugin_module_path = "foglamp.plugins.{}".format(task_type)
            import_file_name = "{path}.{dir}.{file}".format(path=plugin_module_path, dir=plugin, file=plugin)
            _plugin = __import__(import_file_name, fromlist=[''])

            script = '["tasks/north"]'
            # Fetch configuration from the configuration defined in the plugin
            plugin_info = _plugin.plugin_info()
            if plugin_info['type'] != task_type:
                msg = "Plugin of {} type is not supported".format(plugin_info['type'])
                _logger.exception(msg)
                return web.HTTPBadRequest(reason=msg)
            plugin_config = plugin_info['config']
            process_name = 'north'
        except ImportError as ex:
            # Checking for C-type plugins
            script = '["tasks/north_c"]'
            plugin_info = apiutils.get_plugin_info(plugin)
            if plugin_info['type'] != task_type:
                msg = "Plugin of {} type is not supported".format(plugin_info['type'])
                _logger.exception(msg)
                return web.HTTPBadRequest(reason=msg)
            plugin_config = plugin_info['config']
            process_name = 'north_c'
            if not plugin_config:
                _logger.exception("Plugin %s import problem from path %s. %s", plugin, plugin_module_path, str(ex))
                raise web.HTTPNotFound(reason='Plugin "{}" import problem from path "{}"'.format(plugin, plugin_module_path))
        except Exception as ex:
            _logger.exception("Failed to fetch plugin configuration. %s", str(ex))
            raise web.HTTPInternalServerError(reason='Failed to fetch plugin configuration.')

        storage = connect.get_storage_async()

        # Check that the schedule name is not already registered
        count = await check_schedules(storage, name)
        if count != 0:
            raise web.HTTPBadRequest(reason='A north instance with this name already exists')

        # Check that the process name is not already registered
        count = await check_scheduled_processes(storage, process_name)
        if count == 0:  # Create the scheduled process entry for the new task
            payload = PayloadBuilder().INSERT(name=process_name, script=script).payload()
            try:
                res = await storage.insert_into_tbl("scheduled_processes", payload)
            except StorageServerError as ex:
                _logger.exception("Failed to create scheduled process. %s", ex.error)
                raise web.HTTPInternalServerError(reason='Failed to create north instance.')
            except Exception as ex:
                _logger.exception("Failed to create scheduled process. %s", ex)
                raise web.HTTPInternalServerError(reason='Failed to create north instance.')

        # If successful then create a configuration entry from plugin configuration
        try:
            # Create a configuration category from the configuration defined in the plugin
            category_desc = plugin_config['plugin']['description']
            config_mgr = ConfigurationManager(storage)
            await config_mgr.create_category(category_name=name,
                                             category_description=category_desc,
                                             category_value=plugin_config,
                                             keep_original_items=True)
            # Create the parent category for all North tasks
            await config_mgr.create_category("North", {}, 'North tasks', True)
            await config_mgr.create_child_category("North", [name])
        except Exception as ex:
            await revert_configuration(storage, name)  # Revert configuration entry
            await revert_parent_child_configuration(storage, name)
            _logger.exception("Failed to create plugin configuration. %s", str(ex))
            raise web.HTTPInternalServerError(reason='Failed to create plugin configuration.')

        # If all successful then lastly add a schedule to run the new task at startup
        try:
            schedule = TimedSchedule() if schedule_type == Schedule.Type.TIMED else \
                       IntervalSchedule() if schedule_type == Schedule.Type.INTERVAL else \
                       ManualSchedule()
            schedule.name = name
            schedule.process_name = process_name
            schedule.day = schedule_day
            m, s = divmod(schedule_time if schedule_time is not None else 0, 60)
            h, m = divmod(m, 60)
            schedule.time = datetime.time().replace(hour=h, minute=m, second=s)
            schedule.repeat = datetime.timedelta(seconds=schedule_repeat if schedule_repeat is not None else 0)
            schedule.exclusive = True
            schedule.enabled = False  # if "enabled" is supplied, it gets activated in save_schedule() via is_enabled flag

            # Save schedule
            await server.Server.scheduler.save_schedule(schedule, is_enabled)
            schedule = await server.Server.scheduler.get_schedule_by_name(name)
        except StorageServerError as ex:
            await revert_configuration(storage, name)  # Revert configuration entry
            await revert_parent_child_configuration(storage, name)
            _logger.exception("Failed to create schedule. %s", ex.error)
            raise web.HTTPInternalServerError(reason='Failed to create north instance.')
        except Exception as ex:
            await revert_configuration(storage, name)  # Revert configuration entry
            await revert_parent_child_configuration(storage, name)
            _logger.exception("Failed to create schedule. %s", str(ex))
            raise web.HTTPInternalServerError(reason='Failed to create north instance.')

    except ValueError as e:
        raise web.HTTPBadRequest(reason=str(e))
    else:
        return web.json_response({'name': name, 'id': str(schedule.schedule_id)})


async def check_scheduled_processes(storage, process_name):
    payload = PayloadBuilder().SELECT("name").WHERE(['name', '=', process_name]).payload()
    result = await storage.query_tbl_with_payload('scheduled_processes', payload)
    return result['count']


async def check_schedules(storage, schedule_name):
    payload = PayloadBuilder().SELECT("schedule_name").WHERE(['schedule_name', '=', schedule_name]).payload()
    result = await storage.query_tbl_with_payload('schedules', payload)
    return result['count']


async def revert_configuration(storage, key):
    payload = PayloadBuilder().WHERE(['key', '=', key]).payload()
    await storage.delete_from_tbl('configuration', payload)


async def revert_parent_child_configuration(storage, key):
    payload = PayloadBuilder().WHERE(['parent', '=', "North"]).AND_WHERE(['child', '=', key]).payload()
    await storage.delete_from_tbl('category_children', payload)
