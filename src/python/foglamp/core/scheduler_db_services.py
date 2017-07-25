# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Storage Services as needed by Processes
"""

import asyncpg

__author__ = "Amarendra Kumar Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

__DB_NAME = 'foglamp'


async def read_scheduled_processes():
    conn = await asyncpg.connect(database=__DB_NAME)
    query = """
        SELECT name, script from scheduled_processes
    """

    stmt = await conn.prepare(query)

    rows = await stmt.fetch()

    columns = ('name', 'script')

    results = []
    for row in rows:
        results.append(dict(zip(columns, row)))

    await conn.close()

    return results


async def create_schedule(payload):
    pass

async def read_schedule(schedule_id=None):
    conn = await asyncpg.connect(database=__DB_NAME)
    query = """
        SELECT id::"varchar",
                process_name,
                schedule_name,
                schedule_type,
                schedule_interval::"varchar",
                schedule_time::"varchar",
                schedule_day::"varchar",
                exclusive
        from schedules
    """

    # FIXME: When schedule_id is not in uuid format, server error occurs
    _where_clause = " WHERE id = $1" if schedule_id else ""

    query += _where_clause

    stmt = await conn.prepare(query)

    rows = await stmt.fetch(schedule_id) if schedule_id else await stmt.fetch()

    results = []
    for row in rows:
        results.append(dict(id=row["id"],
                            process_name=row['process_name'],
                            schedule=dict(schedule_name=row['schedule_name'],
                                          schedule_type=row['schedule_type'],
                                          schedule_interval=row['schedule_interval'],
                                          schedule_time=row['schedule_time'],
                                          schedule_day=row['schedule_day'],
                                          exclusive=row['exclusive']
                                          )))

    await conn.close()

    return results

async def update_schedule(payload):
    pass

async def delete_schedule(payload):
    pass


async def create_task(payload):
    pass


async def read_task(task_id=None, state=None, name=None):
    conn = await asyncpg.connect(database=__DB_NAME)
    query = """
        SELECT
            id::"varchar",
            process_name,
            state,
            start_time::"varchar",
            end_time::"varchar",
            reason,
            pid,
            exit_code
        from tasks
    """

    # FIXME: When task_id is not in uuid format, server error occurs
    _where_clause = " WHERE id = $1" if task_id else ""

    query += _where_clause

    if task_id:
        stmt = await conn.prepare(query)
        rows = await stmt.fetch(task_id)
    else:
        _where_clause = _get_where_clause(name, state)
        query += _where_clause
        stmt = await conn.prepare(query)
        rows = await _get_rows(stmt, name, state)

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
    query = """
        SELECT DISTINCT ON (process_name)
            id::"varchar",
            process_name,
            state,
            start_time::"varchar",
            end_time::"varchar",
            reason,
            pid,
            exit_code
        from tasks
    """

    _where_clause = _get_where_clause(name, state)
    query += _where_clause

    _order_clause = ' ORDER BY process_name ASC, start_time DESC'
    query += _order_clause

    stmt = await conn.prepare(query)

    rows = await _get_rows(stmt, name, state)

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

def _get_where_clause(name, state):
    # TODO: Use enum in place int state
    _where_clause = "" if not state and not name else \
                    " WHERE process_name = $1" if not state and name else \
                    " WHERE state = $1" if state and not name else \
                    " WHERE process_name = $1 and state = $2"
    return _where_clause

async def _get_rows(stmt, name, state):
    rows = await stmt.fetch() if not state and not name else \
            await stmt.fetch(name) if not state and name else \
            await stmt.fetch(state) if state and not name else \
            await stmt.fetch(name, state)
    return rows

# There is no requirement for update_task()

async def delete_task(payload):
    pass

