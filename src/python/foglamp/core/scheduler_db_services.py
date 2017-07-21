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

__DSN = "postgresql://foglamp:foglamp@localhost:5432/foglamp"
__DB_NAME = 'foglamp'


async def create_schedule(payload):
    pass

async def read_schedule(schedule_id=None):
    conn = await asyncpg.connect(dsn=__DSN)
    query = '''
        SELECT id::"varchar",
                process_name,
                schedule_name,
                schedule_type,
                schedule_interval::"varchar",
                schedule_time::"varchar",
                schedule_day::"varchar",
                exclusive
        from schedules
    '''

    # TODO: Investigate why prepared statement is not working
    # if schedule_id is None:
    #     _where_clause = ''
    # else:
    #     _where_clause = ' WHERE id = \'$1\''
    #
    # query += _where_clause
    #
    # stmt = await conn.prepare(query)
    # if schedule_id is None:
    #     rows = await stmt.fetch()
    # else:
    #     rows = await stmt.fetch(schedule_id)

    if not schedule_id:
        _where_clause = ''
    else:
        _where_clause = ' WHERE id = \'{0}\''

    query += _where_clause

    if schedule_id is not None:
        query = query.format(schedule_id)

    rows = await conn.fetch(query)

    columns = (
        'id',
        'process_name',
        'schedule_name',
        'schedule_type',
        'schedule_interval',
        'schedule_time',
        'schedule_day',
        'exclusive'
    )

    results = []
    for row in rows:
        results.append(dict(zip(columns, row)))

    await conn.close()

    return results

async def update_schedule(payload):
    pass

async def delete_schedule(payload):
    pass


async def create_task(payload):
    pass


async def read_task(task_id=None, state=None, name=None):
    conn = await asyncpg.connect(dsn=__DSN)
    query = '''
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
    '''

    # TODO: Investigate why prepared statement is not working
    # if not task_id:
    #     _where_clause = ''
    # else:
    #     _where_clause = ' WHERE id = \'$1\''
    #
    # query += _where_clause
    #
    # if task_id is not None:
    #     stmt = await conn.prepare(query)
    #     rows = await stmt.fetch(task_id)
    # else:
    #     if state is None and name is None:
    #         _where_clause = ''
    #     elif state is None and name is not None:
    #         _where_clause = ' WHERE process_name = \'$1\''
    #     elif state is not None and name is None:
    #         _where_clause = ' WHERE state = \'$1\''
    #     else:
    #         _where_clause = ' WHERE process_name = \'$1\' and state = \'$2\''
    #
    #     query += _where_clause
    #
    #     stmt = await conn.prepare(query)
    #     if state is None and name is None:
    #         rows = await stmt.fetch()
    #     elif state is None and name is not None:
    #         rows = await stmt.fetch(name)
    #     elif state is not None and name is None:
    #         rows = await stmt.fetch(state)
    #     else:
    #         rows = await stmt.fetch(state, name)

    if not task_id:
        _where_clause = ''
    else:
        _where_clause = ' WHERE id = \'{0}\''

    query += _where_clause

    if task_id is not None:
        query = query.format(task_id)
    else:
        if state is None and name is None:
            _where_clause = ''
        elif state is None and name is not None:
            _where_clause = ' WHERE process_name = \'{0}\''
        elif state is not None and name is None:
            _where_clause = ' WHERE state = \'{0}\''
        else:
            _where_clause = ' WHERE process_name = \'{0}\' and state = \'{1}\''
        query += _where_clause

        if state is None and name is None:
            pass
        elif state is None and name is not None:
            query = query.format(name)
        elif state is not None and name is None:
            query = query.format(state)
        else:
            query = query.format(name, state)

    rows = await conn.fetch(query)

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
    conn = await asyncpg.connect(dsn=__DSN)
    query = '''
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
    '''

    # TODO: Investigate why prepared statement is not working
    # if state is None and name is None:
    #     _where_clause = ''
    # elif state is None and name is not None:
    #     _where_clause = ' WHERE process_name = \'$1\''
    # elif state is not None and name is None:
    #     _where_clause = ' WHERE state = \'$1\''
    # else:
    #     _where_clause = ' WHERE process_name = \'$1\' and state = \'$2\''
    #
    # query += _where_clause
    #
    # stmt = await conn.prepare(query)
    # if state is None and name is None:
    #     rows = await stmt.fetch()
    # elif state is None and name is not None:
    #     rows = await stmt.fetch(name)
    # elif state is not None and name is None:
    #     rows = await stmt.fetch(state)
    # else:
    #     rows = await stmt.fetch(state, name)

    if state is None and name is None:
        _where_clause = ''
    elif state is None and name is not None:
        _where_clause = ' WHERE process_name = \'{0}\''
    elif state is not None and name is None:
        _where_clause = ' WHERE state = \'{0}\''
    else:
        _where_clause = ' WHERE process_name = \'{0}\' and state = \'{1}\''

    query += _where_clause

    _order_clause = ' ORDER BY process_name ASC, start_time DESC'
    query += _order_clause

    if state is None and name is None:
        pass
    elif state is None and name is not None:
        query = query.format(name)
    elif state is not None and name is None:
        query = query.format(state)
    else:
        query = query.format(name, state)

    if state is None and name is None:
        pass
    elif state is None and name is not None:
        query = query.format(name)
    elif state is not None and name is None:
        query = query.format(state)
    else:
        query = query.format(name, state)

    rows = await conn.fetch(query)

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


# There is no requirement for update_task()

async def delete_task(payload):
    pass

