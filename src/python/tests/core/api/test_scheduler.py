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


async def add_master_data():
    conn = await asyncpg.connect(database=__DB_NAME)
    await conn.execute('truncate foglamp.schedules, foglamp.tasks')
    await conn.execute(''' DELETE from foglamp.scheduled_processes WHERE name in ('sleep1', 'sleep5', 'sleep10', 'sleep30')''')
    await conn.execute('''insert into foglamp.scheduled_processes(name, script)
        values('sleep1', '["sleep", "1"]')''')
    await conn.execute('''insert into foglamp.scheduled_processes(name, script)
        values('sleep10', '["sleep", "10"]')''')
    await conn.execute('''insert into foglamp.scheduled_processes(name, script)
        values('sleep30', '["sleep", "30"]')''')
    await conn.execute('''insert into foglamp.scheduled_processes(name, script)
        values('sleep5', '["sleep", "5"]')''')
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
            schedule_id = sch['id']
            r = requests.delete(BASE_URL+'/schedule/' + schedule_id)
            retval = dict(r.json())
            assert 200 == r.status_code
            assert retval['id'] == schedule_id
            assert retval['message'] == "Schedule deleted successfully"


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

    def setup_method(self, method):
        pass

    def teardown_method(self, method):
        delete_all_schedules()

    def _create_schedule(self, data):
        r = requests.post(BASE_URL + '/schedule', data=json.dumps(data), headers=headers)
        retval = dict(r.json())
        schedule_id = retval['schedule']['id']

        return schedule_id

    # TODO: Add tests for negative cases. There would be around 4 neagtive test cases for most of the schedule+task methods.
    # Currently only positive test cases have been added.

    @pytest.mark.run(order=1)
    @pytest.mark.asyncio
    async def test_get_scheduled_processes(self):
        r = requests.get(BASE_URL+'/schedule/process')
        retval = dict(r.json())

        assert 200 == r.status_code
        assert 'sleep30' in retval['processes']
        assert 'sleep10' in retval['processes']
        assert 'sleep5' in retval['processes']
        assert 'sleep1' in retval['processes']

    @pytest.mark.run(order=2)
    @pytest.mark.asyncio
    async def test_get_scheduled_process(self):
        r = requests.get(BASE_URL+'/schedule/process/sleep1')

        assert 200 == r.status_code
        assert 'sleep1' == r.json()

    @pytest.mark.run(order=3)
    @pytest.mark.asyncio
    async def test_post_schedule(self):
        data = {"type": 3, "name": "test_post_sch", "process_name": "sleep30", "repeat": "3600"}
        r = requests.post(BASE_URL+'/schedule', data=json.dumps(data), headers=headers)
        retval = dict(r.json())

        assert 200 == r.status_code
        assert not retval['schedule']['id'] is None
        assert retval['schedule']['exclusive'] is True
        assert retval['schedule']['type'] == "INTERVAL"
        assert retval['schedule']['time'] == "None"
        assert retval['schedule']['day'] is None
        assert retval['schedule']['process_name'] == 'sleep30'
        assert retval['schedule']['repeat'] == '1:00:00'
        assert retval['schedule']['name'] == 'test_post_sch'

    @pytest.mark.run(order=4)
    @pytest.mark.asyncio
    async def test_update_schedule(self):
        # First create a schedule to get the schedule_id
        data = {"type": 3, "name": "test_update_sch", "process_name": "sleep30", "repeat": "3600"}
        schedule_id = self._create_schedule(data)

        # Secondly, update the schedule
        data = {"name": "test_update_sch_upd", "repeat": "4"}
        r = requests.put(BASE_URL+'/schedule/' + schedule_id, data=json.dumps(data), headers=headers)
        retval = dict(r.json())
        assert not retval['schedule']['id'] is None

        # These values did not change
        assert retval['schedule']['exclusive'] is True
        # TODO: There is a bug in core/scheduler.py. It does not update the schedule type BUT if you pass a new schedule
        # type in above, it will return the new schedule type even though it does not update the DB record.
        assert retval['schedule']['type'] == "INTERVAL"
        assert retval['schedule']['time'] == "None"
        assert retval['schedule']['day'] is None
        assert retval['schedule']['process_name'] == 'sleep30'

        # Below two values only changed
        assert retval['schedule']['repeat'] == '0:00:04'
        assert retval['schedule']['name'] == 'test_update_sch_upd'

    @pytest.mark.run(order=5)
    @pytest.mark.asyncio
    async def test_delete_schedule(self):
        # First create a schedule to get the schedule_id
        data = {"type": 3, "name": "test_delete_sch", "process_name": "sleep30", "repeat": "3600"}
        schedule_id = self._create_schedule(data)

        # Now check the schedules
        r = requests.delete(BASE_URL+'/schedule/' + schedule_id)
        retval = dict(r.json())

        assert 200 == r.status_code
        assert retval['id'] == schedule_id
        assert retval['message'] == "Schedule deleted successfully"

    @pytest.mark.run(order=6)
    @pytest.mark.asyncio
    async def test_get_schedule(self):
        # First create a schedule to get the schedule_id
        data = {"type": 3, "name": "test_get_sch", "process_name": "sleep30", "repeat": "3600"}
        schedule_id = self._create_schedule(data)

        # Now check the schedule
        r = requests.get(BASE_URL+'/schedule/' + schedule_id)
        retval = dict(r.json())

        assert 200 == r.status_code
        assert retval['id'] == schedule_id
        assert retval['exclusive'] is True
        assert retval['type'] == "INTERVAL"
        assert retval['time'] == "None"
        assert retval['day'] is None
        assert retval['process_name'] == 'sleep30'
        assert retval['repeat'] == '1:00:00'
        assert retval['name'] == 'test_get_sch'

    @pytest.mark.run(order=7)
    @pytest.mark.asyncio
    async def test_get_schedules(self):
        # First create two schedules to get the schedule_id
        data = {"type": 3, "name": "test_get_schA", "process_name": "sleep30", "repeat": "3600"}
        schedule_id1 = self._create_schedule(data)

        await asyncio.sleep(4)

        data = {"type": 2, "name": "test_get_schB", "process_name": "sleep30", "day": 5, "time": 44500}
        schedule_id2 = self._create_schedule(data)

        await asyncio.sleep(4)

        # Now check the schedules
        r = requests.get(BASE_URL+'/schedule')
        retval = dict(r.json())

        assert 200 == r.status_code
        assert 2 == len(retval['schedules'])
        # Because of unpredictibility in the sequence of the items, this method of assert has been adopted
        assert retval['schedules'][0]['id'] in [schedule_id1, schedule_id2]
        assert retval['schedules'][0]['exclusive'] is True
        assert retval['schedules'][0]['type'] in ["INTERVAL", "TIMED"]
        assert retval['schedules'][0]['time'] in ["None", '12:21:40']
        assert retval['schedules'][0]['day'] in [None, 5]
        assert retval['schedules'][0]['process_name'] == 'sleep30'
        assert retval['schedules'][0]['repeat'] in ['1:00:00', '0:00:00']
        assert retval['schedules'][0]['name'] in ['test_get_schA', 'test_get_schB']

        assert retval['schedules'][1]['id'] in [schedule_id1, schedule_id2]
        assert retval['schedules'][1]['exclusive'] is True
        assert retval['schedules'][1]['type'] in ["INTERVAL", "TIMED"]
        assert retval['schedules'][1]['time'] in ["None", '12:21:40']
        assert retval['schedules'][1]['day'] in [None, 5]
        assert retval['schedules'][1]['process_name'] == 'sleep30'
        assert retval['schedules'][1]['repeat'] in ['1:00:00', '0:00:00']
        assert retval['schedules'][1]['name'] in ['test_get_schA', 'test_get_schB']

    @pytest.mark.run(order=8)
    @pytest.mark.asyncio
    async def test_start_schedule(self):
        # First create a schedule to get the schedule_id
        data = {"type": 3, "name": "test_start_sch", "process_name": "sleep30", "repeat": "600"}
        schedule_id = self._create_schedule(data)

        # Now start the schedules
        r = requests.post(BASE_URL+'/schedule/start/' + schedule_id)
        retval = dict(r.json())

        assert retval['id'] == schedule_id
        assert retval['message'] == "Schedule started successfully"

        # Allow sufficient time for task record to be created
        await asyncio.sleep(4)

        # Verify with Task record as to one task has been created
        r = requests.get(BASE_URL+'/task')
        retval = dict(r.json())

        assert 200 == r.status_code
        assert 1 == len(retval['tasks'])
        assert retval['tasks'][0]['state'] == 'RUNNING'
        assert retval['tasks'][0]['process_name'] == 'sleep30'

