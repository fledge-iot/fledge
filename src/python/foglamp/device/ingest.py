# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""FogLAMP Sensor Readings Ingest API"""

import asyncio
import datetime
import uuid

import aiopg.sa
import psycopg2
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from foglamp import logger
from foglamp import statistics


__author__ = "Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_LOGGER = logger.setup(__name__)

_READINGS_TBL = sa.Table(
    'readings',
    sa.MetaData(),
    sa.Column('asset_code', sa.types.VARCHAR(50)),
    sa.Column('read_key', sa.types.VARCHAR(50)),
    sa.Column('user_ts', sa.types.TIMESTAMP),
    sa.Column('reading', JSONB))
"""Defines the table that data will be inserted into"""

_CONNECTION_STRING = "dbname='foglamp'"

_STATISTICS_WRITE_FREQUENCY_SECONDS = 5


class Ingest(object):
    """Adds sensor readings to FogLAMP

    Also tracks readings-related statistics.
    """

    # Class attributes
    _readings = 0  # type: int
    """Number of readings accepted before statistics were flushed to storage"""

    _discarded_readings = 0  # type: int
    """Number of readings rejected before statistics were flushed to storage"""

    _write_statistics_loop_task = None  # type: asyncio.Task
    """asyncio task for :meth:`_write_statistics_loop`"""

    _sleep_task = None  # type: asyncio.Task
    """asyncio task for asyncio.sleep"""

    _stop = False  # type: bool
    """Set to true when the server needs to stop"""

    @classmethod
    def start(cls):
        """Starts the server"""
        cls._write_statistics_loop_task = asyncio.ensure_future(cls._write_statistics_loop())

    @classmethod
    async def stop(cls):
        """Stops the server

        Saves any pending statistics are saved
        """
        if cls._stop or cls._write_statistics_loop_task is None:
            return

        cls._stop = True

        if cls._sleep_task is not None:
            cls._sleep_task.cancel()
            cls._sleep_task = None

        await cls._write_statistics_loop_task
        cls._write_statistics_loop_task = None

    @classmethod
    def increment_discarded_readings(cls):
        """Increments the number of discarded sensor readings"""
        cls._discarded_readings += 1

    @classmethod
    async def _write_statistics_loop(cls):
        """Periodically commits collected readings statistics"""
        _LOGGER.info("Device statistics writer started")

        while not cls._stop:
            # stop() calls _sleep_task.cancel().
            # Tracking _sleep_task separately is cleaner than canceling
            # this entire coroutine because allowing database activity to be
            # interrupted will result in strange behavior.
            cls._sleep_task = asyncio.ensure_future(
                                asyncio.sleep(_STATISTICS_WRITE_FREQUENCY_SECONDS))

            try:
                await cls._sleep_task
            except asyncio.CancelledError:
                pass

            cls._sleep_task = None

            try:
                await statistics.update_statistics_value('READINGS', cls._readings)
                cls._readings = 0

                await statistics.update_statistics_value('DISCARDED', cls._discarded_readings)
                cls._discarded_readings = 0
            # TODO catch real exception
            except Exception:
                _LOGGER.exception("An error occurred while writing readings statistics")

        _LOGGER.info("Device statistics writer stopped")

    @classmethod
    async def add_readings(cls, asset: str, timestamp: datetime.datetime,
                           key: uuid.UUID = None, readings: dict = None)->None:
        """Add asset readings to FogLAMP

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

            IOError:
                Server error

            ValueError:
                An invalid value was provided
        """
        success = False

        try:
            if asset is None:
                raise ValueError("asset can not be None")

            if timestamp is None:
                raise ValueError("timestamp can not be None")

            if readings is None:
                readings = dict()
            elif not isinstance(readings, dict):
                # Postgres allows values like 5 be converted to JSON
                # Downstream processors can not handle this
                raise ValueError("readings type must be dict")

            # Comment out to test IntegrityError
            # key = '123e4567-e89b-12d3-a456-426655440000'

            # SQLAlchemy / Postgres convert/verify data types ...

            insert = _READINGS_TBL.insert()
            insert = insert.values(asset_code=asset,
                                   reading=readings,
                                   read_key=key,
                                   user_ts=timestamp)

            _LOGGER.debug('Database command: %s', insert)

            try:
                # How to test an insert error:
                # key = 6
                async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
                    async with engine.acquire() as conn:
                        try:
                            await conn.execute(insert)
                            success = True
                        except psycopg2.IntegrityError as e:
                            # This exception is also thrown for NULL violations
                            # So the code above verifies not-NULL columns don't have
                            # corresponding None values
                            success = None  # Do not increment discarded_readings. Already stored.
                            _LOGGER.info(
                                "Duplicate key (%s) inserting sensor values. Asset: '%s'"
                                " Readings:\n%s\n\n%s",
                                key, asset, readings, e)
            except (psycopg2.DataError, psycopg2.ProgrammingError) as e:
                raise ValueError(e)
            except Exception as e:
                _LOGGER.exception('Insert failed: %s', insert)
                raise IOError(e)
        finally:
            if success is not None:
                if success:
                    cls._readings += 1
                else:
                    cls._discarded_readings += 1

