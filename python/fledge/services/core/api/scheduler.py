# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge.readthedocs.io/
# FLEDGE_END

import json
import datetime
import uuid
from aiohttp import web
from fledge.services.core import server
from fledge.services.core.scheduler.entities import Schedule, StartUpSchedule, TimedSchedule, IntervalSchedule, \
    ManualSchedule, Task
from fledge.services.core.scheduler.exceptions import *
from fledge.common.storage_client.exceptions import StorageServerError
from fledge.services.core import connect
from fledge.common.storage_client.payload_builder import PayloadBuilder

__author__ = "Amarendra K. Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

__DEFAULT_LIMIT = 20

_help = """
    -------------------------------------------------------------------------------
    | GET  POST       | /fledge/schedule/process                                 |
    | GET             | /fledge/schedule/process/{scheduled_process_name}        |

    | GET POST        | /fledge/schedule                                         |
    | GET PUT DELETE  | /fledge/schedule/{schedule_id}                           |
    | PUT             | /fledge/schedule/{schedule_id}/enable                    |
    | PUT             | /fledge/schedule/{schedule_id}/disable                   |
    | PUT             | /fledge/schedule/enable                                  |
    | PUT             | /fledge/schedule/disable                                 |
    | POST            | /fledge/schedule/start/{schedule_id}                     |
    | GET             | /fledge/schedule/type                                    |

    | GET             | /fledge/task                                             |
    | GET             | /fledge/task/latest                                      |
    | GET             | /fledge/task/{task_id}                                   |
    | GET             | /fledge/task/state                                       |
    | PUT             | /fledge/task/{task_id}/cancel                            |
    -------------------------------------------------------------------------------
"""


#################################
# Scheduled_processes
#################################


async def get_scheduled_processes(request):
    """
    Returns:
            a list of all the defined scheduled_processes from scheduled_processes table

    :Example:
             curl -X GET http://localhost:8081/fledge/schedule/process
    """

    processes_list = await server.Server.scheduler.get_scheduled_processes()

    processes = []
    for proc in processes_list:
        processes.append(proc.name)

    return web.json_response({'processes': processes})


async def get_scheduled_process(request):
    """
    Returns:
            a list of all the defined scheduled_processes from scheduled_processes table

    :Example:
        curl -X GET http://localhost:8081/fledge/schedule/process/purge
        curl -X GET http://localhost:8081/fledge/schedule/process/purge%2Cbackup%2Crestore
        curl -X GET http://localhost:8081/fledge/schedule/process/purge%2Cbackup%2Cstats%20collector
    """

    scheduled_process_names = request.match_info.get('scheduled_process_name', None)
    scheduled_process_name = scheduled_process_names.split(',')
    payload = PayloadBuilder().SELECT("name").WHERE(["name", "in", scheduled_process_name]).payload()
    _storage = connect.get_storage_async()
    scheduled_process = await _storage.query_tbl_with_payload('scheduled_processes', payload)

    if len(scheduled_process['rows']) == 0:
        raise web.HTTPNotFound(reason='No such Scheduled Process: {}.'.format(scheduled_process_name))

    if len(scheduled_process['rows']) == 1:
        retval = scheduled_process['rows'][0].get("name")
    else:
        retval = scheduled_process['rows']
    return web.json_response(retval)


async def post_scheduled_process(request: web.Request) -> web.Response:
    """
    Create a new process name in scheduled_process table

    data:
            process_name - Name of scheduled process name
            script - path for the script

    :Example:
             curl -d '{"process_name": "sleep30", "script": "[services/test]"}' -sX POST  http://localhost:8081/fledge/schedule/process
    """
    data = await request.json()
    process_name = data.get('process_name', None)
    script = data.get('script', None)
    if process_name is None:
        msg = "Missing process_name property in payload."
        raise web.HTTPBadRequest(body=json.dumps({"message": msg}), reason=msg)
    if script is None:
        msg = "Missing script property in payload."
        raise web.HTTPBadRequest(body=json.dumps({"message": msg}), reason=msg)
    if len(process_name.strip()) == 0:
        msg = "Process name cannot be empty."
        raise web.HTTPBadRequest(body=json.dumps({"message": msg}), reason=msg)
    if len(script.strip()) == 0:
        msg = "Script cannot be empty."
        raise web.HTTPBadRequest(body=json.dumps({"message": msg}), reason=msg)

    # Check that the process name is not already registered
    payload = PayloadBuilder().SELECT("name").WHERE(['name', '=', process_name]).payload()
    storage = connect.get_storage_async()
    result = await storage.query_tbl_with_payload('scheduled_processes', payload)
    if result['count'] == 0:
        # Now first create the scheduled process entry for the new service
        payload = PayloadBuilder().INSERT(name=process_name, script=script).payload()
        try:
            await storage.insert_into_tbl("scheduled_processes", payload)
            # Update _process_scripts dict of scheduler
            server.Server.scheduler._process_scripts.update({process_name: script})
        except StorageServerError as err:
            msg = str(err)
            raise web.HTTPInternalServerError(body=json.dumps(
                {"message": "Storage error: {}".format(msg)}), reason=msg)
        except Exception as ex:
            msg = str(ex)
            raise web.HTTPInternalServerError(body=json.dumps(
                {"message": "Failed to create scheduled process. {}".format(msg)}), reason=msg)
        else:
            return web.json_response({"message": "{} process name created successfully.".format(process_name)})
    else:
        msg = '{} process name already exists.'.format(process_name)
        raise web.HTTPBadRequest(body=json.dumps({"message": msg}), reason=msg)


#################################
# Schedules
#################################


def _extract_args(data, curr_value):
    try:
        if 'type' in data and (not isinstance(data['type'], int) and not data['type'].isdigit()):
            raise ValueError('Error in type: {}'.format(data['type']))

        if 'day' in data:
            if isinstance(data['day'], float) or (isinstance(data['day'], str) and (data['day'].strip() != "" and not data['day'].isdigit())):
                raise ValueError('Error in day: {}'.format(data['day']))

        if 'time' in data and (not isinstance(data['time'], int) and not data['time'].isdigit()):
            raise ValueError('Error in time: {}'.format(data['time']))

        if 'repeat' in data and (not isinstance(data['repeat'], int) and not data['repeat'].isdigit()):
            raise ValueError('Error in repeat: {}'.format(data['repeat']))

        _schedule = dict()

        _schedule['schedule_id'] = curr_value['schedule_id'] if curr_value else None

        s_type = data.get('type') if 'type' in data else curr_value['schedule_type'] if curr_value else 0
        _schedule['schedule_type'] = int(s_type)

        s_day = data.get('day') if 'day' in data else curr_value['schedule_day'] if curr_value and curr_value[
            'schedule_day'] else None
        _schedule['schedule_day'] = int(s_day) if s_day is not None and (
            isinstance(s_day, int) or (not isinstance(s_day, int) and s_day.isdigit())) else None

        s_time = data.get('time') if 'time' in data else curr_value['schedule_time'] if curr_value and curr_value[
            'schedule_time'] else 0
        _schedule['schedule_time'] = int(s_time)

        s_repeat = data.get('repeat') if 'repeat' in data else curr_value['schedule_repeat'] if curr_value and \
                                                                                                curr_value[
                                                                                                    'schedule_repeat'] else 0
        _schedule['schedule_repeat'] = int(s_repeat)

        _schedule['schedule_name'] = data.get('name') if 'name' in data else curr_value[
            'schedule_name'] if curr_value else None

        _schedule['schedule_process_name'] = data.get('process_name') if 'process_name' in data else curr_value[
            'schedule_process_name'] if curr_value else None

        _schedule['schedule_exclusive'] = data.get('exclusive') if 'exclusive' in data else curr_value[
            'schedule_exclusive'] if curr_value else 'True'
        _schedule['schedule_exclusive'] = 'True' if (
            (type(_schedule['schedule_exclusive']) is str and _schedule['schedule_exclusive'].lower() in ['t', 'true']) or (
            (type(_schedule['schedule_exclusive']) is bool and _schedule['schedule_exclusive'] is True))) else 'False'

        _schedule['schedule_enabled'] = data.get('enabled') if 'enabled' in data else curr_value[
            'schedule_enabled'] if curr_value else 'True'
        _schedule['schedule_enabled'] = 'True' if (
            (type(_schedule['schedule_enabled']) is str and _schedule['schedule_enabled'].lower() in ['t', 'true']) or (
            (type(_schedule['schedule_enabled']) is bool and _schedule['schedule_enabled'] is True))) else 'False'

        _schedule['is_enabled_modified'] = None
        if 'enabled' in data:
            _schedule['is_enabled_modified'] = True if _schedule['schedule_enabled'] == 'True' else False

    except ValueError as ex:
        raise web.HTTPBadRequest(reason=str(ex))

    return _schedule


async def _check_schedule_post_parameters(data, curr_value=None):
    """
    Private method to validate post data for creating a new schedule or updating an existing schedule

    Args:
         data:

    Returns:
            list errors
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
        if not _schedule.get('schedule_time'):
            _errors.append('Schedule time cannot be empty for TIMED schedule.')
        if _schedule.get('schedule_day') is not None and (not isinstance(_schedule.get('schedule_day'), int) or (
                _schedule.get('schedule_day') < 1 or _schedule.get('schedule_day') > 7)):
            _errors.append('Day must either be None or must be an integer and in range 1-7.')
        if not isinstance(_schedule.get('schedule_time'), int) or (
                _schedule.get('schedule_time') < 0 or _schedule.get('schedule_time') > 86399):
            _errors.append('Time must be an integer and in range 0-86399.')

    # Raise error if repeat is missing or is non integers
    if _schedule.get('schedule_type') == Schedule.Type.INTERVAL:
        if 'schedule_repeat' not in _schedule:
            _errors.append('Repeat is required for INTERVAL Schedule type.')
        elif not isinstance(_schedule.get('schedule_repeat'), int):
            _errors.append('Repeat must be an integer.')

    # Raise error if day is non integer
    if _schedule.get('schedule_day') is not None and not isinstance(_schedule.get('schedule_day'), int):
        _errors.append('Day must either be None or must be an integer.')

    # Raise error if time is non integer
    if not isinstance(_schedule.get('schedule_time'), int):
        _errors.append('Time must be an integer.')

    # Raise error if repeat is non integer
    if not isinstance(_schedule.get('schedule_repeat'), int):
        _errors.append('Repeat must be an integer.')

    # Raise error if name and process_name are missing for a new schedule
    if not _schedule.get('schedule_name') or not _schedule.get('schedule_process_name'):
        _errors.append('Schedule name and Process name cannot be empty.')

    # Raise error if scheduled_process name is wrong
    payload = PayloadBuilder().SELECT("name").WHERE(["name", "=", _schedule.get('schedule_process_name')]).payload()
    _storage = connect.get_storage_async()
    scheduled_process = await _storage.query_tbl_with_payload('scheduled_processes', payload)

    if len(scheduled_process['rows']) == 0:
        raise ScheduleProcessNameNotFoundError('No such Scheduled Process name: {}'.format(_schedule.get('schedule_process_name')))

    # Raise error if exclusive is wrong
    if _schedule.get('schedule_exclusive') not in ['True', 'False']:
        _errors.append('Schedule exclusive error: {}'.format(_schedule.get('schedule_exclusive')))

    # Raise error if enabled is wrong
    if _schedule.get('schedule_enabled') not in ['True', 'False']:
        _errors.append('Schedule enabled error: {}'.format(_schedule.get('schedule_enabled')))

    return _errors


async def _execute_add_update_schedule(data, curr_value=None):
    """
    Private method common to create a new schedule and update an existing schedule

    Args:
         data:

    Returns:
            schedule_id (new for created, existing for updated)
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
    schedule.enabled = True if _schedule.get('schedule_enabled') == 'True' else False

    # Save schedule
    await server.Server.scheduler.save_schedule(schedule, _schedule['is_enabled_modified'])

    updated_schedule_id = schedule.schedule_id

    return updated_schedule_id


async def get_schedules(request):
    """
    Returns:
            a list of all the defined schedules from schedules table

    :Example:
             curl -X GET http://localhost:8081/fledge/schedule
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
            'exclusive': sch.exclusive,
            'enabled': sch.enabled
        })

    return web.json_response({'schedules': schedules})


async def get_schedule(request):
    """
    Returns:
          the information for the given schedule from schedules table

    :Example:
            curl -X GET  http://localhost:8081/fledge/schedule/2176eb68-7303-11e7-8cf7-a6006ad3dba0
    """

    try:
        schedule_id = request.match_info.get('schedule_id', None)

        try:
            assert uuid.UUID(schedule_id)
        except ValueError as ex:
            raise web.HTTPNotFound(reason="Invalid Schedule ID {}".format(schedule_id))

        sch = await server.Server.scheduler.get_schedule(uuid.UUID(schedule_id))

        schedule = {
            'id': str(sch.schedule_id),
            'name': sch.name,
            "processName": sch.process_name,
            'type': Schedule.Type(int(sch.schedule_type)).name,
            'repeat': sch.repeat.total_seconds() if sch.repeat else 0,
            'time': (sch.time.hour * 60 * 60 + sch.time.minute * 60 + sch.time.second) if sch.time else 0,
            'day': sch.day,
            'exclusive': sch.exclusive,
            'enabled': sch.enabled
        }

        return web.json_response(schedule)
    except (ValueError, ScheduleNotFoundError) as ex:
        raise web.HTTPNotFound(reason=str(ex))


async def enable_schedule_with_name(request):
    """ Enables the schedule for given schedule_name or schedule_id in request payload

    curl -X PUT http://localhost:8081/fledge/schedule/enable  -d '{"schedule_name": "a schedule name"}'

    :param request: {"schedule_name": "sinusoid"} or {"schedule_id": "uuid of schedule"}
    :return:
    """
    try:
        data = await request.json()

        sch_name = data.get('schedule_name', None)
        sch_id = data.get('schedule_id', None)

        if not sch_name and not sch_id:
            raise web.HTTPBadRequest(reason='Schedule name or ID is required')

        if sch_name and not sch_id:
            storage_client = connect.get_storage_async()
            payload = PayloadBuilder().SELECT("id").WHERE(['schedule_name', '=', sch_name]).payload()
            result = await storage_client.query_tbl_with_payload('schedules', payload)

            if int(result['count']):
                sch_id = result['rows'][0]['id']

        if sch_id:
            try:
                assert uuid.UUID(sch_id)
            except (TypeError, ValueError):
                raise web.HTTPNotFound(reason="No Schedule with ID {}".format(sch_id))

        status, reason = await server.Server.scheduler.enable_schedule(uuid.UUID(sch_id))

        schedule = {
            'scheduleId': sch_id,
            'status': status,
            'message': reason
        }

    except (KeyError, ValueError, ScheduleNotFoundError) as e:
        raise web.HTTPNotFound(reason=str(e))
    else:
        return web.json_response(schedule)


async def disable_schedule_with_name(request):
    """ Disable the schedule for given schedule_name or schedule_id in request payload

    curl -X PUT http://localhost:8081/fledge/schedule/disable -d '{"schedule_name": "a schedule name"}'

    :param request: {"schedule_name": "sinusoid"} or {"schedule_id": "uuid of schedule"}
    :return:
    """
    try:
        data = await request.json()

        sch_name = data.get('schedule_name', None)
        sch_id = data.get('schedule_id', None)

        if not sch_name and not sch_id:
            raise web.HTTPBadRequest(reason='Schedule name or ID is required')

        if sch_name and not sch_id:
            storage_client = connect.get_storage_async()
            payload = PayloadBuilder().SELECT("id").WHERE(['schedule_name', '=', sch_name]).payload()
            result = await storage_client.query_tbl_with_payload('schedules', payload)

            if int(result['count']):
                sch_id = result['rows'][0]['id']

        if sch_id:
            try:
                assert uuid.UUID(sch_id)
            except (TypeError, ValueError):
                raise web.HTTPNotFound(reason="No Schedule with ID {}".format(sch_id))

        status, reason = await server.Server.scheduler.disable_schedule(uuid.UUID(sch_id))

        schedule = {
            'scheduleId': sch_id,
            'status': status,
            'message': reason
        }

    except (KeyError, ValueError, ScheduleNotFoundError) as e:
        raise web.HTTPNotFound(reason=str(e))
    else:
        return web.json_response(schedule)


async def enable_schedule(request):
    """
    Enable the given schedule from schedules table

    :Example:
             curl -X PUT  http://localhost:8081/fledge/schedule/ac6dd55d-f55d-44f7-8741-984604bf2384/enable
    """

    try:
        schedule_id = request.match_info.get('schedule_id', None)

        try:
            assert uuid.UUID(schedule_id)
        except ValueError as ex:
            raise web.HTTPNotFound(reason="Invalid Schedule ID {}".format(schedule_id))

        status, reason = await server.Server.scheduler.enable_schedule(uuid.UUID(schedule_id))

        schedule = {
            'scheduleId': schedule_id,
            'status': status,
            'message': reason
        }

        return web.json_response(schedule)
    except (ValueError, ScheduleNotFoundError) as ex:
        raise web.HTTPNotFound(reason=str(ex))


async def disable_schedule(request):
    """
    Disable the given schedule from schedules table

    :Example:
             curl -X PUT  http://localhost:8081/fledge/schedule/ac6dd55d-f55d-44f7-8741-984604bf2384/disable
    """

    try:
        schedule_id = request.match_info.get('schedule_id', None)

        try:
            assert uuid.UUID(schedule_id)
        except ValueError as ex:
            raise web.HTTPNotFound(reason="Invalid Schedule ID {}".format(schedule_id))

        status, reason = await server.Server.scheduler.disable_schedule(uuid.UUID(schedule_id))

        schedule = {
            'scheduleId': schedule_id,
            'status': status,
            'message': reason
        }

        return web.json_response(schedule)
    except (ValueError, ScheduleNotFoundError) as ex:
        raise web.HTTPNotFound(reason=str(ex))


async def start_schedule(request):
    """
    Starts a given schedule

    :Example:
             curl -X POST  http://localhost:8081/fledge/schedule/start/fd439e5b-86ba-499a-86d3-34a6e5754b5a
    """

    try:
        schedule_id = request.match_info.get('schedule_id', None)

        try:
            assert uuid.UUID(schedule_id)
        except ValueError as ex:
            raise web.HTTPNotFound(reason="Invalid Schedule ID {}".format(schedule_id))

        await server.Server.scheduler.get_schedule(uuid.UUID(schedule_id))

        # Start schedule
        resp = await server.Server.scheduler.queue_task(uuid.UUID(schedule_id))

        if resp is True:
            return web.json_response({'id': schedule_id, 'message': 'Schedule started successfully'})
        else:
            return web.json_response({'id': schedule_id, 'message': 'Schedule could not be started'})

    except (ValueError, ScheduleNotFoundError, NotReadyError) as ex:
        raise web.HTTPNotFound(reason=str(ex))


async def post_schedule(request):
    """
    Create a new schedule in schedules table

    :Example:
             curl -d '{"type": 3, "name": "sleep30test", "process_name": "sleep30", "repeat": "45"}'  -X POST  http://localhost:8081/fledge/schedule
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
            "processName": sch.process_name,
            'type': Schedule.Type(int(sch.schedule_type)).name,
            'repeat': sch.repeat.total_seconds() if sch.repeat else 0,
            'time': (sch.time.hour * 60 * 60 + sch.time.minute * 60 + sch.time.second) if sch.time else 0,
            'day': sch.day,
            'exclusive': sch.exclusive,
            'enabled': sch.enabled
        }

        return web.json_response({'schedule': schedule})
    except (ScheduleNotFoundError, ScheduleProcessNameNotFoundError) as ex:
        raise web.HTTPNotFound(reason=str(ex))
    except ValueError as ex:
        raise web.HTTPBadRequest(reason=str(ex))


async def update_schedule(request):
    """
    Update a schedule in schedules table

    :Example:
             curl -d '{"type": 4, "name": "sleep30 updated", "process_name": "sleep30", "repeat": "15"}'  -X PUT  http://localhost:8081/fledge/schedule/84fe4ea1-df9c-4c87-bb78-cab2e7d5d2cc
    """

    try:
        data = await request.json()
        schedule_id = request.match_info.get('schedule_id', None)

        try:
            assert uuid.UUID(schedule_id)
        except ValueError as ex:
            raise web.HTTPNotFound(reason="Invalid Schedule ID {}".format(schedule_id))

        sch = await server.Server.scheduler.get_schedule(uuid.UUID(schedule_id))
        if not sch:
            raise ScheduleNotFoundError(schedule_id)

        curr_value = dict()
        curr_value['schedule_id'] = sch.schedule_id
        curr_value['schedule_process_name'] = sch.process_name
        curr_value['schedule_name'] = sch.name
        curr_value['schedule_type'] = sch.schedule_type
        curr_value['schedule_repeat'] = sch.repeat.total_seconds() if sch.repeat else 0
        curr_value['schedule_time'] = (sch.time.hour * 60 * 60 + sch.time.minute * 60 + sch.time.second) if sch.time else 0
        curr_value['schedule_day'] = sch.day
        curr_value['schedule_exclusive'] = sch.exclusive
        curr_value['schedule_enabled'] = sch.enabled

        go_no_go = await _check_schedule_post_parameters(data, curr_value)
        if len(go_no_go) != 0:
            raise ValueError("Errors in request: {}".format(','.join(go_no_go)))

        updated_schedule_id = await _execute_add_update_schedule(data, curr_value)

        sch = await server.Server.scheduler.get_schedule(updated_schedule_id)

        schedule = {
            'id': str(sch.schedule_id),
            'name': sch.name,
            "processName": sch.process_name,
            'type': Schedule.Type(int(sch.schedule_type)).name,
            'repeat': sch.repeat.total_seconds() if sch.repeat else 0,
            'time': (sch.time.hour * 60 * 60 + sch.time.minute * 60 + sch.time.second) if sch.time else 0,
            'day': sch.day,
            'exclusive': sch.exclusive,
            'enabled': sch.enabled
        }

        return web.json_response({'schedule': schedule})
    except (ScheduleNotFoundError, ScheduleProcessNameNotFoundError) as ex:
        raise web.HTTPNotFound(reason=str(ex))
    except ValueError as ex:
        raise web.HTTPBadRequest(reason=str(ex))


async def delete_schedule(request):
    """
    Delete a schedule from schedules table

    :Example:
             curl -X DELETE  http://localhost:8081/fledge/schedule/dc9bfc01-066a-4cc0-b068-9c35486db87f
    """

    try:
        schedule_id = request.match_info.get('schedule_id', None)

        try:
            assert uuid.UUID(schedule_id)
        except ValueError as ex:
            raise web.HTTPNotFound(reason="Invalid Schedule ID {}".format(schedule_id))

        retval, message = await server.Server.scheduler.delete_schedule(uuid.UUID(schedule_id))

        return web.json_response({'message': message, 'id': schedule_id})
    except RuntimeWarning:
        raise web.HTTPConflict(reason="Enabled Schedule {} cannot be deleted.".format(schedule_id))
    except (ValueError, ScheduleNotFoundError, NotReadyError) as ex:
        raise web.HTTPNotFound(reason=str(ex))


async def get_schedule_type(request):
    """
    Args:
        request:

    Returns:
         an array of Schedule type enumeration key index values

    :Example:
             curl -X GET  http://localhost:8081/fledge/schedule/type
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
    Returns:
            a task list

    :Example:
             curl -X GET  http://localhost:8081/fledge/task/{task_id}
    """

    try:
        task_id = request.match_info.get('task_id', None)

        try:
            assert uuid.UUID(task_id)
        except ValueError as ex:
            raise web.HTTPNotFound(reason="Invalid Task ID {}".format(task_id))

        tsk = await server.Server.scheduler.get_task(task_id)

        task = {
            'id': str(tsk.task_id),
            'name': tsk.schedule_name,
            'processName': tsk.process_name,
            'state': Task.State(int(tsk.state)).name.capitalize(),
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
    Returns:
            the list of tasks

    :Example:
             curl -X GET  http://localhost:8081/fledge/task

             curl -X GET  http://localhost:8081/fledge/task?limit=2

             curl -X GET  http://localhost:8081/fledge/task?name=xxx

             curl -X GET  http://localhost:8081/fledge/task?state=xxx

             curl -X GET  http://localhost:8081/fledge/task?name=xxx&state=xxx
    """
    try:
        limit = __DEFAULT_LIMIT
        if 'limit' in request.query and request.query['limit'] != '':
            try:
                limit = int(request.query['limit'])
                if limit < 0:
                    raise ValueError
            except ValueError:
                raise web.HTTPBadRequest(reason="Limit must be a positive integer")

        name = None
        if 'name' in request.query and request.query['name'] != '':
            name = request.query['name']

        state = None
        if 'state' in request.query and request.query['state'] != '':
            try:
                state = Task.State[request.query['state'].upper()].value
            except KeyError as ex:
                raise web.HTTPBadRequest(reason="This state value {} not permitted.".format(ex))

        where_clause = None
        if name and state:
            where_clause = (["schedule_name", "=", name], ["state", "=", state])
        elif name:
            where_clause = ["schedule_name", "=", name]
        elif state:
            where_clause = ["state", "=", state]

        tasks = await server.Server.scheduler.get_tasks(where=where_clause, limit=limit)

        if len(tasks) == 0:
            raise web.HTTPNotFound(reason="No Tasks found")

        new_tasks = []
        for task in tasks:
            new_tasks.append(
                {'id': str(task.task_id),
                 'name': task.schedule_name,
                 'processName': task.process_name,
                 'state': Task.State(int(task.state)).name.capitalize(),
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
    Returns:
            the list of the most recent task execution for each name from tasks table

    :Example:
              curl -X GET  http://localhost:8081/fledge/task/latest

              curl -X GET  http://localhost:8081/fledge/task/latest?name=xxx
    """
    payload = PayloadBuilder().SELECT("id", "schedule_name", "process_name", "state", "start_time", "end_time", "reason", "pid", "exit_code")\
        .ALIAS("return", ("start_time", 'start_time'), ("end_time", 'end_time'))\
        .FORMAT("return", ("start_time", "YYYY-MM-DD HH24:MI:SS.MS"), ("end_time", "YYYY-MM-DD HH24:MI:SS.MS"))\
        .ORDER_BY(["schedule_name", "asc"], ["start_time", "desc"])

    if 'name' in request.query and request.query['name'] != '':
        name = request.query['name']
        payload.WHERE(["schedule_name", "=", name])

    try:
        _storage = connect.get_storage_async()
        results = await _storage.query_tbl_with_payload('tasks', payload.payload())

        if len(results['rows']) == 0:
            raise web.HTTPNotFound(reason="No Tasks found")

        tasks = []
        previous_schedule = None
        for row in results['rows']:
            if not row['schedule_name'].strip():
                continue
            if previous_schedule != row['schedule_name']:
                tasks.append(row)
                previous_schedule = row['schedule_name']

        new_tasks = []
        for task in tasks:
            new_tasks.append(
                {'id': str(task['id']),
                 'name': task['schedule_name'],
                 'processName': task['process_name'],
                 'state': [t.name.capitalize() for t in list(Task.State)][int(task['state']) - 1],
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

    :Example:
             curl -X PUT  http://localhost:8081/fledge/task/{task_id}/cancel
    """
    try:
        task_id = request.match_info.get('task_id', None)

        try:
            assert uuid.UUID(task_id)
        except ValueError as ex:
            raise web.HTTPNotFound(reason="Invalid Task ID {}".format(task_id))

        await server.Server.scheduler.get_task(task_id)

        # Cancel Task
        await server.Server.scheduler.cancel_task(uuid.UUID(task_id))

        return web.json_response({'id': task_id, 'message': 'Task cancelled successfully'})
    except (ValueError, TaskNotFoundError, TaskNotRunningError) as ex:
        raise web.HTTPNotFound(reason=str(ex))


async def get_task_state(request):
    """
    Returns:
            an array of Task State enumeration key index values

    :Example:
             curl -X GET  http://localhost:8081/fledge/task/state
    """

    results = []
    for _state in Task.State:
        data = {'index': _state.value, 'name': _state.name.capitalize()}
        results.append(data)

    return web.json_response({'taskState': results})
