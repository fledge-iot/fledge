import datetime
import asyncio
import uuid
import psycopg2

from foglamp import env

import aiocoap
import aiocoap.resource as resource

from cbor2 import loads, dumps

import sqlalchemy as sa
from aiopg.sa import create_engine
from sqlalchemy.dialects.postgresql import JSON, JSONB
from sqlalchemy import exc

metadata = sa.MetaData()

tbl = sa.Table(
    'sensor_values_t'
    , metadata
    , sa.Column('key', sa.types.VARCHAR(50))
    , sa.Column('data', JSONB))


class Ingest(resource.Resource):
    def __init__(self):
        super(Ingest, self).__init__()

    def register(self, root):
        root.add_resource(('other', 'ingest'), self);
        return
        
    async def render_post(self, request):
        r = loads(request.payload)

        key = r.get('id')

        if key is None:
            key = uuid.uuid4().hex
        # key = 'terris'

        # See 
        async with create_engine(env.Env.connection_string) as engine:
            async with engine.acquire() as conn:
                try:
                    await conn.execute(tbl.insert().values(data=r, key=key))
                    #except exc.IntegrityError as e:
                except psycopg2.IntegrityError as e:
                    pass
        return aiocoap.Message(payload=''.encode("utf-8"))

