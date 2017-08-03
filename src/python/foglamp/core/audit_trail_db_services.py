# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import asyncpg
import json
from enum import IntEnum


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

__DB_NAME = 'foglamp'


class _Severity(IntEnum):
    """Enumeration for log.severity"""
    FATAL = 1
    ERROR = 2
    WARNING = 3
    INFORMATION = 4

async def read_audit_entries(limit=None):
    """

    Args:
        limit: the number of audit entries returned to the number specified

    Returns:
        list of audit trail entries sorted with most recent first
    """
    conn = await asyncpg.connect(database=__DB_NAME)
    _limit_clause = " LIMIT $1" if limit else " "

    # TODO: source, severity filter and allow skip (offset) with limit
    # Select the code, ts, level, log from the log table
    query = """
                SELECT code AS source, (ts)::varchar AS timestamp, level AS severity, log AS details 
                FROM log ORDER BY timestamp DESC {limit_clause}
            """.format(limit_clause=_limit_clause)

    stmt = await conn.prepare(query)
    rows = await stmt.fetch(limit) if limit else await stmt.fetch()

    results = []
    for row in rows:
        data = {'source': row['source'], 'timestamp': row['timestamp'], 'severity': _Severity(row['severity']).name,
                'details': json.loads(row['details'])}
        results.append(data)

    # Close the connection.
    await conn.close()

    return results
