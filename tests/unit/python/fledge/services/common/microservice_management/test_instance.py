# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import uuid
from unittest.mock import patch
import pytest

from fledge.services.core.service_registry.service_registry import ServiceRegistry as Service
from fledge.services.core.service_registry.exceptions import *
from fledge.common.service_record import ServiceRecord
from fledge.services.core.interest_registry.interest_registry import InterestRegistry

__author__ = "Amarendra Kumar Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("services", "common", "microservice_management")
class TestInstance:
    def setup_method(self):
        Service._registry = []

    def teardown_method(self):
        Service._registry = []

    async def test_register(self):
        with patch.object(Service._logger, 'info') as log_info:
            idx = Service.register("StorageService1", "Storage", "127.0.0.1", 9999, 1999)
            assert str(uuid.UUID(idx, version=4)) == idx
        assert 1 == log_info.call_count
        args, kwargs = log_info.call_args
        assert args[0].startswith('Registered service instance id=')
        assert args[0].endswith(': <StorageService1, type=Storage, protocol=http, address=127.0.0.1, service port=9999,'
                                ' management port=1999, status=1, token=None>')

    async def test_duplicate_name_registration(self):
        with patch.object(Service._logger, 'info') as log_info:
            idx1 = Service.register("StorageService1", "Storage", "127.0.0.1", 9999, 1999)
            assert str(uuid.UUID(idx1, version=4)) == idx1
        assert 1 == log_info.call_count
        args, kwargs = log_info.call_args
        assert args[0].startswith('Registered service instance id=')
        assert args[0].endswith(': <StorageService1, type=Storage, protocol=http, address=127.0.0.1, service port=9999,'
                                ' management port=1999, status=1, token=None>')

        with pytest.raises(AlreadyExistsWithTheSameName) as excinfo:
            Service.register("StorageService1", "Storage", "127.0.0.1", 9999, 1999)
        assert str(excinfo).endswith('AlreadyExistsWithTheSameName')

    async def test_duplicate_address_port_registration(self):
        with patch.object(Service._logger, 'info') as log_info:
            idx1 = Service.register("StorageService1", "Storage", "127.0.0.1", 9999, 1999)
            assert str(uuid.UUID(idx1, version=4)) == idx1
        assert 1 == log_info.call_count
        args, kwargs = log_info.call_args
        assert args[0].startswith('Registered service instance id=')
        assert args[0].endswith(': <StorageService1, type=Storage, protocol=http, address=127.0.0.1, service port=9999,'
                                ' management port=1999, status=1, token=None>')

        with pytest.raises(AlreadyExistsWithTheSameAddressAndPort) as excinfo:
            Service.register("StorageService2", "Storage", "127.0.0.1", 9999, 1998)
        assert str(excinfo).endswith('AlreadyExistsWithTheSameAddressAndPort')

    async def test_duplicate_address_and_mgt_port_registration(self):
        with patch.object(Service._logger, 'info') as log_info:
            idx1 = Service.register("StorageService1", "Storage", "127.0.0.1", 9999, 1999)
            assert str(uuid.UUID(idx1, version=4)) == idx1
        assert 1 == log_info.call_count
        args, kwargs = log_info.call_args
        assert args[0].startswith('Registered service instance id=')
        assert args[0].endswith(': <StorageService1, type=Storage, protocol=http, address=127.0.0.1, service port=9999,'
                                ' management port=1999, status=1, token=None>')

        with pytest.raises(AlreadyExistsWithTheSameAddressAndManagementPort) as excinfo:
            Service.register("StorageService2", "Storage", "127.0.0.1", 9998, 1999)
        assert str(excinfo).endswith('AlreadyExistsWithTheSameAddressAndManagementPort')

    async def test_register_wrong_type(self):
        with pytest.raises(ServiceRecord.InvalidServiceType) as excinfo:
            Service.register("StorageService1", "WrongType", "127.0.0.1", 9999, 1999)
        assert str(excinfo).endswith('InvalidServiceType')

    async def test_register_invalid_port(self):
        with pytest.raises(NonNumericPortError) as excinfo:
            Service.register("StorageService2", "Storage", "127.0.0.1", "808a", 1999)
        assert str(excinfo).endswith('NonNumericPortError')

    async def test_register_invalid_mgt_port(self):
        with pytest.raises(NonNumericPortError) as excinfo:
            Service.register("StorageService2", "Core", "127.0.0.1", 8888, "199a")
        assert str(excinfo).endswith('NonNumericPortError')

    async def test_unregister(self, mocker):
        # register a service
        with patch.object(Service._logger, 'info') as log_info:
            idx = Service.register("StorageService2", "Storage", "127.0.0.1", 8888, 1888)
            assert str(uuid.UUID(idx, version=4)) == idx
        assert 1 == log_info.call_count
        arg, kwarg = log_info.call_args
        assert arg[0].startswith('Registered service instance id=')
        assert arg[0].endswith(': <StorageService2, type=Storage, protocol=http, address=127.0.0.1, service port=8888,'
                               ' management port=1888, status=1, token=None>')

        mocker.patch.object(InterestRegistry, '__init__', return_value=None)
        mocker.patch.object(InterestRegistry, 'get', return_value=list())

        # deregister the same
        with patch.object(Service._logger, 'info') as log_info2:
            t = Service.unregister(idx)
            assert idx == t
        assert 1 == log_info2.call_count
        args, kwargs = log_info2.call_args
        assert args[0].startswith('Stopped service instance id=')
        assert args[0].endswith(': <StorageService2, type=Storage, protocol=http, address=127.0.0.1, '
                                'service port=8888, management port=1888, status=2, token=None>')

        s = Service.get(idx)
        assert s[0]._status == 2  # Unregistered

    async def test_get(self):
        with patch.object(Service._logger, 'info') as log_info:
            s = Service.register("StorageService", "Storage", "localhost", 8881, 1888)
            c = Service.register("CoreService", "Core", "localhost", 7771, 1777)
            d = Service.register("SouthService", "Southbound", "127.0.0.1", 9991, 1999, "https")
        assert 3 == log_info.call_count

        _service = Service.get()
        assert 3 == len(_service)

        assert s == _service[0]._id
        assert "StorageService" == _service[0]._name
        assert "Storage" == _service[0]._type
        assert "localhost" == _service[0]._address
        assert 8881 == int(_service[0]._port)
        assert 1888 == int(_service[0]._management_port)
        # validates default set to HTTP
        assert "http" == _service[0]._protocol

        assert c == _service[1]._id
        assert "CoreService" == _service[1]._name
        assert "Core" == _service[1]._type
        assert "localhost" == _service[1]._address
        assert 7771 == int(_service[1]._port)
        assert 1777 == int(_service[1]._management_port)
        # validates default set to HTTP
        assert "http" == _service[1]._protocol

        assert d == _service[2]._id
        assert "SouthService" == _service[2]._name
        assert "Southbound" == _service[2]._type
        assert "127.0.0.1" == _service[2]._address
        assert 9991 == int(_service[2]._port)
        assert 1999 == int(_service[2]._management_port)
        assert "https" == _service[2]._protocol

    async def test_get_fail(self):
        with pytest.raises(DoesNotExist) as excinfo:
            with patch.object(Service._logger, 'info') as log_info:
                Service.register("StorageService", "Storage", "127.0.0.1", 8888, 9999)
                Service.get('incorrect_id')
            assert 1 == log_info.call_count
            args, kwargs = log_info.call_args
            assert args[0].startswith('Registered service instance id=')
            assert args[0].endswith(
                ': <StorageService1, type=Storage, protocol=http, address=127.0.0.1, service port=8888,'
                ' management port=9999, status=1, token=None>')
        assert str(excinfo).endswith('DoesNotExist')
