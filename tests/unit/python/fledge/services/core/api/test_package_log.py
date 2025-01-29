# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import os
import json
import pathlib
import asyncio
from pathlib import PosixPath
import sys

from unittest.mock import Mock, MagicMock, patch, mock_open
from aiohttp import web

import pytest
from fledge.services.core import routes
from fledge.services.core.api import package_log
from fledge.services.core import connect
from fledge.common.storage_client.storage_client import StorageClientAsync


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2019, Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class TestPackageLog:

    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop)
        # fill the routes table
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    @pytest.fixture
    def logs_path(self):
        return "{}/logs".format(pathlib.Path(__file__).parent)

    async def test_get_logs(self, client, logs_path):
        files = ["190801-13-21-56.log",
                 "190801-13-18-02-fledge-north-httpc-install.log",
                 "190801-14-55-25-fledge-south-sinusoid-install.log",
                 "191024-04-21-56-list.log",
                 "230619-10-20-31-fledge-south-http-south-remove.log",
                 "230619-10-17-36-fledge-south-s2opcua-update.log",
                 "trace.log",
                 "20230609_093006_Trace_00000.log",
                 "trace.txt",
                 "syslog"
                 ]
        with patch.object(package_log, '_get_logs_dir', side_effect=[logs_path]):
            with patch('os.walk') as mockwalk:
                mockwalk.return_value = [(str(logs_path), [], files)]
                resp = await client.get('/fledge/package/log')
                assert 200 == resp.status
                res = await resp.text()
                jdict = json.loads(res)
                logs = jdict["logs"]
                assert len(files) - 2 == len(logs)
                obj = logs[0]
                assert files[0] == obj['filename']
                assert "2019-08-01 13:21:56" == obj['timestamp']
                assert "190801-13-21-56" == obj['name']
                obj = logs[1]
                assert files[1] == obj['filename']
                assert "2019-08-01 13:18:02" == obj['timestamp']
                assert "fledge-north-httpc-install" == obj['name']
                obj = logs[2]
                assert files[2] == obj['filename']
                assert "2019-08-01 14:55:25" == obj['timestamp']
                assert "fledge-south-sinusoid-install" == obj['name']
                obj = logs[3]
                assert files[3] == obj['filename']
                assert "2019-10-24 04:21:56" == obj['timestamp']
                assert "list" == obj['name']
                obj = logs[4]
                assert files[4] == obj['filename']
                assert "2023-06-19 10:20:31" == obj['timestamp']
                assert "fledge-south-http-south-remove" == obj['name']
                obj = logs[5]
                assert files[5] == obj['filename']
                assert "2023-06-19 10:17:36" == obj['timestamp']
                assert "fledge-south-s2opcua-update" == obj['name']
                obj = logs[6]
                assert files[6] == obj['filename']
                assert len(obj['timestamp']) > 0
                assert "trace" == obj['name']
                obj = logs[7]
                assert files[7] == obj['filename']
                assert len(obj['timestamp']) > 0
                assert "20230609_093006_Trace_00000" == obj['name']
            mockwalk.assert_called_once_with(logs_path, topdown=True)

    async def test_get_log_by_name_with_invalid_extension(self, client):
        resp = await client.get('/fledge/package/log/blah.txt')
        assert 400 == resp.status
        assert "Accepted file extension is .log" == resp.reason

    async def test_get_log_by_name_when_it_doesnot_exist(self, client, logs_path):
        files = ["190801-13-18-02-fledge-north-httpc.log"]
        with patch.object(package_log, '_get_logs_dir', side_effect=[logs_path]):
            with patch('os.walk') as mockwalk:
                mockwalk.return_value = [(str(logs_path), [], files)]
                resp = await client.get('/fledge/package/log/190801-13-21-56.log')
                assert 404 == resp.status
                assert "190801-13-21-56.log file not found" == resp.reason

    async def test_get_log_by_name(self, client, logs_path):
        log_filepath = Mock()
        log_filepath.open = mock_open()
        log_filepath.is_file.return_value = True
        log_filepath.stat.return_value = MagicMock()
        log_filepath.stat.st_size = 1024

        filepath = Mock()
        filepath.name = '190801-13-21-56.log'
        filepath.open = mock_open()
        filepath.with_name.return_value = log_filepath
        with patch.object(package_log, '_get_logs_dir', return_value=logs_path):
            with patch('os.walk'):
                with patch("aiohttp.web.FileResponse",
                           return_value=web.FileResponse(path=os.path.realpath(__file__))) as f_res:
                    resp = await client.get('/fledge/package/log/{}'.format(str(filepath.name)))
                    assert 200 == resp.status
                    assert 'OK' == resp.reason
                args, kwargs = f_res.call_args
                assert {'path': PosixPath(pathlib.Path("{}/{}".format(logs_path, filepath.name)))} == kwargs
                assert 1 == f_res.call_count

    @pytest.mark.parametrize("action", [
        'upgrade',
        'blah',
        1
    ])
    async def test_get_package_status_with_bad_action(self, client, action):
        msg = "Accepted package actions are ('list', 'install', 'purge', 'update')"
        resp = await client.get('/fledge/package/{}/status'.format(action))
        assert 400 == resp.status
        assert msg == resp.reason
        r = await resp.text()
        actual = json.loads(r)
        assert {"message": msg} == actual

    @pytest.mark.parametrize("action, status", [
        ('list', -1),
        ('install', 0),
        ('purge', -1),
        ('update', 127),
        ('Install', 1),
        ('PURGE', 0)
    ])
    async def test_get_package_status_with_no_record(self, client, action, status):
        payload = {"return": ["id", "name", "action", "status", "log_file_uri"],
                   "where": {"column": "action", "condition": "=", "value": action.lower()}}

        async def mock_coro():
            return {"rows": []}

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await mock_coro()
        else:
            _rv = asyncio.ensure_future(mock_coro())
        
        storage_client_mock = MagicMock(StorageClientAsync)
        msg = "'No record found'"
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=_rv) as tbl_patch:
                resp = await client.get('/fledge/package/{}/status'.format(action))
                assert 404 == resp.status
                assert msg == resp.reason
                r = await resp.text()
                actual = json.loads(r)
                assert {'message': msg} == actual
            args, kwargs = tbl_patch.call_args_list[0]
            assert 'packages' == args[0]
            assert payload == json.loads(args[1])

    @pytest.mark.parametrize("action, status", [
        ('list', -1),
        ('install', 0),
        ('purge', -1),
        ('update', 127),
        ('Install', 1),
        ('PURGE', 0)
    ])
    async def test_get_package_status(self, client, action, status):
        payload = {"return": ["id", "name", "action", "status", "log_file_uri"],
                   "where": {"column": "action", "condition": "=", "value": action.lower()}}

        async def mock_coro():
            return {"rows": [{'id': 'b57fd5c5-8079-49ff-b6a1-9515cbd259e4', 'name': 'fledge-south-modbus',
                              'action': action, 'status': status,
                              'log_file_uri': 'log/201006-17-02-53-fledge-south-modbus-{}.log'.format(action.lower())}]}

        def convert_status_and_log_file_uri(old):
            new = old
            if old['status'] == 0:
                new['status'] = 'success'
            elif old['status'] == -1:
                new['status'] = 'in-progress'
            else:
                new['status'] = 'failed'
            new['logFileURI'] = old['log_file_uri']
            del old['log_file_uri']
            return new

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await mock_coro()
        else:
            _rv = asyncio.ensure_future(mock_coro())
        
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=_rv) as tbl_patch:
                resp = await client.get('/fledge/package/{}/status'.format(action))
                assert 200 == resp.status
                r = await resp.text()
                actual = json.loads(r)
                res = await mock_coro()
                expected = convert_status_and_log_file_uri(res['rows'][0])
                assert expected == actual['packageStatus'][0]
            args, kwargs = tbl_patch.call_args_list[0]
            assert 'packages' == args[0]
            assert payload == json.loads(args[1])

    @pytest.mark.parametrize("uid, action, status, index", [
        ('b57fd5c5-8079-49ff-b6a1-9515cbd259e4', 'install', -1, 0),
        ('1cd38675-fea8-4783-b3b5-463ed6c8cbe8', 'install', 0, 1),
        ('5c7be038-ce36-449e-8a09-580108ee25ca', 'PURGE', -1, 3)
    ])
    async def test_get_package_status_by_uid(self, client, uid, action, status, index):
        payload = {"return": ["id", "name", "action", "status", "log_file_uri"],
                   "where": {"column": "action", "condition": "=", "value": action.lower(),
                             "and": {"column": "id", "condition": "=", "value": uid}}}

        async def mock_coro():
            return {"rows": [{'id': 'b57fd5c5-8079-49ff-b6a1-9515cbd259e4', 'name': 'fledge-south-random',
                              'action': "install", 'status': -1,
                              'log_file_uri': 'log/201006-17-02-53-fledge-south-random-install.log'},
                             {'id': '1cd38675-fea8-4783-b3b5-463ed6c8cbe8', 'name': 'fledge-north-kafka',
                              'action': "install", 'status': 0,
                              'log_file_uri': 'log/201007-01-02-53-fledge-north-kafka-install.log'},
                             {'id': '63f3c84b-0cbf-4c76-b9bf-848779fbcc6f', 'name': 'fledge-filter-fft',
                              'action': "update", 'status': 127,
                              'log_file_uri': 'log/201006-12-02-12-fledge-filter-fft-update.log'},
                             {'id': '5c7be038-ce36-449e-8a09-580108ee25ca', 'name': 'fledge-south-modbus',
                              'action': "purge", 'status': -1,
                              'log_file_uri': 'log/201006-17-02-53-fledge-south-modbus-purge.log'}
                             ]}

        def convert_status_and_log_file_uri(old):
            new = old
            if old['status'] == 0:
                new['status'] = 'success'
            elif old['status'] == -1:
                new['status'] = 'in-progress'
            else:
                new['status'] = 'failed'
            new['logFileURI'] = old['log_file_uri']
            del old['log_file_uri']
            return new

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await mock_coro()
        else:
            _rv = asyncio.ensure_future(mock_coro())
        
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=_rv) as tbl_patch:
                resp = await client.get('/fledge/package/{}/status?id={}'.format(action, uid))
                assert 200 == resp.status
                r = await resp.text()
                actual = json.loads(r)
                res = await mock_coro()
                expected = convert_status_and_log_file_uri(res['rows'][index])
                assert expected == actual['packageStatus'][index]
            args, kwargs = tbl_patch.call_args_list[0]
            assert 'packages' == args[0]
            assert payload == json.loads(args[1])
