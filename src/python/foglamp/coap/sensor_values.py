import uuid
import psycopg2
import aiocoap
import aiocoap.resource as resource
import logging
import sqlalchemy as sa
from cbor2 import loads
from sqlalchemy.dialects.postgresql import JSONB
import aiopg.sa
import foglamp.model as model

class SensorValues(resource.Resource):
    '''Handles other/sensor_values requests'''
    def __init__(self):
        self.__sensor_values_tbl = sa.Table(
            'sensor_values_t',
            sa.MetaData(),
            sa.Column('key', sa.types.VARCHAR(50)),
            sa.Column('data', JSONB))

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
        # key = 'same'

        async with aiopg.sa.create_engine(model.db_connection_string) as engine:
            async with engine.acquire() as conn:
                try:
                    await conn.execute(self.__sensor_values_tbl.insert().values(data=payload, key=key))
                except psycopg2.IntegrityError as e:
                    logging.getLogger('coap-server').exception(
                        "Duplicate key (%s) inserting sensor values: %s"
                        , key # Maybe the generated key is the problem
                        , original_payload)
        return aiocoap.Message(payload=''.encode("utf-8"))

