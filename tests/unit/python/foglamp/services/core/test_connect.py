# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from unittest.mock import patch
import pytest

from foglamp.services.core.service_registry.service_registry import ServiceRegistry
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
        ServiceRegistry._registry = []

    def teardown_method(self):
        ServiceRegistry._registry = []

    def test_get_storage(self):
        ServiceRegistry.register("FogLAMP Storage", "Storage", "127.0.0.1", 37449, 37843)
        storage_client = connect.get_storage()
        assert isinstance(storage_client, StorageClient)

    @patch('foglamp.services.core.connect._logger')
    def test_exception_when_no_storage(self, mock_logger):
        with pytest.raises(DoesNotExist) as excinfo:
            connect.get_storage()
        assert str(excinfo).endswith('DoesNotExist')
        mock_logger.exception.assert_called_once_with('')

    @patch('foglamp.services.core.connect._logger')
    def test_exception_when_non_foglamp_storage(self, mock_logger):
        ServiceRegistry.register("foo", "Storage", "127.0.0.1", 1, 2)
        with pytest.raises(DoesNotExist) as excinfo:
            connect.get_storage()
        assert str(excinfo).endswith('DoesNotExist')
        mock_logger.exception.assert_called_once_with('')
