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


__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# Module attributes
__DB_NAME = "foglamp"
BASE_URL = 'http://localhost:8082/foglamp'
headers = {"Content-Type": 'application/json'}

pytestmark = pytest.mark.asyncio

async def add_master_data():
    conn = await asyncpg.connect(database=__DB_NAME)
    await conn.execute('''DELETE from foglamp.tasks WHERE process_name IN ('testsleep30', 'echo_test')''')
    await conn.execute(''' DELETE from foglamp.schedules WHERE process_name IN ('testsleep30', 'echo_test')''')
    await conn.execute(''' DELETE from foglamp.scheduled_processes WHERE name IN ('testsleep30', 'echo_test')''')
    await conn.execute('''insert into foglamp.scheduled_processes(name, script)
        values('testsleep30', '["sleep", "30"]')''')
    await conn.execute('''insert into foglamp.scheduled_processes(name, script)
        values('echo_test', '["echo", "Hello"]')''')
    await conn.close()
    await asyncio.sleep(4)

async def delete_master_data():
    conn = await asyncpg.connect(database=__DB_NAME)
    await conn.execute('''DELETE from foglamp.tasks WHERE process_name IN ('testsleep30', 'echo_test')''')
    await conn.execute(''' DELETE from foglamp.schedules WHERE process_name IN ('testsleep30', 'echo_test')''')
    await conn.execute(''' DELETE from foglamp.scheduled_processes WHERE name IN ('testsleep30', 'echo_test')''')
    await conn.close()
    await asyncio.sleep(4)


class TestTask:
    @classmethod
    def setup_class(cls):
        asyncio.get_event_loop().run_until_complete(add_master_data())
        from subprocess import call
        call(["foglamp", "start"])
        time.sleep(2)

    @classmethod
    def teardown_class(cls):
        from subprocess import call
        call(["foglamp", "stop"])
        asyncio.get_event_loop().run_until_complete(delete_master_data())

    def setup_method(self, method):
        pass

    def teardown_method(self, method):
        pass

    def _schedule_task(self, data):
        r = requests.post(BASE_URL + '/schedule', data=json.dumps(data), headers=headers)
        retval = dict(r.json())
        schedule_id = retval['schedule']['id']

        # Now start the schedule to create a Task record
        r = requests.post(BASE_URL+'/schedule/start/' + schedule_id)
        retval = dict(r.json())
        assert retval['id'] == schedule_id
        assert retval['message'] == "Schedule started successfully"


    # TODO: Add tests for negative cases. There would be around 4 neagtive test cases for most of the schedule+task methods.
    # Currently only positive test cases have been added.

    @pytest.mark.run(order=1)
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
        assert retval['tasks'][0]['state'] == 'RUNNING'
        assert retval['tasks'][0]['process_name'] == 'testsleep30'

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
        assert retval['state'] == 'CANCELED'

    @pytest.mark.run(order=2)
    async def test_get_tasks_latest(self):
        # First create a schedule to get the schedule_id
        data = {"type": 3, "name": "test_get_task2", "process_name": "testsleep30", "repeat": 2}
        self._schedule_task(data)

        # Allow multiple tasks to be created
        await asyncio.sleep(14)

        # Verify with Task record as to more than one task have been created
        r = requests.get(BASE_URL+'/task')
        retval = dict(r.json())
        assert len(retval['tasks']) > 1

        # Verify only one Task record is returned
        r = requests.get(BASE_URL+'/task/latest')
        retval = dict(r.json())

        assert 200 == r.status_code
        assert 1 == len(retval['tasks'])
        assert retval['tasks'][0]['process_name'] == 'testsleep30'

    @pytest.mark.run(order=3)
    async def test_get_tasks(self):
        # First create a schedule to get the schedule_id
        data = {"type": 3, "name": "test_get_task3", "process_name": "echo_test", "repeat": 2}
        self._schedule_task(data)

        # Allow multiple task records to be created
        await asyncio.sleep(4)

        # Verify that 3 Tasks with given process_name are created in 4 seconds
        rr = requests.get(BASE_URL+'/task')
        retvall = dict(rr.json())

        assert 200 == rr.status_code
        list_tasks = [tasks['process_name'] for tasks in retvall['tasks']]
        assert list_tasks.count(data['process_name']) == 3

    @pytest.mark.run(order=4)
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
