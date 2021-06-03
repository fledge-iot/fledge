# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

from unittest.mock import patch
import pytest

from fledge.services.core.service_registry.service_registry import ServiceRegistry
from fledge.services.core.service_registry.exceptions import *
from fledge.services.core.interest_registry.interest_registry import InterestRegistry

__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("services", "core", "service-registry")
class TestServiceRegistry:

    def setup_method(self):
        ServiceRegistry._registry = list()

    def teardown_method(self):
        ServiceRegistry._registry = list()

    def test_register(self):
        with patch.object(ServiceRegistry._logger, 'info') as log_info:
            s_id = ServiceRegistry.register("A name", "Storage", "127.0.0.1", 1234, 4321, 'http')
            assert 36 == len(s_id)  # uuid version 4 len
            assert 1 == len(ServiceRegistry._registry)
        assert 1 == log_info.call_count
        args, kwargs = log_info.call_args
        assert args[0].startswith('Registered service instance id=')
        assert args[0].endswith(': <A name, type=Storage, protocol=http, address=127.0.0.1, service port=1234,'
                                ' management port=4321, status=1, token=None>')

    def test_register_with_service_port_none(self):
        with patch.object(ServiceRegistry._logger, 'info') as log_info:
            s_id = ServiceRegistry.register("A name", "Southbound", "127.0.0.1", None, 4321, 'http')
            assert 36 == len(s_id)  # uuid version 4 len
            assert 1 == len(ServiceRegistry._registry)
        assert 1 == log_info.call_count
        args, kwargs = log_info.call_args
        assert args[0].startswith('Registered service instance id=')
        assert args[0].endswith(': <A name, type=Southbound, protocol=http, address=127.0.0.1, service port=None,'
                                ' management port=4321, status=1, token=None>')

    def test_register_with_same_name(self):
        """raise AlreadyExistsWithTheSameName"""
        with patch.object(ServiceRegistry._logger, 'info') as log_info1:
            ServiceRegistry.register("A name", "Storage", "127.0.0.1", 1, 2, 'http')
            assert 1 == len(ServiceRegistry._registry)
        assert 1 == log_info1.call_count
        args, kwargs = log_info1.call_args
        assert args[0].startswith('Registered service instance id=')
        assert args[0].endswith(': <A name, type=Storage, protocol=http, address=127.0.0.1, service port=1,'
                                ' management port=2, status=1, token=None>')

        with pytest.raises(Exception) as excinfo:
            with patch.object(ServiceRegistry._logger, 'info') as log_info2:
                ServiceRegistry.register("A name", "Storage", "127.0.0.2", 3, 4, 'http')
                assert 1 == len(ServiceRegistry._registry)
            assert 0 == log_info2.call_count
        assert excinfo.type is AlreadyExistsWithTheSameName

    def test_register_with_same_address_and_port(self):
        """raise AlreadyExistsWithTheSameAddressAndPort"""
        with patch.object(ServiceRegistry._logger, 'info') as log_info1:
            ServiceRegistry.register("A name", "Storage", "127.0.0.1", 1234, 1, 'http')
            assert 1 == len(ServiceRegistry._registry)
        assert 1 == log_info1.call_count
        args, kwargs = log_info1.call_args
        assert args[0].startswith('Registered service instance id=')
        assert args[0].endswith(': <A name, type=Storage, protocol=http, address=127.0.0.1, service port=1234,'
                                ' management port=1, status=1, token=None>')

        with pytest.raises(Exception) as excinfo:
            with patch.object(ServiceRegistry._logger, 'info') as log_info2:
                ServiceRegistry.register("B name", "Storage", "127.0.0.1", 1234, 2, 'http')
                assert 1 == len(ServiceRegistry._registry)
            assert 0 == log_info2.call_count
        assert excinfo.type is AlreadyExistsWithTheSameAddressAndPort

    def test_register_with_same_address_and_mgt_port(self):
        """raise AlreadyExistsWithTheSameAddressAndManagementPort"""
        with patch.object(ServiceRegistry._logger, 'info') as log_info1:
            ServiceRegistry.register("A name", "Storage", "127.0.0.1", 1, 1234, 'http')
            assert 1 == len(ServiceRegistry._registry)
        assert 1 == log_info1.call_count
        args, kwargs = log_info1.call_args
        assert args[0].startswith('Registered service instance id=')
        assert args[0].endswith(': <A name, type=Storage, protocol=http, address=127.0.0.1, service port=1,'
                                ' management port=1234, status=1, token=None>')

        with pytest.raises(Exception) as excinfo:
            with patch.object(ServiceRegistry._logger, 'info') as log_info2:
                ServiceRegistry.register("B name", "Storage", "127.0.0.1", 2, 1234, 'http')
                assert 1 == len(ServiceRegistry._registry)
            assert 0 == log_info2.call_count
        assert excinfo.type is AlreadyExistsWithTheSameAddressAndManagementPort

    def test_register_with_bad_service_port(self):
        """raise NonNumericPortError"""
        with pytest.raises(Exception) as excinfo:
            with patch.object(ServiceRegistry._logger, 'info') as log_info:
                ServiceRegistry.register("B name", "Storage", "127.0.0.1", "s01", 1234, 'http')
                assert 1 == len(ServiceRegistry._registry)
            assert 0 == log_info.call_count
        assert excinfo.type is NonNumericPortError

    def test_register_with_bad_management_port(self):
        """raise NonNumericPortError"""
        with pytest.raises(Exception) as excinfo:
            with patch.object(ServiceRegistry._logger, 'info') as log_info:
                ServiceRegistry.register("B name", "Storage", "127.0.0.1", 1234, "m01", 'http')
                assert 0 == len(ServiceRegistry._registry)
            assert 0 == log_info.call_count
        assert excinfo.type is NonNumericPortError

    def test_unregister(self, mocker):
        mocker.patch.object(InterestRegistry, '__init__', return_value=None)
        mocker.patch.object(InterestRegistry, 'get', return_value=list())

        with patch.object(ServiceRegistry._logger, 'info') as log_info1:
            reg_id = ServiceRegistry.register("A name", "Storage", "127.0.0.1", 1234, 4321, 'http')
            assert 1 == len(ServiceRegistry._registry)
        assert 1 == log_info1.call_count
        arg, kwarg = log_info1.call_args
        assert arg[0].startswith('Registered service instance id=')
        assert arg[0].endswith(': <A name, type=Storage, protocol=http, address=127.0.0.1, service port=1234,'
                               ' management port=4321, status=1, token=None>')

        with patch.object(ServiceRegistry._logger, 'info') as log_info2:
            s_id = ServiceRegistry.unregister(reg_id)
            assert 36 == len(s_id)  # uuid version 4 len
            assert 1 == len(ServiceRegistry._registry)
            s = ServiceRegistry.get(idx=s_id)
            assert s[0]._status == 2
        assert 1 == log_info2.call_count
        args, kwargs = log_info2.call_args
        assert args[0].startswith('Stopped service instance id=')
        assert args[0].endswith(': <A name, type=Storage, protocol=http, address=127.0.0.1, service port=1234,'
                                ' management port=4321, status=2, token=None>')

    def test_unregister_non_existing_service_record(self):
        """raise DoesNotExist"""
        with pytest.raises(Exception) as excinfo:
            with patch.object(ServiceRegistry._logger, 'info') as log_info:
                ServiceRegistry.unregister("blah")
                assert 0 == len(ServiceRegistry._registry)
            assert 0 == log_info.call_count
        assert excinfo.type is DoesNotExist
