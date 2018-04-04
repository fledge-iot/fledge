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
    | GET POST        | /foglamp/category                                         |
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
            curl -X GET http://localhost:8081/foglamp/category
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

    # TODO: make it optimized and elegant
    cf_mgr = ConfigurationManager(connect.get_storage())
    category = await cf_mgr.get_category_all_items(category_name)

    if category is None:
        raise web.HTTPNotFound(reason="No such Category found for {}".format(category_name))

    return web.json_response(category)


async def create_category(request):
    """
    Args:
         request: A JSON object that defines the category

    Returns:
            category info

    :Example:
            curl -d '{"key": "TEST", "description": "description", "value": {"info": {"description": "Test", "type": "boolean", "default": "true"}}}' -X POST http://localhost:8081/foglamp/category
    """
    try:
        cf_mgr = ConfigurationManager(connect.get_storage())
        data = await request.json()
        if not isinstance(data, dict):
            raise ValueError('Data payload must be a dictionary')

        valid_post_keys = ['key', 'description', 'value']
        for k in valid_post_keys:
            if k not in list(data.keys()):
                raise KeyError("'{}' param required to create a category".format(k))

        category_name = data.get('key')
        category_desc = data.get('description')
        category_value = data.get('value')

        should_keep_original_items = data.get('keep_original_items', False)
        if not isinstance(should_keep_original_items, bool):
            raise web.HTTPBadRequest(reason="keep_original_items should be boolean true | false")

        await cf_mgr.create_category(category_name=category_name, category_description=category_desc,
                                     category_value=category_value, keep_original_items=should_keep_original_items)

        category_info = await cf_mgr.get_category_all_items(category_name=category_name)
        if category_info is None:
            raise web.HTTPNotFound(reason="No such {} found".format(category_info))

    except (KeyError, ValueError, TypeError) as ex:
        raise web.HTTPBadRequest(reason=str(ex))

    except Exception as ex:
        raise web.HTTPException(reason=str(ex))

    return web.json_response({"key": category_name, "description": category_desc, "value": category_info})


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

    # TODO: make it optimized and elegant
    cf_mgr = ConfigurationManager(connect.get_storage())
    category_item = await cf_mgr.get_category_item(category_name, config_item)

    if category_item is None:
        raise web.HTTPNotFound(reason="No such Category item found for {}".format(config_item))

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
    except KeyError:
        raise web.HTTPBadRequest(reason='Missing required value for {}'.format(config_item))

    try:
        await cf_mgr.set_category_item_value_entry(category_name, config_item, value)
    except ValueError:
        raise web.HTTPNotFound(reason="No detail found for the category_name: {} and config_item: {}".format(category_name, config_item))

    result = await cf_mgr.get_category_item(category_name, config_item)
    if result is None:
        raise web.HTTPNotFound(reason="No detail found for the category_name: {} and config_item: {}".format(category_name, config_item))

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

    # TODO: make it optimized and elegant
    cf_mgr = ConfigurationManager(connect.get_storage())
    try:
        await cf_mgr.set_category_item_value_entry(category_name, config_item, '')
    except ValueError:
        raise web.HTTPNotFound(reason="No detail found for the category_name: {} and config_item: {}".format(category_name, config_item))

    result = await cf_mgr.get_category_item(category_name, config_item)

    if result is None:
        raise web.HTTPNotFound(reason="No detail found for the category_name: {} and config_item: {}".format(category_name, config_item))

    return web.json_response(result)
