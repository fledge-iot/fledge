# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import time
from aiohttp import web
from foglamp import configuration_manager

__author__ = "Amarendra K. Sinha, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

START_TIME = time.time()

HELP = """
    -----------------------------------------------------------------------
    | GET             | /ping                                             |

    | GET             | /categories                                       |
    | GET             | /category/{category_name}                         |
    | GET             | /category/{category_name}/{config_item}           |
    | PUT DELETE      | /category/{category_name}/{config_item}/{value}   |

    -----------------------------------------------------------------------
"""


async def ping(request):
    """

    :param request:
    :return: basic health information json payload
    {'uptime': 32892} Time in seconds since FogLAMP started
    """

    since_started = time.time() - START_TIME

    return web.json_response({'uptime': since_started})


#################################
###  Configuration Manager
#################################

async def get_categories(request):
    """

    :param request:
    :return: the list of known categories in the configuration database
    """
    categories = await configuration_manager.get_all_category_names()
    categories_json = [{"key": i[0], "description": i[1]} for i in categories]
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

    :param request: category_name & config_item is required
    :return:  the configuration item in the given category.
    """
    category_name = request.match_info.get('category_name', None)
    config_item = request.match_info.get('config_item', None)
    category_item = await configuration_manager.get_category_item(category_name, config_item)

    # TODO:
    if category_name is None:
        category_item = []
    elif config_item is None:
        category_item = []

    return web.json_response(category_item)


async def set_configuration_item(request):
    """

    :param request: category_name, config_item is required and value is required only when PUT
    :return: set the configuration item value in the given category.
    """

    category_name = request.match_info.get('category_name', None)
    config_item = request.match_info.get('config_item', None)
    value = request.match_info.get('value', None)

    if request.method == 'DELETE':
        value = ''

    await configuration_manager.set_category_item_value_entry(category_name, config_item, value)
    result = await configuration_manager.get_category_item(category_name, config_item)

    return web.json_response(result)


async def create_category(request):
    """

    :param request:
    :return:
    """
    # TODO: Missing in doc itself. Should we need to add create_category or
    # configuration manager will do the stuff by own.
    pass
