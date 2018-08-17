# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test services/south/ingest.py

"""
import copy
import pytest
from unittest.mock import MagicMock
from foglamp.services.south.ingest import *
from foglamp.services.south import ingest
from foglamp.common.storage_client.storage_client import StorageClientAsync, ReadingsStorageClientAsync
from foglamp.common.microservice_management_client.microservice_management_client import MicroserviceManagementClient


__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@asyncio.coroutine
def mock_coro():
    yield from false_coro()

async def false_coro():
    return True

def get_cat(old_config):
    new_config = {}
    for key, value in old_config.items():
        new_value = copy.deepcopy(value)
        new_value['value'] = new_value['default']
        new_config.update({key: new_value})
    return new_config

@pytest.allure.feature("unit")
@pytest.allure.story("services", "south", "ingest")
class TestIngest:
    def setup_method(self):
        # Important - We need to initialize class variables before each test
        Ingest._core_management_host = ""
        Ingest._core_management_port = 0
        Ingest.readings_storage_async = None  # type: Readings
        Ingest.storage_async = None  # type: Storage
        Ingest._readings_stats = 0  # type: int
        Ingest._discarded_readings_stats = 0  # type: int
        Ingest._sensor_stats = {}  # type: dict
        Ingest._write_statistics_task = None  # type: asyncio.Task
        Ingest._write_statistics_sleep_task = None  # type: asyncio.Task
        Ingest._stop = False
        Ingest._started = False
        Ingest._readings_lists = None  # type: List
        Ingest._current_readings_list_index = 0
        Ingest._insert_readings_tasks = None  # type: List[asyncio.Task]
        Ingest._readings_list_batch_size_reached = None  # type: List[asyncio.Event]
        Ingest._readings_list_not_empty = None  # type: List[asyncio.Event]
        Ingest._readings_lists_not_full = None  # type: asyncio.Event
        Ingest._insert_readings_wait_tasks = None  # type: List[asyncio.Task]
        Ingest._last_insert_time = 0  # type: int
        Ingest._readings_list_size = 0  # type: int
        Ingest._write_statistics_frequency_seconds = 5
        Ingest._readings_buffer_size = 500
        Ingest._max_concurrent_readings_inserts = 5
        Ingest._readings_insert_batch_size = 100
        Ingest._readings_insert_batch_timeout_seconds = 1
        Ingest._max_readings_insert_batch_connection_idle_seconds = 60
        Ingest._max_readings_insert_batch_reconnect_wait_seconds = 10
        Ingest.category = 'South'
        Ingest.default_config = {
            "write_statistics_frequency_seconds": {
                "description": "The number of seconds to wait before writing readings-related "
                               "statistics to storage",
                "type": "integer",
                "default": str(Ingest._write_statistics_frequency_seconds)
            },
            "readings_buffer_size": {
                "description": "The maximum number of readings to buffer in memory",
                "type": "integer",
                "default": str(Ingest._readings_buffer_size)
            },
            "max_concurrent_readings_inserts": {
                "description": "The maximum number of concurrent processes that send batches of "
                               "readings to storage",
                "type": "integer",
                "default": str(Ingest._max_concurrent_readings_inserts)
            },
            "readings_insert_batch_size": {
                "description": "The maximum number of readings in a batch of inserts",
                "type": "integer",
                "default": str(Ingest._readings_insert_batch_size)
            },
            "readings_insert_batch_timeout_seconds": {
                "description": "The number of seconds to wait for a readings list to reach the "
                               "minimum batch size",
                "type": "integer",
                "default": str(Ingest._readings_insert_batch_timeout_seconds)
            },
            "max_readings_insert_batch_connection_idle_seconds": {
                "description": "Close storage connections used to insert readings when idle for "
                               "this number of seconds",
                "type": "integer",
                "default": str(Ingest._max_readings_insert_batch_connection_idle_seconds)
            },
            "max_readings_insert_batch_reconnect_wait_seconds": {
                "description": "The maximum number of seconds to wait before reconnecting to "
                               "storage when inserting readings",
                "type": "integer",
                "default": str(Ingest._max_readings_insert_batch_reconnect_wait_seconds)
            },
        }

    @pytest.mark.asyncio
    async def test_read_config(self, mocker):
        # GIVEN
        Ingest.storage_async = MagicMock(spec=StorageClientAsync)
        Ingest.readings_storage_async = MagicMock(spec=ReadingsStorageClientAsync)
        mocker.patch.object(MicroserviceManagementClient, "__init__", return_value=None)
        create_cfg = mocker.patch.object(MicroserviceManagementClient, "create_configuration_category", return_value=None)
        get_cfg = mocker.patch.object(MicroserviceManagementClient, "get_configuration_category", return_value=get_cat(Ingest.default_config))
        Ingest._parent_service = MagicMock(_core_microservice_management_client=MicroserviceManagementClient())

        # WHEN
        await Ingest._read_config()

        # THEN
        assert 1 == create_cfg.call_count
        assert 1 == get_cfg.call_count
        new_config = get_cat(Ingest.default_config)
        assert Ingest._write_statistics_frequency_seconds == \
               int(new_config['write_statistics_frequency_seconds']['value'])
        assert Ingest._readings_buffer_size == int(new_config['readings_buffer_size']['value'])
        assert Ingest._max_concurrent_readings_inserts == \
               int(new_config['max_concurrent_readings_inserts']['value'])
        assert Ingest._readings_insert_batch_size == int(new_config['readings_insert_batch_size']['value'])
        assert Ingest._readings_insert_batch_timeout_seconds == \
               int(new_config['readings_insert_batch_timeout_seconds']['value'])
        assert Ingest._max_readings_insert_batch_connection_idle_seconds == \
               int(new_config['max_readings_insert_batch_connection_idle_seconds']['value'])
        assert Ingest._max_readings_insert_batch_reconnect_wait_seconds == \
               int(new_config['max_readings_insert_batch_reconnect_wait_seconds']['value'])
        
    @pytest.mark.asyncio
    async def test_start(self, mocker):
        # GIVEN
        mocker.patch.object(StorageClientAsync, "__init__", return_value=None)
        mocker.patch.object(ReadingsStorageClientAsync, "__init__", return_value=None)
        log_warning = mocker.patch.object(ingest._LOGGER, "warning")
        mocker.patch.object(MicroserviceManagementClient, "__init__", return_value=None)
        create_cfg = mocker.patch.object(MicroserviceManagementClient, "create_configuration_category", return_value=None)
        get_cfg = mocker.patch.object(MicroserviceManagementClient, "get_configuration_category", return_value=get_cat(Ingest.default_config))
        parent_service = MagicMock(_core_microservice_management_client=MicroserviceManagementClient())
        mocker.patch.object(Ingest, "_write_statistics", return_value=mock_coro())
        mocker.patch.object(Ingest, "_insert_readings", return_value=mock_coro())

        # WHEN
        await Ingest.start(parent=parent_service)

        # THEN
        assert 1 == create_cfg.call_count
        assert 1 == get_cfg.call_count
        assert Ingest._stop is False
        assert Ingest._started is True
        assert Ingest._readings_list_size == int(Ingest._readings_buffer_size / (
            Ingest._max_concurrent_readings_inserts))
        assert Ingest._last_insert_time is 0
        assert Ingest._max_concurrent_readings_inserts == len(Ingest._insert_readings_wait_tasks)
        assert Ingest._max_concurrent_readings_inserts == len(Ingest._readings_list_batch_size_reached)
        assert Ingest._max_concurrent_readings_inserts == len(Ingest._readings_list_not_empty)
        assert Ingest._max_concurrent_readings_inserts == len(Ingest._readings_lists)
        assert 0 == log_warning.call_count

    @pytest.mark.asyncio
    async def test_stop(self, mocker):
        # GIVEN
        mocker.patch.object(StorageClientAsync, "__init__", return_value=None)
        mocker.patch.object(ReadingsStorageClientAsync, "__init__", return_value=None)
        log_exception = mocker.patch.object(ingest._LOGGER, "exception")
        mocker.patch.object(MicroserviceManagementClient, "__init__", return_value=None)
        create_cfg = mocker.patch.object(MicroserviceManagementClient, "create_configuration_category", return_value=None)
        get_cfg = mocker.patch.object(MicroserviceManagementClient, "get_configuration_category", return_value=get_cat(Ingest.default_config))
        parent_service = MagicMock(_core_microservice_management_client=MicroserviceManagementClient())
        mocker.patch.object(Ingest, "_write_statistics", return_value=mock_coro())
        mocker.patch.object(Ingest, "_insert_readings", return_value=mock_coro())

        # WHEN
        await Ingest.start(parent=parent_service)
        await asyncio.sleep(1)
        await Ingest.stop()

        # THEN
        assert 1 == create_cfg.call_count
        assert 1 == get_cfg.call_count
        assert Ingest._stop is True
        assert Ingest._started is False
        assert Ingest._insert_readings_wait_tasks is None
        assert Ingest._insert_readings_tasks is None
        assert Ingest._readings_lists is None
        assert Ingest._readings_list_batch_size_reached is None
        assert Ingest._readings_list_not_empty is None
        assert Ingest._readings_lists_not_full is None
        assert 0 == log_exception.call_count

    @pytest.mark.asyncio
    async def test_increment_discarded_readings(self, mocker):
        # GIVEN
        # WHEN
        Ingest.increment_discarded_readings()

        # THEN
        assert 1 == Ingest._discarded_readings_stats

    @pytest.mark.skip(reason="This method uses a while True loop. Investigate as to how to write unit test for an infinite loop.")
    @pytest.mark.asyncio
    async def test__insert_readings(self, mocker):
        pass

    @pytest.mark.skip(reason="This method uses a while True loop. Investigate as to how to write unit test for an infinite loop.")
    @pytest.mark.asyncio
    async def test_write_statistics(self, mocker):
        pass

    @pytest.mark.asyncio
    async def test_is_available_at_start(self, mocker):
        # GIVEN
        Ingest._max_concurrent_readings_inserts = 1
        Ingest._readings_list_size = 2
        Ingest._current_readings_list_index = 0
        Ingest._readings_lists = []
        Ingest._readings_lists.append([])
        # Insert one task and leave room for more
        Ingest._readings_lists[0].append(mock_coro())
        log_warning = mocker.patch.object(ingest._LOGGER, "warning")
        mocker.patch.object(Ingest, "_write_statistics", return_value=mock_coro())
        mocker.patch.object(Ingest, "_insert_readings", return_value=mock_coro())

        # WHEN
        retval = Ingest.is_available()

        # THEN
        assert retval is True
        assert 0 == log_warning.call_count

    @pytest.mark.asyncio
    async def test_is_available_at_stop(self, mocker):
        # GIVEN
        Ingest._max_concurrent_readings_inserts = 1
        Ingest._readings_list_size = 2
        Ingest._current_readings_list_index = 0
        Ingest._readings_lists = []
        Ingest._readings_lists.append([])
        Ingest._readings_lists[0].append(mock_coro())
        log_warning = mocker.patch.object(ingest._LOGGER, "warning")
        Ingest._stop = True
        mocker.patch.object(Ingest, "_write_statistics", return_value=mock_coro())
        mocker.patch.object(Ingest, "_insert_readings", return_value=mock_coro())

        # WHEN
        retval = Ingest.is_available()

        # THEN
        assert retval is False
        assert 0 == log_warning.call_count

    @pytest.mark.asyncio
    async def test_is_available_when_all_lists_full(self, mocker):
        # GIVEN
        Ingest._max_concurrent_readings_inserts = 1
        Ingest._readings_list_size = 2
        Ingest._current_readings_list_index = 0
        Ingest._readings_lists = []
        Ingest._readings_lists.append([])
        # Insert two tasks
        Ingest._readings_lists[0].append(mock_coro())
        Ingest._readings_lists[0].append(mock_coro())
        log_warning = mocker.patch.object(ingest._LOGGER, "warning")
        mocker.patch.object(Ingest, "_write_statistics", return_value=mock_coro())
        mocker.patch.object(Ingest, "_insert_readings", return_value=mock_coro())

        # WHEN
        retval = Ingest.is_available()

        # THEN
        assert retval is False
        assert 1 == log_warning.call_count
        log_warning.assert_called_with('The ingest service is unavailable %s', 0)

    @pytest.mark.asyncio
    async def test_add_readings_all_ok(self, mocker):
        # GIVEN
        data = {
                "timestamp": "2017-01-02T01:02:03.23232Z-05:00",
                "asset": "pump1",
                "key": uuid.uuid4(),
                "readings": {
                    "velocity": "500",
                    "temperature": {
                        "value": "32",
                        "unit": "kelvin"
                    }
                }
        }
        Ingest._max_concurrent_readings_inserts = 1
        Ingest._readings_list_size = 2
        Ingest._current_readings_list_index = 0
        Ingest._readings_lists = []
        Ingest._readings_lists.append([])
        Ingest._readings_list_not_empty = []
        Ingest._readings_list_not_empty.append(asyncio.Event())
        Ingest._started = True
        mocker.patch.object(Ingest, "_write_statistics", return_value=mock_coro())
        mocker.patch.object(Ingest, "_insert_readings", return_value=mock_coro())
        mocker.patch.object(MicroserviceManagementClient, "__init__", return_value=None)
        mocker.patch.object(MicroserviceManagementClient, "create_asset_tracker_event", return_value=None)
        assert 0 == len(Ingest._readings_lists[0])
        assert 'PUMP1' not in list(Ingest._sensor_stats.keys())

        # WHEN
        await Ingest.add_readings(asset=data['asset'],
                                  timestamp=data['timestamp'],
                                  key=data['key'],
                                  readings=data['readings'])

        # THEN
        assert 1 == len(Ingest._readings_lists[0])
        assert 1 == Ingest._sensor_stats['PUMP1']

    @pytest.mark.asyncio
    async def test_add_readings_if_stop(self, mocker):
        # GIVEN
        data = {
                "timestamp": "2017-01-02T01:02:03.23232Z-05:00",
                "asset": "pump1",
                "key": uuid.uuid4(),
                "readings": {
                    "velocity": "500",
                    "temperature": {
                        "value": "32",
                        "unit": "kelvin"
                    }
                }
        }
        Ingest._max_concurrent_readings_inserts = 1
        Ingest._readings_list_size = 2
        Ingest._current_readings_list_index = 0
        Ingest._readings_lists = []
        Ingest._readings_lists.append([])
        Ingest._readings_list_not_empty = []
        Ingest._readings_list_not_empty.append(asyncio.Event())
        Ingest._stop = True
        log_warning = mocker.patch.object(ingest._LOGGER, "warning")
        mocker.patch.object(Ingest, "_write_statistics", return_value=mock_coro())
        mocker.patch.object(Ingest, "_insert_readings", return_value=mock_coro())
        assert 0 == len(Ingest._readings_lists[0])

        # WHEN
        await Ingest.add_readings(asset=data['asset'],
                                  timestamp=data['timestamp'],
                                  key=data['key'],
                                  readings=data['readings'])

        # THEN
        assert 0 == len(Ingest._readings_lists[0])
        assert 1 == log_warning.call_count
        log_warning.assert_called_with('The South Service is stopping')

    @pytest.mark.asyncio
    async def test_add_readings_not_started(self, mocker):
        # GIVEN
        data = {
                "timestamp": "2017-01-02T01:02:03.23232Z-05:00",
                "asset": "pump1",
                "key": uuid.uuid4(),
                "readings": {
                    "velocity": "500",
                    "temperature": {
                        "value": "32",
                        "unit": "kelvin"
                    }
                }
        }
        Ingest._max_concurrent_readings_inserts = 1
        Ingest._readings_list_size = 2
        Ingest._current_readings_list_index = 0
        Ingest._readings_lists = []
        Ingest._readings_lists.append([])
        Ingest._readings_list_not_empty = []
        Ingest._readings_list_not_empty.append(asyncio.Event())
        Ingest._started = False
        mocker.patch.object(Ingest, "_write_statistics", return_value=mock_coro())
        mocker.patch.object(Ingest, "_insert_readings", return_value=mock_coro())
        assert 0 == len(Ingest._readings_lists[0])

        # WHEN
        with pytest.raises(RuntimeError):
            await Ingest.add_readings(asset=data['asset'],
                                      timestamp=data['timestamp'],
                                      key=data['key'],
                                      readings=data['readings'])

        # THEN
        assert 0 == len(Ingest._readings_lists[0])

    @pytest.mark.asyncio
    async def test_add_readings_incorrect_data_values(self, mocker):
        # GIVEN
        data = {
                "timestamp": "2017-01-02T01:02:03.23232Z-05:00",
                "asset": "pump1",
                "key": uuid.uuid4(),
                "readings": {
                    "velocity": "500",
                    "temperature": {
                        "value": "32",
                        "unit": "kelvin"
                    }
                }
        }
        Ingest._max_concurrent_readings_inserts = 1
        Ingest._readings_list_size = 2
        Ingest._current_readings_list_index = 0
        Ingest._readings_lists = []
        Ingest._readings_lists.append([])
        Ingest._readings_list_not_empty = []
        Ingest._readings_list_not_empty.append(asyncio.Event())
        Ingest._started = True
        mocker.patch.object(Ingest, "_write_statistics", return_value=mock_coro())
        mocker.patch.object(Ingest, "_insert_readings", return_value=mock_coro())
        assert 0 == len(Ingest._readings_lists[0])

        # WHEN
        # Check for asset None
        with pytest.raises(ValueError):
            await Ingest.add_readings(asset=None,
                                      timestamp=data['timestamp'],
                                      key=data['key'],
                                      readings=data['readings'])

        # Check for asset not string
        with pytest.raises(TypeError):
            await Ingest.add_readings(asset=123,
                                      timestamp=None,
                                      key=data['key'],
                                      readings=data['readings'])

        # Check for timestamp None
        with pytest.raises(ValueError):
            await Ingest.add_readings(asset=data['asset'],
                                      timestamp=None,
                                      key=data['key'],
                                      readings=data['readings'])

        # Check for key str
        with pytest.raises(TypeError):
            await Ingest.add_readings(asset=data['asset'],
                                      timestamp=data['timestamp'],
                                      key=123,
                                      readings=data['readings'])

        # Check for readings dict
        with pytest.raises(TypeError):
            await Ingest.add_readings(asset=data['asset'],
                                      timestamp=data['timestamp'],
                                      key=data['key'],
                                      readings=123)
        # THEN
        assert 0 == len(Ingest._readings_lists[0])

    @pytest.mark.asyncio
    async def test_add_readings_when_one_list_becomes_full(self, mocker):
        # GIVEN
        data = {
                "timestamp": "2017-01-02T01:02:03.23232Z-05:00",
                "asset": "pump1",
                "key": uuid.uuid4(),
                "readings": {
                    "velocity": "500",
                    "temperature": {
                        "value": "32",
                        "unit": "kelvin"
                    }
                }
        }
        Ingest._max_concurrent_readings_inserts = 2
        Ingest._readings_list_size = 1
        Ingest._readings_insert_batch_size = 1
        Ingest._current_readings_list_index = 0
        Ingest._readings_lists = []
        Ingest._readings_lists.append([])
        Ingest._readings_lists.append([])
        Ingest._readings_list_not_empty = []
        Ingest._readings_list_not_empty.append(asyncio.Event())
        Ingest._readings_list_not_empty.append(asyncio.Event())
        Ingest._readings_list_batch_size_reached = []
        Ingest._readings_list_batch_size_reached.append(asyncio.Event())
        Ingest._readings_list_batch_size_reached.append(asyncio.Event())
        Ingest._started = True
        mocker.patch.object(Ingest, "_write_statistics", return_value=mock_coro())
        mocker.patch.object(Ingest, "_insert_readings", return_value=mock_coro())
        mocker.patch.object(MicroserviceManagementClient, "__init__", return_value=None)
        mocker.patch.object(MicroserviceManagementClient, "create_asset_tracker_event", return_value=None)

        assert 0 == len(Ingest._readings_lists[0])
        assert 'PUMP1' not in list(Ingest._sensor_stats.keys())

        # WHEN
        await Ingest.add_readings(asset=data['asset'],
                                  timestamp=data['timestamp'],
                                  key=data['key'],
                                  readings=data['readings'])
        # First reading_list is full, so now add to second list
        await Ingest.add_readings(asset=data['asset'],
                                  timestamp=data['timestamp'],
                                  key=data['key'],
                                  readings=data['readings'])

        # THEN
        assert 1 == len(Ingest._readings_lists[0])
        assert 1 == len(Ingest._readings_lists[1])
        assert 2 == Ingest._sensor_stats['PUMP1']
