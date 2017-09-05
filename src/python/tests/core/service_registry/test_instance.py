# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import pytest
from foglamp.core.service_registry.instance import Service

__author__ = "Amarendra Kumar Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class TestInstance:
    def setup_method(self, method):
        Service.Instances._registry = []

    def teardown_method(self, method):
        pass

    @pytest.mark.asyncio
    async def test_register(self):
        r = Service.Instances.register("StorageService1", "Storage", "127.0.0.1", "9999")

        # TODO: add check returned id for valid UUID ver 4
        assert "StorageService1" == r._name
        assert "Storage" == r._type
        assert "127.0.0.1" == r._address
        assert "9999" == r._port

    @pytest.mark.asyncio
    async def test_register_wrong_type(self):
        with pytest.raises(Service.InvalidServiceType) as excinfo:
            Service.Instances.register("StorageService1", "Wrong", "127.0.0.1", "9999")

        assert str(excinfo).endswith('InvalidServiceType')

    @pytest.mark.asyncio
    async def test_unregister(self):
        r = Service.Instances.register("StorageService2", "Storage", "127.0.0.1", "8888")

        # TODO: add check returned id for valid UUID ver 4
        service_id = r._id

        t = Service.Instances.unregister(service_id)
        assert service_id == t

        with pytest.raises(Service.DoesNotExist) as excinfo:
            l = Service.Instances.get(service_id)
        assert str(excinfo).endswith('DoesNotExist')

    @pytest.mark.asyncio
    async def test_get(self):
        s = Service.Instances.register("StorageService", "Storage", "127.0.0.1", "8888")
        d = Service.Instances.register("DeviceService", "Device", "127.0.0.1", "9999")

        l = Service.Instances.get()

        assert 2 == len(l)
        assert s._id == l[0]._id
        assert d._id == l[1]._id

    @pytest.mark.asyncio
    async def test_get_fail(self):
        with pytest.raises(Service.DoesNotExist) as excinfo:
            s = Service.Instances.register("StorageService", "Storage", "127.0.0.1", "8888")
            l = Service.Instances.get('incorrect_id')

        assert str(excinfo).endswith('DoesNotExist')
