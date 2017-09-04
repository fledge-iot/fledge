# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""FogLAMP Sensor Readings Ingest API"""

import asyncio
import datetime
import logging
import time
import uuid
from typing import List, Union

import asyncpg
import dateutil.parser
import json

from foglamp import logger
from foglamp import statistics


__author__ = "Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_LOGGER = logger.setup(__name__)  # type: logging.Logger
# _LOGGER = logger.setup(__name__, level=logging.DEBUG)  # type: logging.Logger
# _LOGGER = logger.setup(__name__, destination=logger.CONSOLE, level=logging.DEBUG)

_STATISTICS_WRITE_FREQUENCY_SECONDS = 5


class Ingest(object):
    """Adds sensor readings to FogLAMP

    Also tracks readings-related statistics.

    Readings are added to a configurable number of queues. These queues are processed
    concurrently. Each queue is assigned to a database connection. Queued items are
    batched into a single insert transaction. The size of these batches have a
    configurable maximum and minimum.
    """

    # Class attributes
    _readings_stats = 0  # type: int
    """Number of readings accepted before statistics were flushed to storage"""

    _discarded_readings_stats = 0  # type: int
    """Number of readings rejected before statistics were flushed to storage"""

    _write_statistics_task = None  # type: asyncio.Task
    """asyncio task for :meth:`_write_statistics`"""

    _write_statistics_sleep_task = None  # type: asyncio.Task
    """asyncio task for asyncio.sleep"""

    _stop = False
    """Set to true when the server needs to stop"""

    _started = False
    """True when the server has been started"""

    _readings_queues = None  # type: List
    """insert objects are added to these queues"""

    _current_readings_queue_index = 0
    """Which queue to insert into next"""

    _insert_readings_tasks = None  # type: List[asyncio.Task]
    """asyncio tasks for :meth:`_insert_readings`"""

    _readings_queue_batch_size_reached = None  # type: List[asyncio.Event]
    """Fired when a queue has reached _readings_batch_size"""

    _readings_queue_not_empty = None  # type: List[asyncio.Event]
    """Fired when a queue transitions from empty to not_empty"""

    _readings_queues_not_full = None  # type: asyncio.Event
    """Fired when items are removed from any readings queue"""

    _insert_readings_wait_tasks = None  # type: List[asyncio.Task]
    """asyncio tasks blocking :meth:`_insert_readings` that can be canceled"""

    _last_insert_time = 0  # type: int
    """epoch time of last insert"""

    # Configuration
    _max_idle_db_connection_seconds = 180
    """Close database connections when idle for this number of seconds"""

    _max_readings_queues = 5
    """Maximum number of insert queues. Each queue has its own database connection."""

    _readings_batch_size = 50
    """Maximum number of rows in a batch of inserts"""

    _readings_batch_timeout_seconds = 1
    """Number of seconds to wait for a queue to reach the minimum batch size"""

    _max_readings_queue_size = 4*_readings_batch_size
    """Maximum number of items in a queue"""

    @classmethod
    async def start(cls):
        """Starts the server"""
        if cls._started:
            return

        # TODO: Read config

        # Start asyncio tasks
        cls._write_statistics_task = asyncio.ensure_future(cls._write_statistics())

        cls._last_insert_time = 0

        cls._insert_readings_tasks = []
        cls._insert_readings_wait_tasks = []
        cls._readings_queue_batch_size_reached = []
        cls._readings_queue_not_empty = []
        cls._readings_queues = []

        for _ in range(cls._max_readings_queues):
            cls._readings_queues.append([])
            cls._insert_readings_wait_tasks.append(None)
            cls._insert_readings_tasks.append(asyncio.ensure_future(cls._insert_readings(_)))
            cls._readings_queue_batch_size_reached.append(asyncio.Event())
            cls._readings_queue_not_empty.append(asyncio.Event())

        cls._readings_queues_not_full = asyncio.Event()

        cls._started = True

    @classmethod
    async def stop(cls):
        """Stops the server

        Flushes pending statistics and readings to the database
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
                _LOGGER.exception('An exception occurred in Ingest._insert_readings')

        cls._started = False

        cls._insert_readings_wait_tasks = None
        cls._insert_readings_tasks = None
        cls._readings_queues = None
        cls._readings_queue_batch_size_reached = None
        cls._readings_queue_not_empty = None
        cls._readings_queues_not_full = None

        # Write statistics
        if cls._write_statistics_sleep_task is not None:
            cls._write_statistics_sleep_task.cancel()
            cls._write_statistics_sleep_task = None

        try:
            await cls._write_statistics_task
            cls._write_statistics_task = None
        except Exception:
            _LOGGER.exception('An exception occurred in Ingest._write_statistics')

        cls._stop = False

    @classmethod
    def increment_discarded_readings(cls):
        """Increments the number of discarded sensor readings"""
        cls._discarded_readings_stats += 1

    @classmethod
    async def _close_connection(cls, connection: asyncpg.connection.Connection):
        if connection is not None:
            try:
                await connection.close()
            except Exception:
                _LOGGER.exception('Closing connection failed')

    @classmethod
    async def _insert_readings(cls, queue_index):
        """Inserts rows into the readings table using _queue

        Uses "copy" to load rows into a temp table and then
        inserts the temp table into the readings table because
        "copy" does not support "on conflict ignore"
        """
        _LOGGER.info('Insert readings loop started')

        connection = None  # type: asyncpg.connection.Connection
        queue = cls._readings_queues[queue_index]  # type: List
        min_readings_reached = \
            cls._readings_queue_batch_size_reached[queue_index]  # type: asyncio.Event
        queue_not_empty = cls._readings_queue_not_empty[queue_index]  # type: asyncio.Event
        queues_not_full = cls._readings_queues_not_full  # type: asyncio.Event

        while True:
            # Wait for enough items in the queue to fill a batch
            # for some minimum amount of time
            while not cls._stop:
                if len(queue) >= cls._readings_batch_size:
                    break

                min_readings_reached.clear()
                waiter = asyncio.ensure_future(min_readings_reached.wait())
                cls._insert_readings_wait_tasks[queue_index] = waiter

                # _LOGGER.debug('Waiting for entire batch: Queue index: %s Size: %s',
                #               queue_index, len(queue))

                try:
                    await asyncio.wait_for(waiter, cls._readings_batch_timeout_seconds)
                    # _LOGGER.debug('Released: Queue index: %s Size: %s',
                    #               queue_index, len(queue))
                except asyncio.CancelledError:
                    # _LOGGER.debug('Cancelled: Queue index: %s Size: %s',
                    #               queue_index, len(queue))
                    break
                except asyncio.TimeoutError:
                    # _LOGGER.debug('Timed out: Queue index: %s Size: %s',
                    #               queue_index, len(queue))
                    break
                finally:
                    cls._insert_readings_wait_tasks[queue_index] = None

            if not len(queue):
                if cls._stop:
                    break  # Terminate this method

                # Wait for one item in the queue
                queue_not_empty.clear()
                waiter = asyncio.ensure_future(queue_not_empty.wait())
                cls._insert_readings_wait_tasks[queue_index] = waiter

                # _LOGGER.debug('Waiting for first item: Queue index: %s', queue_index)

                try:
                    if connection is None:
                        await waiter
                    else:
                        await asyncio.wait_for(waiter, cls._max_idle_db_connection_seconds)
                except asyncio.CancelledError:
                    # Don't assume the queue is empty

                    # _LOGGER.debug('Cancelled: Queue index: %s Size: %s',
                    #               queue_index, len(queue))
                    continue
                except asyncio.TimeoutError:
                    # _LOGGER.debug('Closing idle database connection: Queue index: %s Size: %s',
                    #               queue_index, len(queue))
                    await cls._close_connection(connection)
                    del connection
                    continue
                finally:
                    cls._insert_readings_wait_tasks[queue_index] = None

            # If batch size still not reached but another queue has inserted
            # recently, wait some more
            if (not cls._stop) and (len(queue) < cls._readings_batch_size) and (
                    time.time() - cls._last_insert_time) < cls._readings_batch_timeout_seconds:
                continue
                
            batch_size = len(queue)
            if batch_size > cls._readings_batch_size:
                batch_size = cls._readings_batch_size

            # inserts = queue[:batch_size]
            inserts = [(item[0], item[1], item[2],
                       json.dumps(item[3])) for item in queue[:batch_size]]

            attempt = 0

            while True:
                cls._last_insert_time = time.time()

                # _LOGGER.debug('Begin insert: Queue index: %s Batch size: %s', queue_index, batch_size)

                try:
                    if connection is None:
                        connection = await asyncpg.connect(database='foglamp')
                        # Create a temp table for 'copy' command
                        await connection.execute('create temp table t_readings '
                                                 'as select asset_code, user_ts, read_key, reading '
                                                 'from foglamp.readings where 1=0')
                    else:
                        await connection.execute('truncate table t_readings')

                    await connection.copy_records_to_table(table_name='t_readings',
                                                           records=inserts)

                    await connection.execute('insert into foglamp.readings '
                                             '(asset_code,user_ts,read_key,reading) '
                                             'select * from t_readings on conflict do nothing')

                    # batch_size = int(result[5:])
                    cls._readings_stats += batch_size

                    # _LOGGER.debug('End insert: Queue index: %s Batch size: %s',
                    #               queue_index, batch_size)

                    break
                except Exception:  # TODO: Catch exception from asyncpg
                    attempt += 1

                    # TODO logging each time is overkill
                    _LOGGER.exception('Insert failed on attempt #%s, queue index: %s',
                                      attempt, queue_index)

                    if cls._stop and attempt > 2:
                        # Stopping. Discard the entire queue upon failure.
                        batch_size = len(queue)
                        cls._discarded_readings_stats += batch_size
                        break
                    else:
                        if connection is None:
                            # Connection failure
                            await asyncio.sleep(1)
                        else:
                            await cls._close_connection(connection)
                            del connection

            del inserts
            del queue[:batch_size]

            if not queues_not_full.is_set():
                queues_not_full.set()

        # End of the method
        await cls._close_connection(connection)

        _LOGGER.info('Insert readings loop stopped')

    @classmethod
    async def _write_statistics(cls):
        """Periodically commits collected readings statistics"""
        _LOGGER.info('Device statistics writer started')

        while not cls._stop:
            # stop() calls _write_statistics_sleep_task.cancel().
            # Tracking _write_statistics_sleep_task separately is cleaner than canceling
            # this entire coroutine because allowing database activity to be
            # interrupted will result in strange behavior.
            cls._write_statistics_sleep_task = asyncio.ensure_future(
                asyncio.sleep(_STATISTICS_WRITE_FREQUENCY_SECONDS))

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
                _LOGGER.exception('An error occurred while writing readings statistics')

        _LOGGER.info('Device statistics writer stopped')

    @classmethod
    def is_available(cls) -> bool:
        """Indicates whether all queues are currently full

        Returns:
            False - All of the queues are full
            True - Otherwise
        """
        if cls._stop:
            return False

        queue_index = cls._current_readings_queue_index
        if len(cls._readings_queues[queue_index]) < cls._max_readings_queue_size:
            return True

        if cls._max_readings_queues > 1:
            for queue_index in range(cls._max_readings_queues):
                if len(cls._readings_queues[queue_index]) < cls._max_readings_queue_size:
                    cls._current_readings_queue_index = queue_index
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
                key, the readings are only written to the database once
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

            if not isinstance(timestamp, datetime.datetime):
                # validate
                timestamp = dateutil.parser.parse(timestamp)

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

        # Wait for an empty slot in the queue
        while not cls.is_available():
            cls._readings_queues_not_full.clear()
            await cls._readings_queues_not_full.wait()
            if cls._stop:
                raise RuntimeError('The device server is stopping')

        queue_index = cls._current_readings_queue_index
        queue = cls._readings_queues[queue_index]

        queue.append((asset, timestamp, key, readings))
        # queue.append((asset, timestamp, key, json.dumps(readings)))

        queue_size = len(queue)

        # _LOGGER.debug('Add readings queue index: %s size: %s', cls._current_readings_queue_index,
        #               queue_size)

        if queue_size == 1:
            cls._readings_queue_not_empty[queue_index].set()

        if queue_size == cls._readings_batch_size:
            cls._readings_queue_batch_size_reached[queue_index].set()
            # _LOGGER.debug('Set event queue index: %s size: %s',
            #               cls._current_readings_queue_index, len(queue))

        # When the current queue is full, move on to the next queue
        if cls._max_readings_queues > 1 and queue_size >= cls._readings_batch_size:
            # Start at the beginning to reduce the number of database connections
            for queue_index in range(cls._readings_batch_size):
                if len(cls._readings_queues[queue_index]) < cls._readings_batch_size:
                    cls._current_readings_queue_index = queue_index
                    break
