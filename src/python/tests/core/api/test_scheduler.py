# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import time
import json
import requests
import pytest
from foglamp.core.server import Scheduler


__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class TestScheduler:
    @classmethod
    def setup_class(cls):
        from subprocess import call
        call(["foglamp", "start"])
        time.sleep(2)


    @classmethod
    def teardown_class(cls):
        from subprocess import call
        call(["foglamp", "stop"])


    def setup_method(self, method):
        Scheduler().populate_test_data()


    def teardown_method(self, method):
        pass


    def test_get_scheduled_processes(self):
        r = requests.get('http://localhost:8082/foglamp/schedule/process')
        retval = dict(r.json())

        assert 200 == r.status_code
        assert 'sleep30' in retval['processes']
        assert 'sleep10' in retval['processes']
        assert 'sleep5' in retval['processes']
        assert 'sleep1' in retval['processes']


    def test_get_scheduled_process(self):
        r = requests.get('http://localhost:8082/foglamp/schedule/process/sleep1')
        assert 200 == r.status_code
        assert 'sleep1' == r.json()


    def test_post_schedule(self):
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


    def test_update_schedule(self):
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
        print(retval)

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

    def test_delete_schedule(self):
        # First create a schedule to get the schedule_id
        headers = {"Content-Type": 'application/json'}
        data = {"type": 3, "name": "test_delete_sch", "process_name": "sleep30", "repeat": "45"}

        r = requests.post('http://localhost:8082/foglamp/schedule', data=json.dumps(data), headers=headers)
        retval = dict(r.json())

        assert 200 == r.status_code
        schedule_id = retval['schedule']['id']

        # Secondly, delete the schedule
        r = requests.delete('http://localhost:8082/foglamp/schedule/' + schedule_id)
        retval = dict(r.json())
        print(retval)

        assert 200 == r.status_code
        assert retval['id'] == schedule_id
        assert retval['message'] == "Schedule deleted successfully."


    def test_get_schedule(self):
        # First create a schedule to get the schedule_id
        headers = {"Content-Type": 'application/json'}
        data = {"type": 3, "name": "test_get_sch", "process_name": "sleep30", "repeat": "45"}

        r = requests.post('http://localhost:8082/foglamp/schedule', data=json.dumps(data), headers=headers)
        retval = dict(r.json())

        assert 200 == r.status_code
        schedule_id = retval['schedule']['id']

        # Secondly, get the schedule
        r = requests.get('http://localhost:8082/foglamp/schedule/' + schedule_id)
        retval = dict(r.json())
        print(retval)

        assert 200 == r.status_code
        assert retval['id'] == schedule_id
        assert retval['exclusive'] == True
        assert retval['type'] == "INTERVAL"
        assert retval['time'] == "None"
        assert retval['day'] == None
        assert retval['process_name'] == 'sleep30'
        assert retval['repeat'] == '0:00:45'
        assert retval['name'] == 'test_get_sch'



    def test_get_schedules(self):
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

        # Secondly, check the schedules
        r = requests.get('http://localhost:8082/foglamp/schedule')
        retval = dict(r.json())
        print(retval)

        assert 200 == r.status_code
        assert len(retval['schedules']) == 2

        assert retval['schedules'][0]['id'] == schedule_id1
        assert retval['schedules'][0]['exclusive'] == True
        assert retval['schedules'][0]['type'] == "INTERVAL"
        assert retval['schedules'][0]['time'] == "None"
        assert retval['schedules'][0]['day'] == None
        assert retval['schedules'][0]['process_name'] == 'sleep30'
        assert retval['schedules'][0]['repeat'] == '0:00:45'
        assert retval['schedules'][0]['name'] == 'test_get_schA'

        assert retval['schedules'][1]['id'] == schedule_id2
        assert retval['schedules'][1]['exclusive'] == True
        assert retval['schedules'][1]['type'] == "TIMED"
        assert retval['schedules'][1]['time'] == "0:00:00"
        assert retval['schedules'][1]['day'] == 5
        assert retval['schedules'][1]['process_name'] == 'sleep30'
        assert retval['schedules'][1]['repeat'] == None
        assert retval['schedules'][1]['name'] == 'test_get_schB'


    def test_start_schedule(self):
        pass

    def test_get_task(self):
        pass

    def test_get_tasks(self):
        pass

    def test_get_tasks_latest(self):
        pass

    def test_cancel_task(self):
        pass


