# -*- coding: utf-8 -*-

import pytest
import time
from unittest.mock import patch
from aiohttp import web
import asyncio
import sys
from fledge.common.storage_client.storage_client import ReadingsStorageClientAsync, StorageClientAsync
from fledge.common.process import FledgeProcess
from fledge.services.common.microservice import FledgeMicroservice, _logger
from fledge.common.microservice_management_client.microservice_management_client import MicroserviceManagementClient


__author__ = "Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# test abstract methods
# test FledgeProcess class things it needs
# test that it registers with core
# test the microservice management api

_DEFAULT_CONFIG = {
    'plugin': {
        'description': 'Python module name of the plugin to load',
        'type': 'string',
        'default': 'coap_listen',
        'value': 'coap_listen'
    },
    'local_services': {
        'description': 'Restrict microservice to localhost',
        'type': 'boolean',
        'default': 'false',
        'value': 'false',
    }
}


class TestFledgeMicroservice:

    def test_constructor_abstract_method_missing(self):
        with pytest.raises(TypeError):
            fm = FledgeMicroservice()
        with pytest.raises(TypeError):
            class FledgeMicroserviceImp(FledgeMicroservice):
                pass
            fm = FledgeMicroserviceImp()
        with pytest.raises(TypeError):
            class FledgeMicroserviceImp(FledgeMicroservice):
                async def change(self):
                    pass
                async def shutdown(self):
                    pass
            fm = FledgeMicroserviceImp()
        with pytest.raises(TypeError):
            class FledgeMicroserviceImp(FledgeMicroservice):
                def run(self):
                    pass
                async def shutdown(self):
                    pass
            fm = FledgeMicroserviceImp()
        with pytest.raises(TypeError):
            class FledgeMicroserviceImp(FledgeMicroservice):
                def run(self):
                    pass
                async def change(self):
                    pass
            fm = FledgeMicroserviceImp()

    def test_constructor_good(self, loop):
        class FledgeMicroserviceImp(FledgeMicroservice):
            def __init__(self):
                super().__init__()

            def run(self):
                pass

            async def change(self):
                pass

            async def shutdown(self):
                pass

            async def get_track(self):
                pass

            async def add_track(self):
                pass

        with patch.object(asyncio, 'get_event_loop', return_value=loop):
            with patch.object(sys, 'argv', ['pytest', '--address', 'corehost', '--port', '32333', '--name', 'sname']):
                with patch.object(MicroserviceManagementClient, '__init__', return_value=None) as mmc_patch:
                    with patch.object(MicroserviceManagementClient, 'create_configuration_category', return_value=None):
                        with patch.object(MicroserviceManagementClient, 'create_child_category',
                                          return_value=None):
                            with patch.object(MicroserviceManagementClient, 'get_configuration_category', return_value=_DEFAULT_CONFIG):
                                with patch.object(ReadingsStorageClientAsync, '__init__',
                                                  return_value=None) as rsc_async_patch:
                                    with patch.object(StorageClientAsync, '__init__',
                                                      return_value=None) as sc_async_patch:
                                        with patch.object(FledgeMicroservice, '_make_microservice_management_app', return_value=None) as make_patch:
                                             with patch.object(FledgeMicroservice, '_run_microservice_management_app', side_effect=None) as run_patch:
                                                 with patch.object(FledgeProcess, 'register_service_with_core', return_value={'id':'bla'}) as reg_patch:
                                                     with patch.object(FledgeMicroservice, '_get_service_registration_payload', return_value=None) as payload_patch:
                                                        fm = FledgeMicroserviceImp()
        # from FledgeProcess
        assert fm._core_management_host is 'corehost'
        assert fm._core_management_port == 32333
        assert fm._name is 'sname'
        assert hasattr(fm, '_core_microservice_management_client')
        assert hasattr(fm, '_readings_storage_async')
        assert hasattr(fm, '_storage_async')
        assert hasattr(fm, '_start_time')
        # from FledgeMicroservice
        assert hasattr(fm, '_microservice_management_app')
        assert hasattr(fm, '_microservice_management_handler')
        assert hasattr(fm, '_microservice_management_server')
        assert hasattr(fm, '_microservice_management_host')
        assert hasattr(fm, '_microservice_management_port')
        assert hasattr(fm, '_microservice_id')
        assert hasattr(fm, '_type')
        assert hasattr(fm, '_protocol')

    def test_constructor_exception(self, loop):
        class FledgeMicroserviceImp(FledgeMicroservice):
            def __init__(self):
                super().__init__()

            def run(self):
                pass

            async def change(self):
                pass

            async def shutdown(self):
                pass

            async def get_track(self):
                pass

            async def add_track(self):
                pass

        with patch.object(asyncio, 'get_event_loop', return_value=loop):
            with patch.object(sys, 'argv', ['pytest', '--address', 'corehost', '--port', '32333', '--name', 'sname']):
                with patch.object(MicroserviceManagementClient, '__init__', return_value=None) as mmc_patch:
                    with patch.object(MicroserviceManagementClient, 'create_configuration_category', return_value=None):
                        with patch.object(MicroserviceManagementClient, 'create_child_category',
                                          return_value=None):
                            with patch.object(MicroserviceManagementClient, 'get_configuration_category', return_value=_DEFAULT_CONFIG):
                                with patch.object(ReadingsStorageClientAsync, '__init__',
                                                  return_value=None) as rsc_async_patch:
                                    with patch.object(StorageClientAsync, '__init__',
                                                      return_value=None) as sc_async_patch:
                                        with patch.object(FledgeMicroservice, '_make_microservice_management_app', side_effect=Exception()) as make_patch:
                                            with patch.object(_logger, 'exception') as logger_patch:
                                                with pytest.raises(Exception) as excinfo:
                                                    fm = FledgeMicroserviceImp()
                                            args = logger_patch.call_args
                                            assert 'Unable to initialize FledgeMicroservice' == args[0][1]

    @pytest.mark.asyncio
    async def test_ping(self, loop):
        class FledgeMicroserviceImp(FledgeMicroservice):
            def __init__(self):
                super().__init__()

            def run(self):
                pass

            async def change(self):
                pass

            async def shutdown(self):
                pass

            async def get_track(self):
                pass

            async def add_track(self):
                pass

        with patch.object(asyncio, 'get_event_loop', return_value=loop):
            with patch.object(sys, 'argv', ['pytest', '--address', 'corehost', '--port', '32333', '--name', 'sname']):
                with patch.object(MicroserviceManagementClient, '__init__', return_value=None) as mmc_patch:
                    with patch.object(MicroserviceManagementClient, 'create_configuration_category', return_value=None):
                        with patch.object(MicroserviceManagementClient, 'create_child_category',
                                          return_value=None):
                            with patch.object(MicroserviceManagementClient, 'get_configuration_category', return_value=_DEFAULT_CONFIG):
                                with patch.object(ReadingsStorageClientAsync, '__init__',
                                                  return_value=None) as rsc_async_patch:
                                    with patch.object(StorageClientAsync, '__init__',
                                                      return_value=None) as sc_async_patch:
                                        with patch.object(FledgeMicroservice, '_make_microservice_management_app', return_value=None) as make_patch:
                                             with patch.object(FledgeMicroservice, '_run_microservice_management_app', side_effect=None) as run_patch:
                                                 with patch.object(FledgeProcess, 'register_service_with_core', return_value={'id':'bla'}) as reg_patch:
                                                     with patch.object(FledgeMicroservice, '_get_service_registration_payload', return_value=None) as payload_patch:
                                                         with patch.object(web, 'json_response', return_value=None) as response_patch:
                                                             # called once on FledgeProcess init for _start_time, once for ping
                                                             with patch.object(time, 'time', return_value=1) as time_patch:
                                                                 fm = FledgeMicroserviceImp()
                                                                 await fm.ping(None)
        response_patch.assert_called_once_with({'uptime': 0})
