# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""FogLAMP Sensor Readings Ingest API"""

import asyncio
import logging

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

_LOGGER = logger.setup(__name__)  # type: logging.Logger

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

    Internally tracks readings-related statistics.
    """

    # Class attributes
    _num_readings = 0  # type: int
    """number of readings accepted before statistics were flushed to the database"""

    _num_discarded_readings = 0  # type: int
    """number of readings rejected before statistics were flushed to the database"""

    _sleep_task = None  # type:
    """Asyncio task that is sleeping"""

    _write_statistics_loop_task = None  # type:
    """Asyncio task that is sleeping"""

    _stop = False  # type: bool
    """Set to true when the server needs to stop"""

    @classmethod
    def start(cls):
        """Starts the server"""
        cls._write_statistics_loop_task = asyncio.ensure_future(cls._write_statistics_loop())

    @classmethod
    async def stop(cls):
        if cls._stop or cls._write_statistics_loop_task is None:
            return

        cls._stop = True

        if cls._sleep_task is not None:
            cls._sleep_task.cancel()
            cls._sleep_task = None

        await cls._write_statistics_loop_task
        cls._write_statistics_loop_task = None

    @classmethod
    def increment_discarded_messages(cls):
        cls._num_discarded_readings += 1

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
                await statistics.update_statistics_value('READINGS', cls._num_readings)
                cls._num_readings = 0

                await statistics.update_statistics_value('DISCARDED', cls._num_discarded_readings)
                cls._num_discarded_readings = 0
            # TODO catch real exception
            except Exception:
                _LOGGER.exception("An error occurred while writing readings statistics")

        _LOGGER.info("Ingest statistics writer stopped")

    @classmethod
    async def add_readings(cls, data: dict)->None:
        """Sends asset readings to storage layer

        Args:
            data:
            {
                "timestamp": "2017-01-02T01:02:03.23232Z-05:00",
                "asset": "pump1",
                "readings": {
                    "velocity": "500",
                    "temperature": {
                        "value": "32",
                        "unit": "kelvin"
                    }
                }
            }

        Raises KeyError: data is missing a required field
        Raises IOError: some type of failure occurred
        """

        # TODO: The data format is documented
        # at https://docs.google.com/document/d/1rJXlOqCGomPKEKx2ReoofZTXQt9dtDiW_BHU7FYsj-k/edit#
        # and will be moved to a .rst file

        cls._num_readings += 1

        # Required keys in the data
        try:
            asset = data['asset']
            timestamp = data['timestamp']
        except KeyError:
            cls._num_discarded_readings += 1
            raise

        # Optional keys in the data
        readings = data.get('sensor_values', {})
        key = data.get('key')

        # Comment out to test IntegrityError
        # key = '123e4567-e89b-12d3-a456-426655440000'

        try:
            async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
                async with engine.acquire() as conn:
                    try:
                        await conn.execute(_READINGS_TBL.insert().values(
                            asset_code=asset, reading=readings, read_key=key, user_ts=timestamp))
                    except psycopg2.IntegrityError:
                        _LOGGER.exception(
                            'Duplicate key (%s) inserting sensor values:\n%s',
                            key,
                            data)
        # TODO: Catch real exception
        except Exception:
            cls._num_discarded_readings += 1
            _LOGGER.exception(
                "Database error occurred. Payload:\n%s",
                data)
            raise
