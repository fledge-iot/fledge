# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


import json
import pathlib
from pathlib import PosixPath

from unittest.mock import Mock, MagicMock, patch, mock_open
from collections import Counter

from aiohttp import web

import pytest


from foglamp.services.core import routes
from foglamp.services.core.api import package_log

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2019, Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("api", "package-log")
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
        files = ["190801-13-21-56.log", "190801-13-18-02-foglamp-north-httpc-install.log",
                 "190801-14-55-25-foglamp-south-sinusoid-install.log", "191024-04-21-56-list.log"]
        with patch.object(package_log, '_get_logs_dir', side_effect=[logs_path]):
            with patch('os.walk') as mockwalk:
                mockwalk.return_value = [(str(logs_path), [], files)]
                resp = await client.get('/foglamp/package/log')
                assert 200 == resp.status
                res = await resp.text()
                jdict = json.loads(res)
                logs = jdict["logs"]
                assert 4 == len(logs)
                assert files[0] == logs[0]['filename']
                assert "2019-08-01 13:21:56" == logs[0]['timestamp']
                assert "" == logs[0]['name']
                assert files[1] == logs[1]['filename']
                assert "2019-08-01 13:18:02" == logs[1]['timestamp']
                assert "foglamp-north-httpc-install" == logs[1]['name']
                assert files[2] == logs[2]['filename']
                assert "2019-08-01 14:55:25" == logs[2]['timestamp']
                assert "foglamp-south-sinusoid-install" == logs[2]['name']
                assert files[3] == logs[3]['filename']
                assert "2019-10-24 04:21:56" == logs[3]['timestamp']
                assert "list" == logs[3]['name']
            mockwalk.assert_called_once_with(logs_path)

    async def test_get_log_by_name_with_invalid_extension(self, client):
        resp = await client.get('/foglamp/package/log/blah.txt')
        assert 400 == resp.status
        assert "Accepted file extension is .log" == resp.reason

    async def test_get_log_by_name_when_it_doesnot_exist(self, client, logs_path):
        files = ["190801-13-18-02-foglamp-north-httpc.log"]
        with patch.object(package_log, '_get_logs_dir', side_effect=[logs_path]):
            with patch('os.walk') as mockwalk:
                mockwalk.return_value = [(str(logs_path), [], files)]
                resp = await client.get('/foglamp/package/log/190801-13-21-56.log')
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
                with patch("aiohttp.web.FileResponse", return_value=web.FileResponse(path=filepath)) as f_res:
                    resp = await client.get('/foglamp/package/log/{}'.format(filepath.name))
                    assert 200 == resp.status
                    assert 'OK' == resp.reason
                args, kwargs = f_res.call_args
                assert {'path': PosixPath(pathlib.Path("{}/{}".format(logs_path, filepath.name)))} == kwargs
                assert 1 == f_res.call_count
