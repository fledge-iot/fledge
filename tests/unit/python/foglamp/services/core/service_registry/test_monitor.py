# -*- coding: utf-8 -*-

import pytest

from unittest.mock import MagicMock
from unittest.mock import patch
from unittest.mock import call
import aiohttp
import json
import asyncio
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.common.storage_client.storage_client import StorageClient
from foglamp.common.audit_logger import AuditLogger
from foglamp.services.core import connect
from foglamp.services.core.service_registry.monitor import Monitor
from foglamp.services.core.service_registry.service_registry import ServiceRegistry
from foglamp.services.core.service_registry import exceptions as service_registry_exceptions

__author__ = "Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("core", "monitor")
class TestMonitor:
    @pytest.fixture
    def reset_service_registry(self):
        del ServiceRegistry._registry[:]
        yield
        del ServiceRegistry._registry[:]

    @pytest.mark.asyncio
    async def test__monitor_good_uptime(self, reset_service_registry):
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
        s_id_1 = ServiceRegistry.register(
            'sname1', 'Storage', 'saddress1', 1, 1,  'protocol1')
        monitor = Monitor()
        monitor._sleep_interval = Monitor._DEFAULT_SLEEP_INTERVAL

        # throw the TestMonitorException when sleep is called (end of infinite loop)
        with patch.object(Monitor, '_sleep', side_effect=TestMonitorException()):
            with patch.object(aiohttp.ClientSession, 'get', return_value=AsyncSessionContextManagerMock()):
                with pytest.raises(TestMonitorException) as excinfo:
                    await monitor._monitor_loop()
        # service is good, so it should remain in the service registry
        assert len(ServiceRegistry.get(idx=s_id_1)) is 1
        assert ServiceRegistry.get(idx=s_id_1)[0]._status is 1

    @pytest.mark.asyncio
    async def test__monitor_exceed_attempts(self, reset_service_registry):
        async def async_mock(return_value):
            return return_value
        # used to mock client session context manager

        class AsyncSessionContextManagerMock(MagicMock):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            async def __aenter__(self):
                # mock response (error- exception)
                raise Exception()

            async def __aexit__(self, *args):
                return None
        # as monitor loop is as infinite loop, this exception is thrown when we need to exit the loop

        class TestMonitorException(Exception):
            pass
        # register a service
        s_id_1 = ServiceRegistry.register(
            'sname1', 'Storage', 'saddress1', 1, 1,  'protocol1')
        monitor = Monitor()
        monitor._sleep_interval = Monitor._DEFAULT_SLEEP_INTERVAL
        sleep_side_effect_list = list()
        # _MAX_ATTEMPTS is 15
        # throw exception on the 16th time sleep is called - the first 15 sleeps are used during retries
        for i in range(0, 15):
            sleep_side_effect_list.append(async_mock(None))
        sleep_side_effect_list.append(TestMonitorException())
        with patch.object(Monitor, '_sleep', side_effect=sleep_side_effect_list):
            with patch.object(aiohttp.ClientSession, 'get', return_value=AsyncSessionContextManagerMock()):
                with pytest.raises(TestMonitorException) as excinfo:
                    await monitor._monitor_loop()
        # service is bad, so it would be removed from the service registry
        with pytest.raises(service_registry_exceptions.DoesNotExist) as excinfo:
            assert len(ServiceRegistry.get(idx=s_id_1)) is 0
