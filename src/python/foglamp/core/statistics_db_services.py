# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Storage Services as needed by Processes
"""

import asyncpg
from collections import OrderedDict

__author__ = "Amarendra Kumar Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

__DB_NAME = 'foglamp'


async def read_statistics():
    conn = await asyncpg.connect(database=__DB_NAME)
    query = """
        SELECT key, description, value, previous_value, ts FROM statistics ORDER BY key
    """

    stmt = await conn.prepare(query)

    rows = await stmt.fetch()

    columns = ('key',
               'description',
               'value',
               'previous_value',
               'ts'
               )

    results = {}
    for row in rows:
        temp = OrderedDict(zip(columns, row))
        results.update({temp['key']: temp['value']})

    await conn.close()

    return results

async def read_statistics_history(limit=None):
    conn = await asyncpg.connect(database=__DB_NAME)
    _limit_clause = " LIMIT $1" if limit else " "

    query = """
                SELECT date_trunc('second', ts::timestamptz)::varchar as ts,
                        key,
                        value FROM statistics_history
                WHERE ts IN (SELECT distinct ts FROM statistics_history ORDER BY ts DESC {limit_clause})
                ORDER BY ts, key;
            """.format(limit_clause=_limit_clause)

    stmt = await conn.prepare(query)
    rows = await stmt.fetch(limit) if limit else await stmt.fetch()

    columns = ('ts', 'key', 'value')

    results = []
    first_time = True
    temp_ts = None
    temp_dict = {}

    for row in rows:
        if temp_ts != row['ts']:
            if not first_time:
                temp_dict.update({'ts': temp_ts})
                results.append(temp_dict)
            temp_dict = {}
            temp_ts = row['ts']

        temp = OrderedDict(zip(columns, row))
        temp_dict.update({temp['key']: temp['value']})
        first_time = False

    # Append last leftover dict
    temp_dict.update({'ts': temp_ts})
    results.append(temp_dict)

    await conn.close()

    return results
