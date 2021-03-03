# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test fledge/services/core/service_registry/exceptions.py """

import pytest

from fledge.services.core.service_registry.exceptions import *

__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("services", "core", "service_registry")
class TestServiceRegistryExceptions:

    def test_DoesNotExist(self):
        with pytest.raises(Exception) as excinfo:
            raise DoesNotExist()
        assert excinfo.type is DoesNotExist
        assert issubclass(excinfo.type, Exception)
        assert "" == str(excinfo.value)

    def test_AlreadyExistsWithTheSameName(self):
        with pytest.raises(Exception) as excinfo:
            raise AlreadyExistsWithTheSameName()
        assert excinfo.type is AlreadyExistsWithTheSameName
        assert issubclass(excinfo.type, Exception)
        assert "" == str(excinfo.value)

    def test_AlreadyExistsWithTheSameAddressAndPort(self):
        with pytest.raises(Exception) as excinfo:
            raise AlreadyExistsWithTheSameAddressAndPort()
        assert excinfo.type is AlreadyExistsWithTheSameAddressAndPort
        assert issubclass(excinfo.type, Exception)
        assert "" == str(excinfo.value)

    def test_AlreadyExistsWithTheSameAddressAndManagementPort(self):
        with pytest.raises(Exception) as excinfo:
            raise AlreadyExistsWithTheSameAddressAndManagementPort()
        assert excinfo.type is AlreadyExistsWithTheSameAddressAndManagementPort
        assert issubclass(excinfo.type, Exception)
        assert "" == str(excinfo.value)

    def test_NonNumericPortError(self):
        with pytest.raises(Exception) as excinfo:
            raise NonNumericPortError()
        assert excinfo.type is NonNumericPortError
        assert issubclass(excinfo.type, TypeError)
        assert "" == str(excinfo.value)
