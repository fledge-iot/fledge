# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Storage Services as needed by Processes
"""

import asyncpg
import json

__author__ = "Amarendra Kumar Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

__DSN = "postgresql://foglamp:foglamp@localhost:5432/foglamp"
# __DB_NAME = 'foglamp'


async def create_schedule(payload):
    pass

async def read_schedule(payload):
    pass

async def update_schedule(payload):
    pass

async def delete_schedule(payload):
    pass


async def create_task(payload):
    pass


async def read_task(state=None, name=None):
    conn = await asyncpg.connect(dsn=__DSN)
    query = '''
        SELECT t.id::"varchar", p.name, t.state, t.start_time::"varchar", t.end_time::"varchar", t.reason, t.pid, t.exit_code from tasks t
        JOIN scheduled_processes p ON t.process_name = p.name
    '''
    _where_clause = '' if state is None and name is None else \
                    ' WHERE process_name = $1' if state is None and name is not None else \
                    ' WHERE state = $1' if state is not None and name is None else \
                    ' WHERE process_name = $1 and state = $2'

    query += _where_clause
    stmt = await conn.prepare(query)


    # rows = await stmt.fetch() if state is None and name is None else \
    #         await stmt.fetch(name) if state is None and name is not None else \
    #         await stmt.fetch(state) if state is not None and name is None else \
    #         await stmt.fetch(state, name)

    if state is None and name is None:
        rows = await stmt.fetch()
    elif state is None and name is not None:
        rows = await stmt.fetch(name)
    elif state is not None and name is None:
        rows = await stmt.fetch(state)
    else:
        rows = await stmt.fetch(state, name)
    columns = ('id',
        'process_name',
        'state',
        'start_time',
        'end_time',
        'reason',
        'pid',
        'exit_code'
    )
    results = []
    for row in rows:
        results.append(dict(zip(columns, row)))

    await conn.close()

    return results

async def read_tasks_latest(state=None, name=None):
    conn = await asyncpg.connect(database=__DB_NAME)
    query = '''
        SELECT s.id, p.name, s.state, s.start_time, s.end_time, s.reason, s.pid, s.exit_code FROM schedules s
        JOIN scheduled_processes p ON s->process_name = p->name
    '''

    _where_clause = '' if state is None and name is None else \
                    ' WHERE process_name = $1' if state is None and name is not None else \
                    ' WHERE state = $1' if state is not None and name is None else \
                    ' WHERE process_name = $1 and state = $2'

    query += _where_clause

    _order_clause = ' ORDER BY start_time DESC'
    query += _order_clause

    _limit_clause = ' LIMIT 1'
    query += _limit_clause

    stmt = await conn.prepare(query)

    columns = ('id',
        'process_name',
        'state',
        'start_time',
        'end_time',
        'reason',
        'pid',
        'exit_code'
    )
    results = []

    rows = await stmt.fetch() if state is None and name is None else \
            await stmt.fetch(name) if state is None and name is not None else \
            await stmt.fetch(state) if state is not None and name is None else \
            await stmt.fetch(state, name)

    for row in rows:
        results.append(dict(zip(columns, row)))

    await conn.close()

    return results

# There is no requirement for update_task()

async def delete_task(payload):
    pass

