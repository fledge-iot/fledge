import datetime
import asyncio
import uuid
import psycopg2
import aiocoap
import aiocoap.resource as resource
import logging
import sqlalchemy as sa
from cbor2 import loads
from sqlalchemy.dialects.postgresql import JSONB
from aiopg.sa import create_engine
from foglamp.configurator import Configurator

metadata = sa.MetaData()

__tbl__ = sa.Table(
    'sensor_values_t'
    , metadata
    , sa.Column('key', sa.types.VARCHAR(50))
    , sa.Column('data', JSONB))
'''Incoming data is inserted into this table'''


class SensorValues(resource.Resource):
    '''Handles other/sensor_values requests'''
    def __init__(self):
        super(SensorValues, self).__init__()

    def register(self, resourceRoot):
        '''Registers URI with aiocoap'''
        resourceRoot.add_resource(('other', 'sensor-values'), self);
        return

    async def render_post(self, request):
        '''Sends incoming data to database'''
        original_payload = loads(request.payload)
        
        payload = dict(original_payload)

        key = payload.get('key')

        if key is None:
            key = uuid.uuid4()
        else:
            del payload['key']
            
        # Demonstrate IntegrityError
        key = 'same'
        
        async with create_engine(Configurator().db_conn_str) as engine:
            async with engine.acquire() as conn:
                try:
                    await conn.execute(__tbl__.insert().values(data=payload, key=key))
                except psycopg2.IntegrityError as e:
                    logging.getLogger('coap-server').exception(
                        "Duplicate key (%s) inserting sensor values: %s"
                        , key # Maybe the generated key is the problem
                        , original_payload)
        return aiocoap.Message(payload=''.encode("utf-8"))

