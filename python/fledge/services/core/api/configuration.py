# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import copy
from aiohttp import web
import binascii
import urllib.parse
import os
from typing import Dict

from fledge.services.core import connect
from fledge.common.configuration_manager import ConfigurationManager, _optional_items
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.common.audit_logger import AuditLogger
from fledge.common.common import _FLEDGE_ROOT, _FLEDGE_DATA
from fledge.common import logger

__author__ = "Amarendra K. Sinha, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    --------------------------------------------------------------------------------
    | GET POST       | /fledge/category                                           |
    | GET PUT DELETE | /fledge/category/{category_name}                           |
    | GET POST PUT   | /fledge/category/{category_name}/{config_item}             |
    | DELETE         | /fledge/category/{category_name}/{config_item}/value       |
    | POST           | /fledge/category/{category_name}/{config_item}/upload      |
    | GET POST       | /fledge/category/{category_name}/children                  |
    | DELETE         | /fledge/category/{category_name}/children/{child_category} |
    | DELETE         | /fledge/category/{category_name}/parent                    |
    --------------------------------------------------------------------------------
"""

script_dir = _FLEDGE_DATA + '/scripts/' if _FLEDGE_DATA else _FLEDGE_ROOT + "/data/scripts/"
_logger = logger.setup(__name__)

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
            curl -sX GET http://localhost:8081/fledge/category
            curl -sX GET http://localhost:8081/fledge/category?root=true
            curl -sX GET 'http://localhost:8081/fledge/category?root=true&children=true'
    """
    cf_mgr = ConfigurationManager(connect.get_storage_async())

    if 'root' in request.query and request.query['root'].lower() in ['true', 'false']:
        is_root = True if request.query['root'].lower() == 'true' else False
        # to get nested categories, if children is true
        is_children = True if 'children' in request.query and request.query['children'].lower() == 'true' else False
        if is_children:
            categories_json = await cf_mgr.get_all_category_names(root=is_root, children=is_children)
        else:
            categories = await cf_mgr.get_all_category_names(root=is_root)
            categories_json = [{"key": c[0], "description": c[1], "displayName": c[2]} for c in categories]
    else:
        categories = await cf_mgr.get_all_category_names()
        categories_json = [{"key": c[0], "description": c[1], "displayName": c[2]} for c in categories]

    return web.json_response({'categories': categories_json})


async def get_category(request):
    """
    Args:
         request: category_name is required

    Returns:
            the configuration items in the given category.

    :Example:
            curl -X GET http://localhost:8081/fledge/category/PURGE_READ
    """
    category_name = request.match_info.get('category_name', None)
    category_name = urllib.parse.unquote(category_name) if category_name is not None else None

    cf_mgr = ConfigurationManager(connect.get_storage_async())
    category = await cf_mgr.get_category_all_items(category_name)

    if category is None:
        raise web.HTTPNotFound(reason="No such Category found for {}".format(category_name))

    try:
        request.is_core_mgt
    except AttributeError:
        category = hide_password(category)

    return web.json_response(category)


async def create_category(request):
    """
    Args:
         request: A JSON object that defines the category

    Returns:
            category info

    :Example:
            curl -d '{"key": "TEST", "description": "description", "value": {"info": {"description": "Test", "type": "boolean", "default": "true"}}}' -X POST http://localhost:8081/fledge/category
            curl -d '{"key": "TEST", "description": "description", "display_name": "Display test", "value": {"info": {"description": "Test", "type": "boolean", "default": "true"}}}' -X POST http://localhost:8081/fledge/category
            curl -d '{"key": "TEST", "description": "description", "value": {"info": {"description": "Test", "type": "boolean", "default": "true"}}, "children":["child1", "child2"]}' -X POST http://localhost:8081/fledge/category
    """
    keep_original_items = None
    if 'keep_original_items' in request.query and request.query['keep_original_items'] != '':
        keep_original_items = request.query['keep_original_items'].lower()
        if keep_original_items not in ['true', 'false']:
            raise ValueError("Only 'true' and 'false' are allowed for keep_original_items. {} given.".format(keep_original_items))

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
        category_display_name = data.get('display_name')
        should_keep_original_items = True if keep_original_items == 'true' else False
        if not len(category_name.strip()):
            raise ValueError('Key should not be empty')
        if category_display_name is not None:
            if not len(category_display_name.strip()):
                category_display_name = category_name

        await cf_mgr.create_category(category_name=category_name, category_description=category_desc,
                                     category_value=category_value, display_name=category_display_name, keep_original_items=should_keep_original_items)

        category_info = await cf_mgr.get_category_all_items(category_name=category_name)
        if category_info is None:
            raise LookupError('No such %s found' % category_name)
        result = {"key": category_name, "description": category_desc, "value": category_info, "displayName": cf_mgr._cacheManager.cache[category_name]['displayName']}
        if data.get('children'):
            r = await cf_mgr.create_child_category(category_name, data.get('children'))
            result.update(r)
        try:
            request.is_core_mgt
        except AttributeError:
            result['value'] = hide_password(result['value'])
    except (KeyError, ValueError, TypeError) as ex:
        raise web.HTTPBadRequest(reason=str(ex))
    except LookupError as ex:
        raise web.HTTPNotFound(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=str(ex))
    return web.json_response(result)


async def delete_category(request):
    """
    Args:
         request: category_name required
    Returns:
        Success message on successful deletion 
    Raises:
        TypeError/ValueError/Exception on error
    :Example:
            curl -X DELETE http://localhost:8081/fledge/category/{category_name}
    """
    category_name = request.match_info.get('category_name', None)
    category_name = urllib.parse.unquote(category_name) if category_name is not None else None

    try:
        cf_mgr = ConfigurationManager(connect.get_storage_async())
        await cf_mgr.delete_category_and_children_recursively(category_name)
    except (ValueError, TypeError) as ex:
        raise web.HTTPBadRequest(reason=ex)
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=ex)
    else:
        return web.json_response({'result': 'Category {} deleted successfully.'.format(category_name)})


async def get_category_item(request):
    """
    Args:
         request: category_name & config_item are required

    Returns:
            the configuration item in the given category.

    :Example:
            curl -X GET http://localhost:8081/fledge/category/PURGE_READ/age
    """
    category_name = request.match_info.get('category_name', None)
    config_item = request.match_info.get('config_item', None)

    category_name = urllib.parse.unquote(category_name) if category_name is not None else None
    config_item = urllib.parse.unquote(config_item) if config_item is not None else None

    cf_mgr = ConfigurationManager(connect.get_storage_async())
    category_item = await cf_mgr.get_category_item(category_name, config_item)
    if category_item is None:
        raise web.HTTPNotFound(reason="No such Category item found for {}".format(config_item))

    try:
        request.is_core_mgt
    except AttributeError:
        category_item = hide_password(category_item)

    return web.json_response(category_item)


async def set_configuration_item(request):
    """
    Args:
         request: category_name, config_item, [{"value" : "<some value>"} OR {"optional_key": "some value"}] are required

    Returns:
            set the configuration item value in the given category.

    :Example:
        curl -X PUT -H "Content-Type: application/json" -d '{"value": "<some value>" }' http://localhost:8081/fledge/category/{category_name}/{config_item}
        For {category_name}=>PURGE update value for {config_item}=>age

        curl -X PUT -H "Content-Type: application/json" -d '{"value": "24"}' http://localhost:8081/fledge/category/PURGE_READ/age
        curl -X PUT -H "Content-Type: application/json" -d '{"displayName": "Age"}' http://localhost:8081/fledge/category/PURGE_READ/age
    """
    category_name = request.match_info.get('category_name', None)
    config_item = request.match_info.get('config_item', None)

    category_name = urllib.parse.unquote(category_name) if category_name is not None else None
    config_item = urllib.parse.unquote(config_item) if config_item is not None else None

    data = await request.json()
    cf_mgr = ConfigurationManager(connect.get_storage_async())
    found_optional = {}
    # if multiple param keys in data and if value key is found, then value update for config item will be tried first
    # otherwise it will be looking for optional keys updation
    try:
        value = data['value']
        if isinstance(value, dict):
            pass
        elif not isinstance(value, str):
            raise web.HTTPBadRequest(reason='{} should be a string literal, in double quotes'.format(value))
    except KeyError:
        for k, v in data.items():
            # if multiple optional keys are found, then it will be update only 1 whoever comes first
            if k in _optional_items:
                found_optional = {k: v}
                break
        if not found_optional:
            raise web.HTTPBadRequest(reason='Missing required value for {}'.format(config_item))
    try:
        if not found_optional:
            try:
                is_core_mgt = request.is_core_mgt
            except AttributeError:
                storage_value_entry = await cf_mgr.get_category_item(category_name, config_item)
                if storage_value_entry is None:
                    raise ValueError("No detail found for the category_name: {} and item_name: {}"
                               .format(category_name, config_item))
                if 'readonly' in storage_value_entry:
                    if storage_value_entry['readonly'] == 'true':
                        raise TypeError("Update not allowed for {} item_name as it has readonly attribute set".format(config_item))
            await cf_mgr.set_category_item_value_entry(category_name, config_item, value)
        else:
            await cf_mgr.set_optional_value_entry(category_name, config_item, list(found_optional.keys())[0], list(found_optional.values())[0])
    except ValueError as ex:
        raise web.HTTPNotFound(reason=ex) if not found_optional else web.HTTPBadRequest(reason=ex)
    except (TypeError, KeyError) as ex:
        raise web.HTTPBadRequest(reason=ex)

    category_item = await cf_mgr.get_category_item(category_name, config_item)
    if category_item is None:
        raise web.HTTPNotFound(reason="No detail found for the category_name: {} and config_item: {}".format(category_name, config_item))

    try:
        request.is_core_mgt
    except AttributeError:
        category_item = hide_password(category_item)

    return web.json_response(category_item)


async def update_configuration_item_bulk(request):
    """ Bulk update config items

     :Example:
        curl -X PUT -H "Content-Type: application/json" -d '{"config_item_key": "<some value>", "config_item2_key": "<some value>" }' http://localhost:8081/fledge/category/{category_name}
    """
    category_name = request.match_info.get('category_name', None)
    category_name = urllib.parse.unquote(category_name) if category_name is not None else None

    try:
        data = await request.json()
        if not data:
            return web.HTTPBadRequest(reason='Nothing to update')
        cf_mgr = ConfigurationManager(connect.get_storage_async())
        try:
            is_core_mgt = request.is_core_mgt
        except AttributeError:
            for item_name, new_val in data.items():
                storage_value_entry = await cf_mgr.get_category_item(category_name, item_name)
                if storage_value_entry is None:
                    raise KeyError("{} config item not found".format(item_name))
                else:
                    if 'readonly' in storage_value_entry:
                        if storage_value_entry['readonly'] == 'true':
                            raise TypeError(
                                "Bulk update not allowed for {} item_name as it has readonly attribute set".format(item_name))
        await cf_mgr.update_configuration_item_bulk(category_name, data)
    except (NameError, KeyError) as ex:
        raise web.HTTPNotFound(reason=ex)
    except (ValueError, TypeError) as ex:
        raise web.HTTPBadRequest(reason=ex)
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=ex)
    else:
        cat = await cf_mgr.get_category_all_items(category_name)
        try:
            request.is_core_mgt
        except AttributeError:
            cat = hide_password(cat)
        return web.json_response(cat)


async def add_configuration_item(request):
    """
    Args:
        request: A JSON object that defines the config item and has key-pair
                 (default, type, description, value[optional])

    Returns:
        Json response with message key

    :Example:
        curl -d '{"default": "true", "description": "Test description", "type": "boolean"}' -X POST https://localhost:1995/fledge/category/{category_name}/{new_config_item} --insecure
        curl -d '{"default": "true", "description": "Test description", "type": "boolean", "value": "false"}' -X POST https://localhost:1995/fledge/category/{category_name}/{new_config_item} --insecure
    """
    category_name = request.match_info.get('category_name', None)
    new_config_item = request.match_info.get('config_item', None)

    category_name = urllib.parse.unquote(category_name) if category_name is not None else None
    new_config_item = urllib.parse.unquote(new_config_item) if new_config_item is not None else None

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
        await cf_mgr._validate_category_val(category_name=category_name, category_val=config_item_dict, set_value_val_from_default_val=False)

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
        raise web.HTTPInternalServerError(reason=str(ex))

    return web.json_response({"message": "{} config item has been saved for {} category".format(new_config_item, category_name)})


async def delete_configuration_item_value(request):
    """
    Args:
        request: category_name, config_item are required

    Returns:
        set the configuration item value to empty string in the given category

    :Example:
        curl -X DELETE http://localhost:8081/fledge/category/{category_name}/{config_item}/value

        For {category_name}=>PURGE delete value for {config_item}=>age
        curl -X DELETE http://localhost:8081/fledge/category/PURGE_READ/age/value

    """
    category_name = request.match_info.get('category_name', None)
    config_item = request.match_info.get('config_item', None)

    category_name = urllib.parse.unquote(category_name) if category_name is not None else None
    config_item = urllib.parse.unquote(config_item) if config_item is not None else None

    cf_mgr = ConfigurationManager(connect.get_storage_async())
    try:
        category_item = await cf_mgr.get_category_item(category_name, config_item)
        if category_item is None:
            raise ValueError
        try:
            is_core_mgt = request.is_core_mgt
        except AttributeError:
            if 'readonly' in category_item:
                if category_item['readonly'] == 'true':
                    raise TypeError(
                        "Delete not allowed for {} item_name as it has readonly attribute set".format(config_item))
        await cf_mgr.set_category_item_value_entry(category_name, config_item, category_item['default'])
    except ValueError:
        raise web.HTTPNotFound(reason="No detail found for the category_name: {} and config_item: {}".format(category_name, config_item))
    except TypeError as ex:
        raise web.HTTPBadRequest(reason=str(ex))

    result = await cf_mgr.get_category_item(category_name, config_item)

    if result is None:
        raise web.HTTPNotFound(reason="No detail found for the category_name: {} and config_item: {}".format(category_name, config_item))

    try:
        request.is_core_mgt
    except AttributeError:
        result = hide_password(result)

    return web.json_response(result)


async def get_child_category(request):
    """
    Args:
         request: category_name is required

    Returns:
            list of categories that are children of name category

    :Example:
            curl -X GET http://localhost:8081/fledge/category/south/children
    """
    category_name = request.match_info.get('category_name', None)
    category_name = urllib.parse.unquote(category_name) if category_name is not None else None

    cf_mgr = ConfigurationManager(connect.get_storage_async())

    try:
        children = await cf_mgr.get_category_child(category_name)
    except ValueError as ex:
        raise web.HTTPNotFound(reason=str(ex))

    return web.json_response({"categories": children})


async def create_child_category(request):
    """
    Args:
         request: category_name is required and JSON object that defines the child category

    Returns:
        parent of the children being added

    :Example:
            curl -d '{"children": ["coap", "http", "sinusoid"]}' -X POST http://localhost:8081/fledge/category/south/children
    """
    cf_mgr = ConfigurationManager(connect.get_storage_async())
    data = await request.json()
    if not isinstance(data, dict):
        raise ValueError('Data payload must be a dictionary')

    category_name = request.match_info.get('category_name', None)
    category_name = urllib.parse.unquote(category_name) if category_name is not None else None

    children = data.get('children')

    try:
        r = await cf_mgr.create_child_category(category_name, children)
    except TypeError as ex:
        raise web.HTTPBadRequest(reason=str(ex))
    except ValueError as ex:
        raise web.HTTPNotFound(reason=str(ex))

    return web.json_response(r)


async def delete_child_category(request):
    """
    Args:
        request: category_name, child_category are required

    Returns:
        remove the link b/w child category and its parent

    :Example:
        curl -X DELETE http://localhost:8081/fledge/category/{category_name}/children/{child_category}

    """
    category_name = request.match_info.get('category_name', None)
    child_category = request.match_info.get('child_category', None)
    category_name = urllib.parse.unquote(category_name) if category_name is not None else None

    cf_mgr = ConfigurationManager(connect.get_storage_async())
    try:
        result = await cf_mgr.delete_child_category(category_name, child_category)

    except TypeError as ex:
        raise web.HTTPBadRequest(reason=str(ex))
    except ValueError as ex:
        raise web.HTTPNotFound(reason=str(ex))

    return web.json_response({"children": result})


async def delete_parent_category(request):
    """
    Args:
        request: category_name

    Returns:
        remove the link b/w parent-child category for the parent

    :Example:
        curl -X DELETE http://localhost:8081/fledge/category/{category_name}/parent

    """
    category_name = request.match_info.get('category_name', None)
    category_name = urllib.parse.unquote(category_name) if category_name is not None else None

    cf_mgr = ConfigurationManager(connect.get_storage_async())
    try:
        await cf_mgr.delete_parent_category(category_name)
    except TypeError as ex:
        raise web.HTTPBadRequest(reason=str(ex))
    except ValueError as ex:
        raise web.HTTPNotFound(reason=str(ex))

    return web.json_response({"message": "Parent-child relationship for the parent-{} is deleted".format(category_name)})


async def upload_script(request):
    """ Upload script for a given config item

    :Example:
            curl -F "script=@filename.py" http://localhost:8081/fledge/category/{category_name}/{config_item}/upload
    """
    category_name = request.match_info.get('category_name', None)
    config_item = request.match_info.get('config_item', None)

    category_name = urllib.parse.unquote(category_name) if category_name is not None else None
    config_item = urllib.parse.unquote(config_item) if config_item is not None else None
    cf_mgr = ConfigurationManager(connect.get_storage_async())
    category_item = await cf_mgr.get_category_item(category_name, config_item)
    if category_item is None:
        raise web.HTTPNotFound(reason="No such Category item found for {}".format(config_item))

    config_item_type = category_item['type']
    if config_item_type != 'script':
        raise web.HTTPBadRequest(reason="Accepted config item type is 'script' but found {}".format(config_item_type))

    data = await request.post()

    # contains the name of the file in string format
    script_file = data.get('script')
    if not script_file:
        raise web.HTTPBadRequest(reason="Script file is missing")

    # TODO: For the time being accepted extension is '.py'
    script_filename = script_file.filename
    if not script_filename.endswith('.py'):
        raise web.HTTPBadRequest(reason="Accepted file extension is .py")

    script_file_data = data['script'].file
    script_file_content = script_file_data.read()
    prefix_file_name = category_name.lower() + "_" + config_item.lower() + "_"
    file_name = prefix_file_name + script_filename
    script_file_path = script_dir + file_name
    # If 'scripts' dir not exists, then create
    if not os.path.exists(script_dir):
        os.makedirs(script_dir)
    # Write contents to file and save under scripts dir path; it will be overwritten if exists
    with open(script_file_path, 'wb') as f:
        f.write(script_file_content)

    # the hexadecimal representation of the binary data
    hex_data = binascii.hexlify(script_file_content)
    str_data = hex_data.decode('utf-8')

    try:
        # Save the value to database
        await cf_mgr.set_category_item_value_entry(category_name, config_item, str_data, script_file_path)
        # Remove old files for combination categoryName_configItem_* and retain only the latest one
        _all_files = os.listdir(script_dir)
        for name in _all_files:
            if name.startswith(prefix_file_name):
                if name != file_name:
                    os.remove(script_dir + name)

    except Exception as ex:
        os.remove(script_file_path)
        raise web.HTTPBadRequest(reason=ex)
    else:
        result = await cf_mgr.get_category_item(category_name, config_item)
        return web.json_response(result)


def hide_password(config: dict) -> Dict:
    new_config = copy.deepcopy(config)
    try:
        for k, v in new_config.items():
            if v['type'] == 'password':
                v['value'] = "****"
    except TypeError:
        if new_config['type'] == 'password':
            new_config['value'] = "****"
    return new_config
