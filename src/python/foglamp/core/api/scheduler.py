# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import datetime
import time

from aiohttp import web

from foglamp.core import server
from foglamp.core.api import scheduler_db_services
from foglamp.core.scheduler import Scheduler, StartUpSchedule, TimedSchedule, IntervalSchedule, ManualSchedule, Task

__author__ = "Amarendra K. Sinha, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

__start_time = time.time()

_help = """
    -------------------------------------------------------------------------------
    | GET             | /foglamp/schedule/process                                 |

    | GET             | /foglamp/schedules                                        |
    | POST            | /foglamp/schedule                                         |
    | GET PUT DELETE  | /foglamp/schedule/{schedule_id}                           |

    | GET             | /foglamp/tasks                                            |
    | GET             | /foglamp/tasks/latest                                     |
    | GET DELETE      | /foglamp/task/{task_id}                                   |
    -------------------------------------------------------------------------------
"""


#################################
# Scheduled_processes
#################################


async def get_scheduled_processes(request):
    """
    Returns a list of all the defined scheduled_processes from scheduled_processes table
    """

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
    """
    Returns a list of all the defined scheduled_processes from scheduled_processes table
    """

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


def _extract_args(data, curr_value):
    _schedule = dict()

    _schedule['schedule_id'] = curr_value['schedule_id'] if curr_value else None

    s_type = data.get('type') if 'type' in data else curr_value['schedule_type'] if curr_value else 0
    _schedule['schedule_type'] = int(s_type)

    s_day = data.get('day') if 'day' in data else curr_value['schedule_day'] if curr_value and curr_value['schedule_day'] else 0
    _schedule['schedule_day'] = int(s_day)

    s_time = data.get('time') if 'time' in data else curr_value['schedule_time'] if curr_value and curr_value['schedule_time'] else 0
    _schedule['schedule_time'] = int(s_time)

    s_repeat = data.get('repeat') if 'repeat' in data else curr_value['schedule_repeat'] if curr_value and curr_value['schedule_repeat']else 0
    _schedule['schedule_repeat'] = int(s_repeat)

    _schedule['schedule_name'] = data.get('name') if 'name' in data else curr_value['schedule_name'] if curr_value else None

    _schedule['schedule_process_name'] = data.get('process_name') if 'process_name' in data else curr_value['schedule_process_name'] if curr_value else None

    _schedule['schedule_exclusive'] = data.get('exclusive') if 'exclusive' in data else curr_value['schedule_exclusive'] if curr_value else 'True'
    _schedule['schedule_exclusive'] = 'True' if _schedule['schedule_exclusive'] else 'False'

    return _schedule


async def _check_schedule_post_parameters(data, curr_value=None):
    """
    Private method to validate post data for creating a new schedule or updating an existing schedule

    :param data:
    :return: list errors
    """

    _schedule = _extract_args(data, curr_value)

    _errors = list()

    # Raise error if schedule_type is missing for a new schedule
    if 'schedule_id' not in _schedule and not _schedule.get('schedule_type'):
        _errors.append('Schedule type cannot be empty.')

    # Raise error if schedule_type is wrong
    if _schedule.get('schedule_type') not in list(Scheduler._ScheduleType):
        _errors.append('Schedule type error: {}'.format(_schedule.get('schedule_type')))

    # Raise error if day and time are missing for schedule_type = TIMED
    if _schedule.get('schedule_type') == Scheduler._ScheduleType.TIMED:
        if not _schedule.get('schedule_day') or not _schedule.get('schedule_time'):
            _errors.append('Schedule day and time cannot be empty for TIMED schedule.')
        elif not isinstance(_schedule.get('schedule_day'), int):
            _errors.append('Day must be an integer.')
        elif not isinstance(_schedule.get('schedule_time'), int):
            _errors.append('Time must be an integer.')

    # Raise error if repeat is missing or is non integers
    if _schedule.get('schedule_type') == Scheduler._ScheduleType.INTERVAL:
        if 'schedule_repeat' not in _schedule:
            _errors.append('repeat is required for INTERVAL Schedule type.')
        elif not isinstance(int(_schedule.get('schedule_repeat')), int):
            _errors.append('Repeat must be an integer.')

    # Raise error if day is non integer
    if not isinstance(_schedule.get('schedule_day'), int):
        _errors.append('Day must be an integer.')

    # Raise error if time is non integer
    if not isinstance(_schedule.get('schedule_time'), int):
        _errors.append('Time must be an integer.')

    # Raise error if repeat is non integer
    if not isinstance(int(_schedule.get('schedule_repeat')), int):
        _errors.append('Repeat must be an integer.')

    # Raise error if name and process_name are missing for a new schedule
    if not _schedule.get('schedule_name') or not _schedule.get('schedule_process_name'):
        _errors.append('Schedule name and Process name cannot be empty.')

    # Raise error if scheduled_process name is wrong
    scheduled_process = await scheduler_db_services.read_scheduled_processes(_schedule.get('schedule_process_name'))
    if not scheduled_process:
        _errors.append('No such Scheduled Process name: {}'.format(_schedule.get('schedule_process_name')))

    # Raise error if exclusive is wrong
    if _schedule.get('schedule_exclusive') not in ['True', 'False']:
        _errors.append('Schedule exclusive error: {}'.format(_schedule.get('schedule_exclusive')))

    return _errors


async def _execute_add_update_schedule(data, curr_value=None):
    """
    Private method common to create a new schedule and update an existing schedule

    :param data:
    :return: schedule_id (new for created, existing for updated)
    """

    _schedule = _extract_args(data, curr_value)

    # Create schedule object as Scheduler.save_schedule requires an object
    if _schedule.get('schedule_type') == Scheduler._ScheduleType.STARTUP:
        schedule = StartUpSchedule()
    elif _schedule.get('schedule_type') == Scheduler._ScheduleType.TIMED:
        schedule = TimedSchedule()
        schedule.day = _schedule.get('schedule_day')
        m, s = divmod(_schedule.get('schedule_time'), 60)
        h, m = divmod(m, 60)
        schedule.time = "{hours}:{minutes}:{seconds}".format(hours=h, minutes=m, seconds=s)
    elif _schedule.get('schedule_type') == Scheduler._ScheduleType.INTERVAL:
        schedule = IntervalSchedule()
    elif _schedule.get('schedule_type') == Scheduler._ScheduleType.MANUAL:
        schedule = ManualSchedule()

    # Populate scheduler object
    schedule.schedule_id = _schedule.get('schedule_id')
    # schedule.schedule_type = schedule_type
    schedule.name = _schedule.get('schedule_name')
    schedule.process_name = _schedule.get('schedule_process_name')
    schedule.repeat = datetime.timedelta(seconds=_schedule['schedule_repeat'])

    schedule.exclusive = True if _schedule.get('schedule_exclusive') == 'True' else False

    # Save schedule
    await server.Server.scheduler.save_schedule(schedule)

    updated_schedule_id = schedule.schedule_id

    return updated_schedule_id


async def get_schedules(request):
    """
    Returns a list of all the defined schedules from schedules table
    """

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
                'repeat': str(sch.repeat),
                'day': sch.day,
                'time': str(sch.time),
                'exclusive': sch.exclusive
            })

        return web.json_response({'schedules': schedules})
    except Exception as ex:
        raise web.HTTPInternalServerError(reason='FogLAMP has encountered an internal error', text=str(ex))


async def get_schedule(request):
    """
    Return the information for the given schedule from schedules table

    :Example: curl -X GET  http://localhost:8082/foglamp/schedule/ac6dd55d-f55d-44f7-8741-984604bf2384
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
            'repeat': str(sch.repeat),
            'day': sch.day,
            'time': str(sch.time),
            'exclusive': sch.exclusive
        }

        return web.json_response(schedule)
    except ValueError as ex:
        raise web.HTTPNotFound(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason='FogLAMP has encountered an internal error', text=str(ex))


async def start_schedule(request):
    """
    Starts a given schedule

    :Example: curl -X GET  http://localhost:8082/foglamp/schedule/start/fd439e5b-86ba-499a-86d3-34a6e5754b5a
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


async def post_schedule(request):
    """
    Create a new schedule in schedules table

    :Example: curl -d '{"type": 3, "name": "sleep30", "process_name": "sleep30", "repeat": "45"}'  -X POST  http://localhost:8082/foglamp/schedule
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
    """
    Update a schedule in schedules table

    :Example: curl -d '{"type": 4, "name": "sleep30 updated", "process_name": "sleep30", "repeat": "15"}'  -X PUT  http://localhost:8082/foglamp/schedule/84fe4ea1-df9c-4c87-bb78-cab2e7d5d2cc
    """

    try:
        data = await request.json()
        schedule_id = request.match_info.get('schedule_id', None)

        if not schedule_id:
            raise ValueError('No such Schedule.')

        schedule = await scheduler_db_services.read_schedule(schedule_id)
        if not schedule:
            raise ValueError('No such Schedule: {}.'.format(schedule_id))

        curr_value = dict()
        curr_value['schedule_id'] = schedule[0]['id']
        curr_value['schedule_process_name'] = schedule[0]['process_name']
        curr_value['schedule_name'] = schedule[0]['schedule']['schedule_name']
        curr_value['schedule_type'] = schedule[0]['schedule']['schedule_type']
        curr_value['schedule_repeat'] = schedule[0]['schedule']['schedule_interval']
        curr_value['schedule_time'] = schedule[0]['schedule']['schedule_time']
        curr_value['schedule_day'] = schedule[0]['schedule']['schedule_day']
        curr_value['schedule_exclusive'] = schedule[0]['schedule']['exclusive']

        go_no_go = await _check_schedule_post_parameters(data, curr_value)
        if len(go_no_go) != 0:
            raise ValueError("Errors in request: {}".format(','.join(go_no_go)))

        updated_schedule_id = await _execute_add_update_schedule(data, curr_value)

        return web.json_response({'message': 'Schedule updated successfully.', 'id': str(updated_schedule_id)})
    except ValueError as ex:
        raise web.HTTPNotFound(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason='FogLAMP has encountered an internal error', text=str(ex))


async def delete_schedule(request):
    """
    Delete a schedule from schedules table

    :Example: curl -X DELETE  http://localhost:8082/foglamp/schedule/dc9bfc01-066a-4cc0-b068-9c35486db87f
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
    """
    Returns a task

    :Example: curl -X GET  http://localhost:8082/foglamp/task/{task_id}?name=xxx&state=xxx
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
    """
    Returns the list of tasks

    :Example: curl -X GET  http://localhost:8082/foglamp/tasks?name=xxx&state=xxx
    """

    try:
        task_id = None

        state = request.query.get('state') if 'state' in request.query else None
        if state:
            if state not in list(Task.State):
                raise ValueError('This state value {} not permitted.'.format(state))
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
    """
    Returns the list of the most recent task execution for each name from tasks table

    :Example: curl -X GET  http://localhost:8082/foglamp/tasks/latest
    """

    try:
        state = request.query.get('state') if 'state' in request.query else None
        if state:
            if state not in list(Task.State):
                raise ValueError('This state value {} not permitted.'.format(state))
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
    """
    Returns a list of all running tasks

    :Example: curl -X GET  http://localhost:8082/foglamp/tasks/running
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


async def cancel_task(request):
    """Cancel a running task from tasks table"""
    pass
