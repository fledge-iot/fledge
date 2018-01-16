# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import time
import json

import asyncpg
import requests
import pytest
import asyncio
from foglamp.services.core.scheduler.scheduler import _SCRIPTS_DIR, _FOGLAMP_ROOT

pytestmark = pytest.mark.asyncio


__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# Module attributes
__DB_NAME = "foglamp"
BASE_URL = 'http://localhost:8081/foglamp'
headers = {"Content-Type": 'application/json'}


async def add_master_data():
    conn = await asyncpg.connect(database=__DB_NAME)
    await conn.execute('''DELETE from foglamp.tasks WHERE process_name IN ('testsleep30', 'echo_test')''')
    await conn.execute(''' DELETE from foglamp.schedules WHERE process_name IN ('testsleep30', 'echo_test')''')
    await conn.execute(''' DELETE from foglamp.scheduled_processes WHERE name IN ('testsleep30', 'echo_test')''')
    await conn.execute("insert into foglamp.scheduled_processes(name, script) values('testsleep30', '[\"python3\",\"" +
                       _FOGLAMP_ROOT + "/tests/integration/foglamp/data/sleep.py\", \"30\"]')")
    await conn.execute('''insert into foglamp.scheduled_processes(name, script)
        values('echo_test', '["echo", "Hello"]')''')
    await conn.execute(''' COMMIT''')
    await conn.close()
    await asyncio.sleep(4)


async def delete_master_data():
    conn = await asyncpg.connect(database=__DB_NAME)
    await conn.execute('''DELETE from foglamp.tasks WHERE process_name IN ('testsleep30', 'echo_test')''')
    await conn.execute(''' DELETE from foglamp.schedules WHERE process_name IN ('testsleep30', 'echo_test')''')
    await conn.execute(''' DELETE from foglamp.scheduled_processes WHERE name IN ('testsleep30', 'echo_test')''')
    await conn.execute(''' COMMIT''')
    await conn.close()
    await asyncio.sleep(4)


async def delete_method_data():
    conn = await asyncpg.connect(database=__DB_NAME)
    await conn.execute('''DELETE from foglamp.tasks WHERE process_name IN ('testsleep30', 'echo_test')''')
    await conn.execute(''' DELETE from foglamp.schedules WHERE process_name IN ('testsleep30', 'echo_test')''')
    await conn.execute(''' COMMIT''')
    await conn.close()
    await asyncio.sleep(4)


@pytest.allure.feature("api")
@pytest.allure.story("task")
class TestTask:
    @classmethod
    def setup_class(cls):
        asyncio.get_event_loop().run_until_complete(add_master_data())
        # TODO: Separate test db from a production/dev db as other running tasks interfere in the test execution
        # Starting foglamp from within test is mandatory, otherwise test scheduled_processes are not added to the
        # server if started externally.
        from subprocess import call
        call([_SCRIPTS_DIR + "/foglamp", "start"])
        # TODO: Due to lengthy start up, now tests need a better way to start foglamp or poll some
        #       external process to check if foglamp has started.
        time.sleep(20)

    @classmethod
    def teardown_class(cls):
        # TODO: Separate test db from a production/dev db as other running tasks interfere in the test execution
        # TODO: Figure out how to do a "foglamp stop" in the new dir structure
        # from subprocess import call
        # call(["scripts/foglamp", "stop"])
        # time.sleep(10)
        asyncio.get_event_loop().run_until_complete(delete_master_data())

    def setup_method(self):
        pass

    def teardown_method(self):
        asyncio.get_event_loop().run_until_complete(delete_method_data())

    def _schedule_task(self, data):
        r = requests.post(BASE_URL + '/schedule', data=json.dumps(data), headers=headers)
        retval = dict(r.json())
        schedule_id = retval['schedule']['id']

        # Now start the schedule to create a Task record
        r = requests.post(BASE_URL+'/schedule/start/' + schedule_id)
        retval = dict(r.json())
        assert retval['id'] == schedule_id
        assert retval['message'] == "Schedule started successfully"
        return schedule_id

    # TODO: Add tests for negative cases.
    # There would be around 4 neagtive test cases for most of the schedule+task methods.
    # Currently only positive test cases have been added.
    async def test_cancel_task(self):
        # First create a schedule to get the schedule_id
        data = {"type": 3, "name": "test_task_1", "process_name": "testsleep30", "repeat": "3600"}
        self._schedule_task(data)

        # Allow sufficient time for task record to be created
        await asyncio.sleep(4)

        # Verify with Task record as to one task has been created
        r = requests.get(BASE_URL+'/task')
        retval = dict(r.json())
        task_id = retval['tasks'][0]['id']
        assert 1 == len(retval['tasks'])
        assert retval['tasks'][0]['state'] == 'Running'
        assert retval['tasks'][0]['name'] == 'testsleep30'

        # Now cancel the runnung task
        r = requests.put(BASE_URL+'/task/cancel/' + task_id)
        retval = dict(r.json())
        assert retval['id'] == task_id
        assert retval['message'] == "Task cancelled successfully"

        # Allow sufficient time for task record to be created
        await asyncio.sleep(4)

        # Verify the task has been cancelled
        r = requests.get(BASE_URL+'/task/' + task_id)
        retval = dict(r.json())

        assert 200 == r.status_code
        assert retval['id'] == task_id
        assert retval['state'] == 'Canceled'

    async def test_get_tasks_latest(self):
        # First create two schedules to get the schedule_id
        data = {"type": 3, "name": "test_get_task2a", "process_name": "testsleep30", "repeat": 2}
        self._schedule_task(data)

        data = {"type": 3, "name": "test_get_task2b", "process_name": "echo_test", "repeat": 10}
        self._schedule_task(data)

        # Allow multiple tasks to be created
        await asyncio.sleep(4)

        # Verify with Task record as to more than one task have been created
        r = requests.get(BASE_URL+'/task')
        retval = dict(r.json())
        assert len(retval['tasks']) > 1

        # Verify only two Tasks record is returned
        r = requests.get(BASE_URL+'/task/latest')
        retval = dict(r.json())

        assert 200 == r.status_code
        assert 2 == len(retval['tasks'])
        assert retval['tasks'][1]['name'] == 'testsleep30'
        assert retval['tasks'][0]['name'] == 'echo_test'

    async def test_get_tasks(self):
        # First create a schedule to get the schedule_id
        data = {"type": 3, "name": "test_get_task3", "process_name": "echo_test", "repeat": 2}
        self._schedule_task(data)

        # Allow multiple task records to be created
        await asyncio.sleep(4)

        # Verify that 3 Tasks with given process_name are created in 4 seconds
        rr = requests.get(BASE_URL+'/task')
        retval = dict(rr.json())

        assert 200 == rr.status_code
        list_tasks = [tasks['name'] for tasks in retval['tasks']]
        # Due to async processing, ascertining exact no. of tasks is not possible
        assert list_tasks.count(data['process_name']) >= 3

    async def test_get_task(self):
        # First create a schedule to get the schedule_id
        data = {"type": 3, "name": "test_get_task4", "process_name": "testsleep30", "repeat": 200}
        self._schedule_task(data)

        # Allow sufficient time for task record to be created
        await asyncio.sleep(4)

        # Verify with Task record as to one task has been created
        r = requests.get(BASE_URL+'/task')
        retval = dict(r.json())
        task_id = retval['tasks'][0]['id']

        # Get Task
        r = requests.get(BASE_URL+'/task/' + task_id)
        retval = dict(r.json())

        assert 200 == r.status_code
        assert retval['id'] == task_id

    async def test_get_state(self):
        r = requests.get(BASE_URL + '/task/state')
        retval = dict(r.json())
        task_state = retval['taskState']

        assert 200 == r.status_code

        # verify the task state count
        assert 4 == len(task_state)

        # verify the name and value of task state
        for i in range(len(task_state)):
            if task_state[i]['index'] == 1:
                assert 1 == task_state[i]['index']
                assert 'Running' == task_state[i]['name']
            elif task_state[i]['index'] == 2:
                assert 2 == task_state[i]['index']
                assert 'Complete' == task_state[i]['name']
            elif task_state[i]['index'] == 3:
                assert 3 == task_state[i]['index']
                assert 'Canceled' == task_state[i]['name']
            elif task_state[i]['index'] == 4:
                assert 4 == task_state[i]['index']
                assert 'Interrupted' == task_state[i]['name']

    @pytest.mark.parametrize("request_params, response_code, response_message", [
        ('/task?limit=0', 404, 'No Tasks found'),
        ('/task?name=12', 404, 'No Tasks found'),
        ('/task?state=blah', 400, "This state value 'BLAH' not permitted."),
        ('/task/4e5ea20b-6685-4f44-ab9f-b307ca226e6c', 404, 'Task not found: 4e5ea20b-6685-4f44-ab9f-b307ca226e6c'),
        ('/task/blah', 404, 'Invalid Task ID blah')
    ])
    async def test_params_with_bad_data(self, request_params, response_code, response_message):
        r = requests.get(BASE_URL + request_params)
        assert response_code == r.status_code
        assert response_message == r.reason
