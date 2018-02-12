# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" FogLAMP package updater API support"""

from aiohttp import web
import uuid
import asyncio
import json
import datetime

# FogLAMP imports
from foglamp.services.core import server
from foglamp.common import logger
from foglamp.services.core.scheduler.entities import ManualSchedule

_LOG_LEVEL_INFO = 20
_logger = logger.setup(__name__, level=_LOG_LEVEL_INFO)

__author__ = "Massimiliano Pinto"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -----------------------------------------
    | PUT             | /foglamp/update     |
    -----------------------------------------
    | no paylod       |                     |
    -----------------------------------------
"""

###
# The update.py is part of the FogLAMP REST API:
# when called via PUT /foglamp/update it will add/fetch the "manual update task"
# to scheduler queue for execution.
#
#

_FOGLAMP_UPDATE_TASK = "FogLAMPUpdater"
_FOGLAMP_MANUAL_UPDATE_SCHEDULE = 'FogLAMP updater on demand'

async def update_package(request):
    """ Queues the execution of FogLAMP package update task

    :Example: curl -X PUT http://localhost:8081/foglamp/update
    """

    create_message = "'" + _FOGLAMP_MANUAL_UPDATE_SCHEDULE + \
                     "': a new shedule has been created"
    status_message = "'" + _FOGLAMP_MANUAL_UPDATE_SCHEDULE + \
                     "' has been queued for execution"
    error_message = "failure creating the schedule '" + \
                    _FOGLAMP_MANUAL_UPDATE_SCHEDULE + "'"
    task_found = False

    # Get all the 'Scheduled Tasks'
    schedule_list = await server.Server.scheduler.get_schedules()

    # Find the manual updater schedule
    for schedule_info in schedule_list:
        if schedule_info.name == _FOGLAMP_MANUAL_UPDATE_SCHEDULE:
            task_found = True

            # Set the schedule id
            schedule_id = schedule_info.schedule_id
            break;

    # If no schedule then create it
    if task_found is False:
        # Create a manual schedule for update
        manual_schedule = ManualSchedule()

        if not manual_schedule:
        # Return error
            _logger.error(error_message)
            return web.json_response({"status": "Failed", "message": error_message})

        # Set schedule fields
        manual_schedule.name = _FOGLAMP_MANUAL_UPDATE_SCHEDULE
        manual_schedule.process_name = _FOGLAMP_UPDATE_TASK
        manual_schedule.repeat = datetime.timedelta(seconds=0)
        manual_schedule.enabled = True
        manual_schedule.exclusive = True

        await server.Server.scheduler.save_schedule(manual_schedule)

        # Set the schedule id
        schedule_id = manual_schedule.schedule_id

        # Log new shedule creation
        _logger.info(create_message + ", ID [" + str(schedule_id) + "]")

    # Add schedule_id to the schedule queue
    await server.Server.scheduler.queue_task(schedule_id)

    # Return success
    return web.json_response({"status": "Running", "message": status_message})
