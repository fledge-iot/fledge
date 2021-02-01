# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import os
import asyncio
import json

from unittest.mock import MagicMock, patch
from collections import Counter
from aiohttp import web
import pytest
from fledge.services.core import routes
from fledge.services.core import connect

from fledge.plugins.storage.common.backup import Backup
from fledge.plugins.storage.common.restore import Restore
from fledge.plugins.storage.common import exceptions

from fledge.services.core.api import backup_restore
from fledge.common.storage_client.storage_client import StorageClientAsync

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@asyncio.coroutine
def mock_coro(*args, **kwargs):
    if len(args) > 0:
        return args[0]
    else:
        return ""


@pytest.allure.feature("unit")
@pytest.allure.story("api", "backup")
class TestBackup:
    """Unit test the Backup functionality
    """
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
        storage_client_mock = MagicMock(StorageClientAsync)
        response = [{'file_name': '1.dump',
                     'id': 1, 'type': '1', 'status': '2',
                     'ts': '2018-02-15 15:18:41.821978+05:30',
                     'exit_code': '0'}]
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(Backup, 'get_all_backups', return_value=mock_coro(response)):
                resp = await client.get('/fledge/backup{}'.format(request_params))
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
        ('?status=BLA', 400, "'BLA' is not a valid status")
    ])
    async def test_get_backups_bad_data(self, client, request_params, response_code, response_message):
        resp = await client.get('/fledge/backup{}'.format(request_params))
        assert response_code == resp.status
        assert response_message == resp.reason

    async def test_get_backups_exceptions(self, client):
        msg = "Internal Server Error"
        with patch.object(connect, 'get_storage_async', side_effect=Exception(msg)):
            resp = await client.get('/fledge/backup')
            assert 500 == resp.status
            assert msg == resp.reason

    async def test_create_backup(self, client):
        async def mock_create():
            return "running_or_failed"

        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(Backup, 'create_backup', return_value=mock_create()):
                resp = await client.post('/fledge/backup')
                assert 200 == resp.status
                assert '{"status": "running_or_failed"}' == await resp.text()

    async def test_create_backup_exception(self, client):
        msg = "Internal Server Error"
        with patch.object(connect, 'get_storage_async', side_effect=Exception(msg)):
            resp = await client.post('/fledge/backup')
            assert 500 == resp.status
            assert msg == resp.reason

    async def test_get_backup_details(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        response = {'id': 1, 'file_name': '1.dump', 'ts': '2018-02-15 15:18:41.821978+05:30',
                    'status': '2', 'type': '1', 'exit_code': '0'}
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(Backup, 'get_backup_details', return_value=mock_coro(response)):
                resp = await client.get('/fledge/backup/{}'.format(1))
                assert 200 == resp.status
                result = await resp.text()
                json_response = json.loads(result)
                assert 3 == len(json_response)
                assert Counter({"id", "date", "status"}) == Counter(json_response.keys())

    @pytest.mark.parametrize("input_exception, response_code, response_message", [
        (exceptions.DoesNotExist, 404, "Backup id 8 does not exist"),
        (Exception("Internal Server Error"), 500, "Internal Server Error")
    ])
    async def test_get_backup_details_exceptions(self, client, input_exception, response_code, response_message):
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(Backup, 'get_backup_details', side_effect=input_exception):
                resp = await client.get('/fledge/backup/{}'.format(8))
                assert response_code == resp.status
                assert response_message == resp.reason

    async def test_get_backup_details_bad_data(self, client):
        resp = await client.get('/fledge/backup/{}'.format('BLA'))
        assert 400 == resp.status
        assert "Invalid backup id" == resp.reason

    async def test_delete_backup(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(Backup, 'delete_backup', return_value=mock_coro(None)):
                resp = await client.delete('/fledge/backup/{}'.format(1))
                assert 200 == resp.status
                result = await resp.text()
                json_response = json.loads(result)
                assert {'message': 'Backup deleted successfully'} == json_response

    @pytest.mark.parametrize("input_exception, response_code, response_message", [
        (exceptions.DoesNotExist, 404, "Backup id 8 does not exist"),
        (Exception("Internal Server Error"), 500, "Internal Server Error")
    ])
    async def test_delete_backup_exceptions(self, client, input_exception, response_code, response_message):
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(Backup, 'delete_backup', side_effect=input_exception):
                resp = await client.delete('/fledge/backup/{}'.format(8))
                assert response_code == resp.status
                assert response_message == resp.reason

    async def test_delete_backup_bad_data(self, client):
        resp = await client.delete('/fledge/backup/{}'.format('BLA'))
        assert 400 == resp.status
        assert "Invalid backup id" == resp.reason

    async def test_get_backup_status(self, client):
        resp = await client.get('/fledge/backup/status')
        assert 200 == resp.status
        result = await resp.text()
        json_response = json.loads(result)
        assert {'backupStatus': [{'index': 1, 'name': 'RUNNING'},
                                 {'index': 2, 'name': 'COMPLETED'},
                                 {'index': 3, 'name': 'CANCELED'},
                                 {'index': 4, 'name': 'INTERRUPTED'},
                                 {'index': 5, 'name': 'FAILED'},
                                 {'index': 6, 'name': 'RESTORED'}]} == json_response

    @pytest.mark.parametrize("input_exception, response_code, response_message", [
        (ValueError, 400, "Invalid backup id"),
        (exceptions.DoesNotExist, 404, "Backup id 8 does not exist"),
        (Exception("Internal Server Error"), 500, "Internal Server Error")
    ])
    async def test_get_backup_download_exceptions(self, client, input_exception, response_code, response_message):
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(Backup, 'get_backup_details', side_effect=input_exception):
                resp = await client.get('/fledge/backup/{}/download'.format(8))
                assert response_code == resp.status
                assert response_message == resp.reason

    async def test_get_backup_download(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        response = {'id': 1, 'file_name': '/usr/local/fledge/data/backup/fledge.db', 'ts': '2018-02-15 15:18:41',
                    'status': '2', 'type': '1'}

        with patch("aiohttp.web.FileResponse", return_value=web.FileResponse(path=os.path.realpath(__file__))) as file_res:
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(Backup, 'get_backup_details', return_value=mock_coro(response)) as patch_backup_detail:
                    with patch('tarfile.open'):
                        resp = await client.get('/fledge/backup/{}/download'.format(1))
                        assert 200 == resp.status
                        assert 'OK' == resp.reason
                patch_backup_detail.assert_called_once_with(1)
        assert 1 == file_res.call_count


@pytest.allure.feature("unit")
@pytest.allure.story("api", "restore")
class TestRestore:
    """Unit test the Restore functionality"""

    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop)
        # fill the routes table
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    async def test_restore_backup(self, client):
        async def mock_restore():
            return "running"

        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(Restore, 'restore_backup', return_value=mock_restore()):
                resp = await client.put('/fledge/backup/{}/restore'.format(1))
                assert 200 == resp.status
                r = await resp.text()
                assert {'status': 'running'} == json.loads(r)

    @pytest.mark.parametrize("backup_id, input_exception, code, message", [
        (8, exceptions.DoesNotExist, 404, "Backup with 8 does not exist"),
        (2, Exception("Internal Server Error"), 500, "Internal Server Error"),
        ('blah', ValueError, 400, 'Invalid backup id')
    ])
    async def test_restore_backup_exceptions(self, client, backup_id, input_exception, code, message):
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(Restore, 'restore_backup', side_effect=input_exception):
                resp = await client.put('/fledge/backup/{}/restore'.format(backup_id))
                assert code == resp.status
                assert message == resp.reason
