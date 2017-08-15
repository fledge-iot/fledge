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
    """number of readings accepted before statistics were flushed to the database"""

    _discarded_readings = 0  # type: int
    """number of readings rejected before statistics were flushed to the database"""

    _write_statistics_loop_task = None  # type: asyncio.Future
    """Asyncio task for :meth:`_write_statistics_loop`"""

    _sleep_task = None  # type: asyncio.Future
    """Asyncio task for asyncio.sleep"""

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
        _LOGGER.info("Ingest statistics writer started")

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
                # TODO Move READINGS and DISCARDED to globals
                await statistics.update_statistics_value('READINGS', cls._readings)
                cls._readings = 0

                await statistics.update_statistics_value('DISCARDED', cls._discarded_readings)
                cls._discarded_readings = 0
            # TODO catch real exception
            except Exception:
                _LOGGER.exception("An error occurred while writing readings statistics")

        _LOGGER.info("Ingest statistics writer stopped")

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
            Exception:
                If this method raises an Exception, the discarded readings counter is
                also incremented.
        """

        try:
            if asset is None:
                raise ValueError("asset can not be None")

            if not isinstance(asset, str):
                raise TypeError("Asset must be a string")

            if timestamp is None:
                raise ValueError("timestamp can not be None")

            if not isinstance(timestamp, datetime.datetime):
                raise TypeError("timestamp must be a datetime.datetime")

            if key is not None and not isinstance(key, uuid.UUID):
                raise TypeError("key must be a uuid.UUID")

            if readings is None:
                readings = dict()
            elif not isinstance(readings, dict):
                raise TypeError("readings must be a dict")

            try:
                # How to test an insert error:
                # key = 'tom'
                async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
                    async with engine.acquire() as conn:
                        try:
                            await conn.execute(_READINGS_TBL.insert().values(
                                asset_code=asset, reading=readings, read_key=key,
                                user_ts=timestamp))
                            cls._readings += 1
                        except psycopg2.IntegrityError:
                            _LOGGER.exception(
                                'Duplicate key (%s) inserting sensor values. Asset: %s\n%s',
                                key, asset, readings)
            except Exception:
                _LOGGER.exception(
                    "Insert failed. Asset: '%s' Readings:\n%s", asset, readings)
                raise
        except Exception:
            cls._discarded_readings += 1
            raise
