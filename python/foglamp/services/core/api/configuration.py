# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from aiohttp import web
from foglamp.services.core import connect
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.common.storage_client.payload_builder import PayloadBuilder
from foglamp.common.audit_logger import AuditLogger

__author__ = "Amarendra K. Sinha, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -------------------------------------------------------------------------------
    | GET POST        | /foglamp/category                                         |
    | GET             | /foglamp/category/{category_name}                         |
    | GET POST PUT    | /foglamp/category/{category_name}/{config_item}           |
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
    cf_mgr = ConfigurationManager(connect.get_storage_async())
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
    cf_mgr = ConfigurationManager(connect.get_storage_async())
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
        cf_mgr = ConfigurationManager(connect.get_storage_async())
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
            raise TypeError('keep_original_items should be boolean true | false')

        await cf_mgr.create_category(category_name=category_name, category_description=category_desc,
                                     category_value=category_value, keep_original_items=should_keep_original_items)

        category_info = await cf_mgr.get_category_all_items(category_name=category_name)
        if category_info is None:
            raise LookupError('No such %s found' % category_name)

    except (KeyError, ValueError, TypeError) as ex:
        raise web.HTTPBadRequest(reason=str(ex))

    except LookupError as ex:
        raise web.HTTPNotFound(reason=str(ex))

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
    cf_mgr = ConfigurationManager(connect.get_storage_async())
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
    cf_mgr = ConfigurationManager(connect.get_storage_async())

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


async def add_configuration_item(request):
    """
    Args:
        request: A JSON object that defines the config item and has key-pair
                 (default, type, description, value[optional])

    Returns:
        Json response with message key

    :Example:
        curl -d '{"default": "true", "description": "Test description", "type": "boolean"}' -X POST https://localhost:1995/foglamp/category/{category_name}/{new_config_item} --insecure
        curl -d '{"default": "true", "description": "Test description", "type": "boolean", "value": "false"}' -X POST https://localhost:1995/foglamp/category/{category_name}/{new_config_item} --insecure
    """
    category_name = request.match_info.get('category_name', None)
    new_config_item = request.match_info.get('config_item', None)

    try:
        storage_client = connect.get_storage_async()
        cf_mgr = ConfigurationManager(storage_client)

        data = await request.json()
        if not isinstance(data, dict):
            raise ValueError('Data payload must be a dictionary')

        # if value key is in data then go ahead with data payload and validate
        # else update the data payload with value key and set its value to default value and validate
        val = data.get('value', None)
        if val is None:
            data.update({'value': data.get('default')})
            config_item_dict = {new_config_item: data}
        else:
            config_item_dict = {new_config_item: data}

        # validate configuration category value
        await cf_mgr._validate_category_val(category_val=config_item_dict, set_value_val_from_default_val=False)

        # validate category
        category = await cf_mgr.get_category_all_items(category_name)
        if category is None:
            raise NameError("No such Category found for {}".format(category_name))

        # check if config item is already in use
        if new_config_item in category.keys():
            raise KeyError("Config item is already in use for {}".format(category_name))

        # merge category values with keep_original_items True
        merge_cat_val = await cf_mgr._merge_category_vals(config_item_dict, category, keep_original_items=True)

        # update category value in storage
        payload = PayloadBuilder().SET(value=merge_cat_val).WHERE(["key", "=", category_name]).payload()
        result = await storage_client.update_tbl("configuration", payload)
        response = result['response']

        # logged audit new config item for category
        audit = AuditLogger(storage_client)
        audit_details = {'category': category_name, 'item': new_config_item, 'value': config_item_dict}
        await audit.information('CONAD', audit_details)

    except (KeyError, ValueError, TypeError) as ex:
        raise web.HTTPBadRequest(reason=str(ex))
    except NameError as ex:
        raise web.HTTPNotFound(reason=str(ex))
    except Exception as ex:
        raise web.HTTPException(reason=str(ex))

    return web.json_response({"message": "{} config item has been saved for {} category".format(new_config_item, category_name)})


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
    cf_mgr = ConfigurationManager(connect.get_storage_async())
    try:
        category_item = await cf_mgr.get_category_item(category_name, config_item)
        if category_item is None:
            raise ValueError

        await cf_mgr.set_category_item_value_entry(category_name, config_item, category_item['default'])
    except ValueError:
        raise web.HTTPNotFound(reason="No detail found for the category_name: {} and config_item: {}".format(category_name, config_item))

    result = await cf_mgr.get_category_item(category_name, config_item)

    if result is None:
        raise web.HTTPNotFound(reason="No detail found for the category_name: {} and config_item: {}".format(category_name, config_item))

    return web.json_response(result)
