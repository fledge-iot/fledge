import pytest
import json
import asyncio
import aiohttp
from unittest.mock import MagicMock
from unittest.mock import patch
from unittest.mock import Mock
from unittest.mock import call
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.services.core.service_registry.service_registry import ServiceRegistry
from foglamp.common.storage_client.storage_client import StorageClient
from foglamp.services.core.service_registry import exceptions as service_registry_exceptions
from foglamp.services.core.interest_registry.interest_registry import InterestRegistry
from foglamp.services.core.interest_registry.interest_registry import InterestRegistrySingleton
from foglamp.services.core.interest_registry import exceptions as interest_registry_exceptions
import foglamp.services.core.interest_registry.change_callback as cb


__author__ = "Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("common", "interest-registry")
class TestChangeCallback:
    @pytest.fixture()
    def reset_state(self):
        # executed before each test
        InterestRegistrySingleton._shared_state = {}
        del ServiceRegistry._registry[:]
        yield
        InterestRegistrySingleton._shared_state = {}
        del ServiceRegistry._registry[:]

    @pytest.mark.asyncio
    async def test_run_good(self, reset_state):
        storage_client_mock = MagicMock(spec=StorageClient)
        cfg_mgr = ConfigurationManager(storage_client_mock)

        s_id_1 = ServiceRegistry.register(
            'sname1', 'Storage', 'saddress1', 1, 1, 'http')
        s_id_2 = ServiceRegistry.register(
            'sname2', 'Southbound', 'saddress2', 2, 2, 'http')
        s_id_3 = ServiceRegistry.register(
            'sname3', 'Southbound', 'saddress3', 3, 3, 'http')
        i_reg = InterestRegistry(cfg_mgr)
        id_1_1 = i_reg.register(s_id_1, 'catname1')
        id_1_2 = i_reg.register(s_id_1, 'catname2')
        id_2_1 = i_reg.register(s_id_2, 'catname1')
        id_2_2 = i_reg.register(s_id_2, 'catname2')
        id_3_3 = i_reg.register(s_id_3, 'catname3')

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
        cm_get_patch.assert_called_once_with('catname1')
        post_patch.assert_has_calls([call('http://saddress1:1/foglamp/change', data='{"category": "catname1", "items": null}', headers={'content-type': 'application/json'}), call(
            'http://saddress2:2/foglamp/change', data='{"category": "catname1", "items": null}', headers={'content-type': 'application/json'})])
        with patch.object(ConfigurationManager, 'get_category_all_items', return_value=async_mock(None)) as cm_get_patch:
            with patch.object(aiohttp.ClientSession, 'post', return_value=AsyncSessionContextManagerMock()) as post_patch:
                await cb.run('catname2')
        cm_get_patch.assert_called_once_with('catname2')
        post_patch.assert_has_calls([call('http://saddress1:1/foglamp/change', data='{"category": "catname2", "items": null}', headers={'content-type': 'application/json'}), call(
            'http://saddress2:2/foglamp/change', data='{"category": "catname2", "items": null}', headers={'content-type': 'application/json'})])
        with patch.object(ConfigurationManager, 'get_category_all_items', return_value=async_mock(None)) as cm_get_patch:
            with patch.object(aiohttp.ClientSession, 'post', return_value=AsyncSessionContextManagerMock()) as post_patch:
                await cb.run('catname3')
        cm_get_patch.assert_called_once_with('catname3')
        post_patch.assert_called_once_with(
            'http://saddress3:3/foglamp/change', data='{"category": "catname3", "items": null}', headers={'content-type': 'application/json'})

    @pytest.mark.asyncio
    async def test_run_empty_interests(self, reset_state):
        storage_client_mock = MagicMock(spec=StorageClient)
        cfg_mgr = ConfigurationManager(storage_client_mock)

        s_id_1 = ServiceRegistry.register(
            'sname1', 'Storage', 'saddress1', 1, 1, 'http')
        s_id_2 = ServiceRegistry.register(
            'sname2', 'Southbound', 'saddress2', 2, 2, 'http')
        s_id_3 = ServiceRegistry.register(
            'sname3', 'Southbound', 'saddress3', 3, 3, 'http')
        i_reg = InterestRegistry(cfg_mgr)

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
        cm_get_patch.assert_not_called()
        post_patch.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_no_intrests_in_cat(self, reset_state):
        storage_client_mock = MagicMock(spec=StorageClient)
        cfg_mgr = ConfigurationManager(storage_client_mock)

        s_id_1 = ServiceRegistry.register(
            'sname1', 'Storage', 'saddress1', 1, 1, 'http')
        s_id_2 = ServiceRegistry.register(
            'sname2', 'Southbound', 'saddress2', 2, 2, 'http')
        s_id_3 = ServiceRegistry.register(
            'sname3', 'Southbound', 'saddress3', 3, 3, 'http')
        i_reg = InterestRegistry(cfg_mgr)
        id_1_2 = i_reg.register(s_id_1, 'catname2')
        id_2_2 = i_reg.register(s_id_2, 'catname2')
        id_3_3 = i_reg.register(s_id_3, 'catname3')

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
        cm_get_patch.assert_not_called()
        post_patch.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_missing_service_record(self, reset_state):
        storage_client_mock = MagicMock(spec=StorageClient)
        cfg_mgr = ConfigurationManager(storage_client_mock)

        s_id_1 = ServiceRegistry.register(
            'sname1', 'Storage', 'saddress1', 1, 1, 'http')
        s_id_2 = ServiceRegistry.register(
            'sname2', 'Southbound', 'saddress2', 2, 2, 'http')
        s_id_3 = ServiceRegistry.register(
            'sname3', 'Southbound', 'saddress3', 3, 3, 'http')
        i_reg = InterestRegistry(cfg_mgr)
        id_fake_1 = i_reg.register('fakeid', 'catname1')
        id_1_1 = i_reg.register(s_id_1, 'catname1')
        id_1_2 = i_reg.register(s_id_1, 'catname2')
        id_2_1 = i_reg.register(s_id_2, 'catname1')
        id_2_2 = i_reg.register(s_id_2, 'catname2')
        id_3_3 = i_reg.register(s_id_3, 'catname3')

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
        cm_get_patch.assert_called_once_with('catname1')
        exception_patch.assert_called_once_with('Unable to notify microservice with uuid %s as it is not found in the service registry', 'fakeid')
        post_patch.assert_has_calls([call('http://saddress1:1/foglamp/change', data='{"category": "catname1", "items": null}', headers={'content-type': 'application/json'}), call(
            'http://saddress2:2/foglamp/change', data='{"category": "catname1", "items": null}', headers={'content-type': 'application/json'})])

    @pytest.mark.asyncio
    async def test_run_general_exception(self, reset_state):
        storage_client_mock = MagicMock(spec=StorageClient)
        cfg_mgr = ConfigurationManager(storage_client_mock)

        s_id_1 = ServiceRegistry.register(
            'sname1', 'Storage', 'saddress1', 1, 1, 'http')
        i_reg = InterestRegistry(cfg_mgr)
        id_1_1 = i_reg.register(s_id_1, 'catname1')

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
        cm_get_patch.assert_called_once_with('catname1')
        exception_patch.assert_called_once_with('Unable to notify microservice with uuid %s due to exception: %s', s_id_1, '')
        post_patch.assert_has_calls([call('http://saddress1:1/foglamp/change', data='{"category": "catname1", "items": null}', headers={'content-type': 'application/json'})])
