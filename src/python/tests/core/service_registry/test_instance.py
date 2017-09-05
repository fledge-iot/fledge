# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import uuid
import pytest

from foglamp.core.service_registry.instance import Service

__author__ = "Amarendra Kumar Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

pytestmark = pytest.mark.asyncio


class TestInstance:

    def setup_method(self):
        Service.Instances._registry = []

    def teardown_method(self):
        Service.Instances._registry = []

    async def test_register(self):
        idx = Service.Instances.register("StorageService1", "Storage", "127.0.0.1", 9999)
        assert str(uuid.UUID(idx, version=4)) == idx

    async def test_duplicate_registration(self):
        idx1 = Service.Instances.register("StorageService1", "Storage", "127.0.0.1", 9999)
        assert str(uuid.UUID(idx1, version=4)) == idx1
        with pytest.raises(Service.AlreadyExistsWithTheSameAddressAndPort) as excinfo:
            Service.Instances.register("StorageService1", "Storage", "127.0.0.1", 9999)
        assert str(excinfo).endswith('AlreadyExistsWithTheSameAddressAndPort')

    async def test_register_wrong_type(self):
        with pytest.raises(Service.InvalidServiceType) as excinfo:
            Service.Instances.register("StorageService1", "WrongType", "127.0.0.1", 9999)
        assert str(excinfo).endswith('InvalidServiceType')

    async def test_register_invalid_port(self):
        with pytest.raises(TypeError) as excinfo:
            Service.Instances.register("StorageService2", "Storage", "127.0.0.1", "808a")
        assert str(excinfo).endswith("TypeError: Service port can be a positive integer only")

    async def test_unregister(self):
        idx = Service.Instances.register("StorageService2", "Storage", "127.0.0.1", 8888)
        assert str(uuid.UUID(idx, version=4)) == idx

        service_id = idx

        t = Service.Instances.unregister(service_id)
        assert service_id == t

        with pytest.raises(Service.DoesNotExist) as excinfo:
            Service.Instances.get(service_id)
        assert str(excinfo).endswith('DoesNotExist')

    async def test_get(self):
        s = Service.Instances.register("StorageService", "Storage", "localhost", 8888)
        d = Service.Instances.register("DeviceService", "Device", "127.0.0.1", 9999, "https")

        l = Service.Instances.get()

        assert 2 == len(l)

        assert s == l[0]._id
        assert "StorageService" == l[0]._name
        assert "Storage" == l[0]._type
        assert "localhost" == l[0]._address
        assert 8888 == int(l[0]._port)
        # validates default set to HTTP
        assert "http" == l[0]._protocol

        assert d == l[1]._id
        assert "DeviceService" == l[1]._name
        assert "Device" == l[1]._type
        assert "127.0.0.1" == l[1]._address
        assert 9999 == int(l[1]._port)
        assert "https" == l[1]._protocol

    async def test_get_fail(self):
        with pytest.raises(Service.DoesNotExist) as excinfo:
            Service.Instances.register("StorageService", "Storage", "127.0.0.1", 8888)
            Service.Instances.get('incorrect_id')
        assert str(excinfo).endswith('DoesNotExist')
