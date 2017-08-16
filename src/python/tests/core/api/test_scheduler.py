# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import time
import json
import requests
import pytest
import asyncio
from foglamp.core.server import Scheduler


__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class TestScheduler:
    def setup_method(self, method):
        asyncio.get_event_loop().run_until_complete(Scheduler().populate_test_data())

        from subprocess import call
        call(["foglamp", "start"])
        time.sleep(1)


    def teardown_method(self, method):
        from subprocess import call
        call(["foglamp", "stop"])
        time.sleep(1)


    @pytest.mark.asyncio
    async def test_get_scheduled_processes(self):
        # r = asyncio.get_event_loop().run_until_complete(requests.get('http://localhost:8082/foglamp/schedule/process'))
        r = requests.get('http://localhost:8082/foglamp/schedule/process')

        retval = dict(r.json())

        assert 200 == r.status_code
        assert 'sleep30' in retval['processes']
        assert 'sleep10' in retval['processes']
        assert 'sleep5' in retval['processes']
        assert 'sleep1' in retval['processes']


    @pytest.mark.asyncio
    async def test_get_scheduled_process(self):
        r = requests.get('http://localhost:8082/foglamp/schedule/process/sleep1')
        assert 200 == r.status_code
        assert 'sleep1' == r.json()


    @pytest.mark.asyncio
    async def test_post_schedule(self):
        headers = {"Content-Type": 'application/json'}
        data = {"type": 3, "name": "test_post_sch", "process_name": "sleep30", "repeat": "45"}

        r = requests.post('http://localhost:8082/foglamp/schedule', data=json.dumps(data), headers=headers)
        retval = dict(r.json())

        assert 200 == r.status_code
        assert not retval['schedule']['id'] == None
        assert retval['schedule']['exclusive'] == True
        assert retval['schedule']['type'] == "INTERVAL"
        assert retval['schedule']['time'] == "None"
        assert retval['schedule']['day'] == None
        assert retval['schedule']['process_name'] == 'sleep30'
        assert retval['schedule']['repeat'] == '0:00:45'
        assert retval['schedule']['name'] == 'test_post_sch'


    @pytest.mark.asyncio
    async def test_update_schedule(self):
        # First create a schedule to get the schedule_id
        headers = {"Content-Type": 'application/json'}
        data = {"type": 3, "name": "test_update_sch", "process_name": "sleep30", "repeat": "45"}

        r = requests.post('http://localhost:8082/foglamp/schedule', data=json.dumps(data), headers=headers)
        retval = dict(r.json())

        assert 200 == r.status_code
        schedule_id = retval['schedule']['id']

        # Secondly, update the schedule
        headers = {"Content-Type": 'application/json'}
        data = {"name": "test_update_sch_upd", "repeat": "4"}

        r = requests.put('http://localhost:8082/foglamp/schedule/'+schedule_id, data=json.dumps(data), headers=headers)
        retval = dict(r.json())

        assert 200 == r.status_code
        assert not retval['schedule']['id'] == None

        # These values did not change
        assert retval['schedule']['exclusive'] == True
        # TODO: There is a bug in core/scheduler.py. It does not update the schedule type BUT if you pass a new schedule
        # type in above, it will return the new schedule type even though it does not update the DB record.
        assert retval['schedule']['type'] == "INTERVAL"
        assert retval['schedule']['time'] == "None"
        assert retval['schedule']['day'] == None
        assert retval['schedule']['process_name'] == 'sleep30'

        # Below two values only changed
        assert retval['schedule']['repeat'] == '0:00:04'
        assert retval['schedule']['name'] == 'test_update_sch_upd'

    @pytest.mark.asyncio
    async def test_delete_schedule(self):
        # First create a schedule to get the schedule_id
        headers = {"Content-Type": 'application/json'}
        data = {"type": 3, "name": "test_delete_sch", "process_name": "sleep30", "repeat": "45"}

        r = requests.post('http://localhost:8082/foglamp/schedule', data=json.dumps(data), headers=headers)
        retval = dict(r.json())

        assert 200 == r.status_code
        schedule_id = retval['schedule']['id']

        # Now check the schedules
        r = requests.delete('http://localhost:8082/foglamp/schedule/' + schedule_id)
        retval = dict(r.json())

        assert 200 == r.status_code
        assert retval['id'] == schedule_id
        assert retval['message'] == "Schedule deleted successfully."


    @pytest.mark.asyncio
    async def test_get_schedule(self):
        # First create a schedule to get the schedule_id
        headers = {"Content-Type": 'application/json'}
        data = {"type": 3, "name": "test_get_sch", "process_name": "sleep30", "repeat": "45"}

        r = requests.post('http://localhost:8082/foglamp/schedule', data=json.dumps(data), headers=headers)
        retval = dict(r.json())

        assert 200 == r.status_code
        schedule_id = retval['schedule']['id']

        # Now check the schedule
        r = requests.get('http://localhost:8082/foglamp/schedule/' + schedule_id)
        retval = dict(r.json())

        assert 200 == r.status_code
        assert retval['id'] == schedule_id
        assert retval['exclusive'] == True
        assert retval['type'] == "INTERVAL"
        assert retval['time'] == "None"
        assert retval['day'] == None
        assert retval['process_name'] == 'sleep30'
        assert retval['repeat'] == '0:00:45'
        assert retval['name'] == 'test_get_sch'


    @pytest.mark.asyncio
    async def test_get_schedules(self):
        # First create two schedules to get the schedule_id
        headers = {"Content-Type": 'application/json'}
        data = {"type": 3, "name": "test_get_schA", "process_name": "sleep30", "repeat": "45"}

        r = requests.post('http://localhost:8082/foglamp/schedule', data=json.dumps(data), headers=headers)
        retval = dict(r.json())

        assert 200 == r.status_code
        schedule_id1 = retval['schedule']['id']

        headers = {"Content-Type": 'application/json'}
        data = {"type": 2, "name": "test_get_schB", "process_name": "sleep30", "day": 5, "time": 44500}

        r = requests.post('http://localhost:8082/foglamp/schedule', data=json.dumps(data), headers=headers)
        retval = dict(r.json())

        assert 200 == r.status_code
        schedule_id2 = retval['schedule']['id']

        # Now check the schedules
        r = requests.get('http://localhost:8082/foglamp/schedule')
        retval = dict(r.json())

        assert 200 == r.status_code
        assert 2 == len(retval['schedules'])

        # Because of unpredictibility in the sequence of the items, this method of assert has been adopted
        assert retval['schedules'][0]['id'] in [schedule_id1, schedule_id2]
        assert retval['schedules'][0]['exclusive'] == True
        assert retval['schedules'][0]['type'] in ["INTERVAL", "TIMED"]
        assert retval['schedules'][0]['time'] in ["None", '12:21:40']
        assert retval['schedules'][0]['day'] in [None, 5]
        assert retval['schedules'][0]['process_name'] == 'sleep30'
        assert retval['schedules'][0]['repeat'] in ['0:00:45', '0:00:00']
        assert retval['schedules'][0]['name'] in ['test_get_schA', 'test_get_schB']

        assert retval['schedules'][1]['id'] in [schedule_id1, schedule_id2]
        assert retval['schedules'][1]['exclusive'] == True
        assert retval['schedules'][1]['type'] in ["INTERVAL", "TIMED"]
        assert retval['schedules'][1]['time'] in ["None", '12:21:40']
        assert retval['schedules'][1]['day'] in [None, 5]
        assert retval['schedules'][1]['process_name'] == 'sleep30'
        assert retval['schedules'][1]['repeat'] in ['0:00:45', '0:00:00']
        assert retval['schedules'][1]['name'] in ['test_get_schA', 'test_get_schB']


    @pytest.mark.asyncio
    async def test_start_schedule(self):
        pass

    @pytest.mark.asyncio
    async def test_get_task(self):
        pass

    @pytest.mark.asyncio
    async def test_get_tasks(self):
        pass

    @pytest.mark.asyncio
    async def test_get_tasks_latest(self):
        pass

    @pytest.mark.asyncio
    async def test_cancel_task(self):
        pass


