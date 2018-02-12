# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test foglamp/common/storage_client/exceptions.py """

import pytest

from foglamp.common.storage_client.exceptions import StorageClientException
from foglamp.common.storage_client.exceptions import *

__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("common", "storage_client")
class TestStorageClientExceptions:

    def test_init_StorageClientException(self):

        with pytest.raises(Exception) as excinfo:
            raise StorageClientException()
        assert excinfo.type is TypeError
        assert "__init__() missing 1 required positional argument: 'code'" == str(excinfo.value)

    def test_default_init_StorageClientException(self):
        with pytest.raises(Exception) as excinfo:
            raise StorageClientException(40)
        assert excinfo.type is StorageClientException
        assert issubclass(excinfo.type, Exception)

        try:
            raise StorageClientException(40)
        except Exception as ex:
            assert ex.__class__ is StorageClientException
            assert issubclass(ex.__class__, Exception)
            assert 40 == ex.code
            assert ex.message is None

    def test_init_args_StorageClientException(self):
        with pytest.raises(Exception) as excinfo:
            raise StorageClientException(code=11, message="foo")
        assert excinfo.type is StorageClientException
        assert issubclass(excinfo.type, Exception)
        # code is 11
        assert "foo" == str(excinfo.value)

        try:
            raise StorageClientException(code=11, message="foo")
        except Exception as ex:
            assert ex.__class__ is StorageClientException
            assert issubclass(ex.__class__, Exception)
            assert 11 == ex.code
            assert "foo" == ex.message

    def test_BadRequest(self):
        with pytest.raises(Exception) as excinfo:
            raise BadRequest()
        assert excinfo.type is BadRequest
        assert issubclass(excinfo.type, StorageClientException)
        # code is 400
        assert "Bad request" == str(excinfo.value)

    def test_BadRequest2(self):
        try:
            raise BadRequest()
        except Exception as ex:
            assert ex.__class__ is BadRequest
            assert issubclass(ex.__class__, StorageClientException)
            assert 400 == ex.code
            assert "Bad request" == ex.message

    def test_StorageServiceUnavailable(self):
        with pytest.raises(Exception) as excinfo:
            raise StorageServiceUnavailable()
        assert excinfo.type is StorageServiceUnavailable
        assert issubclass(excinfo.type, StorageClientException)
        # code is 503
        assert "Storage service is unavailable" == str(excinfo.value)

    def test_InvalidServiceInstance(self):
        with pytest.raises(Exception) as excinfo:
            raise InvalidServiceInstance()
        assert excinfo.type is InvalidServiceInstance
        assert issubclass(excinfo.type, StorageClientException)
        # code is 502
        assert "Storage client needs a valid *FogLAMP storage* micro-service instance" == str(excinfo.value)

    def test_InvalidReadingsPurgeFlagParameters(self):
        with pytest.raises(Exception) as excinfo:
            raise InvalidReadingsPurgeFlagParameters()
        assert excinfo.type is InvalidReadingsPurgeFlagParameters
        assert issubclass(excinfo.type, BadRequest)
        # code is 400
        assert "Purge flag valid options are retain or purge only" == str(excinfo.value)

    def test_PurgeOnlyOneOfAgeAndSize(self):
        with pytest.raises(Exception) as excinfo:
            raise PurgeOnlyOneOfAgeAndSize()
        assert excinfo.type is PurgeOnlyOneOfAgeAndSize
        assert issubclass(excinfo.type, BadRequest)
        # code is 400
        assert "Purge must specify only one of age or size" == str(excinfo.value)

    def test_PurgeOneOfAgeAndSize(self):
        with pytest.raises(Exception) as excinfo:
            raise PurgeOneOfAgeAndSize()
        assert excinfo.type is PurgeOneOfAgeAndSize
        assert issubclass(excinfo.type, BadRequest)
        # code is 400
        assert "Purge must specify one of age or size" == str(excinfo.value)
