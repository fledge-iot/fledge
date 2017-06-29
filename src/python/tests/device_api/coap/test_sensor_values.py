# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import pytest
from unittest.mock import MagicMock
from cbor2 import dumps
from aiocoap.numbers.codes import Code as CoAP_CODES

from foglamp.device_api.coap.sensor_values import SensorValues

__author__    = "Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__   = "Apache 2.0"
__version__   = "${VERSION}"

# TODO The functions and classes between this line
# and the line marked END will be replaced by
# mocks for the storage layer.
#
# Mock the following code:
#
#async with aiopg.sa.create_engine('...') as engine:
#    async with engine.acquire() as conn:
#        await conn.execute(...)
def async_mock(*args, **kwargs):
    """Returns a coroutine that does nothing
    """
    m = MagicMock(*args, **kwargs)

    async def mock_coro(*args, **kwargs):
        return m(*args, **kwargs)

    return mock_coro


class MockConnection(MagicMock):
    """execute() returns a coroutine that does nothing
    """
    execute = async_mock()


class AcquireContextManager(MagicMock):
    """An async context manager that returns a MockConnection in __aenter__
    """
    async def __aenter__(self):
        return MockConnection()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockEngine(MagicMock):
    """aquire() returns a AcquireContextManager object
    """
    acquire = AcquireContextManager()


class CreateEngineContextManager(MagicMock):
    """An async context manager that returns a MockEngine in __aenter__
    """
    async def __aenter__(self):
        return MockEngine()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
        
def _mock_create_engine(mocker):
    mocker.patch('aiopg.sa.create_engine', return_value=CreateEngineContextManager())
# END


class TestSensorValues:
    """Unit tests for SensorValues
    """
    __requests = [
        ({}, CoAP_CODES.BAD_REQUEST),
        ('hello world', CoAP_CODES.BAD_REQUEST),
        ({'asset':'test'}, CoAP_CODES.BAD_REQUEST),
        ({'timestamp':'2017-01-01T00:00:00Z'}, CoAP_CODES.BAD_REQUEST),
        ({'timestamp':'2017-01-01T00:00:00Z', 'asset':'test'}, CoAP_CODES.VALID)
    ]
    """An array of tuples consisting of (payload, expected status code)
    """

    @pytest.mark.parametrize("dict_payload, expected", __requests)
    @pytest.mark.asyncio
    async def test_payload(self, mocker, dict_payload, expected):
        """Runs all test cases in the __requests array"""
        _mock_create_engine(mocker)
        sv = SensorValues()
        request = MagicMock()
        request.payload = dumps(dict_payload)
        return_val = await sv.render_post(request)
        assert return_val.code == expected

