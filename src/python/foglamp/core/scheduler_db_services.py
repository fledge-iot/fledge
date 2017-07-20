# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Storage Services as needed by Processes
"""

import logging
import psycopg2
import aiopg.sa
import asyncio
import aiocoap
import time

import sqlalchemy as sa
from foglamp.db.tables import db_connection_url, t_scheduled_processes, t_schedules, t_tasks

__author__ = "Amarendra Kumar Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


async def create_scheduled_process(payload):
    pass

async def read_scheduled_process(payload):
    pass

async def update_scheduled_process(payload):
    pass

async def delete_scheduled_process(payload):
    pass


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

async def read_task(payload):
    pass

# There is no requirement for update_task()

async def delete_task(payload):
    pass

