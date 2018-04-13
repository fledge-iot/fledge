# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


import json
from unittest.mock import MagicMock, patch, call
from datetime import timedelta, datetime
import uuid
import pytest

from aiohttp import web
from foglamp.services.core import routes
from foglamp.services.core import connect
from foglamp.common.storage_client.storage_client import StorageClient
from foglamp.services.core import server
from foglamp.services.core.scheduler.scheduler import Scheduler
from foglamp.services.core.scheduler.entities import ScheduledProcess, Task, IntervalSchedule, TimedSchedule, StartUpSchedule, ManualSchedule
from foglamp.services.core.scheduler.exceptions import *

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


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
            resp = await client.get('/foglamp/schedule/process')
            assert 200 == resp.status
            result = await resp.text()
            json_response = json.loads(result)
        assert {'processes': ['foo']} == json_response

    async def test_get_scheduled_process(self, client):
        storage_client_mock = MagicMock(StorageClient)
        payload = '{"return": ["name"], "where": {"column": "name", "condition": "=", "value": "purge"}}'
        response = {'rows': [{'name': 'purge'}], 'count': 1}
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
                with patch.object(storage_client_mock, 'query_tbl_with_payload',
                                  return_value=response) as mock_storage_call:
                    resp = await client.get('/foglamp/schedule/process/purge')
                    assert 200 == resp.status
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert 'purge' == json_response
                mock_storage_call.assert_called_with('scheduled_processes', payload)

    async def test_get_scheduled_process_bad_data(self, client):
        storage_client_mock = MagicMock(StorageClient)
        response = {'rows': [], 'count': 0}
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
                with patch.object(storage_client_mock, 'query_tbl_with_payload',
                                  return_value=response):
                    resp = await client.get('/foglamp/schedule/process/bla')
                    assert 404 == resp.status
                    assert 'No such Scheduled Process: bla.' == resp.reason


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
            resp = await client.get('/foglamp/schedule')
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
            resp = await client.get('/foglamp/schedule/{}'.format(self._random_uuid))
            assert 200 == resp.status
            result = await resp.text()
            json_response = json.loads(result)
            assert {'id': str(self._random_uuid),
                    'name': 'foo', 'repeat': 30.0, 'enabled': True,
                    'processName': 'bar', 'type': 'STARTUP', 'day': None,
                    'time': 0, 'exclusive': True} == json_response

    async def test_get_schedule_bad_data(self, client):
            resp = await client.get('/foglamp/schedule/{}'.format("bla"))
            assert 404 == resp.status
            assert 'Invalid Schedule ID bla' == resp.reason

    @pytest.mark.parametrize("exception_name, response_code, response_message", [
        (ScheduleNotFoundError(_random_uuid), 404, 'Schedule not found: {}'.format(_random_uuid)),
        (ValueError, 404, None),
    ])
    async def test_get_schedule_exceptions(self, client, exception_name, response_code, response_message):
        with patch.object(server.Server.scheduler, 'get_schedule', side_effect=exception_name):
            resp = await client.get('/foglamp/schedule/{}'.format(self._random_uuid))
            assert response_code == resp.status
            assert response_message == resp.reason

    async def test_enable_schedule(self, client):
        async def mock_coro():
            return True, "Schedule successfully enabled"

        with patch.object(server.Server.scheduler, 'enable_schedule', return_value=mock_coro()):
            resp = await client.put('/foglamp/schedule/{}/enable'.format(self._random_uuid))
            assert 200 == resp.status
            result = await resp.text()
            json_response = json.loads(result)
            assert {'status': True, 'message': 'Schedule successfully enabled',
                    'scheduleId': '{}'.format(self._random_uuid)} == json_response

    async def test_enable_schedule_bad_data(self, client):
            resp = await client.put('/foglamp/schedule/{}/enable'.format("bla"))
            assert 404 == resp.status
            assert 'Invalid Schedule ID bla' == resp.reason

    @pytest.mark.parametrize("exception_name, response_code, response_message", [
        (ScheduleNotFoundError(_random_uuid), 404, 'Schedule not found: {}'.format(_random_uuid)),
        (ValueError, 404, None),
    ])
    async def test_enable_schedule_exceptions(self, client, exception_name, response_code, response_message):
        with patch.object(server.Server.scheduler, 'enable_schedule', side_effect=exception_name):
            resp = await client.put('/foglamp/schedule/{}/enable'.format(self._random_uuid))
            assert response_code == resp.status
            assert response_message == resp.reason

    async def test_disable_schedule(self, client):
        async def mock_coro():
            return True, "Schedule successfully disabled"

        with patch.object(server.Server.scheduler, 'disable_schedule', return_value=mock_coro()):
            resp = await client.put('/foglamp/schedule/{}/disable'.format(self._random_uuid))
            assert 200 == resp.status
            result = await resp.text()
            json_response = json.loads(result)
            assert {'status': True, 'message': 'Schedule successfully disabled',
                    'scheduleId': '{}'.format(self._random_uuid)} == json_response

    async def test_disable_schedule_bad_data(self, client):
            resp = await client.put('/foglamp/schedule/{}/disable'.format("bla"))
            assert 404 == resp.status
            assert 'Invalid Schedule ID bla' == resp.reason

    @pytest.mark.parametrize("exception_name, response_code, response_message", [
        (ScheduleNotFoundError(_random_uuid), 404, 'Schedule not found: {}'.format(_random_uuid)),
        (ValueError, 404, None),
    ])
    async def test_disable_schedule_exceptions(self, client, exception_name, response_code, response_message):
        with patch.object(server.Server.scheduler, 'disable_schedule', side_effect=exception_name):
            resp = await client.put('/foglamp/schedule/{}/disable'.format(self._random_uuid))
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
                resp = await client.post('/foglamp/schedule/start/{}'.format(self._random_uuid))
                assert 200 == resp.status
                result = await resp.text()
                json_response = json.loads(result)
                assert expected_response == json_response
                mock_queue_task.assert_called_once_with(uuid.UUID('{}'.format(self._random_uuid)))
            mock_get_schedule.assert_called_once_with(uuid.UUID('{}'.format(self._random_uuid)))

    async def test_start_schedule_bad_data(self, client):
            resp = await client.post('/foglamp/schedule/start/{}'.format("bla"))
            assert 404 == resp.status
            assert 'Invalid Schedule ID bla' == resp.reason

    @pytest.mark.parametrize("exception_name, response_code, response_message", [
        (ScheduleNotFoundError(_random_uuid), 404, 'Schedule not found: {}'.format(_random_uuid)),
        (NotReadyError(), 404, None),
        (ValueError, 404, None),
    ])
    async def test_start_schedule_exceptions(self, client, exception_name, response_code, response_message):
        with patch.object(server.Server.scheduler, 'get_schedule', side_effect=exception_name):
            resp = await client.post('/foglamp/schedule/start/{}'.format(self._random_uuid))
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

        storage_client_mock = MagicMock(StorageClient)
        response = {'rows': [{'name': 'p1'}], 'count': 1}
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=response):
                with patch.object(server.Server.scheduler, 'save_schedule', return_value=mock_coro()) \
                        as patch_save_schedule:
                    with patch.object(server.Server.scheduler, 'get_schedule',
                                      return_value=mock_schedule(request_data["type"])) as patch_get_schedule:
                        resp = await client.post('/foglamp/schedule', data=json.dumps(request_data))
                        assert 200 == resp.status
                        result = await resp.text()
                        json_response = json.loads(result)
                        assert expected_response == json_response
                        patch_get_schedule.called_once_with()
                    patch_save_schedule.called_once_with()

    async def test_post_schedule_bad_param(self, client):
        resp = await client.post('/foglamp/schedule', data=json.dumps({'schedule_id': 'bla'}))
        assert 400 == resp.status
        assert 'Schedule ID not needed for new Schedule.' == resp.reason

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
        storage_client_mock = MagicMock(StorageClient)
        response = storage_return
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=response):
                resp = await client.post('/foglamp/schedule', data=json.dumps(request_data))
                assert response_code == resp.status
                assert error_message == resp.reason

    @pytest.mark.parametrize("request_data, expected_response", [
        ({"name": "new"},
         {'schedule': {'id': '{}'.format(_random_uuid), 'time': 0, 'processName': 'bar', 'repeat': 30.0,
                       'exclusive': True, 'enabled': True, 'type': 'STARTUP', 'day': None, 'name': 'new'}}),
        ])
    async def test_update_schedule(self, client, request_data, expected_response):
        async def mock_coro():
            return ""

        async def mock_schedule(*args):
            schedule = StartUpSchedule()
            schedule.schedule_id = self._random_uuid
            schedule.exclusive = True
            schedule.enabled = True
            schedule.process_name = "bar"
            schedule.repeat = timedelta(seconds=30)
            schedule.time = None
            schedule.day = None
            if args[0] == 1:
                schedule.name = "foo"
            else:
                schedule.name = "new"
            return schedule

        storage_client_mock = MagicMock(StorageClient)
        response = {'rows': [{'name': 'p1'}], 'count': 1}
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=response):
                with patch.object(server.Server.scheduler, 'save_schedule', return_value=mock_coro()) \
                        as patch_save_schedule:
                    with patch.object(server.Server.scheduler, 'get_schedule',
                                      side_effect=mock_schedule) as patch_get_schedule:
                        resp = await client.put('/foglamp/schedule/{}'.format(self._random_uuid),
                                                data=json.dumps(request_data))
                        assert 200 == resp.status
                        result = await resp.text()
                        json_response = json.loads(result)
                        assert expected_response == json_response
                        assert 2 == patch_get_schedule.call_count
                        assert call(uuid.UUID(str(self._random_uuid))) == patch_get_schedule.call_args
                arguments, kwargs = patch_save_schedule.call_args
                assert isinstance(arguments[0], StartUpSchedule)

    async def test_update_schedule_bad_param(self, client):
        resp = await client.put('/foglamp/schedule/{}'.format("bla"), data=json.dumps({"a": 1}))
        assert 404 == resp.status
        assert 'Invalid Schedule ID bla' == resp.reason

    async def test_update_schedule_data_not_exist(self, client):
        async def mock_coro():
            return ""

        with patch.object(server.Server.scheduler, 'get_schedule',
                          return_value=mock_coro()) as patch_get_schedule:
            resp = await client.put('/foglamp/schedule/{}'.format(self._random_uuid), data=json.dumps({"a": 1}))
            assert 404 == resp.status
            assert 'Schedule not found: {}'.format(self._random_uuid) == resp.reason
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

        storage_client_mock = MagicMock(StorageClient)
        response = storage_return
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=response):
                with patch.object(server.Server.scheduler, 'get_schedule',
                                  return_value=mock_coro()) as patch_get_schedule:
                    resp = await client.put('/foglamp/schedule/{}'.format(self._random_uuid),
                                            data=json.dumps(request_data))
                    assert response_code == resp.status
                    assert error_message == resp.reason
                    patch_get_schedule.assert_called_once_with(uuid.UUID(str(self._random_uuid)))

    async def test_delete_schedule(self, client):
        async def mock_coro():
            return True, "Schedule deleted successfully."

        with patch.object(server.Server.scheduler, 'delete_schedule', return_value=mock_coro()):
            resp = await client.delete('/foglamp/schedule/{}'.format(self._random_uuid))
            assert 200 == resp.status
            result = await resp.text()
            json_response = json.loads(result)
            assert {'id': '{}'.format(self._random_uuid),
                    'message': 'Schedule deleted successfully.'} == json_response

    async def test_delete_schedule_bad_data(self, client):
            resp = await client.delete('/foglamp/schedule/{}'.format("bla"))
            assert 404 == resp.status
            assert 'Invalid Schedule ID bla' == resp.reason

    @pytest.mark.parametrize("exception_name, response_code, response_message", [
        (ScheduleNotFoundError(_random_uuid), 404, 'Schedule not found: {}'.format(_random_uuid)),
        (NotReadyError(), 404, None),
        (ValueError, 404, None),
        (RuntimeWarning, 409, "Enabled Schedule {} cannot be deleted.".format(str(_random_uuid))),
    ])
    async def test_delete_schedule_exceptions(self, client, exception_name, response_code, response_message):
        with patch.object(server.Server.scheduler, 'delete_schedule', side_effect=exception_name):
            resp = await client.delete('/foglamp/schedule/{}'.format(self._random_uuid))
            assert response_code == resp.status
            assert response_message == resp.reason

    async def test_get_schedule_type(self, client):
        resp = await client.get('/foglamp/schedule/type')
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
            task.process_name = "bar"
            task.end_time = None
            task.exit_code = 0
            task.reason = None
            return task

        storage_client_mock = MagicMock(StorageClient)
        response = {'count': 1, 'rows': [{'process_name': 'bla'}]}
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=response):
                with patch.object(server.Server.scheduler, 'get_task', return_value=mock_coro()):
                    resp = await client.get('/foglamp/task/{}'.format(self._random_uuid))
                    assert 200 == resp.status
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert {'startTime': 'None', 'reason': None,
                            'endTime': 'None', 'state': 'Running',
                            'name': 'bar', 'exitCode': 0,
                            'id': '{}'.format(self._random_uuid)} == json_response

    async def test_get_task_bad_data(self, client):
            resp = await client.get('/foglamp/task/{}'.format("bla"))
            assert 404 == resp.status
            assert 'Invalid Task ID bla' == resp.reason

    @pytest.mark.parametrize("exception_name, response_code, response_message", [
        (TaskNotFoundError(_random_uuid), 404, 'Task not found: {}'.format(_random_uuid)),
        (ValueError, 404, None),
    ])
    async def test_get_task_exceptions(self, client, exception_name, response_code, response_message):
        with patch.object(server.Server.scheduler, 'get_task', side_effect=exception_name):
            resp = await client.get('/foglamp/task/{}'.format(self._random_uuid))
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
            task.process_name = "bla"
            task.end_time = None
            task.exit_code = 0
            task.reason = None
            tasks.append(task)
            return tasks

        storage_client_mock = MagicMock(StorageClient)
        response = {'count': 1, 'rows': [{'process_name': 'bla'}]}
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=response):
                with patch.object(server.Server.scheduler, 'get_tasks', return_value=patch_get_tasks()):
                    resp = await client.get('/foglamp/task{}'.format(request_params))
                    assert 200 == resp.status
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert {'tasks': [{'state': 'Running', 'id': '{}'.format(self._random_uuid),
                                       'endTime': 'None', 'exitCode': 0,
                                       'startTime': 'None', 'reason': None, 'name': 'bla'}]} == json_response

    @pytest.mark.parametrize("request_params, response_code, response_message", [
        ('?limit=invalid', 400, "Limit must be a positive integer"),
        ('?limit=-1', 400, "Limit must be a positive integer"),
        ('?state=BLA', 400, "This state value 'BLA' not permitted."),
    ])
    async def test_get_tasks_exceptions(self, client, request_params, response_code, response_message):
        resp = await client.get('/foglamp/task{}'.format(request_params))
        assert response_code == resp.status
        assert response_message == resp.reason

    async def test_get_tasks_no_task_exception(self, client):
        async def patch_get_tasks():
            tasks = []
            return tasks

        storage_client_mock = MagicMock(StorageClient)
        response = {'count': 0, 'rows': []}
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=response):
                with patch.object(server.Server.scheduler, 'get_tasks', return_value=patch_get_tasks()):
                    resp = await client.get('/foglamp/task{}'.format('?name=bla&state=running'))
                    assert 404 == resp.status
                    assert "No Tasks found" == resp.reason

    @pytest.mark.parametrize("request_params", ['', '?name=bla'])
    async def test_get_tasks_latest(self, client, request_params):
        storage_client_mock = MagicMock(StorageClient)
        response = {'count': 2, 'rows': [
            {'pid': '1', 'reason': '', 'exit_code': '0', 'id': '1',
             'process_name': 'bla', 'end_time': '2018', 'start_time': '2018', 'state': '2'}]}
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=response):
                resp = await client.get('/foglamp/task/latest{}'.format(request_params))
                assert 200 == resp.status
                result = await resp.text()
                json_response = json.loads(result)
                assert {'tasks': [{'reason': '', 'name': 'bla',
                                   'state': 'Complete', 'exitCode': '0', 'endTime': '2018',
                                   'pid': '1', 'startTime': '2018', 'id': '1'}]} == json_response

    @pytest.mark.parametrize("request_params", ['', '?name=not_exist'])
    async def test_get_tasks_latest_no_task_exception(self, client, request_params):
        storage_client_mock = MagicMock(StorageClient)
        response = {'count': 0, 'rows': []}
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=response):
                resp = await client.get('/foglamp/task/latest{}'.format(request_params))
                assert 404 == resp.status
                assert "No Tasks found" == resp.reason

    async def test_cancel_task(self, client):
        async def mock_coro():
            return "some valid values"

        with patch.object(server.Server.scheduler, 'get_task', return_value=mock_coro()):
            with patch.object(server.Server.scheduler, 'cancel_task', return_value=mock_coro()):
                resp = await client.put('/foglamp/task/cancel/{}'.format(self._random_uuid))
                assert 200 == resp.status
                result = await resp.text()
                json_response = json.loads(result)
                assert {'id': '{}'.format(self._random_uuid),
                        'message': 'Task cancelled successfully'} == json_response

    async def test_cancel_task_bad_data(self, client):
            resp = await client.put('/foglamp/task/cancel/{}'.format("bla"))
            assert 404 == resp.status
            assert 'Invalid Task ID {}'.format("bla") == resp.reason

    @pytest.mark.parametrize("exception_name, response_code, response_message", [
        (TaskNotFoundError(_random_uuid), 404, 'Task not found: {}'.format(_random_uuid)),
        (TaskNotRunningError(_random_uuid), 404, 'Task is not running: {}'.format(_random_uuid)),
        (ValueError, 404, None),
    ])
    async def test_cancel_task_exceptions(self, client, exception_name, response_code, response_message):
        async def mock_coro():
            return ""

        with patch.object(server.Server.scheduler, 'get_task', return_value=mock_coro()):
            with patch.object(server.Server.scheduler, 'cancel_task', side_effect=exception_name):
                resp = await client.put('/foglamp/task/cancel/{}'.format(self._random_uuid))
                assert response_code == resp.status
                assert response_message == resp.reason

    async def test_get_task_state(self, client):
        resp = await client.get('/foglamp/task/state')
        assert 200 == resp.status
        result = await resp.text()
        json_response = json.loads(result)
        assert {'taskState': [
            {'name': 'Running', 'index': 1},
            {'name': 'Complete', 'index': 2},
            {'name': 'Canceled', 'index': 3},
            {'name': 'Interrupted', 'index': 4}]} == json_response
