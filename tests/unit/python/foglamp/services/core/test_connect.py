# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from unittest.mock import patch
import pytest

from foglamp.services.core.service_registry.service_registry import ServiceRegistry
from foglamp.services.core.service_registry.exceptions import DoesNotExist
from foglamp.services.core import connect
from foglamp.common.storage_client.storage_client import StorageClientAsync

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
        with patch.object(ServiceRegistry._logger, 'info') as log_info:
            ServiceRegistry.register("FogLAMP Storage", "Storage", "127.0.0.1", 37449, 37843)
            storage_client = connect.get_storage_async()
            assert isinstance(storage_client, StorageClientAsync)
        assert 1 == log_info.call_count
        args, kwargs = log_info.call_args
        assert args[0].startswith('Registered service instance id=')
        assert args[0].endswith(': <FogLAMP Storage, type=Storage, protocol=http, address=127.0.0.1, service port=37449,'
                                ' management port=37843, status=1>')

    @patch('foglamp.services.core.connect._logger')
    def test_exception_when_no_storage(self, mock_logger):
        with pytest.raises(DoesNotExist) as excinfo:
            connect.get_storage_async()
        assert str(excinfo).endswith('DoesNotExist')
        mock_logger.exception.assert_called_once_with('')

    @patch('foglamp.services.core.connect._logger')
    def test_exception_when_non_foglamp_storage(self, mock_logger):
        with patch.object(ServiceRegistry._logger, 'info') as log_info:
            ServiceRegistry.register("foo", "Storage", "127.0.0.1", 1, 2)
        assert 1 == log_info.call_count
        args, kwargs = log_info.call_args
        assert args[0].startswith('Registered service instance id=')
        assert args[0].endswith(': <foo, type=Storage, protocol=http, address=127.0.0.1, service port=1, '
                                'management port=2, status=1>')

        with pytest.raises(DoesNotExist) as excinfo:
            connect.get_storage_async()
        assert str(excinfo).endswith('DoesNotExist')
        mock_logger.exception.assert_called_once_with('')
