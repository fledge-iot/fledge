# -*- coding: utf-8 -*-

import pytest
import sys

from unittest.mock import patch

from fledge.common import process
from fledge.common.storage_client.storage_client import ReadingsStorageClientAsync, StorageClientAsync
from fledge.common.process import FledgeProcess, ArgumentParserError
from fledge.common.microservice_management_client.microservice_management_client import MicroserviceManagementClient


__author__ = "Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("common", "fledge-process")
class TestFledgeProcess:

    def test_constructor_abstract_method_run(self):
        with pytest.raises(TypeError):
            fp = FledgeProcess()
        with pytest.raises(TypeError):
            class FledgeProcessImp(FledgeProcess):
                pass
            fp = FledgeProcessImp()

    @pytest.mark.parametrize('argslist',
                             [(['pytest']),
                              (['pytest, ''--address', 'corehost']),
                              (['pytest', '--address', 'corehost', '--port', '32333'])
                              ])
    def test_constructor_missing_args(self, argslist):
        class FledgeProcessImp(FledgeProcess):
            def run(self):
                pass
        with patch.object(sys, 'argv', argslist):
            with pytest.raises(ArgumentParserError) as excinfo:
                with patch.object(process._logger, "error") as patch_logger:
                    fp = FledgeProcessImp()
                assert 1 == patch_logger.call_count
                patch_logger.assert_called_once_with()
            assert '' in str(excinfo.value)

    def test_constructor_good(self):
        class FledgeProcessImp(FledgeProcess):
            def run(self):
                pass
        with patch.object(sys, 'argv', ['pytest', '--address', 'corehost', '--port', '32333', '--name', 'sname']):
            with patch.object(MicroserviceManagementClient, '__init__', return_value=None) as mmc_patch:
                with patch.object(ReadingsStorageClientAsync, '__init__', return_value=None) as rsc_async_patch:
                    with patch.object(StorageClientAsync, '__init__', return_value=None) as sc_async_patch:
                        fp = FledgeProcessImp()
        mmc_patch.assert_called_once_with('corehost', 32333)
        rsc_async_patch.assert_called_once_with('corehost', 32333)
        sc_async_patch.assert_called_once_with('corehost', 32333)
        assert fp._core_management_host is 'corehost'
        assert fp._core_management_port == 32333
        assert fp._name is 'sname'
        assert hasattr(fp, '_core_microservice_management_client')
        assert hasattr(fp, '_readings_storage_async')
        assert hasattr(fp, '_storage_async')
        assert hasattr(fp, '_start_time')

    def test_get_services_from_core(self):
        class FledgeProcessImp(FledgeProcess):
            def run(self):
                pass
        with patch.object(sys, 'argv', ['pytest', '--address', 'corehost', '--port', '32333', '--name', 'sname']):
            with patch.object(MicroserviceManagementClient, '__init__', return_value=None) as mmc_patch:
                with patch.object(MicroserviceManagementClient, 'get_services', return_value=None) as get_patch:
                    with patch.object(ReadingsStorageClientAsync, '__init__',
                                      return_value=None) as rsc_async_patch:
                        with patch.object(StorageClientAsync, '__init__', return_value=None) as sc_async_patch:
                            fp = FledgeProcessImp()
                            fp.get_services_from_core('foo', 'bar')
        get_patch.assert_called_once_with('foo', 'bar')

    def test_register_service_with_core(self):
        class FledgeProcessImp(FledgeProcess):
            def run(self):
                pass
        with patch.object(sys, 'argv', ['pytest', '--address', 'corehost', '--port', '32333', '--name', 'sname']):
            with patch.object(MicroserviceManagementClient, '__init__', return_value=None) as mmc_patch:
                with patch.object(MicroserviceManagementClient, 'register_service', return_value=None) as register_patch:
                    with patch.object(ReadingsStorageClientAsync, '__init__',
                                      return_value=None) as rsc_async_patch:
                        with patch.object(StorageClientAsync, '__init__', return_value=None) as sc_async_patch:
                            fp = FledgeProcessImp()
                            fp.register_service_with_core('payload')
        register_patch.assert_called_once_with('payload')

    def test_unregister_service_with_core(self):
        class FledgeProcessImp(FledgeProcess):
            def run(self):
                pass
        with patch.object(sys, 'argv', ['pytest', '--address', 'corehost', '--port', '32333', '--name', 'sname']):
            with patch.object(MicroserviceManagementClient, '__init__', return_value=None) as mmc_patch:
                with patch.object(MicroserviceManagementClient, 'unregister_service', return_value=None) as unregister_patch:
                    with patch.object(ReadingsStorageClientAsync, '__init__',
                                      return_value=None) as rsc_async_patch:
                        with patch.object(StorageClientAsync, '__init__', return_value=None) as sc_async_patch:
                            fp = FledgeProcessImp()
                            fp.unregister_service_with_core('id')
        unregister_patch.assert_called_once_with('id')
