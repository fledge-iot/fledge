import datetime
import asyncio
import uuid
from ..env import Env

import aiocoap
import aiocoap.resource as resource

from cbor2 import loads, dumps

import sqlalchemy as sa
from aiopg.sa import create_engine
from sqlalchemy.dialects.postgresql import JSON, JSONB

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
        
        # See 
        async with create_engine(Env.connection_string) as engine:
            async with engine.acquire() as conn:
                await conn.execute(tbl.insert().values(data=r, key=key))
        return aiocoap.Message(payload=''.encode("utf-8"))

