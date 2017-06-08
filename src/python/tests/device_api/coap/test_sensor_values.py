from foglamp.device_api.coap.sensor_values import SensorValues
import unittest
from unittest import mock
from unittest.mock import MagicMock
from cbor2 import dumps
import asyncio


def AsyncMock(*args, **kwargs):
    m = mock.MagicMock(*args, **kwargs)

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
class TestSensorValues(unittest.TestCase):
    @mock.patch('aiopg.sa.create_engine')
    def test_render_post(self, test_patch1):
        test_patch1.return_value = CreateEngineContextManager()
        # test_patch3.return_value = values(data='', key='')
        sv = SensorValues()
        request = MagicMock()
        dict_payload = {'jack': 4098, 'sape': 4139}
        request.payload = dumps(dict_payload)
        returnval = _run(sv.render_post(request))
        assert returnval is not None
        # assert sqlalchemy.Table.insert.mock.assert_called_once_with('blu')
        # assert MagicMockConnection.execute.mock.assert_called_once_with('blu')

