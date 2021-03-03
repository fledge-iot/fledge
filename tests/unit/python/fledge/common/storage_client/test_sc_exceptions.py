# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test fledge/common/storage_client/exceptions.py """

import pytest

from fledge.common.storage_client.exceptions import StorageClientException
from fledge.common.storage_client.exceptions import *

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
        # pytest raises wrapper allow only type, value and traceback info
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

        try:
            raise StorageServiceUnavailable()
        except Exception as ex:
            assert ex.__class__ is StorageServiceUnavailable
            assert issubclass(ex.__class__, StorageClientException)
            assert 503 == ex.code
            assert "Storage service is unavailable" == ex.message

    def test_InvalidServiceInstance(self):
        with pytest.raises(Exception) as excinfo:
            raise InvalidServiceInstance()
        assert excinfo.type is InvalidServiceInstance
        assert issubclass(excinfo.type, StorageClientException)

        try:
            raise InvalidServiceInstance()
        except Exception as ex:
            assert ex.__class__ is InvalidServiceInstance
            assert issubclass(ex.__class__, StorageClientException)
            assert 502 == ex.code
            assert "Storage client needs a valid *Fledge storage* micro-service instance" == ex.message

    def test_InvalidReadingsPurgeFlagParameters(self):
        with pytest.raises(Exception) as excinfo:
            raise InvalidReadingsPurgeFlagParameters()
        assert excinfo.type is InvalidReadingsPurgeFlagParameters
        assert issubclass(excinfo.type, BadRequest)

        try:
            raise InvalidReadingsPurgeFlagParameters()
        except Exception as ex:
            assert ex.__class__ is InvalidReadingsPurgeFlagParameters
            assert issubclass(ex.__class__, BadRequest)
            assert 400 == ex.code
            assert "Purge flag valid options are retain or purge only" == ex.message

    def test_PurgeOneOfAgeAndSize(self):
        with pytest.raises(Exception) as excinfo:
            raise PurgeOneOfAgeAndSize()
        assert excinfo.type is PurgeOneOfAgeAndSize
        assert issubclass(excinfo.type, BadRequest)

        try:
            raise PurgeOneOfAgeAndSize()
        except Exception as ex:
            assert ex.__class__ is PurgeOneOfAgeAndSize
            assert issubclass(ex.__class__, BadRequest)
            assert 400 == ex.code
            assert "Purge must specify one of age or size" == ex.message

    def test_PurgeOnlyOneOfAgeAndSize(self):
        with pytest.raises(Exception) as excinfo:
            raise PurgeOnlyOneOfAgeAndSize()
        assert excinfo.type is PurgeOnlyOneOfAgeAndSize
        assert issubclass(excinfo.type, BadRequest)

        try:
            raise PurgeOnlyOneOfAgeAndSize()
        except Exception as ex:
            assert ex.__class__ is PurgeOnlyOneOfAgeAndSize
            assert issubclass(ex.__class__, BadRequest)
            assert 400 == ex.code
            assert "Purge must specify only one of age or size" == ex.message

    def test_StorageServerError(self):
        with pytest.raises(Exception) as excinfo:
            raise StorageServerError(code=400, reason="blah", error={"k": "v"})
        assert excinfo.type is StorageServerError
        assert issubclass(excinfo.type, Exception)

        try:
            raise StorageServerError(code=400, reason="blah", error={"k": "v"})
        except Exception as ex:
            assert ex.__class__ is StorageServerError
            assert issubclass(ex.__class__, Exception)
            assert 400 == ex.code
            assert "blah" == ex.reason
            assert {"k": "v"} == ex.error
