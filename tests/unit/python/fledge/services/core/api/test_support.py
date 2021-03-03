# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import pathlib
from pathlib import PosixPath

from unittest.mock import patch, mock_open, Mock, MagicMock

from aiohttp import web
import pytest

from fledge.services.core import routes
from fledge.services.core.api import support
from fledge.services.core.support import *

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("api", "bundle-support")
class TestBundleSupport:

    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop)
        # fill the routes table
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    @pytest.fixture
    def support_bundles_dir_path(self):
        return pathlib.Path(__file__).parent

    @pytest.mark.parametrize("data, expected_content, expected_count", [
        (['support-180301-13-35-23.tar.gz', 'support-180301-13-13-13.tar.gz'], {'bundles': ['support-180301-13-35-23.tar.gz', 'support-180301-13-13-13.tar.gz']}, 2),
        (['support-180301-15-25-02.tar.gz', 'fledge.txt'], {'bundles': ['support-180301-15-25-02.tar.gz']}, 1),
        (['fledge.txt'], {'bundles': []}, 0),
        ([], {'bundles': []}, 0)
    ])
    async def test_get_support_bundle(self, client, support_bundles_dir_path, data, expected_content, expected_count):
        path = support_bundles_dir_path / 'support'
        with patch.object(support, '_get_support_dir', return_value=path):
            with patch('os.walk') as mockwalk:
                mockwalk.return_value = [(path, [], data)]
                resp = await client.get('/fledge/support')
                assert 200 == resp.status
                res = await resp.text()
                jdict = json.loads(res)
                assert expected_count == len(jdict['bundles'])
                assert expected_content == jdict
            mockwalk.assert_called_once_with(path)

    async def test_get_support_bundle_by_name(self, client, support_bundles_dir_path):
        gz_filepath = Mock()
        gz_filepath.open = mock_open()
        gz_filepath.is_file.return_value = True
        gz_filepath.stat.return_value = MagicMock()
        gz_filepath.stat.st_size = 1024

        bundle_name = 'support-180301-13-35-23.tar.gz'

        filepath = Mock()
        filepath.name = bundle_name
        filepath.open = mock_open()
        filepath.with_name.return_value = gz_filepath

        with patch("aiohttp.web.FileResponse", return_value=web.FileResponse(path=filepath)) as f_res:
            path = support_bundles_dir_path / 'support'
            with patch.object(support, '_get_support_dir', return_value=path):
                with patch('os.path.isdir', return_value=True):
                    with patch('os.walk') as mockwalk:
                        mockwalk.return_value = [(path, [], [bundle_name])]
                        resp = await client.get('/fledge/support/{}'.format(bundle_name))
                        assert 200 == resp.status
                        assert 'OK' == resp.reason
                mockwalk.assert_called_once_with(path)
                args, kwargs = f_res.call_args
                assert {'path': PosixPath(pathlib.Path(path) / str(bundle_name))} == kwargs
                assert 1 == f_res.call_count

    @pytest.mark.parametrize("data, request_bundle_name", [
        (['support-180301-13-35-23.tar.gz'], 'xsupport-180301-01-15-13.tar.gz'),
        ([], 'support-180301-13-13-13.tar.gz')
    ])
    async def test_get_support_bundle_by_name_not_found(self, client, support_bundles_dir_path, data, request_bundle_name):
        path = support_bundles_dir_path / 'support'
        with patch.object(support, '_get_support_dir', return_value=path):
            with patch('os.path.isdir', return_value=True):
                with patch('os.walk') as mockwalk:
                    mockwalk.return_value = [(path, [], data)]
                    resp = await client.get('/fledge/support/{}'.format(request_bundle_name))
                    assert 404 == resp.status
                    assert '{} not found'.format(request_bundle_name) == resp.reason
            mockwalk.assert_called_once_with(path)

    async def test_get_support_bundle_by_name_bad_request(self, client):
        resp = await client.get('/fledge/support/support-180301-13-35-23.tar')
        assert 400 == resp.status
        assert 'Bundle file extension is invalid' == resp.reason

    async def test_get_support_bundle_by_name_no_dir(self, client, support_bundles_dir_path):
        path = support_bundles_dir_path / 'invalid'
        with patch.object(support, '_get_support_dir', return_value=path):
            with patch('os.path.isdir', return_value=False) as mockisdir:
                resp = await client.get('/fledge/support/bla.tar.gz')
                assert 404 == resp.status
                assert 'Support bundle directory does not exist' == resp.reason
            mockisdir.assert_called_once_with(path)

    async def test_create_support_bundle(self, client):
        async def mock_build():
            return 'support-180301-13-35-23.tar.gz'

        with patch.object(SupportBuilder, "__init__", return_value=None):
            with patch.object(SupportBuilder, "build", return_value=mock_build()):
                resp = await client.post('/fledge/support')
                res = await resp.text()
                jdict = json.loads(res)
                assert 200 == resp.status
                assert {"bundle created": "support-180301-13-35-23.tar.gz"} == jdict

    async def test_create_support_bundle_exception(self, client):
        with patch.object(SupportBuilder, "__init__", return_value=None):
            with patch.object(SupportBuilder, "build", side_effect=RuntimeError("blah")):
                resp = await client.post('/fledge/support')
                assert 500 == resp.status
                assert "Support bundle could not be created. blah" == resp.reason

    async def test_get_syslog_entries_all_ok(self, client):
        def mock_syslog():
            return """
        echo "Mar 19 14:00:53 nerd51-ThinkPad Fledge[18809] INFO: server: fledge.services.core.server: start core
        Mar 19 14:00:53 nerd51-ThinkPad Fledge[18809] INFO: server: fledge.services.core.server: Management API started on http://0.0.0.0:38311
        Mar 19 14:00:53 nerd51-ThinkPad Fledge[18809] INFO: server: fledge.services.core.server: start storage, from directory /home/asinha/Development/Fledge/scripts
        Mar 19 14:00:54 nerd51-ThinkPad Fledge[18809] INFO: service_registry: fledge.services.core.service_registry.service_registry: Registered service instance id=479a90ec-0d1d-4845-b2c5-f1d9ce72ac8e: <Fledge Storage, type=Storage, protocol=http, address=localhost, service port=33395, management port=45952, status=1>
        Mar 19 14:00:58 nerd51-ThinkPad Fledge[18809] INFO: server: fledge.services.core.server: start scheduler
        Mar 19 14:00:58 nerd51-ThinkPad Fledge Storage[18809]: Registered configuration category STORAGE, registration id 3db674a7-9569-4950-a328-1204834fba7e
        Mar 19 14:00:58 nerd51-ThinkPad Fledge[18809] INFO: scheduler: fledge.services.core.scheduler.scheduler: Starting Scheduler: Management port received is 38311
        Mar 19 14:00:58 nerd51-ThinkPad Fledge[18809] INFO: scheduler: fledge.services.core.scheduler.scheduler: Scheduled task for schedule 'purge' to start at 2018-03-19 15:00:58.912532
        Mar 19 14:00:58 nerd51-ThinkPad Fledge[18809] INFO: scheduler: fledge.services.core.scheduler.scheduler: Scheduled task for schedule 'stats collection' to start at 2018-03-19 14:01:13.912532
        Mar 19 14:00:58 nerd51-ThinkPad Fledge[18809] INFO: scheduler: fledge.services.core.scheduler.scheduler: Scheduled task for schedule 'certificate checker' to start at 2018-03-19 15:05:00
        Apr 22 13:59:39 aj Fledge S1[28584] INFO: sinusoid: module.name: Sinusoid plugin_init called
        Apr 22 13:57:08 aj Fledge S2[26398] INFO: sinusoid: module.name: Sinusoid plugin_reconfigure called
        Apr 22 14:04:59 aj Fledge HT[7080] INFO: sending_process: sending_process_HT: Started"
        """

        with patch.object(support, "__GET_SYSLOG_CMD_TEMPLATE", mock_syslog()):
            with patch.object(support, "__GET_SYSLOG_TOTAL_MATCHED_LINES", """echo "13" """):
                resp = await client.get('/fledge/syslog')
                res = await resp.text()
                jdict = json.loads(res)
                assert 200 == resp.status
                assert 13 == jdict['count']
                assert 'INFO' in jdict['logs'][0]
                assert 'Fledge' in jdict['logs'][0]
                assert 'Fledge Storage' in jdict['logs'][5]

    async def test_get_syslog_entries_all_with_level_error(self, client):
        def mock_syslog():
            return """
            echo "Sep 12 13:31:41 nerd-034 Fledge PI[9241] ERROR: sending_process: sending_process_PI: cannot complete the sending operation
            Dec 18 15:15:10 aj-ub1804 Fledge OMF[12145]: FATAL: Signal 11 (Segmentation fault) trapped:
            Dec 18 15:15:10 aj-ub1804 Fledge OMF[12145]: INFO: Signal 11 (Segmentation fault) trapped:"
            """

        with patch.object(support, "__GET_SYSLOG_CMD_WITH_ERROR_TEMPLATE", mock_syslog()):
            with patch.object(support, "__GET_SYSLOG_ERROR_MATCHED_LINES", """echo "2" """):
                resp = await client.get('/fledge/syslog?level=error')
                res = await resp.text()
                jdict = json.loads(res)
                assert 200 == resp.status
                assert 2 == jdict['count']
                assert 'ERROR' in jdict['logs'][0]

    async def test_get_syslog_entries_all_with_level_warning(self, client):
        def mock_syslog():
            return """
            echo "Sep 12 14:31:36 nerd-034 Fledge Storage[8683]: SQLite3 storage plugin raising error: UNIQUE constraint failed: readings.read_key
            Sep 12 17:42:23 nerd-034 Fledge[16637] WARNING: server: fledge.services.core.server: A Fledge PID file has been found: [/home/fledge/Development/Fledge/data/var/run/fledge.core.pid] found, ignoring it."
            """
        with patch.object(support, "__GET_SYSLOG_CMD_WITH_WARNING_TEMPLATE", mock_syslog()):
            with patch.object(support, "__GET_SYSLOG_WARNING_MATCHED_LINES", """echo "2" """):
                resp = await client.get('/fledge/syslog?level=warning')
                res = await resp.text()
                jdict = json.loads(res)
                assert 200 == resp.status
                assert 2 == jdict['count']
                assert 'error' in jdict['logs'][0]
                assert 'WARNING' in jdict['logs'][1]

    async def test_get_syslog_entries_from_storage(self, client):
        def mock_syslog():
            return """
            echo "Sep 12 14:31:41 nerd-034 Fledge Storage[8874]: Starting service...
            Sep 12 14:46:36 nerd-034 Fledge Storage[8683]: SQLite3 storage plugin raising error: UNIQUE constraint failed: readings.read_key
            Sep 12 14:56:41 nerd-034 Fledge Storage[8979]: warning No directory found"
            """
        with patch.object(support, "__GET_SYSLOG_CMD_TEMPLATE", mock_syslog()):
            with patch.object(support, "__GET_SYSLOG_TOTAL_MATCHED_LINES", """echo "3" """):
                resp = await client.get('/fledge/syslog?source=Storage')
                res = await resp.text()
                jdict = json.loads(res)
                assert 200 == resp.status
                assert 3 == jdict['count']
                assert 'Fledge Storage' in jdict['logs'][0]
                assert 'error' in jdict['logs'][1]
                assert 'warning' in jdict['logs'][2]

    async def test_get_syslog_entries_from_storage_with_level_warning(self, client):
        def mock_syslog():
            return """
            echo "Sep 12 14:31:36 nerd-034 Fledge Storage[8683]: SQLite3 storage plugin raising error: UNIQUE constraint failed: readings.read_key
            Sep 12 14:46:41 nerd-034 Fledge Storage[8979]: warning No directory found"
            """
        with patch.object(support, "__GET_SYSLOG_CMD_WITH_WARNING_TEMPLATE", mock_syslog()):
            with patch.object(support, "__GET_SYSLOG_WARNING_MATCHED_LINES", """echo "3" """):
                resp = await client.get('/fledge/syslog?source=storage&level=warning')
                res = await resp.text()
                jdict = json.loads(res)
                assert 200 == resp.status
                assert 3 == jdict['count']
                assert 'Fledge Storage' in jdict['logs'][0]
                assert 'error' in jdict['logs'][0]
                assert 'warning' in jdict['logs'][1]

    @pytest.mark.parametrize("param, message", [
        ("__DEFAULT_LIMIT", "Limit must be a positive integer"),
        ("__DEFAULT_OFFSET", "Offset must be a positive integer OR Zero"),
    ])
    async def test_get_syslog_entries_exception(self, client, param, message):
        with patch.object(support, param, "garbage"):
            resp = await client.get('/fledge/syslog')
            assert 400 == resp.status
            assert message == resp.reason

    async def test_get_syslog_entries_cmd_exception(self, client):
        msg = 'Internal Server Error'
        with patch.object(subprocess, "Popen", side_effect=Exception(msg)):
            resp = await client.get('/fledge/syslog')
            assert 500 == resp.status
            assert msg == resp.reason

    async def test_get_syslog_entries_from_name(self, client):
        def mock_syslog():
            return """echo "Apr 23 18:30:21 aj Fledge Sine 1[21288] ERROR: sinusoid: module.name: Sinusoid plugin_init" 
            """
        with patch.object(support, "__GET_SYSLOG_CMD_TEMPLATE", mock_syslog()):
            with patch.object(support, "__GET_SYSLOG_TOTAL_MATCHED_LINES", """echo "1" """):
                resp = await client.get('/fledge/syslog?source=Sine 1')
                assert 200 == resp.status
                res = await resp.text()
                jdict = json.loads(res)
                assert 1 == jdict['count']
                assert 'Fledge Sine 1' in jdict['logs'][0]

    @pytest.mark.parametrize("template_name, matched_lines, level, actual_count", [
        ('__GET_SYSLOG_CMD_WITH_ERROR_TEMPLATE', '__GET_SYSLOG_ERROR_MATCHED_LINES', 'error', 0),
        ('__GET_SYSLOG_CMD_WITH_INFO_TEMPLATE', '__GET_SYSLOG_INFO_MATCHED_LINES', 'info', 3)
    ])
    async def test_get_syslog_entries_from_name_with_level(self, client, template_name, matched_lines, level,
                                                           actual_count):
        def mock_syslog(_level):
            if _level == 'info':
                return """echo "Apr 23 18:30:21 aj Fledge HT[31901] INFO: sending_process: sending_process_HT: Started
                 Apr 23 18:48:52 aj Fledge HT[31901] INFO: sending_process: sending_process_HT: Stopped
                 Apr 23 18:48:52 aj Fledge HT[31901] INFO: sending_process: sending_process_HT: Execution completed" """
            else:
                return """echo "" """
        with patch.object(support, template_name, mock_syslog(level)):
            with patch.object(support, matched_lines, """echo "{}" """.format(actual_count)):
                resp = await client.get('/fledge/syslog?source=HT&level={}'.format(level))
                assert 200 == resp.status
                res = await resp.text()
                jdict = json.loads(res)
                assert actual_count == jdict['count']

    @pytest.mark.parametrize("level", [
        1,
        "blah",
        "panic",
        "emerg",
        "alert",
        "crit",
        "notice"
    ])
    async def test_bad_level_in_syslog_entry(self, client, level):
        resp = await client.get('/fledge/syslog?level={}'.format(level))
        msg = "{} is invalid level. Supported levels are ['info', 'warning', 'error', 'debug']".format(level)
        assert 400 == resp.status
        assert msg == resp.reason
        res = await resp.text()
        jdict = json.loads(res)
        assert msg == jdict['message']

    @pytest.mark.parametrize("template_name, matched_lines, level, actual_count", [
        ('__GET_SYSLOG_CMD_WITH_INFO_TEMPLATE', '__GET_SYSLOG_INFO_MATCHED_LINES', 'info', 7),
        ('__GET_SYSLOG_CMD_WITH_ERROR_TEMPLATE', '__GET_SYSLOG_ERROR_MATCHED_LINES', 'error', 4),
        ('__GET_SYSLOG_CMD_WITH_WARNING_TEMPLATE', '__GET_SYSLOG_WARNING_MATCHED_LINES', 'warning', 5),
        ('__GET_SYSLOG_CMD_TEMPLATE', '__GET_SYSLOG_TOTAL_MATCHED_LINES', 'debug', 8)
    ])
    async def test_get_syslog_entries_with_level(self, client, template_name, matched_lines, level, actual_count):
        def mock_syslog(_level):
            if _level == 'info':
                return """echo "Dec 21 10:20:03 aj-ub1804 Fledge[14623] WARNING: server: fledge.services.core.server: A Fledge PID file has been found.
                Dec 21 12:20:03 aj-ub1804 Fledge[14623] ERROR: change_callback: fledge.services.core.interest_registry.change_callback: Unable to notify microservice with uuid dc2b2f3a-0310-426f-8d1c-8bd3853fcf2f due to exception
                Dec 12 13:31:41 aj-ub1804 Fledge PI[9241] ERROR: sending_process: sending_process_PI: cannot complete the sending operation
                Dec 21 15:15:10 aj-ub1804 Fledge OMF[12145]: FATAL: Signal 11 (Segmentation fault) trapped:
                Dec 21 16:52:48 aj-ub1804 Fledge[24953] INFO: scheduler: fledge.services.core.scheduler.scheduler: Service HTC records successfully removed
                Dec 21 16:52:54 aj-ub1804 Fledge[24953] INFO: service_registry: fledge.services.core.service_registry.service_registry
                Dec 21 25:15:10 aj-ub1804 Fledge OMF[12145]: FATAL: (0) 00x55ac77b9d1b9 handler(int) + 73---------"
                """
            elif _level == 'warning':
                return """echo "Dec 21 10:20:03 aj-ub1804 Fledge[14623] WARNING: server: fledge.services.core.server: A Fledge PID file has been found.
                Dec 21 12:20:03 aj-ub1804 Fledge[14623] ERROR: change_callback: fledge.services.core.interest_registry.change_callback: Unable to notify microservice with uuid dc2b2f3a-0310-426f-8d1c-8bd3853fcf2f due to exception
                Dec 12 13:31:41 aj-ub1804 Fledge PI[9241] ERROR: sending_process: sending_process_PI: cannot complete the sending operation
                Dec 21 15:15:10 aj-ub1804 Fledge OMF[12145]: FATAL: Signal 11 (Segmentation fault) trapped:
                Dec 21 25:15:10 aj-ub1804 Fledge OMF[12145]: FATAL: (0) 00x55ac77b9d1b9 handler(int) + 73---------" """
            elif _level == 'error':
                return """echo "Dec 21 12:20:03 aj-ub1804 Fledge[14623] ERROR: change_callback: fledge.services.core.interest_registry.change_callback: Unable to notify microservice with uuid dc2b2f3a-0310-426f-8d1c-8bd3853fcf2f due to exception
                Dec 12 13:31:41 aj-ub1804 Fledge PI[9241] ERROR: sending_process: sending_process_PI: cannot complete the sending operation
                Dec 21 15:15:10 aj-ub1804 Fledge OMF[12145]: FATAL: Signal 11 (Segmentation fault) trapped:
                Dec 21 25:15:10 aj-ub1804 Fledge OMF[12145]: FATAL: (0) 00x55ac77b9d1b9 handler(int) + 73---------" """
            else:
                return """echo "Dec 21 10:20:03 aj-ub1804 Fledge[14623] WARNING: server: fledge.services.core.server: A Fledge PID file has been found.
                Dec 21 12:20:03 aj-ub1804 Fledge[14623] ERROR: change_callback: fledge.services.core.interest_registry.change_callback: Unable to notify microservice with uuid dc2b2f3a-0310-426f-8d1c-8bd3853fcf2f due to exception
                Dec 12 13:31:41 aj-ub1804 Fledge PI[9241] ERROR: sending_process: sending_process_PI: cannot complete the sending operation
                Dec 21 15:15:10 aj-ub1804 Fledge OMF[12145]: FATAL: Signal 11 (Segmentation fault) trapped:
                Dec 21 16:52:48 aj-ub1804 Fledge[24953] INFO: scheduler: fledge.services.core.scheduler.scheduler: Service HTC records successfully removed
                Dec 21 16:52:54 aj-ub1804 Fledge[24953] INFO: service_registry: fledge.services.core.service_registry.service_registry
                Dec 21 25:15:10 aj-ub1804 Fledge OMF[12145]: FATAL: (0) 00x55ac77b9d1b9 handler(int) + 73---------
                Dec 21 25:15:10 aj-ub1804 Fledge sin[11011]: DEBUG: 'sinusoid' plugin reconfigure called" """

        with patch.object(support, template_name, mock_syslog(level)):
            with patch.object(support, matched_lines, """echo "{}" """.format(actual_count)):
                resp = await client.get('/fledge/syslog?level={}'.format(level))
                assert 200 == resp.status
                res = await resp.text()
                jdict = json.loads(res)
                assert actual_count == jdict['count']
