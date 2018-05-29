# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import uuid
from unittest.mock import patch
import pytest

from foglamp.services.core.service_registry.service_registry import ServiceRegistry as Service
from foglamp.services.core.service_registry.exceptions import *
from foglamp.common.service_record import ServiceRecord
from foglamp.services.core.interest_registry.interest_registry import InterestRegistry

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

    async def test_duplicate_name_registration(self):
        with patch.object(Service._logger, 'info') as log_info:
            idx1 = Service.register("StorageService1", "Storage", "127.0.0.1", 9999, 1999)
            assert str(uuid.UUID(idx1, version=4)) == idx1
        assert 1 == log_info.call_count

        with pytest.raises(AlreadyExistsWithTheSameName) as excinfo:
            Service.register("StorageService1", "Storage", "127.0.0.1", 9999, 1999)
        assert str(excinfo).endswith('AlreadyExistsWithTheSameName')

    async def test_duplicate_address_port_registration(self):
        with patch.object(Service._logger, 'info') as log_info:
            idx1 = Service.register("StorageService1", "Storage", "127.0.0.1", 9999, 1999)
            assert str(uuid.UUID(idx1, version=4)) == idx1
        assert 1 == log_info.call_count

        with pytest.raises(AlreadyExistsWithTheSameAddressAndPort) as excinfo:
            Service.register("StorageService2", "Storage", "127.0.0.1", 9999, 1998)
        assert str(excinfo).endswith('AlreadyExistsWithTheSameAddressAndPort')

    async def test_duplicate_address_and_mgt_port_registration(self):
        with patch.object(Service._logger, 'info') as log_info:
            idx1 = Service.register("StorageService1", "Storage", "127.0.0.1", 9999, 1999)
            assert str(uuid.UUID(idx1, version=4)) == idx1
        assert 1 == log_info.call_count

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

        mocker.patch.object(InterestRegistry, '__init__', return_value=None)
        mocker.patch.object(InterestRegistry, 'get', return_value=list())

        # deregister the same
        with patch.object(Service._logger, 'info') as log_info2:
            t = Service.unregister(idx)
            assert idx == t
        assert 1 == log_info2.call_count

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
        assert str(excinfo).endswith('DoesNotExist')
