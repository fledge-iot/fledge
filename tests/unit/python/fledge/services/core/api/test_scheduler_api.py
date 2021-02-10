# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END


import asyncio
import json
from unittest.mock import MagicMock, patch, call
from datetime import timedelta, datetime
import uuid
import pytest

from aiohttp import web
from fledge.services.core import routes
from fledge.services.core import connect
from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.services.core import server
from fledge.services.core.scheduler.scheduler import Scheduler
from fledge.services.core.scheduler.entities import ScheduledProcess, Task, IntervalSchedule, TimedSchedule, StartUpSchedule, ManualSchedule
from fledge.services.core.scheduler.exceptions import *

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@asyncio.coroutine
def mock_coro_response(*args, **kwargs):
    if len(args) > 0:
        return args[0]
    else:
        return ""


@pytest.allure.feature("unit")
@pytest.allure.story("core", "api", "schedule")
class TestScheduledProcesses:

    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop)
        # fill the routes table
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    def setup_method(self):
        server.Server.scheduler = Scheduler(None, None)

    def teardown_method(self):
        server.Server.scheduler = None

    async def test_get_scheduled_processes(self, client):
        async def mock_coro():
            processes = []
            process = ScheduledProcess()
            process.name = "foo"
            process.script = "bar"
            processes.append(process)
            return processes

        with patch.object(server.Server.scheduler, 'get_scheduled_processes', return_value=mock_coro()):
            resp = await client.get('/fledge/schedule/process')
            assert 200 == resp.status
            result = await resp.text()
            json_response = json.loads(result)
        assert {'processes': ['foo']} == json_response

    async def test_get_scheduled_process(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        payload = '{"return": ["name"], "where": {"column": "name", "condition": "in", "value": ["purge"]}}'
        response = {'rows': [{'name': 'purge'}], 'count': 1}
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(storage_client_mock, 'query_tbl_with_payload',
                                  return_value=mock_coro_response(response)) as mock_storage_call:
                    resp = await client.get('/fledge/schedule/process/purge')
                    assert 200 == resp.status
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert 'purge' == json_response
                mock_storage_call.assert_called_with('scheduled_processes', payload)

    async def test_get_scheduled_process_bad_data(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        response = {'rows': [], 'count': 0}
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(storage_client_mock, 'query_tbl_with_payload',
                                  return_value=mock_coro_response(response)):
                    resp = await client.get('/fledge/schedule/process/bla')
                    assert 404 == resp.status
                    assert "No such Scheduled Process: ['bla']." == resp.reason

    async def test_post_scheduled_process(self, client):
        payload = {'process_name': 'manage', "script": '["tasks/manage"]'}
        storage_client_mock = MagicMock(StorageClientAsync)
        response = {'rows': [], 'count': 0}
        ret_val = {"response": "inserted", "rows_affected": 1}
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=mock_coro_response(response)
                              ) as query_tbl_patch:
                with patch.object(storage_client_mock, 'insert_into_tbl', return_value=mock_coro_response(ret_val)
                                  ) as insert_tbl_patch:
                    with patch.object(server.Server.scheduler, '_get_process_scripts',
                                      return_value=mock_coro_response(None)) as get_process_script_patch:
                        resp = await client.post('/fledge/schedule/process', data=json.dumps(payload))
                        assert 200 == resp.status
                        result = await resp.text()
                        json_response = json.loads(result)
                        assert {'message': '{} process name created successfully.'.format(
                            payload['process_name'])} == json_response
                    get_process_script_patch.assert_called_once_with()
                assert insert_tbl_patch.called
                args, kwargs = insert_tbl_patch.call_args_list[0]
                assert 'scheduled_processes' == args[0]
                assert {'name': 'manage', 'script': '["tasks/manage"]'} == json.loads(args[1])
            assert query_tbl_patch.called
            args, kwargs = query_tbl_patch.call_args_list[0]
            assert 'scheduled_processes' == args[0]
            assert {"return": ["name"], "where": {"column": "name", "condition": "=", "value": "manage"}
                    } == json.loads(args[1])

    @pytest.mark.parametrize("request_data, response_code, error_message", [
        ({}, 400, "Missing process_name property in payload."),
        ({"process_name": ""}, 400, "Missing script property in payload."),
        ({"script": ""}, 400, "Missing process_name property in payload."),
        ({"processName": "", "script": ""}, 400, "Missing process_name property in payload."),
        ({"process_name": "", "script": '["tasks/statistics"]'}, 400, "Process name cannot be empty."),
        ({"process_name": "new", "script": ""}, 400, "Script cannot be empty."),
        ({"process_name": " ", "script": '["tasks/statistics"]'}, 400, "Process name cannot be empty."),
        ({"process_name": " new", "script": " "}, 400, "Script cannot be empty."),
        ({"process_name": "purge", "script": '["tasks/purge"]'}, 400, "purge process name already exists.")
    ])
    async def test_post_scheduled_process_bad_data(self, client, request_data, response_code, error_message):
        storage_client_mock = MagicMock(StorageClientAsync)
        response = {'rows': [{"name": "purge"}], 'count': 1}
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=mock_coro_response(response)):
                resp = await client.post('/fledge/schedule/process', data=json.dumps(request_data))
                assert response_code == resp.status
                assert error_message == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {'message': error_message} == json_response


class TestSchedules:
    _random_uuid = uuid.uuid4()

    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop)
        # fill the routes table
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    def setup_method(self):
        server.Server.scheduler = Scheduler(None, None)

    def teardown_method(self):
        server.Server.scheduler = None

    async def test_get_schedules(self, client):
        async def mock_coro():
            schedules = []
            schedule = StartUpSchedule()
            schedule.schedule_id = "1"
            schedule.exclusive = True
            schedule.enabled = True
            schedule.name = "foo"
            schedule.process_name = "bar"
            schedule.repeat = timedelta(seconds=30)
            schedule.time = None
            schedule.day = None
            schedules.append(schedule)
            return schedules

        with patch.object(server.Server.scheduler, 'get_schedules', return_value=mock_coro()):
            resp = await client.get('/fledge/schedule')
            assert 200 == resp.status
            result = await resp.text()
            json_response = json.loads(result)
            assert {'schedules': [
                {'name': 'foo', 'day': None, 'type': 'STARTUP', 'processName': 'bar',
                 'time': 0, 'id': '1', 'exclusive': True, 'enabled': True, 'repeat': 30.0}
            ]} == json_response

    async def test_get_schedule(self, client):
        async def mock_coro():
            schedule = StartUpSchedule()
            schedule.schedule_id = self._random_uuid
            schedule.exclusive = True
            schedule.enabled = True
            schedule.name = "foo"
            schedule.process_name = "bar"
            schedule.repeat = timedelta(seconds=30)
            schedule.time = None
            schedule.day = None
            return schedule

        with patch.object(server.Server.scheduler, 'get_schedule', return_value=mock_coro()):
            resp = await client.get('/fledge/schedule/{}'.format(self._random_uuid))
            assert 200 == resp.status
            result = await resp.text()
            json_response = json.loads(result)
            assert {'id': str(self._random_uuid),
                    'name': 'foo', 'repeat': 30.0, 'enabled': True,
                    'processName': 'bar', 'type': 'STARTUP', 'day': None,
                    'time': 0, 'exclusive': True} == json_response

    async def test_get_schedule_bad_data(self, client):
            resp = await client.get('/fledge/schedule/{}'.format("bla"))
            assert 404 == resp.status
            assert 'Invalid Schedule ID bla' == resp.reason

    @pytest.mark.parametrize("exception_name, response_code, response_message", [
        (ScheduleNotFoundError(_random_uuid), 404, 'Schedule not found: {}'.format(_random_uuid)),
        (ValueError, 404, ''),
    ])
    async def test_get_schedule_exceptions(self, client, exception_name, response_code, response_message):
        with patch.object(server.Server.scheduler, 'get_schedule', side_effect=exception_name):
            resp = await client.get('/fledge/schedule/{}'.format(self._random_uuid))
            assert response_code == resp.status
            assert response_message == resp.reason

    async def test_enable_schedule(self, client):
        async def mock_coro():
            return True, "Schedule successfully enabled"

        with patch.object(server.Server.scheduler, 'enable_schedule', return_value=mock_coro()):
            resp = await client.put('/fledge/schedule/{}/enable'.format(self._random_uuid))
            assert 200 == resp.status
            result = await resp.text()
            json_response = json.loads(result)
            assert {'status': True, 'message': 'Schedule successfully enabled',
                    'scheduleId': '{}'.format(self._random_uuid)} == json_response

    async def test_enable_schedule_bad_data(self, client):
            resp = await client.put('/fledge/schedule/{}/enable'.format("bla"))
            assert 404 == resp.status
            assert 'Invalid Schedule ID bla' == resp.reason

    @pytest.mark.parametrize("exception_name, response_code, response_message", [
        (ScheduleNotFoundError(_random_uuid), 404, 'Schedule not found: {}'.format(_random_uuid)),
        (ValueError, 404, ''),
    ])
    async def test_enable_schedule_exceptions(self, client, exception_name, response_code, response_message):
        with patch.object(server.Server.scheduler, 'enable_schedule', side_effect=exception_name):
            resp = await client.put('/fledge/schedule/{}/enable'.format(self._random_uuid))
            assert response_code == resp.status
            assert response_message == resp.reason

    async def test_disable_schedule(self, client):
        async def mock_coro():
            return True, "Schedule successfully disabled"

        with patch.object(server.Server.scheduler, 'disable_schedule', return_value=mock_coro()):
            resp = await client.put('/fledge/schedule/{}/disable'.format(self._random_uuid))
            assert 200 == resp.status
            result = await resp.text()
            json_response = json.loads(result)
            assert {'status': True, 'message': 'Schedule successfully disabled',
                    'scheduleId': '{}'.format(self._random_uuid)} == json_response

    async def test_disable_schedule_bad_data(self, client):
            resp = await client.put('/fledge/schedule/{}/disable'.format("bla"))
            assert 404 == resp.status
            assert 'Invalid Schedule ID bla' == resp.reason

    @pytest.mark.parametrize("exception_name, response_code, response_message", [
        (ScheduleNotFoundError(_random_uuid), 404, 'Schedule not found: {}'.format(_random_uuid)),
        (ValueError, 404, ''),
    ])
    async def test_disable_schedule_exceptions(self, client, exception_name, response_code, response_message):
        with patch.object(server.Server.scheduler, 'disable_schedule', side_effect=exception_name):
            resp = await client.put('/fledge/schedule/{}/disable'.format(self._random_uuid))
            assert response_code == resp.status
            assert response_message == resp.reason

    @pytest.mark.parametrize("return_queue_task, expected_response", [
        (True, {'message': 'Schedule started successfully', 'id': '{}'.format(_random_uuid)}),
        (False, {'message': 'Schedule could not be started', 'id': '{}'.format(_random_uuid)}),
    ])
    async def test_start_schedule(self, client, return_queue_task, expected_response):
        async def mock_coro():
            return ""

        async def patch_queue_task(_resp):
            return _resp

        with patch.object(server.Server.scheduler, 'get_schedule', return_value=mock_coro()) as mock_get_schedule:
            with patch.object(server.Server.scheduler, 'queue_task', return_value=patch_queue_task(return_queue_task)) \
                    as mock_queue_task:
                resp = await client.post('/fledge/schedule/start/{}'.format(self._random_uuid))
                assert 200 == resp.status
                result = await resp.text()
                json_response = json.loads(result)
                assert expected_response == json_response
                mock_queue_task.assert_called_once_with(uuid.UUID('{}'.format(self._random_uuid)))
            mock_get_schedule.assert_called_once_with(uuid.UUID('{}'.format(self._random_uuid)))

    async def test_start_schedule_bad_data(self, client):
            resp = await client.post('/fledge/schedule/start/{}'.format("bla"))
            assert 404 == resp.status
            assert 'Invalid Schedule ID bla' == resp.reason

    @pytest.mark.parametrize("exception_name, response_code, response_message", [
        (ScheduleNotFoundError(_random_uuid), 404, 'Schedule not found: {}'.format(_random_uuid)),
        (NotReadyError(), 404, ''),
        (ValueError, 404, ''),
    ])
    async def test_start_schedule_exceptions(self, client, exception_name, response_code, response_message):
        with patch.object(server.Server.scheduler, 'get_schedule', side_effect=exception_name):
            resp = await client.post('/fledge/schedule/start/{}'.format(self._random_uuid))
            assert response_code == resp.status
            assert response_message == resp.reason

    @pytest.mark.parametrize("request_data, expected_response", [
        ({"type": 1, "name": "foo", "process_name": "bar"},
         {'schedule': {'type': 'STARTUP', 'day': None, 'name': 'foo', 'exclusive': True, 'enabled': True,
                       'id': '{}'.format(_random_uuid), 'processName': 'bar', 'time': 0, 'repeat': 0}}),
        ({"type": 2, "day": 1, "time": 10, "name": "foo", "process_name": "bar"},
         {'schedule': {'name': 'foo', 'processName': 'bar', 'time': 10, 'enabled': True,
                       'id': '{}'.format(_random_uuid), 'repeat': 0, 'exclusive': True, 'day': 1,
                       'type': 'TIMED'}}),
        ({"type": 3, "repeat": 15, "name": "foo", "process_name": "bar"},
         {'schedule': {'day': None, 'type': 'INTERVAL', 'exclusive': True, 'enabled': True, 'time': 0, 'repeat': 15.0,
                       'name': 'foo', 'id': '{}'.format(_random_uuid), 'processName': 'bar'}}),
        ({"type": 4, "name": "foo", "process_name": "bar"},
         {'schedule': {'day': None, 'enabled': True, 'repeat': 0, 'id': '{}'.format(_random_uuid),
                       'type': 'MANUAL', 'name': 'foo', 'exclusive': True, 'processName': 'bar', 'time': 0}}),
        ])
    async def test_post_schedule(self, client, request_data, expected_response):
        async def mock_coro():
            return ""

        async def mock_schedules():
            schedule1 = ManualSchedule()
            schedule1.schedule_id = self._random_uuid
            schedule1.exclusive = True
            schedule1.enabled = True
            schedule1.name = "bar"
            schedule1.process_name = "foo"

            schedule2 = IntervalSchedule()
            schedule2.schedule_id = self._random_uuid
            schedule2.repeat = timedelta(seconds=15)
            schedule2.exclusive = True
            schedule2.enabled = True
            schedule2.name = "stats collection"
            schedule2.process_name = "stats collector"
            return [schedule1, schedule2]

        async def mock_schedule(_type):
            if _type == 1:
                schedule = StartUpSchedule()
                schedule.repeat = None
                schedule.time = None
                schedule.day = None
            elif _type == 2:
                schedule = TimedSchedule()
                schedule.repeat = None
                schedule.time = datetime(1, 1, 1, 0, 0, 10)
                schedule.day = 1
            elif _type == 3:
                schedule = IntervalSchedule()
                schedule.repeat = timedelta(seconds=15)
                schedule.time = None
                schedule.day = None
            else:
                schedule = ManualSchedule()
                schedule.repeat = None
                schedule.time = None
                schedule.day = None
            schedule.schedule_id = self._random_uuid
            schedule.exclusive = True
            schedule.enabled = True
            schedule.name = "foo"
            schedule.process_name = "bar"
            return schedule

        storage_client_mock = MagicMock(StorageClientAsync)
        response = {'rows': [{'name': 'p1'}], 'count': 1}
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=mock_coro_response(response)):
                with patch.object(server.Server.scheduler, 'get_schedules',
                                  return_value=mock_schedules()) as patch_get_schedules:
                    with patch.object(server.Server.scheduler, 'get_schedule',
                                      return_value=mock_schedule(request_data["type"])) as patch_get_schedule:
                        with patch.object(server.Server.scheduler, 'save_schedule',
                                          return_value=mock_coro()) as patch_save_schedule:
                            resp = await client.post('/fledge/schedule', data=json.dumps(request_data))
                            assert 200 == resp.status
                            result = await resp.text()
                            json_response = json.loads(result)
                            assert expected_response == json_response
                        assert 1 == patch_save_schedule.call_count
                    patch_get_schedule.assert_called_once_with(None)
                patch_get_schedules.assert_called_once_with()

    async def test_post_schedule_bad_param(self, client):
        resp = await client.post('/fledge/schedule', data=json.dumps({'schedule_id': 'bla'}))
        assert 400 == resp.status
        assert 'Schedule ID not needed for new Schedule.' == resp.reason
        result = await resp.text()
        json_response = json.loads(result)
        assert {'message': 'Schedule ID not needed for new Schedule.'} == json_response

    @pytest.mark.parametrize("request_data, response_code, error_message, storage_return", [
        ({"type": 'bla'}, 400, "Error in type: bla", {'rows': [{'name': 'bla'}], 'count': 1}),
        ({"day": 'bla'}, 400, "Error in day: bla", {'rows': [{'name': 'bla'}], 'count': 1}),
        ({"time": 'bla'}, 400, "Error in time: bla", {'rows': [{'name': 'bla'}], 'count': 1}),
        ({"repeat": 'bla'}, 400, "Error in repeat: bla", {'rows': [{'name': 'bla'}], 'count': 1}),
        ({"type": 2, "name": "sch1", "process_name": "p1"}, 400,
         "Errors in request: Schedule time cannot be empty for TIMED schedule. 1",
         {'rows': [{'name': 'bla'}], 'count': 1}),
        ({"type": 2, "day": 9, "time": 1, "name": "sch1", "process_name": "p1"}, 400,
         "Errors in request: Day must either be None or must be an integer and in range 1-7. 1",
         {'rows': [{'name': 'bla'}], 'count': 1}),
        ({"type": 2, "day": 5, "time": -1, "name": "sch1", "process_name": "p1"}, 400,
         "Errors in request: Time must be an integer and in range 0-86399. 1",
         {'rows': [{'name': 'bla'}], 'count': 1}),
        ({"type": 200}, 400,
         "Errors in request: Schedule type error: 200,Schedule name and Process name cannot be empty. 2",
         {'rows': [{'name': 'bla'}], 'count': 1}),
        ({"type": 1, "name": "sch1", "process_name": "p1"}, 404,
         "No such Scheduled Process name: p1",
         {'rows': [], 'count': 0}),
    ])
    async def test_post_schedule_bad_data(self, client, request_data, response_code, error_message, storage_return):
        storage_client_mock = MagicMock(StorageClientAsync)
        response = storage_return
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=mock_coro_response(response)):
                resp = await client.post('/fledge/schedule', data=json.dumps(request_data))
                assert response_code == resp.status
                assert error_message == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {'message': error_message} == json_response

    @pytest.mark.parametrize("request_data", [
        {"type": 4, "name": "purge", "process_name": "purge", "repeat": "45"},
        {"type": 1, "name": "Sine", "process_name": "south_c",  "repeat": 0}
    ])
    async def test_duplicate_post_schedule(self, client, request_data):
        async def mock_schedules():
            schedule1 = ManualSchedule()
            schedule1.schedule_id = self._random_uuid
            schedule1.exclusive = True
            schedule1.enabled = True
            schedule1.name = "purge"
            schedule1.process_name = "purge"

            schedule2 = StartUpSchedule()
            schedule2.schedule_id = self._random_uuid
            schedule2.exclusive = True
            schedule2.enabled = True
            schedule2.name = "Sine"
            schedule2.process_name = "south_c"

            schedule3 = IntervalSchedule()
            schedule3.schedule_id = self._random_uuid
            schedule3.repeat = timedelta(seconds=15)
            schedule3.exclusive = True
            schedule3.enabled = True
            schedule3.name = "stats collection"
            schedule3.process_name = "stats collector"

            return [schedule1, schedule2, schedule3]

        storage_client_mock = MagicMock(StorageClientAsync)
        response = {'rows': [{'name': 'purge'}, {'name': 'south_c'}, {'name': 'stats collector'}], 'count': 3}
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=mock_coro_response(response)):
                with patch.object(server.Server.scheduler, 'get_schedules',
                                  return_value=mock_schedules()) as patch_get_schedules:
                    resp = await client.post('/fledge/schedule', data=json.dumps(request_data))
                    assert 409 == resp.status
                    assert "Duplicate schedule name entry found" == resp.reason
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert {'message': 'Duplicate schedule name entry found'} == json_response
                patch_get_schedules.assert_called_once_with()

    @pytest.mark.parametrize("request_data, expected_response", [
        ({"name": "new"},
         {'schedule': {'id': '{}'.format(_random_uuid), 'time': 0, 'processName': 'bar', 'repeat': 30.0,
                       'exclusive': True, 'enabled': True, 'type': 'STARTUP', 'day': None, 'name': 'new'}}),
        ])
    async def test_update_schedule(self, client, request_data, expected_response):
        async def mock_coro():
            return ""

        async def mock_schedules():
            schedule1 = ManualSchedule()
            schedule1.schedule_id = self._random_uuid
            schedule1.exclusive = True
            schedule1.enabled = True
            schedule1.name = "purge"
            schedule1.process_name = "purge"

            schedule2 = StartUpSchedule()
            schedule2.schedule_id = self._random_uuid
            schedule2.exclusive = True
            schedule2.enabled = True
            schedule2.name = "Sine"
            schedule2.process_name = "south_c"

            schedule3 = IntervalSchedule()
            schedule3.schedule_id = self._random_uuid
            schedule3.repeat = timedelta(seconds=15)
            schedule3.exclusive = True
            schedule3.enabled = True
            schedule3.name = "stats collection"
            schedule3.process_name = "stats collector"

            return [schedule1, schedule2, schedule3]

        async def mock_schedule(*args):
            schedule = StartUpSchedule()
            schedule.schedule_id = self._random_uuid
            schedule.exclusive = True
            schedule.enabled = True
            schedule.process_name = "bar"
            schedule.repeat = timedelta(seconds=30)
            schedule.time = None
            schedule.day = None
            schedule.name = "foo" if args[0] == 1 else "new"
            return schedule

        storage_client_mock = MagicMock(StorageClientAsync)
        response = {'rows': [{'name': 'p1'}], 'count': 1}
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=mock_coro_response(response)):
                with patch.object(server.Server.scheduler, 'get_schedules',
                                  return_value=mock_schedules()) as patch_get_schedules:
                    with patch.object(server.Server.scheduler, 'save_schedule',
                                      return_value=mock_coro()) as patch_save_schedule:
                        with patch.object(server.Server.scheduler, 'get_schedule',
                                          side_effect=mock_schedule) as patch_get_schedule:
                            resp = await client.put('/fledge/schedule/{}'.format(self._random_uuid),
                                                    data=json.dumps(request_data))
                            assert 200 == resp.status
                            result = await resp.text()
                            json_response = json.loads(result)
                            assert expected_response == json_response
                        assert 2 == patch_get_schedule.call_count
                        assert call(uuid.UUID(str(self._random_uuid))) == patch_get_schedule.call_args
                    arguments, kwargs = patch_save_schedule.call_args
                    assert isinstance(arguments[0], StartUpSchedule)
                patch_get_schedules.assert_called_once_with()

    async def test_update_schedule_bad_param(self, client):
        error_msg = 'Invalid Schedule ID bla'
        resp = await client.put('/fledge/schedule/{}'.format("bla"), data=json.dumps({"a": 1}))
        assert 400 == resp.status
        assert error_msg == resp.reason
        result = await resp.text()
        json_response = json.loads(result)
        assert {'message': error_msg} == json_response

    async def test_update_schedule_data_not_exist(self, client):
        async def mock_coro():
            return ""

        with patch.object(server.Server.scheduler, 'get_schedule',
                          return_value=mock_coro()) as patch_get_schedule:
            error_message = 'Schedule not found: {}'.format(self._random_uuid)
            resp = await client.put('/fledge/schedule/{}'.format(self._random_uuid), data=json.dumps({"a": 1}))
            assert 404 == resp.status
            assert error_message == resp.reason
            result = await resp.text()
            json_response = json.loads(result)
            assert {'message': error_message} == json_response
        patch_get_schedule.assert_called_once_with(uuid.UUID('{}'.format(self._random_uuid)))

    @pytest.mark.parametrize("request_data, response_code, error_message, storage_return", [
        ({"type": 'bla'}, 400, "Error in type: bla", {'rows': [{'name': 'bla'}], 'count': 1}),
        ({"day": 'bla'}, 400, "Error in day: bla", {'rows': [{'name': 'bla'}], 'count': 1}),
        ({"time": 'bla'}, 400, "Error in time: bla", {'rows': [{'name': 'bla'}], 'count': 1}),
        ({"repeat": 'bla'}, 400, "Error in repeat: bla", {'rows': [{'name': 'bla'}], 'count': 1}),
        ({"type": 2, "name": "sch1", "process_name": "p1"}, 400,
         "Errors in request: Schedule time cannot be empty for TIMED schedule.",
         {'rows': [{'name': 'bla'}], 'count': 1}),
        ({"type": 2, "day": 9, "time": 1, "name": "sch1", "process_name": "p1"}, 400,
         "Errors in request: Day must either be None or must be an integer and in range 1-7.",
         {'rows': [{'name': 'bla'}], 'count': 1}),
        ({"type": 2, "day": 5, "time": -1, "name": "sch1", "process_name": "p1"}, 400,
         "Errors in request: Time must be an integer and in range 0-86399.",
         {'rows': [{'name': 'bla'}], 'count': 1}),
        ({"type": 200}, 400,
         "Errors in request: Schedule type error: 200",
         {'rows': [{'name': 'bla'}], 'count': 1}),
        ({"type": 1, "name": "sch1", "process_name": "p1"}, 404,
         "No such Scheduled Process name: p1",
         {'rows': [], 'count': 0}),
    ])
    async def test_update_schedule_bad_data(self, client, request_data, response_code, error_message, storage_return):
        async def mock_coro():
            schedule = StartUpSchedule()
            schedule.schedule_id = self._random_uuid
            schedule.exclusive = True
            schedule.enabled = True
            schedule.name = "foo"
            schedule.process_name = "bar"
            schedule.repeat = timedelta(seconds=30)
            schedule.time = None
            schedule.day = None
            return schedule

        storage_client_mock = MagicMock(StorageClientAsync)
        response = storage_return
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=mock_coro_response(response)):
                with patch.object(server.Server.scheduler, 'get_schedule',
                                  return_value=mock_coro()) as patch_get_schedule:
                    resp = await client.put('/fledge/schedule/{}'.format(self._random_uuid),
                                            data=json.dumps(request_data))
                    assert response_code == resp.status
                    assert error_message == resp.reason
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert {'message': error_message} == json_response
                patch_get_schedule.assert_called_once_with(uuid.UUID(str(self._random_uuid)))

    @pytest.mark.parametrize("payload", [
        {'name': 'purge'},
        {'name': "purge", 'type': 3, 'repeat': 15, 'exclusive': 'true', 'enabled': 'true'},
        {'name': "purge", 'enabled': 'false'},
        {'name': "purge", 'enabled': 'true', 'repeat': 15},
    ])
    async def test_duplicate_name_update_schedule(self, client, payload):
        async def mock_schedules():
            schedule1 = ManualSchedule()
            schedule1.schedule_id = "2176eb68-7303-11e7-8cf7-a6006ad3dba0"
            schedule1.exclusive = True
            schedule1.enabled = True
            schedule1.name = "purge"
            schedule1.process_name = "purge"

            schedule2 = StartUpSchedule()
            schedule2.schedule_id = self._random_uuid
            schedule2.repeat = timedelta(seconds=15)
            schedule2.exclusive = True
            schedule2.enabled = True
            schedule2.name = "foo"
            schedule2.process_name = "bar"
            return [schedule1, schedule2]

        async def mock_schedule(*args):
            schedule = StartUpSchedule()
            schedule.schedule_id = self._random_uuid
            schedule.exclusive = True
            schedule.enabled = True
            schedule.process_name = "bar"
            schedule.repeat = timedelta(seconds=30)
            schedule.time = None
            schedule.day = None
            schedule.name = "foo" if args[0] == 1 else "new"
            return schedule

        storage_client_mock = MagicMock(StorageClientAsync)
        response = {'rows': [{'name': 'purge'}], 'count': 1}
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=mock_coro_response(response)):
                with patch.object(server.Server.scheduler, 'get_schedule',
                                  side_effect=mock_schedule) as patch_get_schedule:
                    with patch.object(server.Server.scheduler, 'get_schedules',
                                      return_value=mock_schedules()) as patch_get_schedules:
                        resp = await client.put('/fledge/schedule/{}'.format(self._random_uuid),
                                                data=json.dumps(payload))
                        assert 409 == resp.status
                        result = await resp.text()
                        json_response = json.loads(result)
                        assert {'message': 'Duplicate schedule name entry found'} == json_response
                    patch_get_schedules.assert_called_once_with()
                patch_get_schedule.assert_called_once_with(uuid.UUID(str(self._random_uuid)))

    async def test_delete_schedule(self, client):
        async def mock_coro():
            return True, "Schedule deleted successfully."

        with patch.object(server.Server.scheduler, 'delete_schedule', return_value=mock_coro()):
            resp = await client.delete('/fledge/schedule/{}'.format(self._random_uuid))
            assert 200 == resp.status
            result = await resp.text()
            json_response = json.loads(result)
            assert {'id': '{}'.format(self._random_uuid),
                    'message': 'Schedule deleted successfully.'} == json_response

    async def test_delete_schedule_bad_data(self, client):
            resp = await client.delete('/fledge/schedule/{}'.format("bla"))
            assert 404 == resp.status
            assert 'Invalid Schedule ID bla' == resp.reason

    @pytest.mark.parametrize("exception_name, response_code, response_message", [
        (ScheduleNotFoundError(_random_uuid), 404, 'Schedule not found: {}'.format(_random_uuid)),
        (NotReadyError(), 404, ''),
        (ValueError, 404, ''),
        (RuntimeWarning, 409, "Enabled Schedule {} cannot be deleted.".format(str(_random_uuid))),
    ])
    async def test_delete_schedule_exceptions(self, client, exception_name, response_code, response_message):
        with patch.object(server.Server.scheduler, 'delete_schedule', side_effect=exception_name):
            resp = await client.delete('/fledge/schedule/{}'.format(self._random_uuid))
            assert response_code == resp.status
            assert response_message == resp.reason

    async def test_get_schedule_type(self, client):
        resp = await client.get('/fledge/schedule/type')
        assert 200 == resp.status
        result = await resp.text()
        json_response = json.loads(result)
        assert {'scheduleType': [{'name': 'STARTUP', 'index': 1},
                                 {'name': 'TIMED', 'index': 2},
                                 {'name': 'INTERVAL', 'index': 3},
                                 {'name': 'MANUAL', 'index': 4}]} == json_response


class TestTasks:
    _random_uuid = uuid.uuid4()

    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop)
        # fill the routes table
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    def setup_method(self):
        server.Server.scheduler = Scheduler(None, None)

    def teardown_method(self):
        server.Server.scheduler = None

    async def test_get_task(self, client):
        async def mock_coro():
            task = Task()
            task.task_id = self._random_uuid
            task.state = Task.State.RUNNING
            task.start_time = None
            task.schedule_name = "bar"
            task.process_name = "bar"
            task.end_time = None
            task.exit_code = 0
            task.reason = None
            return task

        storage_client_mock = MagicMock(StorageClientAsync)
        response = {'count': 1, 'rows': [{'process_name': 'bla'}]}
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=mock_coro_response(response)):
                with patch.object(server.Server.scheduler, 'get_task', return_value=mock_coro()):
                    resp = await client.get('/fledge/task/{}'.format(self._random_uuid))
                    assert 200 == resp.status
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert {'startTime': 'None', 'reason': None,
                            'endTime': 'None', 'state': 'Running',
                            'name': 'bar', 'processName': 'bar', 'exitCode': 0,
                            'id': '{}'.format(self._random_uuid)} == json_response

    async def test_get_task_bad_data(self, client):
            resp = await client.get('/fledge/task/{}'.format("bla"))
            assert 404 == resp.status
            assert 'Invalid Task ID bla' == resp.reason

    @pytest.mark.parametrize("exception_name, response_code, response_message", [
        (TaskNotFoundError(_random_uuid), 404, 'Task not found: {}'.format(_random_uuid)),
        (ValueError, 404, ''),
    ])
    async def test_get_task_exceptions(self, client, exception_name, response_code, response_message):
        with patch.object(server.Server.scheduler, 'get_task', side_effect=exception_name):
            resp = await client.get('/fledge/task/{}'.format(self._random_uuid))
            assert response_code == resp.status
            assert response_message == resp.reason

    @pytest.mark.parametrize("request_params", [
        '',
        '?limit=1',
        '?name=bla',
        '?state=running',
        '?limit=1&name=bla&state=running',
    ])
    async def test_get_tasks(self, client, request_params):
        async def patch_get_tasks():
            tasks = []
            task = Task()
            task.task_id = self._random_uuid
            task.state = Task.State.RUNNING
            task.start_time = None
            task.schedule_name = "bla"
            task.process_name = "bla"
            task.end_time = None
            task.exit_code = 0
            task.reason = None
            tasks.append(task)
            return tasks

        storage_client_mock = MagicMock(StorageClientAsync)
        response = {'count': 1, 'rows': [{'process_name': 'bla'}]}
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=mock_coro_response(response)):
                with patch.object(server.Server.scheduler, 'get_tasks', return_value=patch_get_tasks()):
                    resp = await client.get('/fledge/task{}'.format(request_params))
                    assert 200 == resp.status
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert {'tasks': [{'state': 'Running', 'id': '{}'.format(self._random_uuid),
                                       'endTime': 'None', 'exitCode': 0,
                                       'startTime': 'None', 'reason': None, 'name': 'bla', 'processName': 'bla'}]} == json_response

    @pytest.mark.parametrize("request_params, response_code, response_message", [
        ('?limit=invalid', 400, "Limit must be a positive integer"),
        ('?limit=-1', 400, "Limit must be a positive integer"),
        ('?state=BLA', 400, "This state value 'BLA' not permitted."),
    ])
    async def test_get_tasks_exceptions(self, client, request_params, response_code, response_message):
        resp = await client.get('/fledge/task{}'.format(request_params))
        assert response_code == resp.status
        assert response_message == resp.reason

    async def test_get_tasks_no_task_exception(self, client):
        async def patch_get_tasks():
            tasks = []
            return tasks

        storage_client_mock = MagicMock(StorageClientAsync)
        response = {'count': 0, 'rows': []}
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=mock_coro_response(response)):
                with patch.object(server.Server.scheduler, 'get_tasks', return_value=patch_get_tasks()):
                    resp = await client.get('/fledge/task{}'.format('?name=bla&state=running'))
                    assert 404 == resp.status
                    assert "No Tasks found" == resp.reason

    @pytest.mark.parametrize("request_params", ['', '?name=bla'])
    async def test_get_tasks_latest(self, client, request_params):
        storage_client_mock = MagicMock(StorageClientAsync)
        response = {'count': 2, 'rows': [
            {'pid': '1', 'reason': '', 'exit_code': '0', 'id': '1',
             'process_name': 'bla', 'schedule_name': 'bla', 'end_time': '2018', 'start_time': '2018', 'state': '2'}]}
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=mock_coro_response(response)):
                resp = await client.get('/fledge/task/latest{}'.format(request_params))
                assert 200 == resp.status
                result = await resp.text()
                json_response = json.loads(result)
                assert {'tasks': [{'reason': '', 'name': 'bla', 'processName': 'bla',
                                   'state': 'Complete', 'exitCode': '0', 'endTime': '2018',
                                   'pid': '1', 'startTime': '2018', 'id': '1'}]} == json_response

    @pytest.mark.parametrize("request_params", ['', '?name=not_exist'])
    async def test_get_tasks_latest_no_task_exception(self, client, request_params):
        storage_client_mock = MagicMock(StorageClientAsync)
        response = {'count': 0, 'rows': []}
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=mock_coro_response(response)):
                resp = await client.get('/fledge/task/latest{}'.format(request_params))
                assert 404 == resp.status
                assert "No Tasks found" == resp.reason

    async def test_cancel_task(self, client):
        async def mock_coro():
            return "some valid values"

        with patch.object(server.Server.scheduler, 'get_task', return_value=mock_coro()):
            with patch.object(server.Server.scheduler, 'cancel_task', return_value=mock_coro()):
                resp = await client.put('/fledge/task/{}/cancel'.format(self._random_uuid))
                assert 200 == resp.status
                result = await resp.text()
                json_response = json.loads(result)
                assert {'id': '{}'.format(self._random_uuid),
                        'message': 'Task cancelled successfully'} == json_response

    async def test_cancel_task_bad_data(self, client):
            resp = await client.put('/fledge/task/{}/cancel'.format("bla"))
            assert 404 == resp.status
            assert 'Invalid Task ID {}'.format("bla") == resp.reason

    @pytest.mark.parametrize("exception_name, response_code, response_message", [
        (TaskNotFoundError(_random_uuid), 404, 'Task not found: {}'.format(_random_uuid)),
        (TaskNotRunningError(_random_uuid), 404, 'Task is not running: {}'.format(_random_uuid)),
        (ValueError, 404, ''),
    ])
    async def test_cancel_task_exceptions(self, client, exception_name, response_code, response_message):
        async def mock_coro():
            return ""

        with patch.object(server.Server.scheduler, 'get_task', return_value=mock_coro()):
            with patch.object(server.Server.scheduler, 'cancel_task', side_effect=exception_name):
                resp = await client.put('/fledge/task/{}/cancel'.format(self._random_uuid))
                assert response_code == resp.status
                assert response_message == resp.reason

    async def test_get_task_state(self, client):
        resp = await client.get('/fledge/task/state')
        assert 200 == resp.status
        result = await resp.text()
        json_response = json.loads(result)
        assert {'taskState': [
            {'name': 'Running', 'index': 1},
            {'name': 'Complete', 'index': 2},
            {'name': 'Canceled', 'index': 3},
            {'name': 'Interrupted', 'index': 4}]} == json_response
