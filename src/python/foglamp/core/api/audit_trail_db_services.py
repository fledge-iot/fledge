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

async def read_audit_entries(limit=None, offset=None, source=None, severity=None):
    """
    Args:
        limit: the number of audit entries returned to the number specified

        source: filter the audit entries to be only those from the specified source

        severity: filter the audit entries to only those of the specified severity

        offset: skip the first n entries in the audit table, used with limit to implemented paged interfaces

    Returns:
            list of audit trail entries sorted with most recent first
    """
    conn = await asyncpg.connect(database=__DB_NAME)

    _limit_clause = " LIMIT {0}".format(limit) if limit else " "
    _offset_clause = " "
    if limit:
        _offset_clause = " OFFSET {0}".format(offset) if offset else " "

    # HACK: This way when we can more in the future we do not get an exponential explosion of if statements
    _where_clause = " WHERE 1=1 "
    if source:
        _where_clause += "AND code='{0}' ".format(source)
    if severity:
        _where_clause += "AND level={0} ".format(_Severity[severity].value)

    # Select the code, ts, level, log from the log table
    query = """
                SELECT code AS source, (ts)::varchar AS timestamp, level AS severity, log AS details 
                FROM log{where_clause}ORDER BY timestamp DESC{limit_clause}{offset_clause}
            """.format(limit_clause=_limit_clause, where_clause=_where_clause, offset_clause=_offset_clause)
    rows = await conn.fetch(query)

    results = []
    for row in rows:
        data = {'source': row['source'], 'timestamp': row['timestamp'], 'severity': _Severity(row['severity']).name,
                'details': json.loads(row['details'])}
        results.append(data)

    # Close the connection.
    await conn.close()

    return results
