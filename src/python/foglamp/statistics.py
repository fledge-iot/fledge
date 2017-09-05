# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Statistics API """

# import logging
import aiopg.sa
import sqlalchemy as sa

from foglamp import logger

__author__ = "Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_statistics_tbl = sa.Table(
    'statistics',
    sa.MetaData(),
    sa.Column('key', sa.types.CHAR(10)),
    sa.Column('description', sa.types.VARCHAR(255)),
    sa.Column('value', sa.types.BIGINT),
    sa.Column('previous_value', sa.types.BIGINT),
    sa.Column('ts', sa.types.TIMESTAMP)
)
"""Defines the table that data will be used for CRUD operations"""

_connection_string = "dbname='foglamp'"
_logger = logger.setup(__name__)

async def _update_statistics_value(statistics_key, value_increment):
    async with aiopg.sa.create_engine(_connection_string) as engine:
        async with engine.acquire() as conn:
            await conn.execute(_statistics_tbl.update(_statistics_tbl.c.key == statistics_key).values(value=_statistics_tbl.c.value + value_increment))


async def update_statistics_value(statistics_key, value_increment):
    """Update the value column only of a statistics row based on key

    Keyword Arguments:
    category_name -- statistics key value (required)
    value_increment -- amount to increment the value by

    Return Values:
    None
    """
    try:
        return await _update_statistics_value(statistics_key, value_increment)
    except:
        _logger.exception(
            'Unable to update statistics value based on statistics_key %s and value_increment %s', statistics_key, value_increment)
        raise

# async def main():
#     await update_statistics_value('READINGS',10)
#
# if __name__ == '__main__':
#     import asyncio
#     loop = asyncio.get_event_loop()
#     loop.run_until_complete(main())
