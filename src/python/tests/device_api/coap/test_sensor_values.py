# -*- coding: utf-8 -*-

import pytest
from unittest.mock import MagicMock
from cbor2 import dumps
import asyncio
from aiocoap.numbers.codes import Code as CoAP_CODES

from foglamp.device_api.coap.sensor_values import SensorValues

__author__ = 'Terris Linenbach'
__version__ = '${VERSION}'

# TODO The functions and classes between this line
# and the line marked END will be replaced by
# mocks that for the storage layer.
def async_mock(*args, **kwargs):
    """Returns a coroutine that does nothing"""
    m = MagicMock(*args, **kwargs)

    async def mock_coro(*args, **kwargs):
        return m(*args, **kwargs)

    # mock_coro.mock = m # what?
    return mock_coro


class MockConnection(MagicMock):
    """Calling execute() on this object returns a coroutine that does nothing"""
    execute = async_mock()


class AcquireContextManager(MagicMock):
    """An async context manager that returns a MockConnection object in __aenter__"""
    async def __aenter__(self):
        return MockConnection()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockEngine(MagicMock):
    """Calling aquire() on the object returns a AcquireContextManager object"""
    acquire = AcquireContextManager()


class CreateEngineContextManager(MagicMock):
    """An async context manager that returns a MockEngine object in __aenter__"""
    async def __aenter__(self):
        engine = MockEngine()
        return engine

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

# END


def _run(coroutine):
    """Block until the provided coroutine has finished"""
    return asyncio.get_event_loop().run_until_complete(coroutine)


_requests = [
    ({}, CoAP_CODES.BAD_REQUEST),
    ('hello world', CoAP_CODES.BAD_REQUEST),
    ({'asset':'test'}, CoAP_CODES.BAD_REQUEST),
    ({'timestamp':'2017-01-01T00:00:00Z'}, CoAP_CODES.BAD_REQUEST),
    ({'timestamp':'2017-01-01T00:00:00Z', 'asset':'test'}, CoAP_CODES.VALID)
]


class TestSensorValues:
    """Unit tests for SensorValues"""
    @staticmethod
    def __setup(mocker):
        mocker.patch('aiopg.sa.create_engine', return_value=CreateEngineContextManager())

    @pytest.mark.parametrize("dict_payload, expected", _requests)
    def test_payload(self, mocker, dict_payload, expected):
        self.__setup(mocker)
        sv = SensorValues()
        request = MagicMock()
        request.payload = dumps(dict_payload)
        return_val = _run(sv.render_post(request))
        assert return_val.code == expected

