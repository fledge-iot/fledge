# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""FogLAMP Scheduler"""

import time
import asyncio
from asyncio.subprocess import Process
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as sa_pg

__author__ = "Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

class Scheduler(object):
    """FogLAMP scheduler"""

    class __ScheduleTypes:
        TIMED = 0
        INTERVAL = 0

    __scheduled_processes_tbl = None # type: sa.Table
    __schedules_tbl = None # type: sa.Table

    def __init__(self):
        """Constructor"""

        # Class variables (begin)
        if __schedules_tbl is None:
            __schedules_tbl =
                sa.Table( 'schedules',
                          sa.Column('process_name', sa.types.VARCHAR(20)),
                          sa.Column('schedule_type', sa.types.INT),
                          sa.Column('schedule_interval'),
                          sa.Column('exclusive')

                          sa.Table(
                              'schedules',
                              sa.MetaData(),
                              sa.Column('asset_cod', sa.types.VARCHAR(50)),
                              sa.Column('read_key', sa.types.VARCHAR(50)),
                              sa.Column('user_ts', sa.types.TIMESTAMP),
                              sa.Column('reading', JSONB))


            CREATE TABLE foglamp.schedules (
                id                uuid                  UNIQUE,   -- Unique uuid, PK
            process_name      character varying(20) NOT NULL, -- FK process name
            schedule_name     character varying(20) NOT NULL, -- schedule name
            schedule_type     smallint              NOT NULL, -- At the moment there are three types
            schedule_interval time,                           -- Schedule interval
            schedule_time     time,                           -- Schedule time
            exclusive         boolean,
                              CONSTRAINT schedules_pkey PRIMARY KEY (id)
            USING INDEX TABLESPACE foglamp,
                                   CONSTRAINT schedules_fk1 FOREIGN KEY (process_name)


            -- List of tasks
            CREATE TABLE foglamp.tasks (
                id           uuid                        UNIQUE,                 -- Unique uuid, PK
            process_name character varying(20)       NOT NULL,               -- Name of the task
            state        smallint                    NOT NULL,               -- State of the task: 1-Running, 2-Complete, 3-Cancelled
            start_time   timestamp(6) with time zone NOT NULL DEFAULT now(), -- The date and time the task started
            end_time     timestamp(6) with time zone,                        -- The date and time the task ended
            reason       character varying(20),                              -- The reason why the task ended
            CONSTRAINT tasks_pkey PRIMARY KEY (id)
            USING INDEX TABLESPACE foglamp,
            CONSTRAINT tasks_fk1 FOREIGN KEY (process_name)
            REFERENCES foglamp.scheduled_processes (name) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION )
            WITH ( OIDS = FALSE ) TABLESPACE foglamp;

            __scheduled_processes_tbl =
                sa.Table( 'scheduled_processes',
                            'script', sa_pg.JSONB )

    # Class variables (end)
        # Instance variables (begin)
        self.__last_check_time = None
        self.__start_time = time.now()
        self.__processes = []  # type: List[Process]
        r"""Long running processes

        A list of
        `Process <https://docs.python.org/3/library/asyncio-subprocess.html#asyncio.asyncio.subprocess.Process>`_
        objects
        """
        # Instance variables (end)


    def shutdown():
        """Stops the scheduler

        Terminates long-running processes like the device server.

        Waits for tasks to finish. There is no way to stop tasks that are already running.
        """
        for process in _processes:
            process.terminate()

    def
        """Processes interval schedules and starts processes"""

    async def _start_device_server():
        """Starts the device server (foglamp.device) as a subprocess"""
        process = await asyncio.create_subprocess_exec(
            'python3', '-m', 'foglamp.device')

        global _processes
        _processes.append(process)


    async def _main():
        await _start_device_server()
        # More is coming


    def start():
        """Start the scheduler"""

        asyncio.ensure_future(_main())

