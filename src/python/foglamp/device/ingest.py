# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""FogLAMP Sensor Readings Ingest API"""

import asyncio
import datetime
import logging
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

    _readings_queues = None  # type: List[asyncio.Queue]
    """insert objects are added to these queues"""

    _current_readings_queue_index = 0
    """Which queue to insert into next"""

    _insert_readings_tasks = None  # type: List[asyncio.Task]
    """asyncio tasks for :meth:`_insert_readings`"""

    _queue_events = None  # type: List[asyncio.Event]

    _insert_readings_wait_tasks = None  # type: List[asyncio.Task]
    """asyncio tasks for asyncio.Queue.get called by :meth:`_insert_readings`"""

    # Configuration
    _num_readings_queues = 1
    """Maximum number of insert queues. Each queue has its own database connection."""

    _max_idle_db_connection_seconds = 180
    """Close database connections when idle for this number of seconds"""

    _min_readings_batch_size = 50
    """Preferred minimum number of rows in a batch of inserts"""

    _max_readings_batch_size = 150
    """Maximum number of rows in a batch of inserts"""
    
    _max_readings_queue_size = 4*_max_readings_batch_size
    """Maximum number of items in a queue"""

    _readings_batch_yield_items = 50
    """While creating a batch, yield to other tasks after this taking this many
    items from the queue"""

    _readings_batch_wait_seconds = 1
    """Number of seconds to wait for a queue to reach the minimum batch size"""

    _max_insert_readings_batch_attempts = 30
    """Number of times to attempt to insert a batch (retry in case of failure). When a
    database connection fails (probably because the database server is down), wait 1 
    second between attempts. 
    """

    _queue_readings_as_dict = True
    """True: readings are stored in the queue as a dict object. False: Readings are
    stored in the queue as a string.
    """

    _populate_readings_queues_round_robin = False
    """True: Fill all queues round robin. False: Fill one queue with _max_readings_batch_size before
    filling the next queue"""

    @classmethod
    async def start(cls):
        """Starts the server"""
        if cls._started:
            return

        # TODO: Read config

        # Start asyncio tasks
        cls._write_statistics_task = asyncio.ensure_future(cls._write_statistics())

        cls._insert_readings_tasks = []
        cls._insert_readings_wait_tasks = []
        cls._queue_events = []
        cls._readings_queues = []

        for _ in range(cls._num_readings_queues):
            cls._readings_queues.append(asyncio.Queue(maxsize=cls._max_readings_queue_size))
            cls._insert_readings_wait_tasks.append(None)
            cls._insert_readings_tasks.append(asyncio.ensure_future(cls._insert_readings(_)))
            cls._queue_events.append(asyncio.Event())

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
        cls._queue_events = None

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

        queue = cls._readings_queues[queue_index]  # type: asyncio.Queue
        event = cls._queue_events[queue_index]  # type: asyncio.Event
        connection = None  # type: asyncpg.connection.Connection

        while True:
            # Wait for enough items in the queue to fill a batch
            # for some minimum amount of time
            while not cls._stop:
                if queue.qsize() >= cls._min_readings_batch_size:
                    break

                event.clear()
                waiter = asyncio.ensure_future(event.wait())
                cls._insert_readings_wait_tasks[queue_index] = waiter

                # _LOGGER.debug('Waiting for entire batch: Queue index: %s Size: %s',
                #               queue_index, queue.qsize())

                try:
                    await asyncio.wait_for(waiter, cls._readings_batch_wait_seconds)
                    # _LOGGER.debug('Released: Queue index: %s Size: %s',
                    #               queue_index, queue.qsize())
                except asyncio.CancelledError:
                    # _LOGGER.debug('Cancelled: Queue index: %s Size: %s',
                    #               queue_index, queue.qsize())
                    break
                except asyncio.TimeoutError:
                    # _LOGGER.debug('Timed out: Queue index: %s Size: %s',
                    #               queue_index, queue.qsize())
                    break
                finally:
                    cls._insert_readings_wait_tasks[queue_index] = None

            try:
                insert = queue.get_nowait()
            except asyncio.QueueEmpty:
                if cls._stop:
                    break

                # Wait for one item in the queue
                waiter = asyncio.ensure_future(queue.get())
                cls._insert_readings_wait_tasks[queue_index] = waiter

                # _LOGGER.debug('Waiting for first item: Queue index: %s Size: %s',
                #               queue_index, queue.qsize())

                try:
                    if connection is None:
                        insert = await waiter
                    else:
                        insert = await asyncio.wait_for(waiter, cls._max_idle_db_connection_seconds)
                except asyncio.CancelledError:
                    # Don't assume the queue is empty

                    # _LOGGER.debug('Cancelled: Queue index: %s Size: %s',
                    #               queue_index, queue.qsize())
                    continue
                except asyncio.TimeoutError:
                    # _LOGGER.debug('Closing idle database connection: Queue index: %s Size: %s',
                    #               queue_index, queue.qsize())
                    await cls._close_connection(connection)
                    connection = None
                    continue
                finally:
                    cls._insert_readings_wait_tasks[queue_index] = None

            if cls._queue_readings_as_dict:
                insert = (insert[0], insert[1], insert[2], json.dumps(insert[3]))
            inserts = [insert]

            yield_num = 1

            # Read a full batch of items from the queue
            while True:
                try:
                    insert = queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

                if cls._queue_readings_as_dict:
                    insert = (insert[0], insert[1], insert[2], json.dumps(insert[3]))
                inserts.append(insert)

                if len(inserts) >= cls._max_readings_batch_size:
                    break

                if cls._readings_batch_yield_items:
                    if yield_num >= cls._readings_batch_yield_items:
                        yield_num = 0
                        await asyncio.sleep(0)
                    else:
                        yield_num += 1

            # _LOGGER.debug('Begin insert: Queue index: %s Batch size: %s',
            #              queue_index, len(inserts))

            for attempt in range(cls._max_insert_readings_batch_attempts):
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

                    cls._readings_stats += len(inserts)

                    # _LOGGER.debug('End insert: Queue index: %s Batch size: %s',
                    #               queue_index, len(inserts))

                    break
                except Exception:  # TODO: Catch exception from asyncpg
                    next_attempt = attempt + 1
                    _LOGGER.exception('Insert failed on attempt #%s', next_attempt)

                    if cls._stop or next_attempt >= cls._max_insert_readings_batch_attempts:
                        cls._discarded_readings_stats += len(inserts)
                    else:
                        if connection is None:
                            # Connection failure
                            await asyncio.sleep(1)
                        else:
                            await cls._close_connection(connection)
                            connection = None

        # Exiting this method
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
            False - All of the queues are empty
            True - Otherwise
        """
        if cls._stop:
            return False

        queue_index = cls._current_readings_queue_index
        if cls._readings_queues[queue_index].qsize() < cls._max_readings_queue_size:
            return True

        for _ in range(1, cls._num_readings_queues):
            queue_index += 1
            if queue_index >= cls._num_readings_queues:
                queue_index = 0
            if cls._readings_queues[queue_index].qsize() < cls._max_readings_queue_size:
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
        # Assume the code beyond this point doesn't 'await'
        # to make sure that the queue is not appended to
        # when cls._stop is True

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

        cls.is_available()  # Locate a queue that isn't maxed out
        queue_index = cls._current_readings_queue_index
        queue = cls._readings_queues[queue_index]

        if not cls._queue_readings_as_dict:
            readings = json.dumps(readings)

        await queue.put((asset, timestamp, key, readings))
        if queue.qsize() >= cls._min_readings_batch_size:
            event = cls._queue_events[queue_index]
            # _LOGGER.debug('Set event queue index: %s size: %s',
            #               cls._current_readings_queue_index, queue.qsize())
            # if not event.is_set():  # TODO is this check necessary?
            event.set()

        # _LOGGER.debug('Queue index: %s size: %s', cls._current_readings_queue_index,
        #               queue.qsize())

        # When the current queue is full, move on to the next queue
        if cls._num_readings_queues > 1 and (cls._populate_readings_queues_round_robin
                                             or queue.qsize() >= cls._max_readings_batch_size):
            queue_index += 1
            if queue_index >= cls._num_readings_queues:
                queue_index = 0
            cls._current_readings_queue_index = queue_index
