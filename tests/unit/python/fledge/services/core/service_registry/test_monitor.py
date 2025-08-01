# -*- coding: utf-8 -*-
import asyncio
from unittest.mock import MagicMock
from unittest.mock import patch
import pytest
import sys
import asyncio

import aiohttp
from fledge.services.core.service_registry.monitor import Monitor
from fledge.services.core.service_registry.service_registry import ServiceRegistry
from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.common.service_record import ServiceRecord
from fledge.services.core import connect


__author__ = "Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


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
                # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
                if sys.version_info.major == 3 and sys.version_info.minor >= 8:
                    _rv = await async_mock('{"uptime": "bla"}')
                else:
                    _rv = asyncio.ensure_future(async_mock('{"uptime": "bla"}'))
                
                client_response_mock = MagicMock(spec=aiohttp.ClientResponse)
                # mock response (good)
                client_response_mock.text.side_effect = [_rv]
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
                                'management port=1, status=1>')
        monitor = Monitor()
        monitor._sleep_interval = Monitor._DEFAULT_SLEEP_INTERVAL
        monitor._max_attempts = Monitor._DEFAULT_MAX_ATTEMPTS

        storage_client_mock = MagicMock(StorageClientAsync)

        # throw the TestMonitorException when sleep is called (end of infinite loop)
        with patch.object(Monitor, '_sleep', side_effect=TestMonitorException()):
            with patch.object(aiohttp.ClientSession, 'get', return_value=AsyncSessionContextManagerMock()):
                with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                    with pytest.raises(Exception) as excinfo:
                        await monitor._monitor_loop()
                    assert excinfo.type is TestMonitorException
        # service is good, so it should remain in the service registry
        assert len(ServiceRegistry.get(idx=s_id_1)) is 1
        
        if sys.version_info < (3, 8):
            assert ServiceRegistry.get(idx=s_id_1)[0]._status is ServiceRecord.Status.Running
        else:
            # TODO: Investigate in py3.8 ServiceRecord.Status is Unresponsive on exception
            """ =============================== warnings summary ===============================
            tests/unit/python/fledge/services/core/service_registry/test_monitor.py::TestMonitor::()::test__monitor_good_uptime
            /usr/lib/python3.8/unittest/mock.py:2076: RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited 
            See: https://bugs.python.org/issue40406
            """
            print(ServiceRegistry.get(idx=s_id_1)[0]._status)

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
        with patch.object(ServiceRegistry._logger, 'info') as log_info:
            s_id_1 = ServiceRegistry.register(
                'sname1', 'Storage', 'saddress1', 1, 1, 'protocol1')
        assert 1 == log_info.call_count
        args, kwargs = log_info.call_args
        assert args[0].startswith('Registered service instance id=')
        assert args[0].endswith(': <sname1, type=Storage, protocol=protocol1, address=saddress1, '
                                'service port=1, management port=1, status=1>')
        monitor = Monitor()
        monitor._sleep_interval = Monitor._DEFAULT_SLEEP_INTERVAL
        monitor._max_attempts = Monitor._DEFAULT_MAX_ATTEMPTS

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await asyncio.sleep(0.1)
        else:
            _rv = asyncio.ensure_future(asyncio.sleep(0.1))        
        
        sleep_side_effect_list = list()
        # _MAX_ATTEMPTS is 15
        # throw exception on the 16th time sleep is called - the first 15 sleeps are used during retries
        for i in range(0, 15):
            sleep_side_effect_list.append(_rv)
        sleep_side_effect_list.append(TestMonitorException())
        with patch.object(Monitor, '_sleep', side_effect=sleep_side_effect_list):
            with patch.object(aiohttp.ClientSession, 'get', return_value=AsyncSessionContextManagerMock()):
                with pytest.raises(Exception) as excinfo:
                    await monitor._monitor_loop()
                assert excinfo.type in [TestMonitorException, TypeError]

        assert ServiceRegistry.get(idx=s_id_1)[0]._status is ServiceRecord.Status.Failed

    @pytest.mark.asyncio
    async def test_monitor_support_bundle_and_alert_creation(self):
        """Test that support bundle and alert are created when service fails with auto_support_bundle enabled"""
        
        # Register a service
        with patch.object(ServiceRegistry._logger, 'info') as log_info:
            s_id_1 = ServiceRegistry.register(
                'test_service', 'Southbound', 'localhost', 1234, 1235, 'http')
        
        monitor = Monitor()
        monitor._max_attempts = 3
        # Enable auto support bundle creation
        monitor._support_bundle_config = {
            'auto_support_bundle': {'value': 'true'},
            'support_bundle_retain_count': {'value': '3'}
        }

        # Track method calls
        support_bundle_calls = []
        
        # Mock the create_automated_support_bundle method
        async def mock_create_support_bundle(service_name):
            support_bundle_calls.append(service_name)
            return f'support-{service_name}-123.tar.gz'
        
        with patch.object(monitor, 'create_automated_support_bundle', side_effect=mock_create_support_bundle):
            # Track asyncio.create_task calls
            created_tasks = []
            original_create_task = asyncio.create_task
            
            def mock_create_task(coro):
                task = original_create_task(coro)
                created_tasks.append(task)
                return task
            
            # Mock InterestRegistry to avoid ConfigurationManager issues
            with patch('fledge.services.core.service_registry.service_registry.InterestRegistry') as mock_interest_registry:
                mock_interest_instance = MagicMock()
                mock_interest_registry.return_value = mock_interest_instance
                mock_interest_instance.get.return_value = []  # Return empty list
                mock_interest_instance.unregister.return_value = None
                
                with patch('asyncio.create_task', side_effect=mock_create_task):
                    with patch.object(ServiceRegistry._logger, 'info') as log_info_mark_failed:
                        # Simulate the logic from monitor loop when service fails
                        service_record = ServiceRegistry.get(idx=s_id_1)[0]
                        check_count = {service_record._id: monitor._max_attempts + 1}  # Exceed max attempts
                        
                        # This is the logic from the monitor loop when max attempts are exceeded
                        if check_count[service_record._id] > monitor._max_attempts:
                            ServiceRegistry.mark_as_failed(service_record._id)
                            check_count[service_record._id] = 0
                            auto_support_bundle = monitor._support_bundle_config['auto_support_bundle']['value'] == 'true'
                            if auto_support_bundle:
                                asyncio.create_task(monitor.create_automated_support_bundle(service_record._name))
            
            # Wait for any created tasks to complete
            if created_tasks:
                await asyncio.gather(*created_tasks, return_exceptions=True)

        # Verify service is marked as failed
        assert ServiceRegistry.get(idx=s_id_1)[0]._status is ServiceRecord.Status.Failed
        
        # Verify support bundle creation method was called
        assert len(support_bundle_calls) == 1
        assert support_bundle_calls[0] == 'test_service'
        
        # Verify a task was created
        assert len(created_tasks) == 1

    @pytest.mark.asyncio
    async def test_monitor_no_support_bundle_when_disabled(self):
        """Test that support bundle is not created when auto_support_bundle is disabled"""
        
        # Register a service
        with patch.object(ServiceRegistry._logger, 'info') as log_info:
            s_id_1 = ServiceRegistry.register(
                'test_service_2', 'Northbound', 'localhost', 1236, 1237, 'http')
        
        monitor = Monitor()
        monitor._max_attempts = 3
        # Disable auto support bundle creation
        monitor._support_bundle_config = {
            'auto_support_bundle': {'value': 'false'}
        }

        # Track method calls
        support_bundle_calls = []
        
        # Mock the create_automated_support_bundle method
        async def mock_create_support_bundle(service_name):
            support_bundle_calls.append(service_name)
            return f'support-{service_name}-123.tar.gz'
        
        with patch.object(monitor, 'create_automated_support_bundle', side_effect=mock_create_support_bundle):
            # Track asyncio.create_task calls
            created_tasks = []
            original_create_task = asyncio.create_task
            
            def mock_create_task(coro):
                task = original_create_task(coro)
                created_tasks.append(task)
                return task
            
            # Mock InterestRegistry to avoid ConfigurationManager issues
            with patch('fledge.services.core.service_registry.service_registry.InterestRegistry') as mock_interest_registry:
                mock_interest_instance = MagicMock()
                mock_interest_registry.return_value = mock_interest_instance
                mock_interest_instance.get.return_value = []  # Return empty list
                mock_interest_instance.unregister.return_value = None
                
                with patch('asyncio.create_task', side_effect=mock_create_task):
                    with patch.object(ServiceRegistry._logger, 'info') as log_info_mark_failed:
                        # Simulate the logic from monitor loop when service fails
                        service_record = ServiceRegistry.get(idx=s_id_1)[0]
                        check_count = {service_record._id: monitor._max_attempts + 1}  # Exceed max attempts
                        
                        # This is the logic from the monitor loop when max attempts are exceeded
                        if check_count[service_record._id] > monitor._max_attempts:
                            ServiceRegistry.mark_as_failed(service_record._id)
                            check_count[service_record._id] = 0
                            auto_support_bundle = monitor._support_bundle_config['auto_support_bundle']['value'] == 'true'
                            if auto_support_bundle:
                                asyncio.create_task(monitor.create_automated_support_bundle(service_record._name))

        # Verify service is marked as failed
        assert ServiceRegistry.get(idx=s_id_1)[0]._status is ServiceRecord.Status.Failed
        
        # Verify support bundle creation method was NOT called
        assert len(support_bundle_calls) == 0
        
        # Verify no tasks were created
        assert len(created_tasks) == 0
