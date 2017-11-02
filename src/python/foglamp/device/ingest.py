# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""FogLAMP Sensor Readings Ingest API"""

import asyncio
import datetime
import time
import uuid
from typing import List, Union

# import dateutil.parser
import json

from foglamp import logger
from foglamp import statistics
from foglamp import configuration_manager
from foglamp.storage.storage import Readings


__author__ = "Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_LOGGER = logger.setup(__name__)  # type: logging.Logger
# _LOGGER = logger.setup(__name__, level=logging.DEBUG)  # type: logging.Logger
# _LOGGER = logger.setup(__name__, destination=logger.CONSOLE, level=logging.DEBUG)


class Ingest(object):
    """Adds sensor readings to FogLAMP

    Also tracks readings-related statistics.
    Readings are added to a configurable list. Configurable batches of inserts are sent to storage
    """

    # Class attributes

    _core_management_host = ""
    _core_management_port = 0

    _readings_stats = 0  # type: int
    """Number of readings accepted before statistics were written to storage"""

    _discarded_readings_stats = 0  # type: int
    """Number of readings rejected before statistics were written to storage"""

    _write_statistics_task = None  # type: asyncio.Task
    """asyncio task for :meth:`_write_statistics`"""

    _write_statistics_sleep_task = None  # type: asyncio.Task
    """asyncio task for asyncio.sleep"""

    _stop = False
    """True when the server needs to stop"""

    _started = False
    """True when the server has been started"""

    _readings_lists = None  # type: List
    """A list of readings lists. Each list contains the inputs to :meth:`add_readings`."""

    _current_readings_list_index = 0
    """Which readings list to insert into next"""

    _insert_readings_tasks = None  # type: List[asyncio.Task]
    """asyncio tasks for :meth:`_insert_readings`"""

    _readings_list_batch_size_reached = None  # type: List[asyncio.Event]
    """Fired when a readings list has reached _readings_insert_batch_size entries"""

    _readings_list_not_empty = None  # type: List[asyncio.Event]
    """Fired when a readings list transitions from empty to not empty"""

    _readings_lists_not_full = None  # type: asyncio.Event
    """Fired when items are removed from any readings list"""

    _insert_readings_wait_tasks = None  # type: List[asyncio.Task]
    """asyncio tasks blocking :meth:`_insert_readings` that can be canceled"""

    _last_insert_time = 0  # type: int
    """epoch time of last insert"""

    _readings_list_size = 0  # type: int
    """Maximum number of readings items in each buffer"""

    # Configuration (begin)
    _write_statistics_frequency_seconds = 5
    """The number of seconds to wait before writing readings-related statistics to storage"""

    _readings_buffer_size = 500
    """Maximum number of readings to buffer in memory"""

    _max_concurrent_readings_inserts = 5
    """Maximum number of concurrent processes that send batches of readings to storage"""

    _readings_insert_batch_size = 100
    """Maximum number of readings in a batch of inserts"""

    _readings_insert_batch_timeout_seconds = 1
    """Number of seconds to wait for a readings list to reach the minimum batch size"""

    _max_readings_insert_batch_connection_idle_seconds = 60
    """Close connections used to insert readings when idle for this number of seconds"""

    _max_readings_insert_batch_reconnect_wait_seconds = 10
    """The maximum number of seconds to wait before reconnecting to storage when inserting readings"""
    # Configuration (end)

    @classmethod
    async def _read_config(cls):
        """Creates default values for the DEVICE configuration category and then reads all
        values for this category
        """
        category = 'DEVICE'

        default_config = {
             "write_statistics_frequency_seconds": {
                "description": "The number of seconds to wait before writing readings-related "
                               "statistics to storage",
                "type": "integer",
                "default": str(cls._write_statistics_frequency_seconds)
             },
            "readings_buffer_size": {
                "description": "The maximum number of readings to buffer in memory",
                "type": "integer",
                "default": str(cls._readings_buffer_size)
            },
            "max_concurrent_readings_inserts": {
                "description": "The maximum number of concurrent processes that send batches of "
                               "readings to storage",
                "type": "integer",
                "default": str(cls._max_concurrent_readings_inserts)
            },
            "readings_insert_batch_size": {
                "description": "The maximum number of readings in a batch of inserts",
                "type": "integer",
                "default": str(cls._readings_insert_batch_size)
            },
            "readings_insert_batch_timeout_seconds": {
                "description": "The number of seconds to wait for a readings list to reach the "
                               "minimum batch size",
                "type": "integer",
                "default": str(cls._readings_insert_batch_timeout_seconds)
            },
            "max_readings_insert_batch_connection_idle_seconds": {
                "description": "Close storage connections used to insert readings when idle for "
                            "this number of seconds",
                "type": "integer",
                "default": str(cls._max_readings_insert_batch_connection_idle_seconds)
            },
            "max_readings_insert_batch_reconnect_wait_seconds": {
                "description": "The maximum number of seconds to wait before reconnecting to "
                                "storage when inserting readings",
                "type": "integer",
                "default": str(cls._max_readings_insert_batch_reconnect_wait_seconds)
            },
        }

        # Create configuration category and any new keys within it
        await configuration_manager.create_category(category, default_config,
                                                    'Device server configuration')

        # Read configuration
        config = await configuration_manager.get_category_all_items(category)

        cls._write_statistics_frequency_seconds = int(config['write_statistics_frequency_seconds']
                                                            ['value'])
        cls._readings_buffer_size = int(config['readings_buffer_size']['value'])
        cls._max_concurrent_readings_inserts = int(config['max_concurrent_readings_inserts']
                                                         ['value'])
        cls._readings_insert_batch_size = int(config['readings_insert_batch_size']['value'])
        cls._readings_insert_batch_timeout_seconds = int(config
                                                         ['readings_insert_batch_timeout_seconds']
                                                         ['value'])
        cls._max_readings_insert_batch_connection_idle_seconds = int(
                config['max_readings_insert_batch_connection_idle_seconds']
                      ['value'])
        cls._max_readings_insert_batch_reconnect_wait_seconds = int(
            config['max_readings_insert_batch_reconnect_wait_seconds']['value'])

    @classmethod
    async def start(cls, core_mgt_host, core_mgt_port):
        """Starts the server"""
        if cls._started:
            return

        cls._core_management_host = core_mgt_host
        cls._core_management_port = core_mgt_port

        await cls._read_config()

        cls._readings_list_size = int(cls._readings_buffer_size / (
            cls._max_concurrent_readings_inserts))

        # Is the buffer size as configured big enough to support all of
        # the buffers filled to the batch size? If not, increase
        # the buffer size.
        if cls._readings_list_size < cls._readings_insert_batch_size:
            cls._readings_list_size = cls._readings_insert_batch_size

            _LOGGER.warning('Readings buffer size as configured (%s) is too small; increasing '
                            'to %s', cls._readings_buffer_size,
                            cls._readings_list_size * cls._max_concurrent_readings_inserts)

        # Start asyncio tasks
        cls._write_statistics_task = asyncio.ensure_future(cls._write_statistics())

        cls._last_insert_time = 0

        cls._insert_readings_tasks = []
        cls._insert_readings_wait_tasks = []
        cls._readings_list_batch_size_reached = []
        cls._readings_list_not_empty = []
        cls._readings_lists = []

        for _ in range(cls._max_concurrent_readings_inserts):
            cls._readings_lists.append([])
            cls._insert_readings_wait_tasks.append(None)
            cls._insert_readings_tasks.append(asyncio.ensure_future(cls._insert_readings(_)))
            cls._readings_list_batch_size_reached.append(asyncio.Event())
            cls._readings_list_not_empty.append(asyncio.Event())

        cls._readings_lists_not_full = asyncio.Event()

        cls._stop = False
        cls._started = True

    @classmethod
    async def stop(cls):
        """Stops the server

        Writes pending statistics and readings to storage
        """
        if cls._stop or not cls._started:
            return

        cls._stop = True

        for task in cls._insert_readings_wait_tasks:
            if task is not None:
                task.cancel()

        for task in cls._insert_readings_tasks:
            try:
                await task
            except Exception:
                _LOGGER.exception('An exception was raised by Ingest._insert_readings')

        cls._insert_readings_wait_tasks = None
        cls._insert_readings_tasks = None
        cls._readings_lists = None
        cls._readings_list_batch_size_reached = None
        cls._readings_list_not_empty = None
        cls._readings_lists_not_full = None

        # Write statistics
        if cls._write_statistics_sleep_task is not None:
            cls._write_statistics_sleep_task.cancel()
            cls._write_statistics_sleep_task = None

        try:
            await cls._write_statistics_task
            cls._write_statistics_task = None
        except Exception:
            _LOGGER.exception('An exception was raised by Ingest._write_statistics')

        cls._started = False

    @classmethod
    def increment_discarded_readings(cls):
        """Increments the number of discarded sensor readings"""
        cls._discarded_readings_stats += 1

    @classmethod
    async def _insert_readings(cls, list_index):
        """Inserts rows into the readings table

        Use Readings().append(json_payload_of_readings)
        """
        _LOGGER.info('Insert readings loop started')

        readings_list = cls._readings_lists[list_index]
        min_readings_reached = cls._readings_list_batch_size_reached[list_index]
        list_not_empty = cls._readings_list_not_empty[list_index]
        lists_not_full = cls._readings_lists_not_full

        while True:
            # Wait for enough items in the list to fill a batch
            # for some minimum amount of time
            while not cls._stop:
                if len(readings_list) >= cls._readings_insert_batch_size:
                    break

                min_readings_reached.clear()
                waiter = asyncio.ensure_future(min_readings_reached.wait())
                cls._insert_readings_wait_tasks[list_index] = waiter

                # _LOGGER.debug('Waiting for entire batch: Queue index: %s Size: %s',
                #               list_index, len(list))

                try:
                    await asyncio.wait_for(waiter, cls._readings_insert_batch_timeout_seconds)
                    # _LOGGER.debug('Released: Queue index: %s Size: %s',
                    #               list_index, len(list))
                except asyncio.CancelledError:
                    # _LOGGER.debug('Cancelled: Queue index: %s Size: %s',
                    #               list_index, len(list))
                    break
                except asyncio.TimeoutError:
                    # _LOGGER.debug('Timed out: Queue index: %s Size: %s',
                    #               list_index, len(list))
                    break
                finally:
                    cls._insert_readings_wait_tasks[list_index] = None

            if not len(readings_list):
                if cls._stop:
                    break  # Terminate this method

                # Wait for one item in the list
                list_not_empty.clear()
                waiter = asyncio.ensure_future(list_not_empty.wait())
                cls._insert_readings_wait_tasks[list_index] = waiter

                # _LOGGER.debug('Waiting for first item: Queue index: %s', list_index)

                try:
                    await asyncio.wait_for(
                            waiter,
                            cls._max_readings_insert_batch_connection_idle_seconds)
                except asyncio.CancelledError:
                    # Don't assume the list is empty

                    # _LOGGER.debug('Cancelled: Queue index: %s Size: %s',
                    #               list_index, len(list))
                    continue
                except asyncio.TimeoutError:
                    # _LOGGER.debug('Closing idle connection: Queue index: %s',
                    #               list_index)
                    continue
                finally:
                    cls._insert_readings_wait_tasks[list_index] = None

            # If batch size still not reached but another list has inserted
            # recently, wait some more
            if (not cls._stop) and (len(readings_list) < cls._readings_insert_batch_size) and ((
                    time.time() - cls._last_insert_time) <
                    cls._readings_insert_batch_timeout_seconds):
                continue

            attempt = 0
            cls._last_insert_time = time.time()

            # Perform insert. Retry when fails.
            readings_storage = Readings(cls._core_management_host, cls._core_management_port)
            while True:
                # _LOGGER.debug('Begin insert: Queue index: %s Batch size: %s', list_index,
                #               len(list))

                try:
                    payload = dict()
                    payload['readings'] = readings_list

                    res = readings_storage.append(json.dumps(payload))

                    try:
                        if res["response"] == "appended":
                            batch_size = len(readings_list)
                            cls._readings_stats += batch_size
                    except KeyError:
                        # if key error in next, it will be automatically in parent except block
                        if res["retryable"]:  # retryable is bool
                            # raise and exception handler will retry
                            raise res["message"]
                        else:
                            # not re-tryable
                            _LOGGER.error(res["message"])
                            batch_size = len(readings_list)
                            cls._discarded_readings_stats += batch_size
                            # let the loop break

                    # _LOGGER.debug('End insert: Queue index: %s Batch size: %s',
                    #               list_index, batch_size)

                    break
                except Exception:
                    attempt += 1

                    # TODO logging each time is overkill
                    _LOGGER.exception('Insert failed on attempt #%s, list index: %s',
                                      attempt, list_index)

                    if cls._stop and attempt >= 1:
                        # Stopping. Discard the entire list upon failure.
                        batch_size = len(readings_list)
                        cls._discarded_readings_stats += batch_size
                        _LOGGER.warning('Insert failed: Queue index: %s Batch size: %s', list_index, batch_size)

                    break

            del readings_list[:batch_size]

            if not lists_not_full.is_set():
                lists_not_full.set()

        _LOGGER.info('Insert readings loop stopped')

    @classmethod
    async def _write_statistics(cls):
        """Periodically commits collected readings statistics"""
        _LOGGER.info('Device statistics writer started')

        while not cls._stop:
            # stop() calls _write_statistics_sleep_task.cancel().
            # Tracking _write_statistics_sleep_task separately is cleaner than canceling
            # this entire coroutine because allowing storage activity to be
            # interrupted will result in strange behavior.
            cls._write_statistics_sleep_task = asyncio.ensure_future(
                asyncio.sleep(cls._write_statistics_frequency_seconds))

            try:
                await cls._write_statistics_sleep_task
            except asyncio.CancelledError:
                pass
            finally:
                cls._write_statistics_sleep_task = None

            readings = cls._readings_stats
            cls._readings_stats = 0

            try:
                await statistics.update_statistics_value('READINGS', readings)
            except Exception:  # TODO catch real exception
                cls._readings_stats += readings
                _LOGGER.exception('An error occurred while writing readings statistics')

            readings = cls._discarded_readings_stats
            cls._discarded_readings_stats = 0
            try:
                await statistics.update_statistics_value('DISCARDED', readings)
            # TODO catch real exception
            except Exception:  # TODO catch real exception
                cls._discarded_readings_stats += readings
                _LOGGER.exception('An error occurred while writing discarded statistics')

        _LOGGER.info('Device statistics writer stopped')

    @classmethod
    def is_available(cls) -> bool:
        """Indicates whether all lists are currently full

        Returns:
            False - All of the lists are full
            True - Otherwise
        """
        if cls._stop:
            return False

        list_index = cls._current_readings_list_index
        if len(cls._readings_lists[list_index]) < cls._readings_list_size:
            return True

        if cls._max_concurrent_readings_inserts > 1:
            for list_index in range(cls._max_concurrent_readings_inserts):
                if len(cls._readings_lists[list_index]) < cls._readings_list_size:
                    cls._current_readings_list_index = list_index
                    return True

        _LOGGER.warning('The ingest service is unavailable')
        return False

    @classmethod
    async def add_readings(cls, asset: str, timestamp: Union[str, datetime.datetime],
                           key: Union[str, uuid.UUID] = None, readings: dict = None)->None:
        """Adds an asset readings record to FogLAMP

        Args:
            asset: Identifies the asset to which the readings belong
            timestamp: When the readings were taken
            key:
                Unique key for these readings. If this method is called multiple with the same
                key, the readings are only written to storage once
            readings: A dictionary of sensor readings

        Raises:
            If this method raises an Exception, the discarded readings counter is
            also incremented.

            RuntimeError:
                The server is stopping or has been stopped

            ValueError, TypeError:
                An invalid value was provided
        """
        if cls._stop:
            raise RuntimeError('The device server is stopping')

        if not cls._started:
            raise RuntimeError('The device server was not started')
            # cls._logger = logger.setup(__name__, destination=logger.CONSOLE, level=logging.DEBUG)

        try:
            if asset is None:
                raise ValueError('asset can not be None')

            if not isinstance(asset, str):
                raise TypeError('asset must be a string')

            if timestamp is None:
                raise ValueError('timestamp can not be None')

            # TODO: for?
            ''' below code from node JS, works fine!
                dt = new Date()
                timestamp = dt.toISOString()
            '''
            # if not isinstance(timestamp, datetime.datetime):
            #     # validate
            #     timestamp = dateutil.parser.parse(timestamp)

            if key is not None and not isinstance(key, uuid.UUID):
                # Validate
                if not isinstance(key, str):
                    raise TypeError('key must be a uuid.UUID or a string')
                # If key is not a string, uuid.UUID throws an Exception that appears to
                # be a TypeError but can not be caught as a TypeError
                key = uuid.UUID(key)

            if readings is None:
                readings = dict()
            elif not isinstance(readings, dict):
                # Postgres allows values like 5 be converted to JSON
                # Downstream processors can not handle this
                raise TypeError('readings must be a dictionary')
        except Exception:
            cls.increment_discarded_readings()
            raise

        # Comment out to test IntegrityError
        # key = '123e4567-e89b-12d3-a456-426655440000'

        # Wait for an empty slot in the list
        while not cls.is_available():
            cls._readings_lists_not_full.clear()
            await cls._readings_lists_not_full.wait()
            if cls._stop:
                raise RuntimeError('The device server is stopping')

        list_index = cls._current_readings_list_index
        readings_list = cls._readings_lists[list_index]

        read = dict()
        read['asset_code'] = asset
        read['read_key'] = str(key)
        read['reading'] = readings
        read['user_ts'] = timestamp

        readings_list.append(read)

        list_size = len(readings_list)

        # _LOGGER.debug('Add readings list index: %s size: %s', cls._current_readings_list_index,
        #               list_size)

        if list_size == 1:
            cls._readings_list_not_empty[list_index].set()

        if list_size == cls._readings_insert_batch_size:
            cls._readings_list_batch_size_reached[list_index].set()
            # _LOGGER.debug('Set event list index: %s size: %s',
            #               cls._current_readings_list_index, len(list))

        # When the current list is full, move on to the next list
        if cls._max_concurrent_readings_inserts > 1 and (
                    list_size >= cls._readings_insert_batch_size):
            # Start at the beginning to reduce the number of connections
            for list_index in range(cls._max_concurrent_readings_inserts):
                if len(cls._readings_lists[list_index]) < cls._readings_insert_batch_size:
                    cls._current_readings_list_index = list_index
                    break
