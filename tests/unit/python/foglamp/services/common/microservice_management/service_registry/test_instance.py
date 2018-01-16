# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import uuid
import pytest

from foglamp.services.core.service_registry.service_registry import ServiceRegistry as Service
from foglamp.services.core.service_registry.exceptions import *
from foglamp.common.service_record import ServiceRecord

__author__ = "Amarendra Kumar Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

pytestmark = pytest.mark.asyncio


@pytest.allure.feature("unit")
@pytest.allure.story("service-registry instance")
class TestInstance:

    def setup_method(self):
        Service._registry = []

    def teardown_method(self):
        Service._registry = []

    async def test_register(self):
        idx = Service.register("StorageService1", "Storage", "127.0.0.1", 9999, 1999)
        assert str(uuid.UUID(idx, version=4)) == idx

    async def test_duplicate_name_registration(self):
        idx1 = Service.register("StorageService1", "Storage", "127.0.0.1", 9999, 1999)
        assert str(uuid.UUID(idx1, version=4)) == idx1
        with pytest.raises(AlreadyExistsWithTheSameName) as excinfo:
            Service.register("StorageService1", "Storage", "127.0.0.1", 9999, 1999)
        assert str(excinfo).endswith('AlreadyExistsWithTheSameName')

    async def test_duplicate_address_port_registration(self):
        idx1 = Service.register("StorageService1", "Storage", "127.0.0.1", 9999, 1999)
        assert str(uuid.UUID(idx1, version=4)) == idx1
        with pytest.raises(AlreadyExistsWithTheSameAddressAndPort) as excinfo:
            Service.register("StorageService2", "Storage", "127.0.0.1", 9999, 1998)
        assert str(excinfo).endswith('AlreadyExistsWithTheSameAddressAndPort')

    async def test_duplicate_address_and_mgt_port_registration(self):
        idx1 = Service.register("StorageService1", "Storage", "127.0.0.1", 9999, 1999)
        assert str(uuid.UUID(idx1, version=4)) == idx1
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

    async def test_unregister(self):
        # register a service
        idx = Service.register("StorageService2", "Storage", "127.0.0.1", 8888, 1888)
        assert str(uuid.UUID(idx, version=4)) == idx

        # deregister the same
        t = Service.unregister(idx)
        assert idx == t

        with pytest.raises(DoesNotExist) as excinfo:
            Service.get(idx)
        assert str(excinfo).endswith('DoesNotExist')

    async def test_get(self):
        s = Service.register("StorageService", "Storage", "localhost", 8881, 1888)
        c = Service.register("CoreService", "Core", "localhost", 7771, 1777)
        d = Service.register("SouthService", "Southbound", "127.0.0.1", 9991, 1999, "https")

        l = Service.get()
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
        assert "SouthService" == l[2]._name
        assert "Southbound" == l[2]._type
        assert "127.0.0.1" == l[2]._address
        assert 9991 == int(l[2]._port)
        assert 1999 == int(l[2]._management_port)
        assert "https" == l[2]._protocol

    async def test_get_fail(self):
        with pytest.raises(DoesNotExist) as excinfo:
            Service.register("StorageService", "Storage", "127.0.0.1", 8888, 9999)
            Service.get('incorrect_id')
        assert str(excinfo).endswith('DoesNotExist')
