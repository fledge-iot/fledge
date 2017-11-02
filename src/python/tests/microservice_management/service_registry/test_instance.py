# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import uuid
import pytest

from foglamp.microservice_management.service_registry.instance import Service

__author__ = "Amarendra Kumar Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

pytestmark = pytest.mark.asyncio


@pytest.allure.feature("unit")
@pytest.allure.story("service-registry instance")
class TestInstance:

    def setup_method(self):
        Service.Instances._registry = []

    def teardown_method(self):
        Service.Instances._registry = []

    async def test_register(self):
        idx = Service.Instances.register("StorageService1", "Storage", "127.0.0.1", 9999, 1999)
        assert str(uuid.UUID(idx, version=4)) == idx

    async def test_duplicate_name_registration(self):
        idx1 = Service.Instances.register("StorageService1", "Storage", "127.0.0.1", 9999, 1999)
        assert str(uuid.UUID(idx1, version=4)) == idx1
        with pytest.raises(Service.AlreadyExistsWithTheSameName) as excinfo:
            Service.Instances.register("StorageService1", "Storage", "127.0.0.1", 9999, 1999)
        assert str(excinfo).endswith('AlreadyExistsWithTheSameName')

    async def test_duplicate_address_port_registration(self):
        idx1 = Service.Instances.register("StorageService1", "Storage", "127.0.0.1", 9999, 1999)
        assert str(uuid.UUID(idx1, version=4)) == idx1
        with pytest.raises(Service.AlreadyExistsWithTheSameAddressAndPort) as excinfo:
            Service.Instances.register("StorageService2", "Storage", "127.0.0.1", 9999, 1998)
        assert str(excinfo).endswith('AlreadyExistsWithTheSameAddressAndPort')

    async def test_duplicate_address_and_mgt_port_registration(self):
        idx1 = Service.Instances.register("StorageService1", "Storage", "127.0.0.1", 9999, 1999)
        assert str(uuid.UUID(idx1, version=4)) == idx1
        with pytest.raises(Service.AlreadyExistsWithTheSameAddressAndManagementPort) as excinfo:
            Service.Instances.register("StorageService2", "Storage", "127.0.0.1", 9998, 1999)
        assert str(excinfo).endswith('AlreadyExistsWithTheSameAddressAndManagementPort')

    async def test_register_wrong_type(self):
        with pytest.raises(Service.InvalidServiceType) as excinfo:
            Service.Instances.register("StorageService1", "WrongType", "127.0.0.1", 9999, 1999)
        assert str(excinfo).endswith('InvalidServiceType')

    async def test_register_invalid_port(self):
        with pytest.raises(Service.NonNumericPortError) as excinfo:
            Service.Instances.register("StorageService2", "Storage", "127.0.0.1", "808a", 1999)
        assert str(excinfo).endswith('NonNumericPortError')

    async def test_register_invalid_mgt_port(self):
        with pytest.raises(Service.NonNumericPortError) as excinfo:
            Service.Instances.register("StorageService2", "Core", "127.0.0.1", 8888, "199a")
        assert str(excinfo).endswith('NonNumericPortError')

    async def test_unregister(self):
        # register a service
        idx = Service.Instances.register("StorageService2", "Storage", "127.0.0.1", 8888, 1888)
        assert str(uuid.UUID(idx, version=4)) == idx

        # deregister the same
        t = Service.Instances.unregister(idx)
        assert idx == t

        with pytest.raises(Service.DoesNotExist) as excinfo:
            Service.Instances.get(idx)
        assert str(excinfo).endswith('DoesNotExist')

    async def test_get(self):
        s = Service.Instances.register("StorageService", "Storage", "localhost", 8881, 1888)
        c = Service.Instances.register("CoreService", "Core", "localhost", 7771, 1777)
        d = Service.Instances.register("DeviceService", "Device", "127.0.0.1", 9991, 1999, "https")

        l = Service.Instances.get()
        assert 3 == len(l)

        assert s == l[0]._id
        assert "StorageService" == l[0]._name
        assert "Storage" == l[0]._type
        assert "localhost" == l[0]._address
        assert 8881 == int(l[0]._port)
        assert 1888 == int(l[0]._management_port)
        # validates default set to HTTP
        assert "http" == l[0]._protocol

        assert c == l[1]._id
        assert "CoreService" == l[1]._name
        assert "Core" == l[1]._type
        assert "localhost" == l[1]._address
        assert 7771 == int(l[1]._port)
        assert 1777 == int(l[1]._management_port)
        # validates default set to HTTP
        assert "http" == l[1]._protocol

        assert d == l[2]._id
        assert "DeviceService" == l[2]._name
        assert "Device" == l[2]._type
        assert "127.0.0.1" == l[2]._address
        assert 9991 == int(l[2]._port)
        assert 1999 == int(l[2]._management_port)
        assert "https" == l[2]._protocol

    async def test_get_fail(self):
        with pytest.raises(Service.DoesNotExist) as excinfo:
            Service.Instances.register("StorageService", "Storage", "127.0.0.1", 8888, 9999)
            Service.Instances.get('incorrect_id')
        assert str(excinfo).endswith('DoesNotExist')
