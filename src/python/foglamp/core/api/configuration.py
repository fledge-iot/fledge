# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from aiohttp import web
from foglamp import configuration_manager

__author__ = "Amarendra K. Sinha, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -------------------------------------------------------------------------------
    | GET             | /foglamp/categories                                       |
    | GET             | /foglamp/category/{category_name}                         |
    | GET PUT DELETE  | /foglamp/category/{category_name}/{config_item}           |
    -------------------------------------------------------------------------------
"""

#################################
#  Configuration Manager
#################################

async def get_categories(request):
    """
    Args:
         request:

    Returns:
            the list of known categories in the configuration database

    :Example:
            curl -X GET http://localhost:8082/foglamp/asset
    """
    categories = await configuration_manager.get_all_category_names()
    categories_json = [{"key": c[0], "description": c[1]} for c in categories]

    return web.json_response({'categories': categories_json})


async def get_category(request):
    """
    Args:
         request: category_name is required

    Returns:
            the configuration items in the given category.

    :Example:
            curl -X GET http://localhost:8082/foglamp/asset/mouse

            curl -X GET http://localhost:8082/foglamp/asset/TI%20sensorTag%2Ftemperature
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
    Args:
         request: category_name & config_item are required

    Returns:
            the configuration item in the given category.

    :Example:
            curl -X GET http://localhost:8082/foglamp/asset/TI%20sensorTag%2Ftemperature/ambient
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
    Args:
         request: category_name, config_item are required
         and For PUT request {"value" : someValue) is required

    Returns:
            set the configuration item value in the given category.

    :Example:
        For {category_name} PURGE  update/delete value for config_item {age}

        curl -X PUT -H "Content-Type: application/json" -d '{"value":some_value}' http://localhost:8082/foglamp/category/{category_name}/{config_item}

        curl -X DELETE http://localhost:8082/foglamp/category/{category_name}/{config_item}
    """
    category_name = request.match_info.get('category_name', None)
    config_item = request.match_info.get('config_item', None)

    if request.method == 'PUT':
        data = await request.json()
        value = data['value']
    elif request.method == 'DELETE':
        value = ''

    await configuration_manager.set_category_item_value_entry(category_name, config_item, value)
    result = await configuration_manager.get_category_item(category_name, config_item)

    return web.json_response(result)
