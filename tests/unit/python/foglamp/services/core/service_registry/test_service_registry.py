# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test foglamp/services/core/service_registry/service_registry.py """

import pytest
from unittest.mock import patch

from foglamp.services.core.service_registry.service_registry import ServiceRegistry
from foglamp.services.core.service_registry.exceptions import *

__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("services", "core", "service-registry")
class TestServiceRegistry:

    def setup_method(self, method):
        ServiceRegistry._registry = list()

    def teardown_method(self, method):
        ServiceRegistry._registry = list()

    def test_register(self):
        with patch.object(ServiceRegistry._logger, 'info') as log_i:
            s_id = ServiceRegistry.register("A name", "Storage", "127.0.0.1", 1234, 4321, 'http')
            assert 36 == len(s_id)  # uuid version 4 len
            assert 1 == len(ServiceRegistry._registry)
        args, kwargs = log_i.call_args
        assert args[0].startswith('Registered service instance id=')
        assert args[0].endswith(': <A name, type=Storage, protocol=http, address=127.0.0.1, service port=1234,'
                                ' management port=4321, status=1>')
        assert 1 == log_i.call_count

    def test_register_with_service_port_none(self):
        with patch.object(ServiceRegistry._logger, 'info') as log_i:
            s_id = ServiceRegistry.register("A name", "Southbound", "127.0.0.1", None, 4321, 'http')
            assert 36 == len(s_id)  # uuid version 4 len
            assert 1 == len(ServiceRegistry._registry)
        args, kwargs = log_i.call_args
        assert args[0].startswith('Registered service instance id=')
        assert args[0].endswith(': <A name, type=Southbound, protocol=http, address=127.0.0.1, service port=None,'
                                ' management port=4321, status=1>')
        assert 1 == log_i.call_count

    def test_register_with_same_name(self):
        """raise AlreadyExistsWithTheSameName"""

        ServiceRegistry.register("A name", "Storage", "127.0.0.1", 1, 2, 'http')
        assert 1 == len(ServiceRegistry._registry)

        with pytest.raises(Exception) as excinfo:
            with patch.object(ServiceRegistry._logger, 'info') as log_i:
                ServiceRegistry.register("A name", "Storage", "127.0.0.2", 3, 4, 'http')
        assert 0 == log_i.call_count
        assert excinfo.type is AlreadyExistsWithTheSameName
        assert 1 == len(ServiceRegistry._registry)

    def test_register_with_same_address_and_port(self):
        """raise AlreadyExistsWithTheSameAddressAndPort"""
        ServiceRegistry.register("A name", "Storage", "127.0.0.1", 1234, 1, 'http')
        assert 1 == len(ServiceRegistry._registry)

        with pytest.raises(Exception) as excinfo:
            with patch.object(ServiceRegistry._logger, 'info') as log_i:
                ServiceRegistry.register("B name", "Storage", "127.0.0.1", 1234, 2, 'http')
        assert 0 == log_i.call_count
        assert excinfo.type is AlreadyExistsWithTheSameAddressAndPort
        assert 1 == len(ServiceRegistry._registry)

    def test_register_with_same_address_and_mgt_port(self):
        """raise AlreadyExistsWithTheSameAddressAndManagementPort"""
        ServiceRegistry.register("A name", "Storage", "127.0.0.1", 1, 1234, 'http')
        assert 1 == len(ServiceRegistry._registry)

        with pytest.raises(Exception) as excinfo:
            with patch.object(ServiceRegistry._logger, 'info') as log_i:
                ServiceRegistry.register("B name", "Storage", "127.0.0.1", 2, 1234, 'http')
        assert 0 == log_i.call_count
        assert excinfo.type is AlreadyExistsWithTheSameAddressAndManagementPort
        assert 1 == len(ServiceRegistry._registry)

    def test_register_with_bad_service_port(self):
        """raise NonNumericPortError"""
        with pytest.raises(Exception) as excinfo:
            with patch.object(ServiceRegistry._logger, 'info') as log_i:
                ServiceRegistry.register("B name", "Storage", "127.0.0.1", "s01", 1234, 'http')
        assert 0 == log_i.call_count
        assert excinfo.type is NonNumericPortError
        assert 0 == len(ServiceRegistry._registry)

    def test_register_with_bad_management_port(self):
        """raise NonNumericPortError"""
        with pytest.raises(Exception) as excinfo:
            with patch.object(ServiceRegistry._logger, 'info') as log_i:
                ServiceRegistry.register("B name", "Storage", "127.0.0.1", 1234, "m01", 'http')
        assert 0 == log_i.call_count
        assert excinfo.type is NonNumericPortError
        assert 0 == len(ServiceRegistry._registry)

    def test_unregister(self):
        reg_id = ServiceRegistry.register("A name", "Storage", "127.0.0.1", 1234, 4321, 'http')
        assert 1 == len(ServiceRegistry._registry)

        with patch.object(ServiceRegistry._logger, 'info') as log_i:
            s_id = ServiceRegistry.unregister(reg_id)
            assert 36 == len(s_id)  # uuid version 4 len
            assert 0 == len(ServiceRegistry._registry)
        args, kwargs = log_i.call_args
        assert args[0].startswith('Unregistered service instance id=')
        assert args[0].endswith(': <A name, type=Storage, protocol=http, address=127.0.0.1, service port=1234,'
                                ' management port=4321, status=1>')
        assert 1 == log_i.call_count

    def test_unregister_non_existing_service_record(self):
        """raise DoesNotExist"""

        with pytest.raises(Exception) as excinfo:
            with patch.object(ServiceRegistry._logger, 'info') as log_i:
                ServiceRegistry.unregister("blah")
        assert 0 == log_i.call_count
        assert excinfo.type is DoesNotExist

