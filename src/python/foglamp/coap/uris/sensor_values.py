import datetime
import asyncio
import uuid

import aiocoap
import aiocoap.resource as resource

from cbor2 import loads, dumps

import psycopg2
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, JSONB
from sqlalchemy import exc

from aiopg.sa import create_engine

from foglamp.env import DbConfig


metadata = sa.MetaData()

tbl = sa.Table(
    'sensor_values_t'
    , metadata
    , sa.Column('key', sa.types.VARCHAR(50))
    , sa.Column('data', JSONB))


class SensorValues(resource.Resource):
    def __init__(self):
        super(SensorValues, self).__init__()

    def register(self, root):
        root.add_resource(('other', 'sensor-values'), self);
        return

    async def render_post(self, request):
        r = loads(request.payload)

        key = r.get('id')

        if key is None:
            key = uuid.uuid4().hex
        # key = 'terris'

        # See
        async with create_engine(DbConfig.conn_str) as engine:
            async with engine.acquire() as conn:
                try:
                    await conn.execute(tbl.insert().values(data=r, key=key))
                    # except exc.IntegrityError as e:
                except psycopg2.IntegrityError as e:
                    print(e)
                    # TODO log the error
        return aiocoap.Message(payload=''.encode("utf-8"))
