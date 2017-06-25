import asyncio
import aiocoap
from unittest.mock import MagicMock
from cbor2 import dumps

from foglamp.device_api.coap.sensor_values import SensorValues


def AsyncMock(*args, **kwargs):
    m = MagicMock(*args, **kwargs)

    async def mock_coro(*args, **kwargs):
        return m(*args, **kwargs)

    mock_coro.mock = m
    return mock_coro


class MagicMockConnection(MagicMock):
    execute = AsyncMock()


class AcquireContextManager(MagicMock):
    async def __aenter__(self):
        connection = MagicMockConnection()
        return connection

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MagicMockEngine(MagicMock):
    acquire = AcquireContextManager()


class CreateEngineContextManager(MagicMock):
    async def __aenter__(self):
        engine = MagicMockEngine()
        return engine

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# http://docs.sqlalchemy.org/en/latest/core/dml.html
class TestSensorValues:
    def test_invalid_payload1(self, mocker):
        """Test Bad Input"""
        mocker.patch('aiopg.sa.create_engine', return_value=CreateEngineContextManager())
        sv = SensorValues()
        request = MagicMock()
        dict_payload = {}
        request.payload = dumps(dict_payload)
        return_val = _run(sv.render_post(request))
        assert return_val.code == aiocoap.numbers.codes.Code.BAD_REQUEST

    def test_invalid_payload2(self, mocker):
        """Test Bad Input"""
        mocker.patch('aiopg.sa.create_engine', return_value=CreateEngineContextManager())
        sv = SensorValues()
        request = MagicMock()
        dict_payload = 'hello world'
        request.payload = dumps(dict_payload)
        return_val = _run(sv.render_post(request))
        assert return_val.code == aiocoap.numbers.codes.Code.BAD_REQUEST

    def test_good_payload(self, mocker):
        """Test Good Input"""
        mocker.patch('aiopg.sa.create_engine', return_value=CreateEngineContextManager())
        sv = SensorValues()
        request = MagicMock()
        dict_payload = {'timestamp':'2017-01-01T00:00:00Z', 'asset':'test'}
        request.payload = dumps(dict_payload)
        return_val = _run(sv.render_post(request))
        assert return_val.code == aiocoap.numbers.codes.Code.VALID

