# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from aiohttp import web
from foglamp.services.core import connect
from foglamp.common.configuration_manager import ConfigurationManager

__author__ = "Amarendra K. Sinha, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -------------------------------------------------------------------------------
    | GET             | /foglamp/categories                                       |
    | GET             | /foglamp/category/{category_name}                         |
    | GET PUT         | /foglamp/category/{category_name}/{config_item}           |
    | DELETE          | /foglamp/category/{category_name}/{config_item}/value     |
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
            curl -X GET http://localhost:8081/foglamp/categories
    """
    # TODO: make it optimized and elegant
    cf_mgr = ConfigurationManager(connect.get_storage())
    categories = await cf_mgr.get_all_category_names()
    categories_json = [{"key": c[0], "description": c[1]} for c in categories]

    return web.json_response({'categories': categories_json})


async def get_category(request):
    """
    Args:
         request: category_name is required

    Returns:
            the configuration items in the given category.

    :Example:
            curl -X GET http://localhost:8081/foglamp/category/PURGE_READ
    """
    category_name = request.match_info.get('category_name', None)

    if not category_name:
        raise web.HTTPBadRequest(reason="Category Name is required")

    # TODO: make it optimized and elegant
    cf_mgr = ConfigurationManager(connect.get_storage())
    category = await cf_mgr.get_category_all_items(category_name)

    if category is None:
        raise web.HTTPNotFound(reason="No such Category Found for {}".format(category_name))

    return web.json_response(category)


async def get_category_item(request):
    """
    Args:
         request: category_name & config_item are required

    Returns:
            the configuration item in the given category.

    :Example:
            curl -X GET http://localhost:8081/foglamp/category/PURGE_READ/age
    """
    category_name = request.match_info.get('category_name', None)
    config_item = request.match_info.get('config_item', None)

    if not category_name or not config_item:
        raise web.HTTPBadRequest(reason="Both Category Name and Config items are required")

    # TODO: make it optimized and elegant
    cf_mgr = ConfigurationManager(connect.get_storage())
    category_item = await cf_mgr.get_category_item(category_name, config_item)

    if category_item is None:
        raise web.HTTPNotFound(reason="No Category Item Found")

    return web.json_response(category_item)


async def set_configuration_item(request):
    """
    Args:
         request: category_name, config_item, {"value" : <some value>} are required

    Returns:
            set the configuration item value in the given category.

    :Example:
        curl -X PUT -H "Content-Type: application/json" -d '{"value": <some value> }' http://localhost:8081/foglamp/category/{category_name}/{config_item}

        For {category_name}=>PURGE update value for {config_item}=>age
        curl -X PUT -H "Content-Type: application/json" -d '{"value": 24}' http://localhost:8081/foglamp/category/PURGE_READ/age

    """
    category_name = request.match_info.get('category_name', None)
    config_item = request.match_info.get('config_item', None)

    data = await request.json()
    # TODO: make it optimized and elegant
    cf_mgr = ConfigurationManager(connect.get_storage())

    try:
        value = data['value']
        await cf_mgr.set_category_item_value_entry(category_name, config_item, value)
        result = await cf_mgr.get_category_item(category_name, config_item)

        if result is None:
            raise web.HTTPNotFound(reason="No detail found for the category_name: {} and config_item: {}".format(category_name, config_item))

    except KeyError:
        raise web.HTTPBadRequest(reason='Missing required value for {}'.format(config_item))

    return web.json_response(result)


async def delete_configuration_item_value(request):
    """
    Args:
        request: category_name, config_item are required

    Returns:
        set the configuration item value to empty string in the given category

    :Example:
        curl -X DELETE http://localhost:8081/foglamp/category/{category_name}/{config_item}/value

        For {category_name}=>PURGE delete value for {config_item}=>age
        curl -X DELETE http://localhost:8081/foglamp/category/PURGE_READ/age/value

    """
    category_name = request.match_info.get('category_name', None)
    config_item = request.match_info.get('config_item', None)

    if not category_name or not config_item:
        raise web.HTTPBadRequest(reason="Both Category Name and Config items are required")

    # TODO: make it optimized and elegant
    cf_mgr = ConfigurationManager(connect.get_storage())
    await cf_mgr.set_category_item_value_entry(category_name, config_item, '')
    result = await cf_mgr.get_category_item(category_name, config_item)

    if result is None:
        raise web.HTTPNotFound(reason="No detail found for the category_name: {} and config_item: {}".format(category_name, config_item))

    return web.json_response(result)
