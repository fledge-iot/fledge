# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from unittest.mock import MagicMock, patch
import pytest

from foglamp.services.core.service_registry.service_registry import ServiceRegistry as Service
from foglamp.services.core.service_registry.exceptions import DoesNotExist
from foglamp.services.core import connect
from foglamp.common.storage_client.storage_client import StorageClient

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("services", "core")
class TestConnect:
    """ Storage connection"""
    
    def setup_method(self):
        Service._registry = []

    def teardown_method(self):
        Service._registry = []

    def test_get_storage(self):
        service_reg = MagicMock(spec=Service)
        service_idx = Service.register("FogLAMP Storage", "Storage", "127.0.0.1", 37449, 37843)
        with patch.object(service_reg, 'get', return_value=service_idx):
            storage_client = connect.get_storage()
            assert isinstance(storage_client, StorageClient)

    def test_get_storage_exception(self):
        service_reg = MagicMock(spec=Service)
        with patch.object(service_reg, 'get', side_effect=Exception()):
            with pytest.raises(DoesNotExist) as excinfo:
                with patch.object(connect._logger, 'exception') as logger_exception:
                    connect.get_storage()
                assert str(excinfo).endswith('DoesNotExist')
                logger_exception.assert_called_once_with()
