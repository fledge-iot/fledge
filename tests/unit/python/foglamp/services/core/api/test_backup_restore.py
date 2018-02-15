# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


import json
from unittest.mock import MagicMock, patch
from aiohttp import web
import pytest
from collections import Counter
from foglamp.services.core import routes
from foglamp.services.core import connect
from foglamp.plugins.storage.postgres.backup_restore.backup_postgres import Backup
from foglamp.services.core.api import backup_restore
from foglamp.common.storage_client.storage_client import StorageClient


__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("api", "core")
class TestBackupRestore:

    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop)
        # fill the routes table
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    @pytest.mark.parametrize("input_data, expected", [
        (1, "RUNNING"),
        (2, "COMPLETED"),
        (3, "CANCELED"),
        (4, "INTERRUPTED"),
        (5, "FAILED"),
        (6, "RESTORED"),
        (7, "UNKNOWN")
    ])
    def test_get_status(self, input_data, expected):
        assert expected == backup_restore._get_status(input_data)

    @pytest.mark.parametrize("request_params", [
        '',
        '?limit=1',
        '?skip=1',
        '?status=completed',
        '?status=failed',
        '?status=restored&skip=10',
        '?status=running&limit=1',
        '?status=canceled&limit=10&skip=0',
        '?status=interrupted&limit=&skip=',
        '?status=&limit=&skip='
    ])
    async def test_get_backups(self, client, request_params):
        storage_client_mock = MagicMock(StorageClient)
        response = [{'file_name': '1.dump',
                     'id': 1, 'type': '1', 'status': '2',
                     'ts': '2018-02-15 15:18:41.821978+05:30',
                     'exit_code': '0'}]
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(Backup, 'get_all_backups', return_value=response):
                    resp = await client.get('/foglamp/backup{}'.format(request_params))
                    assert 200 == resp.status
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert 1 == len(json_response['backups'])
                    assert Counter({"id", "date", "status"}) == Counter(json_response['backups'][0].keys())

    @pytest.mark.parametrize("request_params, response_code, response_message", [
        ('?limit=invalid', 400, "Limit must be a positive integer"),
        ('?limit=-1', 400, "Limit must be a positive integer"),
        ('?skip=invalid', 400, "Skip/Offset must be a positive integer"),
        ('?skip=-1', 400, "Skip/Offset must be a positive integer"),
        ('?status=BLA', 400, "'BLA' is not a valid status"),
        ('', 500, "Internal Server Error")
    ])
    async def test_get_backups_bad_data(self, client, request_params, response_code, response_message):
        resp = await client.get('/foglamp/backup{}'.format(request_params))
        assert response_code == resp.status
        assert response_message == resp.reason
