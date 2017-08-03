# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Storage Services as needed by Processes
"""

import asyncpg

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

__DB_NAME = 'foglamp'


async def read_audit_entries():
    """list of audit trail entries sorted with most recent first"""

    #conn = await asyncpg.connect(database=__DB_NAME)
    conn = await asyncpg.connect(host='localhost', port=5432, user=__DB_NAME, password=__DB_NAME, database=__DB_NAME)

    # Select the code, ts, level, log from the log table
    rows = await conn.fetch(
        'SELECT code, (ts)::varchar, level, log  FROM log ORDER BY ts DESC')
    columns = ('code', 'ts', 'level', 'log')
    results = []
    for row in rows:
        results.append(dict(zip(columns, row)))

    # Close the connection.
    await conn.close()

    return results
