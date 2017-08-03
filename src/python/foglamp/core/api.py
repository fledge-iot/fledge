# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END
import asyncio
import datetime
import time
import re
from aiohttp import web
from foglamp import configuration_manager
from foglamp.core import scheduler_db_services, statistics_db_services
from foglamp.core.scheduler import Scheduler, Schedule, StartUpSchedule, TimedSchedule, IntervalSchedule, ManualSchedule
from foglamp.core import server

__author__ = "Amarendra K. Sinha, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

__start_time = time.time()

_help = """
    ------------------------------------------------------------------------------
    | GET             | /foglamp/ping                                             |

    | GET             | /foglamp/categories                                       |
    | GET             | /foglamp/category/{category_name}                         |
    | GET PUT DELETE  | /foglamp/category/{category_name}/{config_item}           |

    | GET             | /foglamp/schedule/process                                 |

    | GET             | /foglamp/schedules                                        |
    | POST            | /foglamp/schedule                                         |
    | GET PUT DELETE  | /foglamp/schedule/{schedule_id}                           |

    | GET             | /foglamp/tasks                                            |
    | GET             | /foglamp/tasks/latest                                     |
    | POST            | /foglamp/task                                             |
    | GET DELETE      | /foglamp/task/{task_id}                                   |

    | GET             | /foglamp/statistics                                       |
    | GET             | /foglamp/statistics/history                               |
    ------------------------------------------------------------------------------
"""


async def ping(request):
    """

    :param request:
    :return: basic health information json payload
    {'uptime': 32892} Time in seconds since FogLAMP started
    """
    since_started = time.time() - __start_time

    return web.json_response({'uptime': since_started})


#################################
#  Configuration Manager
#################################

async def get_categories(request):
    """

    :param request:
    :return: the list of known categories in the configuration database
    """
    categories = await configuration_manager.get_all_category_names()
    categories_json = [{"key": c[0], "description": c[1]} for c in categories]

    return web.json_response({'categories': categories_json})


async def get_category(request):
    """

    :param request:  category_name is required
    :return: the configuration items in the given category.
    """
    category_name = request.match_info.get('category_name', None)
    category = await configuration_manager.get_category_all_items(category_name)
    # TODO: If category is None from configuration manager. Should we send category
    # as an empty array or error message in JSON format?
    if category is None:
        category = []

    return web.json_response(category)


async def get_category_item(request):
    """

    :param request: category_name & config_item are required
    :return: the configuration item in the given category.
    """
    category_name = request.match_info.get('category_name', None)
    config_item = request.match_info.get('config_item', None)
    category_item = await configuration_manager.get_category_item(category_name, config_item)
    # TODO: better error handling / info message
    if (category_name is None) or (config_item is None):
        category_item = []

    return web.json_response(category_item)


async def set_configuration_item(request):
    """

    :param request: category_name, config_item are required and For PUT request {"value" : someValue) is required
    :return: set the configuration item value in the given category.

    :Example:

        For {category_name} PURGE  update/delete value for config_item {age}

        curl -H "Content-Type: application/json" -X PUT -d '{"value":some_value}' http://localhost:8082/foglamp/category/{category_name}/{config_item}

        curl -X DELETE http://localhost:8082/foglamp/category/{category_name}/{config_item}
    """
    category_name = request.match_info.get('category_name', None)
    config_item = request.match_info.get('config_item', None)

    if request.method == 'PUT':
        data = await request.json()
        value = data['value']
    elif request.method == 'DELETE':
        value = ''

    await configuration_manager.set_category_item_value_entry(category_name, config_item, value)
    result = await configuration_manager.get_category_item(category_name, config_item)

    return web.json_response(result)


#################################
# Scheduled_processes
#################################


async def get_scheduled_processes(request):
    """Returns a list of all the defined scheduled_processes from scheduled_processes table"""

    try:
        # processes = await scheduler_db_services.read_scheduled_processes()
        processes_list = await server.Server.scheduler.get_scheduled_processes()

        processes = []
        for proc in processes_list:
            processes.append({'name': proc.name, 'script': proc.script})

        return web.json_response({'processes': processes})
    except Exception as ex:
        raise web.HTTPInternalServerError(reason='FogLAMP has encountered an internal error', text=str(ex))


async def get_scheduled_process(request):
    """Returns a list of all the defined scheduled_processes from scheduled_processes table"""

    try:
        scheduled_process_name = request.match_info.get('scheduled_process_name', None)

        if not scheduled_process_name:
            raise ValueError('No such Scheduled Process')

        scheduled_process = await scheduler_db_services.read_scheduled_processes(scheduled_process_name)

        if not scheduled_process:
            raise ValueError('No such Scheduled Process: {}.'.format(scheduled_process_name))

        return web.json_response(scheduled_process)
    except ValueError as ex:
        raise web.HTTPNotFound(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason='FogLAMP has encountered an internal error', text=str(ex))


#################################
# Schedules
#################################


async def get_schedules(request):
    """Returns a list of all the defined schedules from schedules table"""

    try:
        # schedules = await scheduler_db_services.read_schedule()
        schedule_list = await server.Server.scheduler.get_schedules()

        schedules = []
        for sch in schedule_list:
            schedules.append({
                'id': str(sch.schedule_id),
                'name': sch.name,
                'process_name': sch.process_name,
                'type': sch.type,
                'repeat': sch.repeat,
                'day': sch.day,
                'time': sch.time,
                'exclusive': sch.exclusive
            })

        return web.json_response({'schedules': schedules})
    except Exception as ex:
        raise web.HTTPInternalServerError(reason='FogLAMP has encountered an internal error', text=str(ex))


async def get_schedule(request):
    """Return the information for the given schedule from schedules table

        Example: curl -X GET  http://localhost:8082/foglamp/schedule/ac6dd55d-f55d-44f7-8741-984604bf2384
    """

    try:
        schedule_id = request.match_info.get('schedule_id', None)

        if not schedule_id:
            raise ValueError('No such Schedule')

        # schedule = await scheduler_db_services.read_schedule(schedule_id)
        sch = await server.Server.scheduler.get_schedule(schedule_id)
        if not sch:
            raise ValueError('No such Schedule')

        schedule = {
            'id': str(sch.schedule_id),
            'name': sch.name,
            'process_name': sch.process_name,
            'type': sch.type,
            'repeat': sch.repeat,
            'day': sch.day,
            'time': sch.time,
            'exclusive': sch.exclusive
        }

        return web.json_response(schedule)
    except ValueError as ex:
        raise web.HTTPNotFound(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason='FogLAMP has encountered an internal error', text=str(ex))


async def start_schedule(request):
    """Starts a given schedule

        Example: curl -X GET  http://localhost:8082/foglamp/schedule/start/fd439e5b-86ba-499a-86d3-34a6e5754b5a
    """

    try:
        schedule_id = request.match_info.get('schedule_id', None)

        if not schedule_id:
            raise ValueError('No such Schedule')

        schedule = await scheduler_db_services.read_schedule(schedule_id)

        if not schedule:
            raise ValueError('No such Schedule')

        # Start schedule
        await server.Server.scheduler.queue_task(schedule_id)

        return web.json_response(schedule)
    except ValueError as ex:
        raise web.HTTPNotFound(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason='FogLAMP has encountered an internal error', text=str(ex))

def _extract_args(data):
    _schedule = dict()

    _schedule['schedule_id'] = data.get('schedule_id', None)

    s_type = data.get('type', 0)
    _schedule['schedule_type'] = int(s_type)

    s_day = data.get('day', 0)
    s_time = data.get('time', 0)
    _schedule['schedule_day'] = int(s_day)
    _schedule['schedule_time'] = int(s_time)

    _schedule['schedule_name'] = data.get('name', None)
    _schedule['schedule_process_name'] = data.get('process_name', None)
    _schedule['schedule_repeat'] = datetime.timedelta(seconds=int(data.get('repeat', 1)))
    _schedule['schedule_exclusive'] = data.get('exclusive', True)

    return _schedule

async def _check_schedule_post_parameters(data):
    _schedule = _extract_args(data)

    _errors = list()

    if not _schedule.get('schedule_id'): # Add a new schedule
        # Raise error if schedule_type is missing
        if not _schedule.get('schedule_type'):
            _errors.append('Schedule type cannot be empty.')

        # Raise error if schedule_type is wrong
        if _schedule.get('schedule_type') not in [Scheduler._ScheduleType.INTERVAL, Scheduler._ScheduleType.TIMED,
                                 Scheduler._ScheduleType.MANUAL, Scheduler._ScheduleType.STARTUP]:
            _errors.append('Schedule type error: {}'.format(_schedule.get('schedule_type')))

        if _schedule.get('schedule_type') == Scheduler._ScheduleType.TIMED:
            # Raise error if day and time are missing for schedule_type = TIMED
            if not _schedule.get('schedule_day') or not _schedule.get('schedule_time'):
                _errors.append('Schedule day and time cannot be empty for TIMED schedule.')
            # TODO: day and time must be integers

        if _schedule.get('schedule_type') == Scheduler._ScheduleType.INTERVAL:
            pass
            # TODO: Check for repeat value if schedule_type is INTERVAL. Repeat must be integers
            # TODO: How to define various values of datetime.timedelta for "repeat"?

        # Raise error if name and process_name are missing
        if not _schedule.get('schedule_name') or not _schedule.get('schedule_process_name'):
            _errors.append('Schedule name and Process name cannot be empty.')

        scheduled_process = await scheduler_db_services.read_scheduled_processes(_schedule.get('schedule_process_name'))

        if not scheduled_process:
            _errors.append('No such Scheduled Process name: {}'.format(_schedule.get('schedule_process_name')))
    else: # Update an existing schedule
        if not _schedule.get('schedule_type'):
            # Raise error if schedule_type is wrong
            if _schedule.get('schedule_type') not in [Scheduler._ScheduleType.INTERVAL, Scheduler._ScheduleType.TIMED,
                                     Scheduler._ScheduleType.MANUAL, Scheduler._ScheduleType.STARTUP]:
                _errors.append('Schedule type error: {}'.format(_schedule.get('schedule_type')))

            if _schedule.get('schedule_type') == Scheduler._ScheduleType.TIMED:
                # Raise error if day and time are missing for schedule_type = TIMED
                if not _schedule.get('schedule_day') or not _schedule.get('schedule_time'):
                    _errors.append('Schedule day and time cannot be empty for TIMED schedule.')
                # TODO: day and time must be integers

            if _schedule.get('schedule_type') == Scheduler._ScheduleType.INTERVAL:
                pass
                # TODO: Check for repeat value if schedule_type is INTERVAL. Repeat must be integers
                # TODO: How to define various values of datetime.timedelta for "repeat"?

        # Raise error if name and process_name are missing
        if not _schedule.get('schedule_process_name'):
            _errors.append('Schedule name and Process name cannot be empty.')

            scheduled_process = await scheduler_db_services.read_scheduled_processes(_schedule.get('schedule_process_name'))

            if not scheduled_process:
                _errors.append('No such Scheduled Process name: {}'.format(_schedule.get('schedule_process_name')))

    return _errors


async def _execute_add_update_schedule(data):
    _schedule = _extract_args(data)

    # Create schedule object as Scheduler.save_schedule requires an object
    if _schedule.get('schedule_type') == Scheduler._ScheduleType.STARTUP:
        schedule = StartUpSchedule()
    elif _schedule.get('schedule_type') == Scheduler._ScheduleType.TIMED:
        schedule = TimedSchedule()
        schedule.day = _schedule.get('schedule_day')
        schedule.time = _schedule.get('schedule_time')
    elif _schedule.get('schedule_type') == Scheduler._ScheduleType.INTERVAL:
        schedule = IntervalSchedule()
    elif _schedule.get('schedule_type') == Scheduler._ScheduleType.MANUAL:
        schedule = ManualSchedule()

    # Populate scheduler object
    schedule.schedule_id = _schedule.get('schedule_id')
    # schedule.schedule_type = schedule_type
    schedule.name = _schedule.get('schedule_name')
    schedule.process_name = _schedule.get('schedule_process_name')
    schedule.repeat = _schedule.get('schedule_repeat')
    schedule.exclusive = _schedule.get('schedule_exclusive')

    # Save schedule
    await server.Server.scheduler.save_schedule(schedule)

    updated_schedule_id = schedule.schedule_id

    return updated_schedule_id


async def post_schedule(request):
    """Create a new schedule in schedules table

        Example: curl -d '{"type": 3, "name": "sleep30", "process_name": "sleep30", "repeat": "45"}'  -X POST  http://localhost:8082/foglamp/schedule
    """

    try:
        data = await request.json()

        schedule_id = data.get('schedule_id', None)
        if schedule_id:
            raise ValueError('Schedule ID not needed for new Schedule.')

        go_no_go = await _check_schedule_post_parameters(data)
        if len(go_no_go) != 0:
            raise ValueError("Errors in request: {} {}".format(','.join(go_no_go), len(go_no_go)))

        updated_schedule_id = await _execute_add_update_schedule(data)

        return web.json_response({'message': 'Schedule created successfully.', 'id': str(updated_schedule_id)})
    except ValueError as ex:
        raise web.HTTPNotFound(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason='FogLAMP has encountered an internal error', text=str(ex))


async def update_schedule(request):
    """Update a schedule in schedules table

        Example: curl -d '{"type": 4, "name": "sleep30 updated", "process_name": "sleep30", "repeat": "15"}'  -X PUT  http://localhost:8082/foglamp/schedule/84fe4ea1-df9c-4c87-bb78-cab2e7d5d2cc
    """

    try:
        data = await request.json()
        schedule_id = request.match_info.get('schedule_id', None)

        if not schedule_id:
            raise ValueError('No such Schedule.')

        is_schedule = await scheduler_db_services.read_schedule(schedule_id)
        if not is_schedule:
            raise ValueError('No such Schedule: {}.'.format(schedule_id))

        go_no_go = await _check_schedule_post_parameters(data)
        if len(go_no_go) != 0:
            raise ValueError("Errors in request: {}".format(','.join(go_no_go)))

        data['schedule_id'] = schedule_id
        updated_schedule_id = await _execute_add_update_schedule(data)

        return web.json_response({'message': 'Schedule updated successfully.', 'id': str(updated_schedule_id)})
    except ValueError as ex:
        raise web.HTTPNotFound(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason='FogLAMP has encountered an internal error', text=str(ex))


async def delete_schedule(request):
    """Delete a schedule from schedules table

        Example: curl -X DELETE  http://localhost:8082/foglamp/schedule/dc9bfc01-066a-4cc0-b068-9c35486db87f
    """

    try:
        schedule_id = request.match_info.get('schedule_id', None)

        if not schedule_id:
            raise ValueError('No such Schedule.')

        is_schedule = await scheduler_db_services.read_schedule(schedule_id)
        if not is_schedule:
            raise ValueError('No such Schedule: {}.'.format(schedule_id))

        await server.Server.scheduler.delete_schedule(schedule_id)

        return web.json_response({'message': 'Schedule deleted successfully.', 'id': schedule_id})
    except ValueError as ex:
        raise web.HTTPNotFound(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason='FogLAMP has encountered an internal error', text=str(ex))


#################################
# Tasks
#################################


async def get_task(request):
    """Returns a task

        Example: curl -X GET  http://localhost:8082/foglamp/task/{task_id}?name=xxx&state=xxx
    """

    try:
        task_id = request.match_info.get('task_id', None)

        if not task_id:
            raise ValueError('No such Task')

        task = await scheduler_db_services.read_task(task_id)

        if not task:
            raise ValueError('No such Task')

        return web.json_response(task)
    except ValueError as ex:
        raise web.HTTPNotFound(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason='FogLAMP has encountered an internal error', text=str(ex))


async def get_tasks(request):
    """Returns the list of tasks

        Example: curl -X GET  http://localhost:8082/foglamp/tasks?name=xxx&state=xxx
    """

    try:
        task_id = None

        # TODO: Use enum in place int state
        state = request.query.get('state') if 'state' in request.query else None
        if state:
            if not re.match("(^[1-4]$)", state):
                raise ValueError('This state value not permitted')
            else:
                state = int(state)

        name = request.query.get('name') if 'name' in request.query else None

        tasks = await scheduler_db_services.read_task(task_id, state, name)

        if not tasks:
            raise ValueError('No such Tasks')

        return web.json_response({'tasks': tasks})
    except ValueError as ex:
        raise web.HTTPNotFound(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason='FogLAMP has encountered an internal error', text=str(ex))


async def get_tasks_latest(request):
    """Returns the list of the most recent task execution for each name from tasks table

        Example: curl -X GET  http://localhost:8082/foglamp/tasks/latest
    """

    try:
        # TODO: Use enum in place int state
        state = request.query.get('state') if 'state' in request.query else None
        if state:
            if not re.match("(^[1-4]$)", state):
                raise ValueError('This state value not permitted')
            else:
                state = int(state)

        name = request.query.get('name') if 'name' in request.query else None

        tasks = await scheduler_db_services.read_tasks_latest(state, name)

        if not tasks:
            raise ValueError('No such Task')

        return web.json_response({'tasks': tasks})
    except ValueError as ex:
        raise web.HTTPNotFound(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason='FogLAMP has encountered an internal error', text=str(ex))


async def get_tasks_running(request):
    """Returns a list of all running tasks

        Example: curl -X GET  http://localhost:8082/foglamp/tasks/running
    """

    try:
        task_list = await server.Server.scheduler.get_running_tasks()

        tasks = []
        for task in task_list:
            tasks.append({
                'id': task.task_id,
                'process_name': task.process_name,
                'state': task.state,
                'start_time': task.start_time
            })

        return web.json_response({'tasks': tasks})
    except Exception as ex:
        raise web.HTTPInternalServerError(reason='FogLAMP has encountered an internal error', text=str(ex))


async def post_task(request):
    """ create a new task"""
    pass

async def cancel_task(request):
    """Cancel a running task from tasks table"""
    pass


#################################
#  Statistics
#################################


async def get_statistics(request):
    """
        Returns a general set of statistics

        Example: curl -X GET http://localhost:8082/foglamp/statistics
    """

    try:
        statistics = await statistics_db_services.read_statistics()

        return web.json_response(statistics)
    except Exception as ex:
        raise web.HTTPInternalServerError(reason='FogLAMP has encountered an internal error', text=str(ex))


async def get_statistics_history(request):
    """
        Returns a list of general set of statistics

        Example: curl -X GET -d limit=1 http://localhost:8082/foglamp/statistics/history
    """

    try:
        limit = request.query.get('limit') if 'limit' in request.query else 0

        statistics = await statistics_db_services.read_statistics_history(int(limit))

        if not statistics:
            raise ValueError('No statistics available')

        # TODO: find out where from this "interval" will be picked and what will be its role in query?
        return web.json_response({"interval": 5, 'statistics': statistics})
    except ValueError as ex:
        raise web.HTTPNotFound(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason='FogLAMP has encountered an internal error', text=str(ex))
