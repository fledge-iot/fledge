""""
Description: The following tests that each parameter changes appropriatly in the scheduler.get_tasks() method based on the call definition. 
Note that a tasks exist in one of the following states: 
  RUNNING     = 1
  COMPLETE    = 2
  CANCELED    = 3
  INTERRUPTED = 4
Test Cases: Testing begins by trying each parameter "independly" and slowly combinations of different ones until it changes all parameters. 
It is important to note that unless SORT is part of the where condition, tests only check the number of rows returned rather than the actual values. 
This is because when SORT isn't declared, the order in which rows are returned aren't guaranteed. 
0.  Error Messages - For INSERTing into tasks table, make sure that values < 1 and > 4 aren't accepted
1.  LIMIT
2.  OFFSET
3.  WHERE
4.  SORT 
5.  LIMIT  + OFFSET
6.  LIMIT  + WHERE
7.  LIMIT  + SORT
8.  OFFSET + WHERE
9.  OFFSET + SORT
10. WHERE  + SORT
11. LIMIT  + OFFSET + WHERE
12. LIMIT  + OFFSET + SORT
13. OFFSET + WHERE  + SORT
14. LIMIT  + OFFSET + WHERE + SORT
"""

import datetime
import random
import time
import uuid
import aiopg
import aiopg.sa
import asyncio
import pytest
import sqlalchemy
import sqlalchemy.dialects.postgresql
from foglamp.core.scheduler.scheduler import Scheduler
from foglamp.core.scheduler.entities import Task

__author__ = "Terris Linenbach, Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# TODO: Get rid of sqlalchemy or any dedicated DB oriented  code in tests.
_CONNECTION_STRING = "dbname='foglamp'"
_TASKS_TABLE = sqlalchemy.Table('tasks', sqlalchemy.MetaData(),
                                       sqlalchemy.Column('id', sqlalchemy.dialects.postgresql.UUID, primary_key=True),
                                       sqlalchemy.Column('process_name', sqlalchemy.types.VARCHAR(20), default=''   ),
                                       sqlalchemy.Column('state', sqlalchemy.types.INT),
                                       sqlalchemy.Column('start_time', sqlalchemy.types.TIMESTAMP),
                                       sqlalchemy.Column('end_time', sqlalchemy.types.TIMESTAMP),
                                       sqlalchemy.Column('pid', sqlalchemy.types.INT),
                                       sqlalchemy.Column('exit_code', sqlalchemy.types.INT),
                                       sqlalchemy.Column('reason', sqlalchemy.types.VARCHAR(255)))

# TODO: To run this test,
#       1) Do 'foglamp start' and note the management_port from syslog
#       2) Change _m_port below with the management_port
#       3) Execute this command: FOGLAMP_ENV=TEST pytest -s -vv tests/core/test_scheduler_get_tasks.py
_address = '0.0.0.0'
_m_port = 41041
scheduler = Scheduler(_address, _m_port)

@pytest.allure.feature("unit")
@pytest.allure.story("scheduler get_tasks")
class TestSchedulerGetTasks:
    @classmethod
    def setup_class(cls):
        asyncio.get_event_loop().run_until_complete(scheduler.start())

    @classmethod
    def teardown_class(cls):
        asyncio.get_event_loop().run_until_complete(scheduler.stop())

    @staticmethod
    async def drop_from_tasks():
        """DELETE data from tasks table"""
        try:
            async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
                async with engine.acquire() as conn:
                    await conn.execute('delete from foglamp.tasks')
        except Exception:
            print('DELETE failed')
            raise

    @staticmethod
    async def insert_into_tasks(total_rows=1000):
        """Insert random set of data into tasks table"""
        process_name = ['sleep1', 'sleep10', 'sleep30', 'sleep5']
        stmt = """INSERT INTO tasks
                        (id, process_name, state, start_time, end_time, pid, exit_code, reason)
                  VALUES """
        insert_into = "('%s', '%s', %s, '%s', '%s', %s, %s, '')"

        for i in range(total_rows):
            if i == total_rows-1:
                stmt = stmt + (insert_into % (str(uuid.uuid4()), random.choice(process_name), random.randint(1,4),
                                              datetime.datetime.fromtimestamp(time.time()),
                                              datetime.datetime.fromtimestamp(time.time()+0.1),
                                              random.randint(11111, 99999), random.randint(-1,1))) + ";"

            else:
                stmt = stmt + (insert_into % (str(uuid.uuid4()), random.choice(process_name), random.randint(1,4),
                                              datetime.datetime.fromtimestamp(time.time()),
                                              datetime.datetime.fromtimestamp(time.time()+0.1),
                                              random.randint(11111, 99999), random.randint(-1,1))) + ", "
        try:
            async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
                async with engine.acquire() as conn:
                    await conn.execute(stmt)
        except Exception:
            print('Insert failed: %s' % stmt)
            raise


    @pytest.mark.asyncio
    async def test_insert_error_tasks_table(self):
        """
        Verify values < 1 and > 4 aren't allowed when inserting into tasks table due to a key constraint
        :assert:
            when state=0 and state=5 ValueError is called
        """
        stmt = """INSERT INTO tasks
                        (id, process_name, state, start_time, end_time, pid, exit_code, reason)
                    VALUES ('%s', '%s', %s, '%s', '%s', %s, %s, '');"""

        for i in (0, 5):
            await self.drop_from_tasks()
            try:
                async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
                    async with engine.acquire() as conn:
                        await conn.execute('delete from foglamp.tasks')
                        await conn.execute(stmt % (str(uuid.uuid4()), 'sleep10', i,
                                                   datetime.datetime.fromtimestamp(time.time()),
                                                   datetime.datetime.fromtimestamp(time.time() + 0.1),
                                                   random.randint(11111, 99999), random.randint(1, 4)))
            except Exception:
                raise

            with pytest.raises(ValueError) as excinfo:
                await scheduler.get_tasks()
            assert "not a valid State" in str(excinfo.value)
        await self.drop_from_tasks()

    @pytest.mark.asyncio
    async def tests_get_tasks_limit(self):
        """
        Verify the numbe of tasks is the same as the limit
        :assert:
            number of tasks returned is equal to the limit
        """
        await self.drop_from_tasks()
        await self.insert_into_tasks()

        for limit in (1, 5, 25, 125, 250, 750, 1000):
            tasks = await scheduler.get_tasks(limit=limit)
            assert len(tasks) == limit
        tasks = await  scheduler.get_tasks()
        assert len(tasks) == 100

        await self.drop_from_tasks()

    @pytest.mark.asyncio
    async def test_get_tasks_offset(self):
        """
        Verify number of tasks is equal to the total_rows - offest
        :assert:
            the count(task) == total_rows - offset
        """
        await self.drop_from_tasks()
        await self.insert_into_tasks(total_rows=100)

        for offset in (0, 1, 5, 10, 25, 50, 75, 100):
            # limit is required for offset
            tasks = await scheduler.get_tasks(limit=100, offset=offset)
            assert len(tasks) == 100 - offset
        await  self.drop_from_tasks()

    @pytest.mark.asyncio
    async def test_get_tasks_where(self):
        """
        Check where condition against an INT value returns correct results
        :assert:
            the number of rows returned is as expected
        """
        await self.drop_from_tasks()
        await self.insert_into_tasks(total_rows=100)

        # Check expected values
        for state in range(1,5):
            stmt = sqlalchemy.select([sqlalchemy.func.count()]).select_from(_TASKS_TABLE).where(
                _TASKS_TABLE.c.state==state)
            try:
                async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
                    async with engine.acquire() as conn:
                        async for result in conn.execute(stmt):
                            expect = result[0]
            except Exception:
                print('Query failed: %s' % stmt)
                raise
            tasks = await scheduler.get_tasks(where=["state", "=", state])
            assert expect == len(tasks)
        await self.drop_from_tasks()

    @pytest.mark.asyncio
    async def test_get_tasks_sorted(self):
        """
        Check that sort variable of scheduler.get_tasks() works properlly
        :assert:
            1. process_name and integer value of task state are as correct
            2. The expected INTEGER value correlate to the actual task state
        """
        await self.drop_from_tasks()
        await self.insert_into_tasks(total_rows=100)

        stmt = sqlalchemy.select([_TASKS_TABLE.c.process_name, _TASKS_TABLE.c.state]).select_from(
            _TASKS_TABLE).order_by(_TASKS_TABLE.c.state.desc(), _TASKS_TABLE.c.process_name.desc())
        expect = []
        try:
            async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
                async with engine.acquire() as conn:
                    async for result in conn.execute(stmt):
                        expect.append(result)
        except Exception:
            print('Query failed: %s' % stmt)
            raise

        tasks = await scheduler.get_tasks(sort=(["state", "desc"], ["process_name", "desc"]))

        assert len(tasks) == len(expect) # verify that the same number of rows are returned
        for i in range(len(expect)):
            assert tasks[i].process_name == expect[i][0]
            assert int(tasks[i].state) == expect[i][1]
            if expect[i][1] == 1:
                assert tasks[i].state == Task.State.RUNNING
            elif expect[i][1] == 2:
                assert tasks[i].state == Task.State.COMPLETE
            elif expect[i][1] == 3:
                assert tasks[i].state == Task.State.CANCELED
            elif expect[i][1] == 4:
                assert tasks[i].state == Task.State.INTERRUPTED
        await self.drop_from_tasks()

    @pytest.mark.asyncio
    async def test_get_tasks_limit_offset(self):
        """
        A combination of limit and offset parameters
        :assert:
            The number of rows returned is equal to the limit of total_rows - offset
        """
        await self.drop_from_tasks()
        await self.insert_into_tasks()

        for limit in (1, 5, 25, 125, 250, 750, 1000):
            for offset in (0, 1, 5, 10, 25, 50, 75, 100):
                stmt = sqlalchemy.select(['*']).select_from(_TASKS_TABLE).offset(offset).limit(limit)
                expect = []
                try:
                    async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
                        async with engine.acquire() as conn:
                            async for result in conn.execute(stmt):
                                expect.append(result)
                except Exception:
                    print('Query failed: %s' % stmt)
                    raise
                tasks = await scheduler.get_tasks(limit=limit, offset=offset)
                assert len(tasks) == len(expect)

    @pytest.mark.asyncio
    async def test_get_tasks_limit_where(self):
        """
        A combination of WHERE condition and limit
        :assert:
            The number of rows returned is equal to the limit of the WHERE condition
        """
        await self.drop_from_tasks()
        await self.insert_into_tasks()

        # Check expected values
        for limit in (1, 5, 25, 125, 250, 750, 1000):
            for state in range(1, 5):
                stmt = sqlalchemy.select(['*']).select_from(_TASKS_TABLE).where(
                    _TASKS_TABLE.c.state == state).limit(limit)
                expect = []
                try:
                    async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
                        async with engine.acquire() as conn:
                            async for result in conn.execute(stmt):
                                expect.append(result)
                except Exception:
                    print('Query failed: %s' % stmt)
                    raise

                tasks = await scheduler.get_tasks(limit=limit, where=["state", "=", state])
                assert len(expect) == len(tasks)

        await self.drop_from_tasks()

    @pytest.mark.asyncio
    async def test_get_tasks_limit_sorted(self):
        """
        A combination of LIMIT and 'ORDER BY'
        :assert:
            1. The number of rows returned is equal to the limit
            2. The value per process_name and state is as expected
            3. The numerical value of expected state is correlated to the proper name of the task.state
        """
        await self.drop_from_tasks()
        await self.insert_into_tasks()

        for limit in (1, 5, 25, 125, 250, 750, 1000):
            stmt = sqlalchemy.select([_TASKS_TABLE.c.process_name, _TASKS_TABLE.c.state]).select_from(
                _TASKS_TABLE).order_by(_TASKS_TABLE.c.state.desc(), _TASKS_TABLE.c.process_name.desc()).limit(limit)
            expect = []
            try:
                async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
                    async with engine.acquire() as conn:
                        async for result in conn.execute(stmt):
                            expect.append(result)
            except Exception:
                print('Query failed: %s' % stmt)
                raise

            tasks = await scheduler.get_tasks(limit=limit, sort=(["state", "desc"], ["process_name", "desc"]))

            assert len(tasks) == len(expect) and len(tasks) == limit  # verify that the same number of rows are returned
            for i in range(len(expect)):
                assert tasks[i].process_name == expect[i][0]
                assert int(tasks[i].state) == expect[i][1]
                if expect[i][1] == 1:
                    assert tasks[i].state == Task.State.RUNNING
                elif expect[i][1] == 2:
                    assert tasks[i].state == Task.State.COMPLETE
                elif expect[i][1] == 3:
                    assert tasks[i].state == Task.State.CANCELED
                elif expect[i][1] == 4:
                    assert tasks[i].state == Task.State.INTERRUPTED
        await self.drop_from_tasks()

    @pytest.mark.asyncio
    async def test_get_tasks_offset_where(self):
        """
        Combination of OFFSET and WHERE conditions in table
        :assert:
            The number of rows returned is equal to the WHERE condition of total_rows - OFFSET
        """
        await self.drop_from_tasks()
        await self.insert_into_tasks(total_rows=100)

        for offset in (0, 1, 5, 10, 25, 50, 75, 100):
            for state in range(1, 5):
                stmt = sqlalchemy.select(['*']).select_from(_TASKS_TABLE).where(
                    _TASKS_TABLE.c.state == state).offset(offset)
                expect = []
                try:
                    async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
                        async with engine.acquire() as conn:
                            async for result in conn.execute(stmt):
                                expect.append(result)
                except Exception:
                    print('Query failed: %s' % stmt)
                    raise

                tasks = await scheduler.get_tasks(offset=offset, where=["state", "=", state])
                assert len(expect) == len(tasks)

        await self.drop_from_tasks()

    @pytest.mark.asyncio
    async def test_get_tasks_offset_sorted(self):
        """
        A combination of OFFSET and SORTED parameters
        :assert:
            1. Total number of rows returned is equal to total_rows - offset
            2. The value per process_name and state is as expected
            3. The numerical value of expected state is correlated to the proper name of the task.state
        """
        total_rows = 100

        await self.drop_from_tasks()
        await self.insert_into_tasks(total_rows=total_rows)

        for offset in (0, 1, 5, 10, 25, 50, 75, 100):
            stmt = sqlalchemy.select([_TASKS_TABLE.c.process_name, _TASKS_TABLE.c.state]).select_from(
                _TASKS_TABLE).order_by(_TASKS_TABLE.c.state.desc(), _TASKS_TABLE.c.process_name.desc()).offset(offset)
            expect = []
            try:
                async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
                    async with engine.acquire() as conn:
                        async for result in conn.execute(stmt):
                            expect.append(result)
            except Exception:
                print('Query failed: %s' % stmt)
                raise

            tasks = await scheduler.get_tasks(limit=100, offset=offset, sort=(["state", "desc"], ["process_name", "desc"]))

            assert len(tasks) == len(expect)  and len(tasks) == total_rows - offset # verify that the same number of rows are returned
            for i in range(len(expect)):
                assert tasks[i].process_name == expect[i][0]
                assert int(tasks[i].state) == expect[i][1]
                if expect[i][1] == 1:
                    assert tasks[i].state == Task.State.RUNNING
                elif expect[i][1] == 2:
                    assert tasks[i].state == Task.State.COMPLETE
                elif expect[i][1] == 3:
                    assert tasks[i].state == Task.State.CANCELED
                elif expect[i][1] == 4:
                    assert tasks[i].state == Task.State.INTERRUPTED
        await self.drop_from_tasks()

    @pytest.mark.asyncio
    async def test_get_tasks_where_sorted(self):
        """
        Case where tasks are based on WHERE condition, and sorted
        :assert:
            1. process_name and integer value of task state are as correct
            2. The expected INTEGER value correlate to the actual task state
        """
        await self.drop_from_tasks()
        await self.insert_into_tasks(total_rows=100)

        for state in range(1, 5):
            stmt = sqlalchemy.select([_TASKS_TABLE.c.process_name, _TASKS_TABLE.c.state]).select_from(
                _TASKS_TABLE).where(_TASKS_TABLE.c.state == state).order_by(_TASKS_TABLE.c.state.desc(),
                                                                            _TASKS_TABLE.c.process_name.desc())
            expect = []
            try:
                async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
                    async with engine.acquire() as conn:
                        async for result in conn.execute(stmt):
                            expect.append(result)
            except Exception:
                print('Query failed: %s' % stmt)
                raise

            tasks = await scheduler.get_tasks(where=["state", "=", state], sort=(["state", "desc"], ["process_name", "desc"]))

            for i in range(len(expect)):
                assert tasks[i].process_name == expect[i][0]
                assert int(tasks[i].state) == expect[i][1]
                if expect[i][1] == 1:
                    assert tasks[i].state == Task.State.RUNNING
                elif expect[i][1] == 2:
                    assert tasks[i].state == Task.State.COMPLETE
                elif expect[i][1] == 3:
                    assert tasks[i].state == Task.State.CANCELED
                elif expect[i][1] == 4:
                    assert tasks[i].state == Task.State.INTERRUPTED
        await self.drop_from_tasks()

    @pytest.mark.asyncio
    async def test_get_tasks_limit_offset_where(self):
        """
        A combination of LIMIT, OFFSET, and WHERE conditions
        :assert:
            The number of tasks is equal to the limit of the total_rows returned based on the WHERE condition - OFFSET
        """
        await self.drop_from_tasks()
        await self.insert_into_tasks()

        for limit in (1, 5, 25, 125, 250, 750, 1000):
            for offset in (0, 1, 5, 10, 25, 50, 75, 100):
                for state in range(1, 5):
                    stmt = sqlalchemy.select(['*']).select_from(_TASKS_TABLE).where(
                        _TASKS_TABLE.c.state == state).offset(offset).limit(limit)
                    expect = []
                    try:
                        async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
                            async with engine.acquire() as conn:
                                async for result in conn.execute(stmt):
                                    expect.append(result)
                    except Exception:
                        print('Query failed: %s' % stmt)
                        raise

                    tasks = await scheduler.get_tasks(limit=limit, offset=offset, where=["state", "=", state])
                    assert len(expect) == len(tasks)

        await self.drop_from_tasks()

    @pytest.mark.asyncio
    async def test_get_tasks_limit_offset_sorted(self):
        """
        A combination of limit, offset, and sorting
        :assert:
            1. The number of rows returned is equal to the limit of the total_rows - offset
            2. process_name and integer value of task state are as correct
            3. The expected INTEGER value correlate to the actual task state
        """
        await self.drop_from_tasks()
        await self.insert_into_tasks()

        for limit in (1, 5, 25, 125, 250, 750, 1000):
            for offset in (0, 1, 5, 10, 25, 50, 75, 100):
                stmt = sqlalchemy.select([_TASKS_TABLE.c.process_name, _TASKS_TABLE.c.state]).select_from(
                    _TASKS_TABLE).order_by(_TASKS_TABLE.c.state.desc(), _TASKS_TABLE.c.process_name.desc()).offset(
                    offset).limit(limit)
                expect = []
                try:
                    async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
                        async with engine.acquire() as conn:
                            async for result in conn.execute(stmt):
                                expect.append(result)
                except Exception:
                    print('Query failed: %s' % stmt)
                    raise

                tasks = await scheduler.get_tasks(limit=limit, offset=offset,
                                                   sort=(["state", "desc"], ["process_name", "desc"]))

                assert len(tasks) == len(expect)  # verify that the same number of rows are returned
                for i in range(len(expect)):
                    assert tasks[i].process_name == expect[i][0]
                    assert int(tasks[i].state) == expect[i][1]
                    if expect[i][1] == 1:
                        assert tasks[i].state == Task.State.RUNNING
                    elif expect[i][1] == 2:
                        assert tasks[i].state == Task.State.COMPLETE
                    elif expect[i][1] == 3:
                        assert tasks[i].state == Task.State.CANCELED
                    elif expect[i][1] == 4:
                        assert tasks[i].state == Task.State.INTERRUPTED
        await self.drop_from_tasks()

    @pytest.mark.asyncio
    async def test_get_tasks_limit_where_sorted(self):
        """
        A combination of LIMIT, WHERE, and SORTing
        :assert:
            1. The number of rows returned is equal to the limit of the total_rows returned based on the WHERE condition
            2. process_name and integer value of task state are as correct
            3. The expected INTEGER value correlate to the actual task state
        """
        await self.drop_from_tasks()
        await self.insert_into_tasks()

        for limit in (1, 5, 25, 125, 250, 750, 1000):
            for state in range(1, 5):
                stmt = sqlalchemy.select([_TASKS_TABLE.c.process_name, _TASKS_TABLE.c.state]).select_from(
                    _TASKS_TABLE).where(_TASKS_TABLE.c.state == state).order_by(_TASKS_TABLE.c.state.desc(),
                                                                                _TASKS_TABLE.c.process_name.desc()
                                                                                ).limit(limit)
                expect = []
                try:
                    async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
                        async with engine.acquire() as conn:
                            async for result in conn.execute(stmt):
                                expect.append(result)
                except Exception:
                    print('Query failed: %s' % stmt)
                    raise

                tasks = await scheduler.get_tasks(limit=limit, where=["state", "=", state],
                                                   sort = (["state", "desc"], ["process_name", "desc"]))

                for i in range(len(expect)):
                    assert tasks[i].process_name == expect[i][0]
                    assert int(tasks[i].state) == expect[i][1]

        await self.drop_from_tasks()


    @pytest.mark.asyncio
    async def test_get_tasks_offset_where_sorted(self):
        """
        A combination of OFFSET, WHERE, and SORTing
        :assert:
            1. The number of rows returned in equal to the total_rows returned based on the WHERE condition - OFFSET
            2. process_name and integer value of task state are as correct
            3. The expected INTEGER value correlate to the actual task state
        """
        await self.drop_from_tasks()
        await self.insert_into_tasks(total_rows=100)

        for offset in (0, 1, 5, 10, 25, 50, 75, 100):
            for state in range(1, 5):
                stmt = sqlalchemy.select([_TASKS_TABLE.c.process_name, _TASKS_TABLE.c.state]).select_from(
                    _TASKS_TABLE).where(_TASKS_TABLE.c.state == state).order_by(_TASKS_TABLE.c.state.desc(),
                                                                                _TASKS_TABLE.c.process_name.desc()
                                                                                ).offset(offset)
                expect = []
                try:
                    async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
                        async with engine.acquire() as conn:
                            async for result in conn.execute(stmt):
                                expect.append(result)
                except Exception:
                    print('Query failed: %s' % stmt)
                    raise

                tasks = await scheduler.get_tasks(offset=offset, where=["state", "=", state],
                                                   sort = (["state", "desc"], ["process_name", "desc"]))

                for i in range(len(expect)):
                    assert tasks[i].process_name == expect[i][0]
                    assert int(tasks[i].state) == expect[i][1]
                    if expect[i][1] == 1:
                        assert tasks[i].state == Task.State.RUNNING
                    elif expect[i][1] == 2:
                        assert tasks[i].state == Task.State.COMPLETE
                    elif expect[i][1] == 3:
                        assert tasks[i].state == Task.State.CANCELED
                    elif expect[i][1] == 4:
                        assert tasks[i].state == Task.State.INTERRUPTED
        await self.drop_from_tasks()

    @pytest.mark.asyncio
    async def test_get_tasks_all_parameters(self):
        """
        A combination of all parameters allowed by scheduler.get_tasks()
        :assert:
            1. The number of rows returned is equal to the limit of the subset of total_rows (based on the WHERE condition) - OFFSET
            2. process_name and integer value of task state are as correct
            3. The expected INTEGER value correlate to the actual task state
        """
        await self.drop_from_tasks()
        await self.insert_into_tasks()
        for limit in (1, 5, 25, 125, 250, 750, 1000):
            for offset in (0, 1, 5, 10, 25, 50, 75, 100):
                for state in range(1, 5):
                    stmt = sqlalchemy.select([_TASKS_TABLE.c.process_name, _TASKS_TABLE.c.state]).select_from(
                        _TASKS_TABLE).where(_TASKS_TABLE.c.state == state).order_by(_TASKS_TABLE.c.state.desc(),
                                                                                    _TASKS_TABLE.c.process_name.desc()
                                                                                    ).offset(offset).limit(limit)
                    expect = []
                    try:
                        async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
                            async with engine.acquire() as conn:
                                async for result in conn.execute(stmt):
                                    expect.append(result)
                    except Exception:
                        print('Query failed: %s' % stmt)
                        raise

                    tasks = await scheduler.get_tasks(offset=offset, limit=limit,
                                                       where=["state", "=", state],
                                                       sort=(["state", "desc"], ["process_name", "desc"]))

                    assert len(tasks) == len(expect)
                    for i in range(len(expect)):
                        assert tasks[i].process_name == expect[i][0]
                        assert int(tasks[i].state) == expect[i][1]
                        if expect[i][1] == 1:
                            assert tasks[i].state == Task.State.RUNNING
                        elif expect[i][1] == 2:
                            assert tasks[i].state == Task.State.COMPLETE
                        elif expect[i][1] == 3:
                            assert tasks[i].state == Task.State.CANCELED
                        elif expect[i][1] == 4:
                            assert tasks[i].state == Task.State.INTERRUPTED
        await self.drop_from_tasks()
