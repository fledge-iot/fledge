from unittest.mock import MagicMock, patch, Mock, call
import pytest

import aiohttp
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.services.core.service_registry.service_registry import ServiceRegistry
from foglamp.common.storage_client.storage_client import StorageClientAsync
from foglamp.services.core.interest_registry.interest_registry import InterestRegistry, InterestRegistrySingleton
import foglamp.services.core.interest_registry.change_callback as cb


__author__ = "Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("common", "interest-registry")
class TestChangeCallback:

    def setup_method(self):
        InterestRegistrySingleton._shared_state = {}
        ServiceRegistry._registry = []

    def teardown_method(self):
        InterestRegistrySingleton._shared_state = {}
        ServiceRegistry._registry = []

    @pytest.mark.asyncio
    async def test_run_good(self):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        cfg_mgr = ConfigurationManager(storage_client_mock)

        with patch.object(ServiceRegistry._logger, 'info') as log_info:
            s_id_1 = ServiceRegistry.register(
                'sname1', 'Storage', 'saddress1', 1, 1, 'http')
            s_id_2 = ServiceRegistry.register(
                'sname2', 'Southbound', 'saddress2', 2, 2, 'http')
            s_id_3 = ServiceRegistry.register(
                'sname3', 'Southbound', 'saddress3', 3, 3, 'http')
        assert 3 == log_info.call_count
        i_reg = InterestRegistry(cfg_mgr)
        i_reg.register(s_id_1, 'catname1')
        i_reg.register(s_id_1, 'catname2')
        i_reg.register(s_id_2, 'catname1')
        i_reg.register(s_id_2, 'catname2')
        i_reg.register(s_id_3, 'catname3')

        # used to mock client session context manager
        async def async_mock(return_value):
            return return_value

        class AsyncSessionContextManagerMock(MagicMock):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            async def __aenter__(self):
                client_response_mock = MagicMock(spec=aiohttp.ClientResponse)
                client_response_mock.text.side_effect = [async_mock(None)]
                status_mock = Mock()
                status_mock.side_effect = [200]
                client_response_mock.status = status_mock()
                return client_response_mock

            async def __aexit__(self, *args):
                return None

        with patch.object(ConfigurationManager, 'get_category_all_items', return_value=async_mock(None)) as cm_get_patch:
            with patch.object(aiohttp.ClientSession, 'post', return_value=AsyncSessionContextManagerMock()) as post_patch:
                await cb.run('catname1')
            post_patch.assert_has_calls([call('http://saddress1:1/foglamp/change', data='{"category": "catname1", "items": null}', headers={'content-type': 'application/json'}),
                                         call('http://saddress2:2/foglamp/change', data='{"category": "catname1", "items": null}', headers={'content-type': 'application/json'})])
        cm_get_patch.assert_called_once_with('catname1')

        with patch.object(ConfigurationManager, 'get_category_all_items', return_value=async_mock(None)) as cm_get_patch:
            with patch.object(aiohttp.ClientSession, 'post', return_value=AsyncSessionContextManagerMock()) as post_patch:
                await cb.run('catname2')
            post_patch.assert_has_calls([call('http://saddress1:1/foglamp/change', data='{"category": "catname2", "items": null}', headers={'content-type': 'application/json'}),
                                         call('http://saddress2:2/foglamp/change', data='{"category": "catname2", "items": null}', headers={'content-type': 'application/json'})])
        cm_get_patch.assert_called_once_with('catname2')

        with patch.object(ConfigurationManager, 'get_category_all_items', return_value=async_mock(None)) as cm_get_patch:
            with patch.object(aiohttp.ClientSession, 'post', return_value=AsyncSessionContextManagerMock()) as post_patch:
                await cb.run('catname3')
            post_patch.assert_called_once_with('http://saddress3:3/foglamp/change', data='{"category": "catname3", "items": null}', headers={'content-type': 'application/json'})
        cm_get_patch.assert_called_once_with('catname3')

    @pytest.mark.asyncio
    async def test_run_empty_interests(self):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        cfg_mgr = ConfigurationManager(storage_client_mock)

        with patch.object(ServiceRegistry._logger, 'info') as log_info:
            ServiceRegistry.register('sname1', 'Storage', 'saddress1', 1, 1, 'http')
            ServiceRegistry.register('sname2', 'Southbound', 'saddress2', 2, 2, 'http')
            ServiceRegistry.register('sname3', 'Southbound', 'saddress3', 3, 3, 'http')
        assert 3 == log_info.call_count
        InterestRegistry(cfg_mgr)

        # used to mock client session context manager
        async def async_mock(return_value):
            return return_value

        class AsyncSessionContextManagerMock(MagicMock):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            async def __aenter__(self):
                client_response_mock = MagicMock(spec=aiohttp.ClientResponse)
                client_response_mock.text.side_effect = [async_mock(None)]
                status_mock = Mock()
                status_mock.side_effect = [200]
                client_response_mock.status = status_mock()
                return client_response_mock

            async def __aexit__(self, *args):
                return None

        with patch.object(ConfigurationManager, 'get_category_all_items') as cm_get_patch:
            with patch.object(aiohttp.ClientSession, 'post') as post_patch:
                await cb.run('catname1')
            post_patch.assert_not_called()
        cm_get_patch.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_no_interests_in_cat(self):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        cfg_mgr = ConfigurationManager(storage_client_mock)

        with patch.object(ServiceRegistry._logger, 'info') as log_info:
            s_id_1 = ServiceRegistry.register(
                'sname1', 'Storage', 'saddress1', 1, 1, 'http')
            s_id_2 = ServiceRegistry.register(
                'sname2', 'Southbound', 'saddress2', 2, 2, 'http')
            s_id_3 = ServiceRegistry.register(
                'sname3', 'Southbound', 'saddress3', 3, 3, 'http')
        assert 3 == log_info.call_count
        i_reg = InterestRegistry(cfg_mgr)
        i_reg.register(s_id_1, 'catname2')
        i_reg.register(s_id_2, 'catname2')
        i_reg.register(s_id_3, 'catname3')

        # used to mock client session context manager
        async def async_mock(return_value):
            return return_value

        class AsyncSessionContextManagerMock(MagicMock):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            async def __aenter__(self):
                client_response_mock = MagicMock(spec=aiohttp.ClientResponse)
                client_response_mock.text.side_effect = [async_mock(None)]
                status_mock = Mock()
                status_mock.side_effect = [200]
                client_response_mock.status = status_mock()
                return client_response_mock

            async def __aexit__(self, *args):
                return None
        with patch.object(ConfigurationManager, 'get_category_all_items') as cm_get_patch:
            with patch.object(aiohttp.ClientSession, 'post') as post_patch:
                await cb.run('catname1')
            post_patch.assert_not_called()
        cm_get_patch.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_missing_service_record(self):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        cfg_mgr = ConfigurationManager(storage_client_mock)

        with patch.object(ServiceRegistry._logger, 'info') as log_info:
            s_id_1 = ServiceRegistry.register(
                'sname1', 'Storage', 'saddress1', 1, 1, 'http')
            s_id_2 = ServiceRegistry.register(
                'sname2', 'Southbound', 'saddress2', 2, 2, 'http')
            s_id_3 = ServiceRegistry.register(
                'sname3', 'Southbound', 'saddress3', 3, 3, 'http')
        assert 3 == log_info.call_count

        i_reg = InterestRegistry(cfg_mgr)
        i_reg.register('fakeid', 'catname1')
        i_reg.register(s_id_1, 'catname1')
        i_reg.register(s_id_1, 'catname2')
        i_reg.register(s_id_2, 'catname1')
        i_reg.register(s_id_2, 'catname2')
        i_reg.register(s_id_3, 'catname3')

        # used to mock client session context manager
        async def async_mock(return_value):
            return return_value

        class AsyncSessionContextManagerMock(MagicMock):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            async def __aenter__(self):
                client_response_mock = MagicMock(spec=aiohttp.ClientResponse)
                client_response_mock.text.side_effect = [async_mock(None)]
                status_mock = Mock()
                status_mock.side_effect = [200]
                client_response_mock.status = status_mock()
                return client_response_mock

            async def __aexit__(self, *args):
                return None

        with patch.object(ConfigurationManager, 'get_category_all_items', return_value=async_mock(None)) as cm_get_patch:
            with patch.object(aiohttp.ClientSession, 'post', return_value=AsyncSessionContextManagerMock()) as post_patch:
                with patch.object(cb._LOGGER, 'exception') as exception_patch:
                    await cb.run('catname1')
                exception_patch.assert_called_once_with(
                    'Unable to notify microservice with uuid %s as it is not found in the service registry', 'fakeid')
            post_patch.assert_has_calls([call('http://saddress1:1/foglamp/change', data='{"category": "catname1", "items": null}', headers={'content-type': 'application/json'}),
                                         call('http://saddress2:2/foglamp/change', data='{"category": "catname1", "items": null}', headers={'content-type': 'application/json'})])
        cm_get_patch.assert_called_once_with('catname1')

    @pytest.mark.asyncio
    async def test_run_general_exception(self):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        cfg_mgr = ConfigurationManager(storage_client_mock)

        with patch.object(ServiceRegistry._logger, 'info') as log_info:
            s_id_1 = ServiceRegistry.register('sname1', 'Storage', 'saddress1', 1, 1, 'http')
        assert 1 == log_info.call_count
        args, kwargs = log_info.call_args
        assert args[0].startswith('Registered service instance id=')
        assert args[0].endswith(': <sname1, type=Storage, protocol=http, address=saddress1, service port=1, management port=1, status=1>')

        i_reg = InterestRegistry(cfg_mgr)
        i_reg.register(s_id_1, 'catname1')

        # used to mock client session context manager
        async def async_mock(return_value):
            return return_value

        class AsyncSessionContextManagerMock(MagicMock):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            async def __aenter__(self):
                raise Exception

            async def __aexit__(self, *args):
                return None

        with patch.object(ConfigurationManager, 'get_category_all_items', return_value=async_mock(None)) as cm_get_patch:
            with patch.object(aiohttp.ClientSession, 'post', return_value=AsyncSessionContextManagerMock()) as post_patch:
                with patch.object(cb._LOGGER, 'exception') as exception_patch:
                    await cb.run('catname1')
                exception_patch.assert_called_once_with(
                    'Unable to notify microservice with uuid %s due to exception: %s', s_id_1, '')
            post_patch.assert_has_calls([call('http://saddress1:1/foglamp/change', data='{"category": "catname1", "items": null}', headers={'content-type': 'application/json'})])
        cm_get_patch.assert_called_once_with('catname1')
