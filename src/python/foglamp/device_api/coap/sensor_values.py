import uuid
import psycopg2
import aiocoap.resource
import logging
import sqlalchemy as sa
from cbor2 import loads
from sqlalchemy.dialects.postgresql import JSONB
import aiopg.sa
import foglamp.env as env


_sensor_values_tbl = sa.Table(
    'readings',
    sa.MetaData(),
    sa.Column('asset_code', sa.types.VARCHAR(50)),
    sa.Column('read_key', sa.types.VARCHAR(50)),
    sa.Column('user_ts', sa.types.TIMESTAMP),
    sa.Column('reading', JSONB))
"""Defines the table that data will be inserted into"""

class SensorValues(aiocoap.resource.Resource):
    """Handles other/sensor_values requests"""
    def __init__(self):
        super(SensorValues, self).__init__()

    def register_handlers(self, resource_root):
        """Registers other/sensor_values URI"""
        resource_root.add_resource(('other', 'sensor-values'), self)
        return

    async def render_post(self, request):
        """Sends incoming data to storage layer"""
        # TODO: Validate request.payload
        original_payload = loads(request.payload)
        
        payload = dict(original_payload)

        key = payload.get('key')

        if key:
            del payload['key']

        # Comment out to demonstrate IntegrityError
        # key = 'same'

        asset = payload.get('asset')

        if asset is not None:
            del payload['asset']

        timestamp = payload.get('timestamp')

        if timestamp:
            del payload['timestamp']

        try:
            async with aiopg.sa.create_engine("postgresql://foglamp:foglamp@localhost:5432/foglamp") as engine:
                async with engine.acquire() as conn:
                    await conn.execute(_sensor_values_tbl.insert().values(
                        asset_code=asset, reading=payload, read_key=key, user_ts=timestamp))
        except psycopg2.IntegrityError as e:
            logging.getLogger('coap-server').exception(
                "Duplicate key (%s) inserting sensor values: %s"
                , key # Maybe the generated key is the problem
                , original_payload)

        return aiocoap.Message(payload=''.encode("utf-8"))

