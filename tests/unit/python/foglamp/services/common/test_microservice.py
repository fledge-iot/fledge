# -*- coding: utf-8 -*-

import pytest

from unittest.mock import patch

from foglamp.common.storage_client.storage_client import ReadingsStorageClient, StorageClient
from foglamp.common.process import FoglampProcess, SilentArgParse, ArgumentParserError
from foglamp.services.common.microservice import FoglampMicroservice
from foglamp.common.microservice_management_client.microservice_management_client import MicroserviceManagementClient


__author__ = "Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# test abstract methods
# test FoglampProcess class things it needs
# test that it registers with core
# test the microservice management api

@pytest.allure.feature("unit")
@pytest.allure.story("common", "foglamp-microservice")
class TestFoglampMicroservice:

    def test_constructor_abstract_method_missing(self):
        with pytest.raises(TypeError):
            fm = FoglampMicroservice()
        with pytest.raises(TypeError):
            class FoglampMicroserviceImp(FoglampMicroservice):
                pass
            fm = FoglampMicroserviceImp()
        with pytest.raises(TypeError):
            class FoglampMicroserviceImp(FoglampMicroservice):
                async def change(self):
                    pass
                async def shutdown(self):
                    pass
            fm = FoglampMicroserviceImp()
        with pytest.raises(TypeError):
            class FoglampMicroserviceImp(FoglampMicroservice):
                def run(self):
                    pass
                async def shutdown(self):
                    pass
            fm = FoglampMicroserviceImp()
        with pytest.raises(TypeError):
            class FoglampMicroserviceImp(FoglampMicroservice):
                def run(self):
                    pass
                async def change(self):
                    pass
            fm = FoglampMicroserviceImp()

    def test_constructor_good(self):
        class FoglampMicroserviceImp(FoglampMicroservice):
            def run(self):
                pass
            async def change(self):
                pass
            async def shutdown(self):
                pass
        def side_effect():
            fm._microservice_management_host = 'host'
            fm._microservice_management_port = 0
        with patch.object(SilentArgParse, 'silent_arg_parse', side_effect=['corehost', 0, 'sname']):
            with patch.object(MicroserviceManagementClient, '__init__', return_value=None) as mmc_patch:
                with patch.object(ReadingsStorageClient, '__init__', return_value=None) as rsc_patch:
                    with patch.object(StorageClient, '__init__', return_value=None) as sc_patch:
                        with patch.object(FoglampMicroservice, '_make_microservice_management_app', return_value=None) as make_patch:
                             with patch.object(FoglampMicroservice, '_run_microservice_management_app', side_effect=side_effect()) as run_patch:
                                 with patch.object(FoglampProcess, 'register_service_with_core', return_value={'id':'bla'}) as reg_patch:
                                     fm = FoglampMicroserviceImp()
        assert fm._core_management_host is 'corehost'
        assert fm._core_management_port is 0
        assert fm._name is 'sname'
        assert hasattr(fm, '_core_microservice_management_client')
        assert hasattr(fm, '_readings_storage')
        assert hasattr(fm, '_storage')
        assert hasattr(fm, '_start_time')

