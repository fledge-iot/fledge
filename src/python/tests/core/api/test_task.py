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
from foglamp.core.scheduler import Schedule, Task


__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# Module attributes
__DB_NAME = "foglamp"
BASE_URL = 'http://localhost:8082/foglamp'
headers = {"Content-Type": 'application/json'}


async def add_master_data():
    conn = await asyncpg.connect(database=__DB_NAME)
    await conn.execute('truncate foglamp.tasks')
    await conn.execute(''' DELETE from foglamp.schedules WHERE process_name in ('testsleep1', 'testsleep5', 'testsleep10', 'testsleep30')''')
    await conn.execute(''' DELETE from foglamp.scheduled_processes WHERE name in ('testsleep1', 'testsleep5', 'testsleep10', 'testsleep30')''')
    await conn.execute('''insert into foglamp.scheduled_processes(name, script)
        values('testsleep1', '["sleep", "1"]')''')
    await conn.execute('''insert into foglamp.scheduled_processes(name, script)
        values('testsleep10', '["sleep", "10"]')''')
    await conn.execute('''insert into foglamp.scheduled_processes(name, script)
        values('testsleep30', '["sleep", "30"]')''')
    await conn.execute('''insert into foglamp.scheduled_processes(name, script)
        values('testsleep5', '["sleep", "5"]')''')
    await conn.execute('commit')
    await asyncio.sleep(4)

async def delete_master_data():
    conn = await asyncpg.connect(database=__DB_NAME)
    await conn.execute('truncate foglamp.tasks')
    await conn.execute(''' DELETE from foglamp.schedules WHERE process_name in ('testsleep1', 'testsleep5', 'testsleep10', 'testsleep30')''')
    await conn.execute(''' DELETE from foglamp.scheduled_processes WHERE name in ('testsleep1', 'testsleep5', 'testsleep10', 'testsleep30')''')
    await conn.execute('commit')
    await asyncio.sleep(4)


def delete_all_schedules():
    """
    Deletes all schedules.
    """

    # Get all the schedules
    r = requests.get(BASE_URL+'/schedule')
    retval = dict(r.json())

    schedule_list = retval['schedules'] or None

    if schedule_list:
        for sch in schedule_list:
            if sch['process_name'] in ['testsleep1', 'testsleep5', 'testsleep10', 'testsleep30']:
                schedule_id = sch['id']
                r = requests.delete(BASE_URL+'/schedule/' + schedule_id)
                retval = dict(r.json())
                assert 200 == r.status_code
                assert retval['id'] == schedule_id
                assert retval['message'] == "Schedule deleted successfully"

def cancel_all_tasks():
    # Get all tasks
    r = requests.get(BASE_URL+'/task')
    retval = dict(r.json())

    task_list = retval['tasks'] or None

    if task_list:
        for task in task_list:
            task_id = task['id']

            if task['state'] == 'RUNNING':
                r = requests.put(BASE_URL + '/task/cancel/' + task_id)
                retval = dict(r.json())
                if not 'error' in list(retval.keys()):
                    assert 200 == r.status_code
                    assert retval['id'] == task_id
                    assert retval['message'] == "Task cancelled successfully"


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
        cancel_all_tasks()
        delete_all_schedules()

    def _create_task(self, data):
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
    @pytest.mark.asyncio
    async def test_cancel_task(self):
        # First create a schedule to get the schedule_id
        data = {"type": 3, "name": "test_task_4", "process_name": "testsleep30", "repeat": "3600"}
        self._create_task(data)

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
    @pytest.mark.asyncio
    async def test_get_tasks_latest(self):
        # First create a schedule to get the schedule_id
        data = {"type": 3, "name": "test_get_task3", "process_name": "testsleep1", "repeat": 2}
        self._create_task(data)

        # Allow multiple tasks to be created
        await asyncio.sleep(14)

        # Verify with Task record as to more than one task have been created
        r = requests.get(BASE_URL+'/task')
        retval = dict(r.json())
        assert len(retval['tasks']) > 0

        # Verify only one Task record is returned
        r = requests.get(BASE_URL+'/task/latest')
        retval = dict(r.json())

        assert 200 == r.status_code
        # TODO: FOGL-410 to add a delete_all_tasks() method in core/scheduler.py
        # Due to this lacking, records from previous tests may or may not be carried forward
        # Uncomment below lines when the above error is fixed
        # assert 1 == len(retval['tasks'])
        assert retval['tasks'][0]['process_name'] == 'testsleep1'

    @pytest.mark.run(order=3)
    @pytest.mark.asyncio
    async def test_get_task(self):
        # First create a schedule to get the schedule_id
        data = {"type": 3, "name": "test_get_task1", "process_name": "testsleep10", "repeat": 200}
        self._create_task(data)

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

    @pytest.mark.run(order=4)
    @pytest.mark.asyncio
    async def test_get_tasks(self):
        # First create a schedule to get the schedule_id
        data = {"type": 3, "name": "test_get_task2", "process_name": "testsleep5", "repeat": 2}
        self._create_task(data)

        # Allow multiple task records to be created
        await asyncio.sleep(4)

        # Verify with Task record as to two  tasks have been created
        rr = requests.get(BASE_URL+'/task')
        retvall = dict(rr.json())

        assert 200 == rr.status_code
        assert len(retvall['tasks']) > 0
        # TODO: add a delete_tasks() method in core/scheduler.py
        # Due to this lacking, one more record is carried forward from previous tests
        # Uncomment below lines when the above error is fixed
        # assert retvall['tasks'][0]['process_name'] == 'testsleep5'
        # assert retvall['tasks'][1]['process_name'] == 'testsleep5'

