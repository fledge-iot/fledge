# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END
import random
import json

import asyncpg
import http.client
import pytest
import asyncio
from datetime import datetime, timezone, timedelta

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# Module attributes
__DB_NAME = "foglamp"
BASE_URL = 'localhost:8082'
headers = {"Content-Type": 'application/json'}

pytestmark = pytest.mark.asyncio

test_data = [{'filename': 'file1', 'ts': datetime.now(), 'type': 0, 'status': 0},
             {'filename': 'file2', 'ts': datetime.now(), 'type': 0, 'status': -1},
             {'filename': 'file1', 'ts': datetime.now(), 'type': 1, 'status': -2}]
test_data_ids = []

async def add_master_data():
    """Inserts master data into backup table and returns the ids of inserted items"""
    global test_data_ids
    conn = await asyncpg.connect(database=__DB_NAME)
    for item in test_data:
        await conn.execute("""INSERT INTO foglamp.backup(file_name,ts,type,status)
                                   VALUES($1, $2, $3, $4);""", item['filename'], item['ts'], item['type'], item['status'])
        res = await conn.fetchval('''SELECT id from foglamp.backup WHERE file_name IN ($1)''', item['filename'])
        test_data_ids.append({item['filename']: res})
    await conn.close()


async def delete_master_data():
    """
    Delete test data records from backup table
    """
    conn = await asyncpg.connect(database=__DB_NAME)
    await conn.execute('''DELETE from foglamp.backup WHERE file_name IN ($1)''', [el['filename'] for el in test_data])
    await conn.close()

async def setup_module(module):
    """
    Delete the created files from backup directory
    """
    # FIXME after actual implementation
    # asyncio.get_event_loop().run_until_complete(add_master_data())
    pass

async def teardown_module(module):
    """
    Delete the created files from backup directory
    """
    # FIXME after actual implementation
    # asyncio.get_event_loop().run_until_complete(delete_master_data())
    pass


@pytest.allure.feature("api")
@pytest.allure.story("backup")
class TestBackup:

    # FIXME : Change in output based on actual implementation
    @pytest.mark.skip(reason="FOGL-529,FOGL-531")
    @pytest.mark.parametrize("request_params, response_code, output", [
        ('', 200, 'expected_output_1'),
        ('?limit=invalid', 200, 'expected_output_2'),
        ('?limit=1', 200, 'expected_output_3'),
        ('?skip=invalid', 200, 'expected_output_4'),
        ('?skip=1', 200, 'expected_output_5'),
        ('?limit=2&skip=1', 200, 'expected_output_6'),
        ('?status=invalid', 200, 'expected_output_7'),
        ('?status=complete', 200, 'expected_output_8'),
        ('?limit=2&skip=1&status=complete', 200, 'expected_output_9'),
    ])
    async def test_get_backups(self, request_params, response_code, output):
        """
        Test to get all backups, where:
        1. No request parameter is passed
        2. valid/invalid limit is specified
        3. valid/invalid skip is specified
        4. valid limit and skip is specified
        5. valid/invalid status is specified
        6. valid limit, skip and status is specified
        There can be multiple records in return, test asserts if test data is present in return or not
        """
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/backup{}'.format(request_params))
        r = conn.getresponse()
        assert response_code == r.status
        r = r.read().decode()
        retval = json.loads(r)
        assert output == retval
        conn.close()

    @pytest.mark.skip(reason="FOGL-529,FOGL-531")
    @pytest.mark.parametrize("request_params, response_code, output", [
        ('/invalid', 200, {'error': {'code': 400, 'message': 'Limit can be a positive integer only'}}),
        ('/{}'.format(test_data_ids[0]['file1']), 200, {"date": '2017-08-30 04:05:10.382', "status": "running"}),
    ])
    async def test_get_backup_details(self, request_params, response_code, output):
        """
        Test to get details of backup, where:
        1. Invalid backup id is specified as query parameter
        2. Valid backup id is specified as query parameter
        """

    @pytest.mark.skip(reason="FOGL-529,FOGL-531")
    async def test_create_backup(self):
        """
        Test checks the api call to create a backup, Use mocks and do not backup as backup is a time consuming process
        """
        pass

    @pytest.mark.skip(reason="FOGL-529,FOGL-531")
    async def test_delete_backup(self):
        """
        Test checks the api call to delete a backup, Use Mocks and test data files as point of removal, do not delete
        an actual backup, scenarios:
        1. Invalid backup id is specified as query parameter
        2. Valid backup id is specified as query parameter
        """
        pass

@pytest.allure.feature("api")
@pytest.allure.story("restore")
class TestRestore:

    @pytest.mark.skip(reason="FOGL-529,FOGL-531")
    async def test_restore(self):
        """
        Test checks the api call to restore a backup, Use mocks and do not restore as it is a time consuming process
        an actual backup, scenarios:
        1. Invalid backup id is specified as query parameter
        2. Valid backup id is specified as query parameter
        """
        pass
