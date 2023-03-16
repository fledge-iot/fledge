# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Fledge package updater API support"""


import json
from aiohttp import web
import datetime
import os
import asyncio
import re

from fledge.common import utils
from fledge.common.logger import FLCoreLogger
from fledge.services.core import server
from fledge.services.core.scheduler.entities import ManualSchedule

_logger = FLCoreLogger().get_logger(__name__)

__author__ = "Massimiliano Pinto"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -----------------------------------------
    | PUT, GET            | /fledge/update   |
    -----------------------------------------
"""

###
# The update.py is part of the Fledge REST API:
# when called via PUT /fledge/update it will add/fetch the "manual update task"
# to scheduler queue for execution.
#
#

_FLEDGE_UPDATE_TASK = "FledgeUpdater"
_FLEDGE_MANUAL_UPDATE_SCHEDULE = 'Fledge updater on demand'


async def update_package(request):
    """ Queues the execution of Fledge package update task

    :Example: curl -X PUT http://localhost:8081/fledge/update
    """

    create_message = "{} : a new schedule has been created".format(_FLEDGE_MANUAL_UPDATE_SCHEDULE)
    status_message = "{}  has been queued for execution".format(_FLEDGE_MANUAL_UPDATE_SCHEDULE)
    error_message = "Failed to create the schedule {}".format(_FLEDGE_MANUAL_UPDATE_SCHEDULE)
    schedule_disable_error_message = "{} schedule is disabled".format(_FLEDGE_MANUAL_UPDATE_SCHEDULE)

    try:
        task_found = False
        # Get all the 'Scheduled Tasks'
        schedule_list = await server.Server.scheduler.get_schedules()

        # Find the manual updater schedule
        for schedule_info in schedule_list:
            if schedule_info.name == _FLEDGE_MANUAL_UPDATE_SCHEDULE:
                task_found = True
                # Set the schedule id
                schedule_id = schedule_info.schedule_id
                if schedule_info.enabled is False:
                    _logger.warning(schedule_disable_error_message)
                    raise ValueError(schedule_disable_error_message)
                break

        # If no schedule then create it
        if task_found is False:
            # Create a manual schedule for update
            manual_schedule = ManualSchedule()

            if not manual_schedule:
                raise ValueError(error_message)
            # Set schedule fields
            manual_schedule.name = _FLEDGE_MANUAL_UPDATE_SCHEDULE
            manual_schedule.process_name = _FLEDGE_UPDATE_TASK
            manual_schedule.repeat = datetime.timedelta(seconds=0)
            manual_schedule.enabled = True
            manual_schedule.exclusive = True

            await server.Server.scheduler.save_schedule(manual_schedule)

            # Set the schedule id
            schedule_id = manual_schedule.schedule_id

            # Log new schedule creation
            _logger.info("%s, ID [ %s ]", create_message, str(schedule_id))

        # Save current logged user token
        token = request.headers.get('authorization', None)
        if token is not None:
            with open(os.path.expanduser('~') + '/.fledge_token', 'w') as f:
                f.write(token)

        # Add schedule_id to the schedule queue
        await server.Server.scheduler.queue_task(schedule_id)
    except ValueError as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        _logger.error("Failed to update Fledge package.{}".format(msg))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({"status": "Running", "message": status_message})


async def get_updates(request: web.Request) -> web.Response:
    """
        Gives list of packages for which updates are available.

        Returns JSON Response
         Sample Response
         {
            "updates": [
            "fledge-south-sinusoid","fledge"
            ]
        }
        Example
         curl -sX GET http://localhost:8081/fledge/update |jq
    """
    update_cmd = "sudo apt update"
    upgradable_pkgs_check_cmd = "apt list --upgradable | grep \^fledge"
    if utils.is_redhat_based():
        update_cmd = "sudo yum check-update"
        upgradable_pkgs_check_cmd = "yum list updates | grep \^fledge"

    update_process = await asyncio.create_subprocess_shell(update_cmd,
                                                           stdout=asyncio.subprocess.PIPE,
                                                           stderr=asyncio.subprocess.PIPE)
    _, stderr = await update_process.communicate()
    if update_process.returncode != 0:
        msg = "Could not run {} due to {}".format(update_cmd, stderr.decode('utf-8'))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))

    upgradable_pkgs_check_process = await asyncio.create_subprocess_shell(upgradable_pkgs_check_cmd,
                                                                          stdout=asyncio.subprocess.PIPE,
                                                                          stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await upgradable_pkgs_check_process.communicate()
    if upgradable_pkgs_check_process.returncode != 0:
        _logger.info("Nothing to upgrade at the moment. {}".format(stderr.decode("utf-8")))
        upgradable_packages = []
        return web.json_response({'updates': upgradable_packages})
    try:
        process_output = stdout.decode("utf-8")
        _logger.debug(process_output)
        # split on new-line
        word_list = re.split(r"\n+", process_output)

        # remove '' from the list
        word_list = [w for w in word_list if w != '']
        packages = []

        # For APT the output of apt list is as follows:
        """
        $ apt list --upgradable
        Listing... Done
        fledge-gui/unknown 1.9.2-440-gf849eed5 all [upgradable from: 1.9.2]
        fledge-south-sinusoid/unknown 1.9.2-1-g38a138f amd64 [upgradable from: 1.9.2]
        """
        # Now match the character / . The string before / is the actual package name we want.
        for word in word_list:
            # TODO find regex for yum as well.
            word_match = re.findall(r".*[/]", word)
            if len(word_match) > 0:
                packages.append(word_match[0].replace('/', '').strip())

        # Make a set to avoid duplicates.
        upgradable_packages = list(set(packages))
    except Exception as ex:
        msg = "Failed to fetch upgradable packages list for the configured repository! {}".format(str(ex))
        _logger.error(msg)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({'updates': upgradable_packages})
