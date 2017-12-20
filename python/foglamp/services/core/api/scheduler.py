# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import datetime
import re
import uuid
from aiohttp import web
from foglamp.services.core import server
from foglamp.services.core.scheduler.entities import Schedule, StartUpSchedule, TimedSchedule, IntervalSchedule, ManualSchedule, Task
from foglamp.services.core.scheduler.exceptions import TaskNotFoundError, ScheduleNotFoundError
from foglamp.services.core import connect
from foglamp.common.storage_client.payload_builder import PayloadBuilder

__author__ = "Amarendra K. Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_help = """
    -------------------------------------------------------------------------------
    | GET             | /foglamp/schedule/process                                 |
    | GET             | /foglamp/schedule/process/{scheduled_process_name}        |
    
    | GET POST        | /foglamp/schedule                                         |
    | GET PUT DELETE  | /foglamp/schedule/{schedule_id}                           |
    | POST            | /foglamp/schedule/start/{schedule_id}                     |
    | GET             | /foglamp/schedule/type                                    |
    
    | GET             | /foglamp/task                                             |
    | GET             | /foglamp/task/latest                                      |
    | GET PUT         | /foglamp/task/{task_id}                                   |
    | GET             | /foglamp/task/state                                       |
    | PUT             | /foglamp/task/cancel/{task_id}                            |
    -------------------------------------------------------------------------------
"""


#################################
# Scheduled_processes
#################################


async def get_scheduled_processes(request):
    """
    Returns a list of all the defined scheduled_processes from scheduled_processes table
    """

    processes_list = await server.Server.scheduler.get_scheduled_processes()

    processes = []
    for proc in processes_list:
        processes.append(proc.name)

    return web.json_response({'processes': processes})


async def get_scheduled_process(request):
    """
    Returns a list of all the defined scheduled_processes from scheduled_processes table
    """

    scheduled_process_name = request.match_info.get('scheduled_process_name', None)

    if not scheduled_process_name:
        raise web.HTTPBadRequest(reason='No Scheduled Process Name given')

    payload = PayloadBuilder().SELECT("name").WHERE(["name", "=", scheduled_process_name]).payload()
    _storage = connect.get_storage()
    scheduled_process = _storage.query_tbl_with_payload('scheduled_processes', payload)

    if len(scheduled_process['rows']) == 0:
        raise web.HTTPNotFound(reason='No such Scheduled Process: {}.'.format(scheduled_process_name))

    return web.json_response(scheduled_process['rows'][0].get("name"))


#################################
# Schedules
#################################


def _extract_args(data, curr_value):
    try:
        if 'type' in data and (not isinstance(data['type'], int) and not data['type'].isdigit()):
            raise ValueError('Error in type: {}'.format(data['type']))

        if 'day' in data and (not isinstance(data['day'], int) and not data['day'].isdigit()):
            raise ValueError('Error in day: {}'.format(data['day']))

        if 'time' in data and (not isinstance(data['time'], int) and not data['time'].isdigit()):
            raise ValueError('Error in time: {}'.format(data['time']))

        if 'repeat' in data and (not isinstance(data['repeat'], int) and not data['repeat'].isdigit()):
            raise ValueError('Error in repeat: {}'.format(data['repeat']))

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
    except ValueError as ex:
        raise web.HTTPBadRequest(reason=str(ex))

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
    if _schedule.get('schedule_type') not in list(Schedule.Type):
        _errors.append('Schedule type error: {}'.format(_schedule.get('schedule_type')))

    # Raise error if day and time are missing for schedule_type = TIMED
    if _schedule.get('schedule_type') == Schedule.Type.TIMED:
        if not _schedule.get('schedule_day'):
            _errors.append('Schedule day and time cannot be empty for TIMED schedule.')
        elif not isinstance(_schedule.get('schedule_day'), int) or (_schedule.get('schedule_day') < 1 or _schedule.get('schedule_day') > 7):
            _errors.append('Day must be an integer and in range 1-7.')
        elif not isinstance(_schedule.get('schedule_time'), int) or (_schedule.get('schedule_time') < 0 or _schedule.get('schedule_time') > 86399):
            _errors.append('Time must be an integer and in range 0-86399.')

    # Raise error if repeat is missing or is non integers
    if _schedule.get('schedule_type') == Schedule.Type.INTERVAL:
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
    payload = PayloadBuilder().SELECT("name").WHERE(["name", "=", _schedule.get('schedule_process_name')]).payload()
    _storage = connect.get_storage()
    scheduled_process = _storage.query_tbl_with_payload('scheduled_processes', payload)

    if len(scheduled_process['rows']) == 0:
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
    if _schedule.get('schedule_type') == Schedule.Type.STARTUP:
        schedule = StartUpSchedule()
    elif _schedule.get('schedule_type') == Schedule.Type.TIMED:
        schedule = TimedSchedule()
        schedule.day = _schedule.get('schedule_day')
        m, s = divmod(_schedule.get('schedule_time'), 60)
        h, m = divmod(m, 60)
        schedule.time = datetime.time().replace(hour=h, minute=m, second=s)
    elif _schedule.get('schedule_type') == Schedule.Type.INTERVAL:
        schedule = IntervalSchedule()
    elif _schedule.get('schedule_type') == Schedule.Type.MANUAL:
        schedule = ManualSchedule()

    # Populate scheduler object
    schedule.schedule_id = _schedule.get('schedule_id')
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

    schedule_list = await server.Server.scheduler.get_schedules()

    schedules = []
    for sch in schedule_list:
        schedules.append({
            'id': str(sch.schedule_id),
            'name': sch.name,
            'processName': sch.process_name,
            'type': Schedule.Type(int(sch.schedule_type)).name,
            'repeat': sch.repeat.total_seconds() if sch.repeat else 0,
            'time': (sch.time.hour * 60 * 60 + sch.time.minute * 60 + sch.time.second) if sch.time else 0,
            'day': sch.day,
            'exclusive': sch.exclusive
        })

    return web.json_response({'schedules': schedules})


async def get_schedule(request):
    """
    Return the information for the given schedule from schedules table

    :Example: curl -X GET  http://localhost:8082/foglamp/schedule/ac6dd55d-f55d-44f7-8741-984604bf2384
    """

    try:
        schedule_id = request.match_info.get('schedule_id', None)

        if not schedule_id:
            raise web.HTTPBadRequest(reason='Schedule ID is required.')

        try:
            assert uuid.UUID(schedule_id)
        except ValueError as ex:
            raise web.HTTPNotFound(reason="Invalid Schedule ID {}".format(schedule_id))

        sch = await server.Server.scheduler.get_schedule(uuid.UUID(schedule_id))

        schedule = {
            'id': str(sch.schedule_id),
            'name': sch.name,
            'processName': sch.process_name,
            'type': Schedule.Type(int(sch.schedule_type)).name,
            'repeat': sch.repeat.total_seconds() if sch.repeat else 0,
            'time': (sch.time.hour * 60 * 60 + sch.time.minute * 60 + sch.time.second) if sch.time else 0,
            'day': sch.day,
            'exclusive': sch.exclusive
        }

        return web.json_response(schedule)
    except (ValueError, ScheduleNotFoundError) as ex:
        raise web.HTTPNotFound(reason=str(ex))


async def start_schedule(request):
    """
    Starts a given schedule

    :Example: curl -X POST  http://localhost:8082/foglamp/schedule/start/fd439e5b-86ba-499a-86d3-34a6e5754b5a
    """

    try:
        schedule_id = request.match_info.get('schedule_id', None)

        if not schedule_id:
            raise web.HTTPBadRequest(reason='Schedule ID is required.')

        try:
            assert uuid.UUID(schedule_id)
        except ValueError as ex:
            raise web.HTTPNotFound(reason="Invalid Schedule ID {}".format(schedule_id))

        sch = await server.Server.scheduler.get_schedule(uuid.UUID(schedule_id))

        # Start schedule
        await server.Server.scheduler.queue_task(uuid.UUID(schedule_id))

        return web.json_response({'id': schedule_id, 'message': 'Schedule started successfully'})
    except (ValueError, ScheduleNotFoundError) as ex:
        raise web.HTTPNotFound(reason=str(ex))


async def post_schedule(request):
    """
    Create a new schedule in schedules table

    :Example: curl -d '{"type": 3, "name": "sleep30test", "process_name": "sleep30", "repeat": "45"}'  -X POST  http://localhost:8082/foglamp/schedule
    """

    try:
        data = await request.json()

        schedule_id = data.get('schedule_id', None)
        if schedule_id:
            raise web.HTTPBadRequest(reason='Schedule ID not needed for new Schedule.')

        go_no_go = await _check_schedule_post_parameters(data)
        if len(go_no_go) != 0:
            raise ValueError("Errors in request: {} {}".format(','.join(go_no_go), len(go_no_go)))

        updated_schedule_id = await _execute_add_update_schedule(data)

        sch = await server.Server.scheduler.get_schedule(updated_schedule_id)

        schedule = {
            'id': str(sch.schedule_id),
            'name': sch.name,
            'processName': sch.process_name,
            'type': Schedule.Type(int(sch.schedule_type)).name,
            'repeat': sch.repeat.total_seconds() if sch.repeat else 0,
            'time': (sch.time.hour * 60 * 60 + sch.time.minute * 60 + sch.time.second) if sch.time else 0,
            'day': sch.day,
            'exclusive': sch.exclusive
        }

        return web.json_response({'schedule': schedule})
    except (ValueError, ScheduleNotFoundError) as ex:
        raise web.HTTPNotFound(reason=str(ex))


async def update_schedule(request):
    """ Update a schedule in schedules table

    :Example: curl -d '{"type": 4, "name": "sleep30 updated", "process_name": "sleep30", "repeat": "15"}'  -X PUT  http://localhost:8082/foglamp/schedule/84fe4ea1-df9c-4c87-bb78-cab2e7d5d2cc
    """

    try:
        data = await request.json()
        schedule_id = request.match_info.get('schedule_id', None)

        if not schedule_id:
            raise web.HTTPBadRequest(reason='Schedule ID is required.')

        try:
            assert uuid.UUID(schedule_id)
        except ValueError as ex:
            raise web.HTTPNotFound(reason="Invalid Schedule ID {}".format(schedule_id))

        sch = await server.Server.scheduler.get_schedule(uuid.UUID(schedule_id))
        if not sch:
            raise ValueError('No such Schedule: {}.'.format(schedule_id))

        curr_value = dict()
        curr_value['schedule_id'] = sch.schedule_id
        curr_value['schedule_process_name'] = sch.process_name
        curr_value['schedule_name'] = sch.name
        curr_value['schedule_type'] = sch.schedule_type
        curr_value['schedule_repeat'] = sch.repeat.total_seconds() if sch.repeat else 0
        curr_value['schedule_time'] = (sch.time.hour * 60 * 60 + sch.time.minute * 60 + sch.time.second) if sch.time else 0
        curr_value['schedule_day'] = sch.day
        curr_value['schedule_exclusive'] = sch.exclusive

        go_no_go = await _check_schedule_post_parameters(data, curr_value)
        if len(go_no_go) != 0:
            raise ValueError("Errors in request: {}".format(','.join(go_no_go)))

        updated_schedule_id = await _execute_add_update_schedule(data, curr_value)

        sch = await server.Server.scheduler.get_schedule(updated_schedule_id)

        schedule = {
            'id': str(sch.schedule_id),
            'name': sch.name,
            'processName': sch.process_name,
            'type': Schedule.Type(int(sch.schedule_type)).name,
            'repeat': sch.repeat.total_seconds() if sch.repeat else 0,
            'time': (sch.time.hour * 60 * 60 + sch.time.minute * 60 + sch.time.second) if sch.time else 0,
            'day': sch.day,
            'exclusive': sch.exclusive
        }

        return web.json_response({'schedule': schedule})
    except (ValueError, ScheduleNotFoundError) as ex:
        raise web.HTTPNotFound(reason=str(ex))


async def delete_schedule(request):
    """
    Delete a schedule from schedules table

    :Example: curl -X DELETE  http://localhost:8082/foglamp/schedule/dc9bfc01-066a-4cc0-b068-9c35486db87f
    """

    try:
        schedule_id = request.match_info.get('schedule_id', None)

        if not schedule_id:
            raise web.HTTPBadRequest(reason='Schedule ID is required.')

        try:
            assert uuid.UUID(schedule_id)
        except ValueError as ex:
            raise web.HTTPNotFound(reason="Invalid Schedule ID {}".format(schedule_id))

        await server.Server.scheduler.delete_schedule(uuid.UUID(schedule_id))

        return web.json_response({'message': 'Schedule deleted successfully', 'id': schedule_id})
    except (ValueError, ScheduleNotFoundError) as ex:
        raise web.HTTPNotFound(reason=str(ex))


async def get_schedule_type(request):
    """
    Args:
        request:

    Returns:
         an array of Schedule type enumeration key index values

    :Example: curl -X GET  http://localhost:8082/foglamp/schedule/type
    """

    results = []
    for _type in Schedule.Type:
        data = {'index': _type.value, 'name': _type.name}
        results.append(data)

    return web.json_response({'scheduleType': results})


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
            raise web.HTTPBadRequest(reason='Task ID is required.')

        try:
            assert uuid.UUID(task_id)
        except ValueError as ex:
            raise web.HTTPNotFound(reason="Invalid Task ID {}".format(task_id))

        tsk = await server.Server.scheduler.get_task(task_id)

        task = {
            'id': str(tsk.task_id),
            'processName': tsk.process_name,
            'state': Task.State(int(tsk.state)).name,
            'startTime': str(tsk.start_time),
            'endTime': str(tsk.end_time),
            'exitCode': tsk.exit_code,
            'reason': tsk.reason
        }

        return web.json_response(task)
    except (ValueError, TaskNotFoundError) as ex:
        raise web.HTTPNotFound(reason=str(ex))


async def get_tasks(request):
    """
    Returns the list of tasks

    :Example: curl -X GET  http://localhost:8082/foglamp/task
    :Example: curl -X GET  http://localhost:8082/foglamp/task?name=xxx
    :Example: curl -X GET  http://localhost:8082/foglamp/task?state=xxx
    :Example: curl -X GET  http://localhost:8082/foglamp/task?name=xxx&state=xxx
    """

    try:
        limit = request.query.get('limit') if 'limit' in request.query else '100'
        if limit:
            if not re.match("(^[0-9]*$)", limit):
                raise web.HTTPBadRequest(reason='This limit {} not permitted.'.format(limit))
            elif int(limit) > 100:
                limit = 100
            else:
                limit = int(limit)

        state = request.query.get('state') if 'state' in request.query else None
        if state:
            if state.upper() not in [t.name for t in list(Task.State)]:
                raise web.HTTPBadRequest(reason='This state value {} not permitted.'.format(state))
            else:
                z = dict()
                for i in list(Task.State):
                    z.update({i.name: i.value})
                state = z[state.upper()]

        name = request.query.get('name') if 'name' in request.query else None

        where_clause = None
        if name and state:
            where_clause = (["process_name", "=", name], ["state", "=", state])
        elif name:
            where_clause = ["process_name", "=", name]
        elif state:
            where_clause = ["state", "=", state]

        tasks = await server.Server.scheduler.get_tasks(where=where_clause, limit=limit)

        if len(tasks) == 0:
            raise TaskNotFoundError("No Tasks")

        new_tasks = []
        for task in tasks:
            new_tasks.append(
                {'id': str(task.task_id),
                 'processName': task.process_name,
                 'state': Task.State(int(task.state)).name,
                 'startTime': str(task.start_time),
                 'endTime': str(task.end_time),
                 'exitCode': task.exit_code,
                 'reason': task.reason
                 }
            )

        return web.json_response({'tasks': new_tasks})
    except (ValueError, TaskNotFoundError) as ex:
        raise web.HTTPNotFound(reason=str(ex))


async def get_tasks_latest(request):
    """
    Returns the list of the most recent task execution for each name from tasks table

    :Example: curl -X GET  http://localhost:8082/foglamp/task/latest
    :Example: curl -X GET  http://localhost:8082/foglamp/task/latest?name=xxx
    """

    try:
        name = request.query.get('name') if 'name' in request.query else None
        if name:
            payload = PayloadBuilder() \
                    .SELECT(("id", "process_name", "state", "start_time", "end_time", "reason", "pid", "exit_code")) \
                    .WHERE(["process_name", "=", name])\
                    .ORDER_BY(["start_time", "desc"]) \
                    .payload()
        else:
            payload = PayloadBuilder() \
                .SELECT(("id", "process_name", "state", "start_time", "end_time", "reason", "pid", "exit_code")) \
                .ORDER_BY(["process_name", "asc"], ["start_time", "desc"]) \
                .payload()
        _storage = connect.get_storage()
        results = _storage.query_tbl_with_payload('tasks', payload)

        tasks = []
        previous_process = None
        for row in results['rows']:
            if previous_process != row['process_name']:
                tasks.append(row)
                previous_process = row['process_name']

        new_tasks = []
        for task in tasks:
            new_tasks.append(
                {'id': str(task['id']),
                 'processName': task['process_name'],
                 'state': [t.name for t in list(Task.State)][int(task['state']) - 1],
                 'startTime': str(task['start_time']),
                 'endTime': str(task['end_time']),
                 'exitCode': task['exit_code'],
                 'reason': task['reason'],
                 'pid': task['pid']
                 }
            )
        return web.json_response({'tasks': new_tasks})
    except (ValueError, TaskNotFoundError) as ex:
        raise web.HTTPNotFound(reason=str(ex))


async def cancel_task(request):
    """Cancel a running task from tasks table

    :Example: curl -X GET  http://localhost:8082/foglamp/task/cancel/{task_id}
    """
    try:
        task_id = request.match_info.get('task_id', None)

        if not task_id:
            raise web.HTTPBadRequest(reason='Task ID is required.')

        try:
            assert uuid.UUID(task_id)
        except ValueError as ex:
            raise web.HTTPNotFound(reason="Invalid Task ID {}".format(task_id))

        task = await server.Server.scheduler.get_task(task_id)

        # Cancel Task
        await server.Server.scheduler.cancel_task(uuid.UUID(task_id))

        return web.json_response({'id': task_id, 'message': 'Task cancelled successfully'})
    except (ValueError, TaskNotFoundError) as ex:
        raise web.HTTPNotFound(reason=str(ex))


async def get_task_state(request):
    """
    Args:
        request:

    Returns:
         an array of Task State enumeration key index values

    :Example: curl -X GET  http://localhost:8082/foglamp/task/state
    """

    results = []
    for _state in Task.State:
        data = {'index': _state.value, 'name': _state.name}
        results.append(data)

    return web.json_response({'taskState': results})
