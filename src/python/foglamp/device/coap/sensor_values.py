# -*- coding: utf-8 -*-
"""FOGLAMP_PRELUDE_BEGIN
{{FOGLAMP_LICENSE_DESCRIPTION}}

See: http://foglamp.readthedocs.io/

Copyright (c) 2017 OSIsoft, LLC
License: Apache 2.0

FOGLAMP_PRELUDE_END
"""

import logging
from cbor2 import loads
import aiocoap
import aiocoap.resource
import psycopg2
import aiopg.sa
import sqlalchemy as sa
import asyncio
from sqlalchemy.dialects.postgresql import JSONB
from foglamp import statistics

"""CoAP handler for coap://other/sensor_readings URI
"""

__author__ = 'Terris Linenbach'
__version__ = '${VERSION}'

_sensor_values_tbl = sa.Table(
    'readings',
    sa.MetaData(),
    sa.Column('asset_code', sa.types.VARCHAR(50)),
    sa.Column('read_key', sa.types.VARCHAR(50)),
    sa.Column('user_ts', sa.types.TIMESTAMP),
    sa.Column('reading', JSONB))
"""Defines the table that data will be inserted into"""

_CONNECTION_STRING = "host='/tmp/' dbname='foglamp'"


class BlockResource(aiocoap.resource.Resource):
    """
    Block resource which supports GET and PUT methods. It sends large
    responses, which trigger blockwise transfer.
    """

    def __init__(self):
        super(BlockResource, self).__init__()
        self.content = ("This is the resource's default content. It is padded "\
                "with numbers to be large enough to trigger blockwise "\
                "transfer.\n" + "0123456789\n" * 100).encode("ascii")

    async def render_get(self, request):
        return aiocoap.Message(payload=self.content)

    async def render_put(self, request):
        json_payload = loads(request.payload)
        print('PUT payload: %s' % json_payload)
        self.content = request.payload
        payload = ("accepted the new payload. inspect here in repr format:"
                   "\n\n%r" % self.content).encode('utf8')

        # asset_code_and_sensor = json_payload["asset"].split("/")
        # if len(asset_code_and_sensor) == 2:
        #     asset_code = asset_code_and_sensor[0]
        #     _sensor = asset_code_and_sensor[1]
        # elif len(asset_code_and_sensor) == 1:
        #     asset_code = asset_code_and_sensor[0]
        #     _sensor = asset_code # or ?
        # # print(asset_code, _sensor)

        # un-comment next line to save to readings table
        # await self.save_readings(json_payload["asset"], json_payload["key"],
                                 # json_payload["sensor_values"], json_payload["timestamp"])
        return aiocoap.Message(payload=payload)

    async def save_readings(self, asset, key, sensor_values, timestamp):
        try:
            async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
                async with engine.acquire() as conn:
                    try:
                        await conn.execute(_sensor_values_tbl.insert().values(
                            asset_code=asset, reading=sensor_values, read_key=key, user_ts=timestamp))
                    except:
                        # TODO make me better
                        raise "could not save to readings table"

        except:
            raise "DB error occured"


class SensorValues(aiocoap.resource.Resource):
    """CoAP handler for coap://readings URI

        Attributes:
            _num_readings (int) : number of readings processed through render_post method since initialization or since the last time _update_statistics() was called
            _num_discarded_readings (int) : number of readings discarded through render_post method since initialization or since the last time _update_statistics() was called
    """

    _CONNECTION_STRING = "host='/tmp/' dbname='foglamp'"

    # 'postgresql://foglamp:foglamp@localhost:5432/foglamp'

    def __init__(self):
        super(SensorValues, self).__init__()
        asyncio.ensure_future(self._update_statistics())
        self._num_readings = 0
        self._num_discarded_readings = 0

    def register_handlers(self, resource_root, uri):
        """Registers other/sensor-values URI"""
        resource_root.add_resource(('other', uri), self)
        return

    async def _update_statistics(self):
        while True:
            await asyncio.sleep(5)
            await statistics.update_statistics_value('READINGS', self._num_readings)
            self._num_readings = 0
            await statistics.update_statistics_value('DISCARDED', self._num_discarded_readings)
            self._num_discarded_readings = 0

    async def render_post(self, request):
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
        """

        # TODO: The payload format is documented
        # at https://docs.google.com/document/d/1rJXlOqCGomPKEKx2ReoofZTXQt9dtDiW_BHU7FYsj-k/edit#
        # and will be moved to a .rst file

        self._num_readings += 1

        # Required keys in the payload
        try:
            payload = loads(request.payload)
            print('POSTed payload: %s' % payload)

            asset = payload['asset']
            timestamp = payload['timestamp']
        except:
            self._num_discarded_readings += 1
            return aiocoap.Message(payload=''.encode("utf-8"), code=aiocoap.numbers.codes.Code.BAD_REQUEST)

        # Optional keys in the payload
        readings = payload.get('sensor_values', {})
        key = payload.get('key')

        # Comment out to test IntegrityError
        # key = '123e4567-e89b-12d3-a456-426655440000'

        try:
            async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
                async with engine.acquire() as conn:
                    try:
                        await conn.execute(_sensor_values_tbl.insert().values(
                            asset_code=asset, reading=readings, read_key=key, user_ts=timestamp))
                    except psycopg2.IntegrityError:
                        logging.getLogger('coap-server').exception(
                            'Duplicate key (%s) inserting sensor values:\n%s',
                            key,
                            payload)
        except Exception:
            logging.getLogger('coap-server').exception(
                "Database error occurred. Payload:\n%s"
                , payload)
            return aiocoap.Message(payload=''.encode("utf-8"), code=aiocoap.numbers.codes.Code.INTERNAL_SERVER_ERROR)

        return aiocoap.Message(payload=''.encode("utf-8"), code=aiocoap.numbers.codes.Code.VALID)
        # TODO what should this return?
