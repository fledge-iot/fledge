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
import uuid
from foglamp.core.scheduler import Schedule


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


class TestScheduler:
    @classmethod
    def setup_class(cls):
        asyncio.get_event_loop().run_until_complete(add_master_data())
        from subprocess import call
        call(["foglamp", "start"])
        time.sleep(4)

    @classmethod
    def teardown_class(cls):
        from subprocess import call
        call(["foglamp", "stop"])
        time.sleep(4)
        asyncio.get_event_loop().run_until_complete(delete_master_data())

    def setup_method(self, method):
        pass

    def teardown_method(self, method):
        pass

    def _create_schedule(self, data):
        r = requests.post(BASE_URL + '/schedule', data=json.dumps(data), headers=headers)
        retval = dict(r.json())
        schedule_id = retval['schedule']['id']

        return schedule_id

    # TODO: Add tests for negative cases. There would be around 4 neagtive test cases for most of the schedule+task methods.
    # Currently only positive test cases have been added.

    @pytest.mark.run(order=1)
    async def test_get_scheduled_processes(self):
        r = requests.get(BASE_URL+'/schedule/process')
        retval = dict(r.json())

        assert 200 == r.status_code
        assert 'testsleep30' in retval['processes']
        assert 'echo_test' in retval['processes']

    @pytest.mark.run(order=2)
    async def test_get_scheduled_process(self):
        r = requests.get(BASE_URL+'/schedule/process/testsleep30')

        assert 200 == r.status_code
        assert 'testsleep30' == r.json()

    @pytest.mark.run(order=3)
    async def test_post_schedule(self):
        data = {"type": 3, "name": "test_post_sch", "process_name": "testsleep30", "repeat": "3600"}
        r = requests.post(BASE_URL+'/schedule', data=json.dumps(data), headers=headers)
        retval = dict(r.json())

        # Assert the POST request response
        assert 200 == r.status_code
        assert uuid.UUID(retval['schedule']['id'], version=4)
        assert retval['schedule']['exclusive'] is True
        assert retval['schedule']['type'] == Schedule.Type(int(data['type'])).name
        assert retval['schedule']['time'] == "None"
        assert retval['schedule']['day'] is None
        assert retval['schedule']['process_name'] == data['process_name']
        assert retval['schedule']['repeat'] == '1:00:00'
        assert retval['schedule']['name'] == data['name']

        # Assert schedule is really created in DB
        r = requests.get(BASE_URL + '/schedule/' + retval['schedule']['id'])
        assert 200 == r.status_code
        retvall = dict(r.json())
        assert retvall['name'] == data['name']

    @pytest.mark.run(order=4)
    async def test_update_schedule(self):
        # First create a schedule to get the schedule_id
        data = {"type": 3, "name": "test_update_sch", "process_name": "testsleep30", "repeat": "3600"}
        schedule_id = self._create_schedule(data)

        # Secondly, update the schedule
        up_data = {"name": "test_update_sch_upd", "repeat": "4", "type": 4}
        r = requests.put(BASE_URL+'/schedule/' + schedule_id, data=json.dumps(up_data), headers=headers)
        retval = dict(r.json())
        assert uuid.UUID(retval['schedule']['id'], version=4)

        # These values did not change
        assert retval['schedule']['exclusive'] is True
        assert retval['schedule']['time'] == "None"
        assert retval['schedule']['day'] is None
        assert retval['schedule']['process_name'] == data['process_name']

        # Below values are changed
        assert retval['schedule']['repeat'] == '0:00:04'
        assert retval['schedule']['name'] == up_data['name']
        assert retval['schedule']['type'] == Schedule.Type(int(up_data['type'])).name

    @pytest.mark.run(order=5)
    async def test_delete_schedule(self):
        # First create a schedule to get the schedule_id
        data = {"type": 3, "name": "test_delete_sch", "process_name": "testsleep30", "repeat": "3600"}
        schedule_id = self._create_schedule(data)

        # Now check the schedules
        r = requests.delete(BASE_URL+'/schedule/' + schedule_id)
        retval = dict(r.json())

        # Assert the DELETE request response
        assert 200 == r.status_code
        assert retval['id'] == schedule_id
        assert retval['message'] == "Schedule deleted successfully"

        # Assert schedule is really deleted from DB
        r = requests.get(BASE_URL + '/schedule/' + schedule_id)
        assert 200 == r.status_code
        retvall = dict(r.json())
        assert 'Schedule not found' in retvall['error']

    @pytest.mark.run(order=6)
    async def test_get_schedule(self):
        # First create a schedule to get the schedule_id
        data = {"type": 3, "name": "test_get_sch", "process_name": "testsleep30", "repeat": "3600"}
        schedule_id = self._create_schedule(data)

        # Now check the schedule
        r = requests.get(BASE_URL+'/schedule/' + schedule_id)
        retval = dict(r.json())

        assert 200 == r.status_code
        assert retval['id'] == schedule_id
        assert retval['exclusive'] is True
        assert retval['type'] == Schedule.Type(int(data['type'])).name
        assert retval['time'] == "None"
        assert retval['day'] is None
        assert retval['process_name'] == data['process_name']
        assert retval['repeat'] == '1:00:00'
        assert retval['name'] == data['name']

    @pytest.mark.run(order=7)
    async def test_get_schedules(self):
        # First create two schedules to get the schedule_id
        data1 = {"type": 3, "name": "test_get_schA", "process_name": "testsleep30", "repeat": "3600"}
        schedule_id1 = self._create_schedule(data1)

        await asyncio.sleep(4)

        data2 = {"type": 2, "name": "test_get_schB", "process_name": "testsleep30", "day": 5, "time": 44500}
        schedule_id2 = self._create_schedule(data2)

        await asyncio.sleep(4)

        # Now check the schedules
        r = requests.get(BASE_URL+'/schedule')
        assert 200 == r.status_code
        retval = dict(r.json())
        ids = [schedules['id'] for schedules in retval['schedules']]
        assert schedule_id1 in ids
        assert schedule_id2 in ids

    @pytest.mark.run(order=8)
    async def test_start_schedule(self):
        # First create a schedule to get the schedule_id
        data = {"type": 3, "name": "test_start_sch", "process_name": "testsleep30", "repeat": "600"}
        schedule_id = self._create_schedule(data)

        # Now start the schedules
        r = requests.post(BASE_URL+'/schedule/start/' + schedule_id)
        retval = dict(r.json())

        assert retval['id'] == schedule_id
        assert retval['message'] == "Schedule started successfully"

        # Allow sufficient time for task record to be created
        await asyncio.sleep(4)

        # Verify with Task record as to one task has been created and running
        r = requests.get(BASE_URL+'/task')
        retval = dict(r.json())
        assert 200 == r.status_code

        l_task_state = []
        for tasks in retval['tasks']:
            if tasks['process_name'] == data['process_name']:
                l_task_state.append(tasks['state'])
        assert l_task_state.count('RUNNING') == 1
