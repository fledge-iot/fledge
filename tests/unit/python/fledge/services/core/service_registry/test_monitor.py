# -*- coding: utf-8 -*-
import asyncio
from unittest.mock import MagicMock
from unittest.mock import patch
import pytest

import aiohttp
from fledge.services.core.service_registry.monitor import Monitor
from fledge.services.core.service_registry.service_registry import ServiceRegistry
from fledge.common.service_record import ServiceRecord

__author__ = "Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("services", "core", "service-registry")
class TestMonitor:

    def setup_method(self):
        ServiceRegistry._registry = []

    def teardown_method(self):
        ServiceRegistry._registry = []

    @pytest.mark.asyncio
    async def test__monitor_good_uptime(self):
        async def async_mock(return_value):
            return return_value
        # used to mock client session context manager

        class AsyncSessionContextManagerMock(MagicMock):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            async def __aenter__(self):
                client_response_mock = MagicMock(spec=aiohttp.ClientResponse)
                # mock response (good)
                client_response_mock.text.side_effect = [
                    async_mock('{"uptime": "bla"}')]
                return client_response_mock

            async def __aexit__(self, *args):
                return None
        # as monitor loop is as infinite loop, this exception is thrown when we need to exit the loop

        class TestMonitorException(Exception):
            pass
        # register a service
        with patch.object(ServiceRegistry._logger, 'info') as log_info:
            s_id_1 = ServiceRegistry.register(
                'sname1', 'Storage', 'saddress1', 1, 1, 'protocol1')
        assert 1 == log_info.call_count
        args, kwargs = log_info.call_args
        assert args[0].startswith('Registered service instance id=')
        assert args[0].endswith(': <sname1, type=Storage, protocol=protocol1, address=saddress1, service port=1, '
                                'management port=1, status=1, token=None>')
        monitor = Monitor()
        monitor._sleep_interval = Monitor._DEFAULT_SLEEP_INTERVAL
        monitor._max_attempts = Monitor._DEFAULT_MAX_ATTEMPTS

        # throw the TestMonitorException when sleep is called (end of infinite loop)
        with patch.object(Monitor, '_sleep', side_effect=TestMonitorException()):
            with patch.object(aiohttp.ClientSession, 'get', return_value=AsyncSessionContextManagerMock()):
                with pytest.raises(Exception) as excinfo:
                    await monitor._monitor_loop()
                assert excinfo.type is TestMonitorException
        # service is good, so it should remain in the service registry
        assert len(ServiceRegistry.get(idx=s_id_1)) is 1
        assert ServiceRegistry.get(idx=s_id_1)[0]._status is ServiceRecord.Status.Running

    @pytest.mark.asyncio
    async def test__monitor_exceed_attempts(self, mocker):
        class AsyncSessionContextManagerMock(MagicMock):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            async def __aenter__(self):
                # mock response (error- exception)
                raise Exception("test")

            async def __aexit__(self, *args):
                return None
        # as monitor loop is as infinite loop, this exception is thrown when we need to exit the loop

        class TestMonitorException(Exception):
            pass

        # register a service
        s_id_1 = ServiceRegistry.register(
            'sname1', 'Storage', 'saddress1', 1, 1, 'protocol1')
        monitor = Monitor()
        monitor._sleep_interval = Monitor._DEFAULT_SLEEP_INTERVAL
        monitor._max_attempts = Monitor._DEFAULT_MAX_ATTEMPTS

        sleep_side_effect_list = list()
        # _MAX_ATTEMPTS is 15
        # throw exception on the 16th time sleep is called - the first 15 sleeps are used during retries
        for i in range(0, 15):
            sleep_side_effect_list.append(asyncio.sleep(.01))
        sleep_side_effect_list.append(TestMonitorException())
        with patch.object(Monitor, '_sleep', side_effect=sleep_side_effect_list):
            with patch.object(aiohttp.ClientSession, 'get', return_value=AsyncSessionContextManagerMock()):
                with pytest.raises(Exception) as excinfo:
                    await monitor._monitor_loop()
                assert excinfo.type in [TestMonitorException, TypeError]

        assert ServiceRegistry.get(idx=s_id_1)[0]._status is ServiceRecord.Status.Failed
