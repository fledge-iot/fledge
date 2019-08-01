# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


import json
import pathlib

from unittest.mock import patch, mock_open
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
        return pathlib.Path(__file__).parent

    async def test_get_logs(self, client, logs_path):
        files = ["190801-13-21-56.log", "190801-13-18-02-foglamp-north-httpc.log",
                 "190801-14-55-25-foglamp-south-sinusoid.log"]
        response_content = {'logs': files}
        with patch.object(package_log, '_get_logs_dir', side_effect=[logs_path / 'logs']):
            with patch('os.walk') as mockwalk:
                mockwalk.return_value = [(str(logs_path / 'logs'), [], files)]
                resp = await client.get('/foglamp/package/log')
                assert 200 == resp.status
                res = await resp.text()
                jdict = json.loads(res)
                logs = jdict["logs"]
                assert 3 == len(logs)
                assert Counter(response_content['logs']) == Counter(logs)
            mockwalk.assert_called_once_with(logs_path / 'logs')

    async def test_get_log_by_name_with_invalid_extension(self, client):
        resp = await client.get('/foglamp/package/log/blah.txt')
        assert 400 == resp.status
        assert "Accepted file extension is .log" == resp.reason

    async def test_get_log_by_name_when_it_doesnot_exist(self, client, logs_path):
        files = ["190801-13-18-02-foglamp-north-httpc.log"]
        with patch.object(package_log, '_get_logs_dir', side_effect=[logs_path / 'logs']):
            with patch('os.walk') as mockwalk:
                mockwalk.return_value = [(str(logs_path / 'logs'), [], files)]
                resp = await client.get('/foglamp/package/log/190801-13-21-56.log')
                assert 404 == resp.status
                assert "190801-13-21-56.log file not found" == resp.reason

    async def test_get_log_by_name(self, client, logs_path):
        with patch.object(package_log, '_get_logs_dir', side_effect=[logs_path / 'logs', logs_path / 'logs/blah.log']):
            with patch('os.walk'):
                with patch('builtins.open', new_callable=mock_open()):
                    resp = await client.get('/foglamp/package/log/190801-13-21-56.log')
                    assert 200 == resp.status
                    res = await resp.text()
                    jdict = json.loads(res)
                    assert {'result': []} == jdict
