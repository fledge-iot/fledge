# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import time
import re
from aiohttp import web
from foglamp import configuration_manager
from foglamp.core import scheduler_db_services

__author__ = "Amarendra K. Sinha, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

__start_time = time.time()

_help = """
    ------------------------------------------------------------------------------
    | GET             | /foglamp/ping                                             |

    | GET             | /foglamp/categories                                       |
    | GET             | /foglamp/category/{category_name}                         |
    | GET DELETE      | /foglamp/category/{category_name}/{config_item}           |
    | PUT             | /foglamp/category/{category_name}/{config_item}/{value}   |

    | GET             | /foglamp/schedules                                        |
    | POST            | /foglamp/schedule                                         |
    | GET             | /foglamp/schedule/{schedule_id}                           |
    | PUT             | /foglamp/schedule/{schedule_id}                           |
    | DELETE          | /foglamp/schedule/{schedule_id}                           |

    | GET             | /foglamp/tasks                                            |
    | GET             | /foglamp/tasks/latest                                     |
    | POST            | /foglamp/task                                             |
    | GET             | /foglamp/task/{task_id}                                   |
    | DELETE          | /foglamp/task/{task_id}                                   |

    ------------------------------------------------------------------------------
"""


async def ping(request):
    """

    :param request:
    :return: basic health information json payload
    {'uptime': 32892} Time in seconds since FogLAMP started
    """
    since_started = time.time() - __start_time

    return web.json_response({'uptime': since_started})


#################################
#  Configuration Manager
#################################

async def get_categories(request):
    """

    :param request:
    :return: the list of known categories in the configuration database
    """
    categories = await configuration_manager.get_all_category_names()
    categories_json = [{"key": c[0], "description": c[1]} for c in categories]

    return web.json_response({'categories': categories_json})


async def get_category(request):
    """

    :param request:  category_name is required
    :return: the configuration items in the given category.
    """
    category_name = request.match_info.get('category_name', None)
    category = await configuration_manager.get_category_all_items(category_name)
    # TODO: If category is None from configuration manager. Should we send category
    # as an empty array or error message in JSON format?
    if category is None:
        category = []

    return web.json_response(category)


async def get_category_item(request):
    """

    :param request: category_name & config_item are required
    :return:  the configuration item in the given category.
    """
    category_name = request.match_info.get('category_name', None)
    config_item = request.match_info.get('config_item', None)
    category_item = await configuration_manager.get_category_item(category_name, config_item)
    # TODO: better error handling / info message
    if (category_name is None) or (config_item is None):
        category_item = []

    return web.json_response(category_item)


async def set_configuration_item(request):
    """

    :param request: category_name, config_item are required and value is required only when PUT
    :return: set the configuration item value in the given category.
    """
    category_name = request.match_info.get('category_name', None)
    config_item = request.match_info.get('config_item', None)
    if request.method == 'PUT':
        value = request.match_info.get('value', None)
    elif request.method == 'DELETE':
        value = ''

    await configuration_manager.set_category_item_value_entry(category_name, config_item, value)
    result = await configuration_manager.get_category_item(category_name, config_item)

    return web.json_response(result)


#################################
#  Scheduler Services
#################################

# Schedules

async def get_schedules(request):
    """Returns a list of all the defined schedules from schedules table"""

    schedules = await scheduler_db_services.read_schedule()

    return web.json_response(schedules)


async def get_schedule(request):
    """Return the information for the given schedule from schedules table"""

    schedule_id = request.match_info.get('schedule_id', None)

    if not schedule_id:
        return web.json_response({'err_msg': 'No such Schedule'})

    schedule = await scheduler_db_services.read_schedule(schedule_id)

    if not schedule:
        return web.json_response({'err_msg': 'No such Schedule'})

    return web.json_response(schedule)


async def post_schedule(request):
    """Create a new schedule in schedules table"""
    pass

async def update_schedule(request):
    """Update a schedule in schedules table"""
    pass

async def delete_schedule(request):
    """Delete a schedule from schedules table"""
    pass


# Tasks

async def get_task(request):
    """Returns a task"""

    task_id = request.match_info.get('task_id', None)

    if not task_id:
        return web.json_response({'err_msg': 'No such Task'})

    task = await scheduler_db_services.read_task(task_id)

    if not task:
        return web.json_response({'err_msg': 'No such Task'})

    return web.json_response(task)

async def get_tasks(request):
    """Returns the list of tasks"""

    task_id = None

    # TODO: Use enum in place int state
    state = request.query.get('state') if 'state' in request.query else None
    state = int(state) if state and re.match("(^[0-9]+$)", state) else 0

    name = request.query.get('name') if 'name' in request.query else None

    tasks = await scheduler_db_services.read_task(task_id, state, name)

    if not tasks:
        return web.json_response({'err_msg': 'No such Tasks'})

    return web.json_response(tasks)

async def get_tasks_latest(request):
    """Returns the list of the most recent task execution for each name from tasks table"""

    # TODO: Use enum in place int state
    state = request.query.get('state') if 'state' in request.query else None
    state = int(state) if state and re.match("(^[0-9]+$)", state) else 0

    name = request.query.get('name') if 'name' in request.query else None

    tasks = await scheduler_db_services.read_tasks_latest(state, name)

    if not tasks:
        return web.json_response({'err_msg': 'No such Tasks'})

    return web.json_response(tasks)

async def post_task(request):
    """ create a new task"""
    pass

async def cancel_task(request):
    """Cancel a running task from tasks table"""
    pass
