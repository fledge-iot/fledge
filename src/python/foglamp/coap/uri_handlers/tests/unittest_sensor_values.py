from foglamp.coap.uri_handlers.sensor_values import SensorValues
from foglamp.coap.uri_handlers.sensor_values import SensorValues
from foglamp.coap.uri_handlers.sensor_values import __tbl__
from foglamp.coap.uri_handlers.sensor_values import *
import sqlalchemy
import unittest
from unittest import mock
from unittest.mock import MagicMock
from cbor2 import dumps

def AsyncMock(*args, **kwargs):
    """
    Mock an async behavior
    Args:
        *args: 
        **kwargs: 

    Returns:
    """
    m = mock.MagicMock(*args, **kwargs)

    async def mock_coro(*args, **kwargs):
        return m(*args, **kwargs)

    mock_coro.mock = m
    return mock_coro

class MagicMockConnection(MagicMock):
    """
    Mock a connection to a node 
    """
    execute = AsyncMock()

class AcquireContextManager(MagicMock):
    """
    An asynchronous context manager is a context manager that is able to suspend execution 
    in its enter and exit methods.
    
    https://www.python.org/dev/peps/pep-0492/
    """
    async def __aenter__(self):
        connection = MagicMockConnection()
        return connection

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

class MagicMockEngine(MagicMock):
    acquire = AcquireContextManager()


class CreateEngineContextManager(MagicMock):
    """
    Mock creation of engine, and it's content
    """
    async def __aenter__(self):
        engine = MagicMockEngine()
        return engine

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

class FakeConfig(MagicMock):
    """
    fake configuration files/information
    """
    db_conn_str = "fake_connection"

def _run(coro):
    """
    Execution of the function based on request (coro) 
    Args:
        coro: 

    Returns:

    """
    return asyncio.get_event_loop().run_until_complete(coro)

# http://docs.sqlalchemy.org/en/latest/core/dml.html
class TestSensorValues(unittest.TestCase):
    @mock.patch('aiopg.sa.create_engine')
    @mock.patch('foglamp.configurator.Configurator.__init__')
    def test_render_post(self, test_patch1, test_patch2):
        test_patch1.return_value = None
        test_patch2.return_value = CreateEngineContextManager() # call of CreateEngineContextManager
        # test_patch3.return_value = values(data='', key='')
        sv = SensorValues() # call of SensorValues
        request = MagicMock() # call of MagicMock
        dict_payload = {'jack': 4098, 'sape': 4139} # dict of sample data
        request.payload = dumps(dict_payload) # dump of sample data
        returnval = _run(sv.render_post(request)) # generate results

        assert returnval is not None # verify results returned are not empty

        # assert sqlalchemy.Table.insert.mock.assert_called_once_with('blu')
        # assert MagicMockConnection.execute.mock.assert_called_once_with('blu')



