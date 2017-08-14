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

_SENSOR_VALUES_TBL = sa.Table(
    'readings',
    sa.MetaData(),
    sa.Column('asset_code', sa.types.VARCHAR(50)),
    sa.Column('read_key', sa.types.VARCHAR(50)),
    sa.Column('user_ts', sa.types.TIMESTAMP),
    sa.Column('reading', JSONB))
"""Defines the table that data will be inserted into"""

_CONNECTION_STRING = "dbname='foglamp'"


class Ingest(object):
    # Class attributes
    _num_readings  = 0  # type: int
    """number of readings processed through render_post method since initialization 
    or since the last time _update_statistics() was called"""

    _num_discarded_readings = 0  # type: int
    """number of readings discarded through render_post method since initialization 
    or since the last time _update_statistics() was called"""

    @staticmethod
    def start():
        asyncio.ensure_future(Ingest._update_statistics())

    @classmethod
    def increment_discarded_messages(cls):
        cls._num_discarded_readings += 1

    @classmethod
    async def _update_statistics(cls):
        """Periodically write statistics to the database"""
        while True:
            await asyncio.sleep(5)
            await statistics.update_statistics_value('READINGS', cls._num_readings)
            cls._num_readings = 0
            await statistics.update_statistics_value('DISCARDED', cls._num_discarded_readings)
            cls._num_discarded_readings = 0

    @classmethod
    async def add_sensor_readings(cls, payload: dict)->None:
        """Sends asset readings to storage layer

        request.payload looks like:
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

        Raises KeyError: payload is missing a required field
        """

        # TODO: The payload format is documented
        # at https://docs.google.com/document/d/1rJXlOqCGomPKEKx2ReoofZTXQt9dtDiW_BHU7FYsj-k/edit#
        # and will be moved to a .rst file

        cls._num_readings += 1

        # Required keys in the payload
        try:
            asset = payload['asset']
            timestamp = payload['timestamp']
        except KeyError:
            cls._num_discarded_readings += 1
            raise

        # Optional keys in the payload
        readings = payload.get('sensor_values', {})
        key = payload.get('key')

        # Comment out to test IntegrityError
        # key = '123e4567-e89b-12d3-a456-426655440000'

        try:
            async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
                async with engine.acquire() as conn:
                    try:
                        await conn.execute(_SENSOR_VALUES_TBL.insert().values(
                            asset_code=asset, reading=readings, read_key=key, user_ts=timestamp))
                    except psycopg2.IntegrityError:
                        _LOGGER.exception(
                            'Duplicate key (%s) inserting sensor values:\n%s',
                            key,
                            payload)
        except Exception as error:
            cls._num_discarded_readings += 1
            _LOGGER.exception(
                "Database error occurred. Payload:\n%s"
                , payload)
            raise IOError(error.message)
