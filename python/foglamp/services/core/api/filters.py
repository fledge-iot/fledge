# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import json
import copy
import aiohttp
from aiohttp import web
from typing import List, Dict, Tuple

from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.services.core import connect
from foglamp.services.core.api import utils as apiutils
from foglamp.common import logger
from foglamp.common.storage_client.payload_builder import PayloadBuilder
from foglamp.common.storage_client.exceptions import StorageServerError
from foglamp.common.storage_client.storage_client import StorageClientAsync

__author__ = "Massimiliano Pinto, Amarendra K Sinha"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    ---------------------------------------------------------------------------
    | POST GET        | /foglamp/filter                                       |
    | PUT GET DELETE  | /foglamp/filter/{user_name}/pipeline                  |
    | GET DELETE      | /foglamp/filter/{filter_name}                         |
    ---------------------------------------------------------------------------
"""

_LOGGER = logger.setup("filter")


async def create_filter(request: web.Request) -> web.Response:
    """
    Create a new filter with a specific plugin
    
    :Example:
     curl -X POST http://localhost:8081/foglamp/filter -d '{"name": "North_Readings_to_PI_scale_stage_1Filter", "plugin": "scale"}'
     curl -X POST http://localhost:8081/foglamp/filter -d '{"name": "North_Readings_to_PI_scale_stage_1Filter", "plugin": "scale", "filter_config": {"offset":"1","enable":"true"}}'

    'name' is the filter name
    'plugin' is the filter plugin name
    'filter_config' is the new configuration of the plugin, part or full, should we desire to modify
    the config at creation time itself

    The plugin is loaded and default config from 'plugin_info'
    is fetched.

    A new config category 'name' is created:
    items are:
       - 'plugin'
       - all items from default plugin config

    NOTE: The 'create_category' call is made with keep_original_items = True

    """
    try:
        data = await request.json()
        filter_name = data.get('name', None)
        plugin_name = data.get('plugin', None)
        filter_config = data.get('filter_config', {})
        if not filter_name or not plugin_name:
            raise TypeError('Filter name, plugin name are mandatory.')

        storage = connect.get_storage_async()
        cf_mgr = ConfigurationManager(storage)

        # Check first whether filter already exists
        category_info = await cf_mgr.get_category_all_items(category_name=filter_name)
        if category_info is not None:
            raise ValueError("This '{}' filter already exists".format(filter_name))

        # Load C filter plugin info
        loaded_plugin_info = apiutils.get_plugin_info(plugin_name, dir='filter')
        if not loaded_plugin_info or 'config' not in loaded_plugin_info:
            message = "Can not get 'plugin_info' detail from plugin '{}'".format(plugin_name)
            raise ValueError(message)

        # Sanity checks
        plugin_config = loaded_plugin_info['config']
        loaded_plugin_type = loaded_plugin_info['type']
        loaded_plugin_name = plugin_config['plugin']['default']
        if plugin_name != loaded_plugin_name or loaded_plugin_type != 'filter':
            raise ValueError(
                "Loaded plugin '{}', type '{}', doesn't match the specified one '{}', type 'filter'".format(
                    loaded_plugin_name, loaded_plugin_type, plugin_name))

        # Set dict value for 'default' if type is JSON. This is required by the configuration manager
        for key, value in plugin_config.items():
            if value['type'] == 'JSON':
                value['default'] = json.loads(json.dumps(value['default']))

        # Check if filter exists in filters table
        payload = PayloadBuilder().WHERE(['name', '=', filter_name]).payload()
        result = await storage.query_tbl_with_payload("filters", payload)
        if len(result["rows"]) == 0:
            # Create entry in filters table
            payload = PayloadBuilder().INSERT(name=filter_name, plugin=plugin_name).payload()
            await storage.insert_into_tbl("filters", payload)

        # Everything ok, now create filter config
        filter_desc = "Configuration of '{}' filter for plugin '{}'".format(filter_name, plugin_name)
        await cf_mgr.create_category(category_name=filter_name,
                                     category_description=filter_desc,
                                     category_value=plugin_config,
                                     keep_original_items=True)

        # If custom filter_config is in POST data, then update the value for each config item
        if filter_config is not None:
            if not isinstance(filter_config, dict):
                raise ValueError('filter_config must be a JSON object')
            await cf_mgr.update_configuration_item_bulk(filter_name, filter_config)

        # Fetch the new created filter: get category items
        category_info = await cf_mgr.get_category_all_items(category_name=filter_name)
        if category_info is None:
            raise ValueError("No such '{}' filter found".format(filter_name))
        else:
            return web.json_response({'filter': filter_name, 'description': filter_desc, 'value': category_info})
    except ValueError as ex:
        _LOGGER.exception("Add filter, caught exception: " + str(ex))
        raise web.HTTPNotFound(reason=str(ex))
    except TypeError as ex:
        _LOGGER.exception("Add filter, caught exception: " + str(ex))
        raise web.HTTPBadRequest(reason=str(ex))
    except StorageServerError as ex:
        await _delete_configuration_category(storage, filter_name)  # Revert configuration entry
        _LOGGER.exception("Failed to create filter. %s", ex.error)
        raise web.HTTPInternalServerError(reason='Failed to create filter.')
    except Exception as ex:
        _LOGGER.exception("Add filter, caught exception:  %s", str(ex))
        raise web.HTTPInternalServerError(reason=str(ex))


async def add_filters_pipeline(request: web.Request) -> web.Response:
    """
    Add filter names to "filter" item in {user_name}

    PUT /foglamp/filter/{user_name}/pipeline
 
    'pipeline' is the array of filter category names to set
    into 'filter' default/value properties

    :Example: set 'pipeline' for user 'NorthReadings_to_PI'
    curl -X PUT http://localhost:8081/foglamp/filter/NorthReadings_to_PI/pipeline -d 
    '{
        "pipeline": ["Scale10Filter", "Python_assetCodeFilter"],
    }'

    Configuration item 'filter' is added to {user_name}
    or updated with the pipeline list

    Returns the filter pipeline on success:
    {"pipeline": ["Scale10Filter", "Python_assetCodeFilter"]} 

    Query string parameters:
    - append_filter=true|false       Default false
    - allow_duplicates=true|false    Default true

    :Example:
    curl -X PUT http://localhost:8081/foglamp/filter/NorthReadings_to_PI/pipeline?append_filter=true|false -d
    '{
        "pipeline": ["Scale10Filter", "Python_assetCodeFilter"],
    }'
    curl -X PUT http://localhost:8081/foglamp/filter/NorthReadings_to_PI/pipeline?allow_duplicates=true|false -d
    '{
        "pipeline": ["Scale10Filter", "Python_assetCodeFilter"],
    }'
    curl -X PUT 'http://localhost:8081/foglamp/filter/NorthReadings_to_PI/pipeline?append_filters=true&allow_duplicates=true|false' -d
    '{
        "pipeline": ["Scale10Filter", "Python_assetCodeFilter"],
    }'

    Delete pipeline:
    curl -X PUT -d '{"pipeline": []}' http://localhost:8081/foglamp/filter/NorthReadings_to_PI/pipeline 

    NOTE: the method also adds the filters category names under
    parent category {user_name}
    """
    try:
        data = await request.json()
        filter_list = data.get('pipeline', None)
        user_name = request.match_info.get('user_name', None)

        # Empty list [] is allowed as it clears the pipeline
        if filter_list is not None and not isinstance(filter_list, list):
            raise TypeError('Pipeline must be a list of filters or an empty value')

        # We just need to update the value of config_item with the "pipeline" property. Check whether
        # we want to replace or update the list or we allow duplicate entries in the list.
        # Default: append and allow duplicates
        append_filter = 'false'
        allow_duplicates = 'true'
        if 'append_filter' in request.query and request.query['append_filter'] != '':
            append_filter = request.query['append_filter'].lower()
            if append_filter not in ['true', 'false']:
                raise ValueError("Only 'true' and 'false' are allowed for append_filter. {} given.".format(
                    append_filter))
        if 'allow_duplicates' in request.query and request.query['allow_duplicates'] != '':
            allow_duplicates = request.query['allow_duplicates'].lower()
            if allow_duplicates not in ['true', 'false']:
                raise ValueError("Only 'true' and 'false' are allowed for allow_duplicates. {} given.".format(
                    allow_duplicates))

        storage = connect.get_storage_async()
        cf_mgr = ConfigurationManager(storage)

        # Check if category_name exists
        category_info = await cf_mgr.get_category_all_items(category_name=user_name)
        if category_info is None:
            raise ValueError("No such '{}' category found.".format(user_name))

        # Check and validate if all filters in the list exists in filters table
        for _filter in filter_list:
            payload = PayloadBuilder().WHERE(['name', '=', _filter]).payload()
            result = await storage.query_tbl_with_payload("filters", payload)
            if len(result["rows"]) == 0:
                raise ValueError("No such '{}' filter found in filters table.".format(_filter))

        config_item = "filter"

        if config_item in category_info:  # Check if config_item key has already been added to the category config
            # Fetch existing filters
            filter_value_from_storage = json.loads(category_info[config_item]['value'])
            current_filters = filter_value_from_storage['pipeline']
            # If filter list is empty don't check current list value
            # Empty list [] clears current pipeline
            if append_filter == 'true' and filter_list:
                new_list = copy.deepcopy(current_filters)
                for _filter in filter_list:
                    if allow_duplicates == 'true' or _filter not in current_filters:
                        new_list.append(_filter)
            else:
                new_list = filter_list
            await _delete_child_filters(storage, cf_mgr, user_name, new_list, old_list=current_filters)
            await _add_child_filters(storage, cf_mgr, user_name, new_list, old_list=current_filters)
            # Config update for filter pipeline and a change callback after category children creation
            await cf_mgr.set_category_item_value_entry(user_name, config_item, {'pipeline': new_list})
        else:  # No existing filters, hence create new item 'config_item' and add the "pipeline" array as a string
            new_item = dict({config_item: {'description': 'Filter pipeline', 'type': 'JSON', 'default': {}, 'readonly':'true'}})
            new_item[config_item]['default'] = json.dumps({'pipeline': filter_list})
            await _add_child_filters(storage, cf_mgr, user_name, filter_list)
            await cf_mgr.create_category(category_name=user_name, category_value=new_item, keep_original_items=True)

        # Fetch up-to-date category item
        result = await cf_mgr.get_category_item(user_name, config_item)
        if result is None:
            message = "No detail found for user: {} and filter: {}".format(user_name, config_item)
            raise ValueError(message)
        else:
            return web.json_response(
                {'result': "Filter pipeline {} updated successfully".format(json.loads(result['value']))})
    except ValueError as ex:
        _LOGGER.exception("Add filters pipeline, caught exception: %s", str(ex))
        raise web.HTTPNotFound(reason=str(ex))
    except TypeError as ex:
        _LOGGER.exception("Add filters pipeline, caught exception: %s", str(ex))
        raise web.HTTPBadRequest(reason=ex)
    except StorageServerError as ex:
        _LOGGER.exception("Add filters pipeline, caught exception: %s", str(ex.error))
        raise web.HTTPInternalServerError(reason=str(ex.error))
    except Exception as ex:
        _LOGGER.exception("Add filters pipeline, caught exception: %s", str(ex))
        raise web.HTTPInternalServerError(reason=str(ex))


async def get_filter(request: web.Request) -> web.Response:
    """ GET filter detail

    :Example:
        curl -X GET http://localhost:8081/foglamp/filter/<filter_name>
    """
    filter_name = request.match_info.get('filter_name', None)
    try:
        storage = connect.get_storage_async()
        cf_mgr = ConfigurationManager(storage)
        filter_detail = {}

        # Fetch the filter items: get category items
        category_info = await cf_mgr.get_category_all_items(filter_name)
        if category_info is None:
            raise ValueError("No such '{}' category found.".format(filter_name))
        filter_detail.update({"config": category_info})

        # Fetch filter detail
        payload = PayloadBuilder().WHERE(['name', '=', filter_name]).payload()
        result = await storage.query_tbl_with_payload("filters", payload)
        if len(result["rows"]) == 0:
            raise ValueError("No such filter '{}' found.".format(filter_name))
        row = result["rows"][0]
        filter_detail.update({"name": row["name"], "plugin": row["plugin"]})

        # Fetch users which are using this filter
        payload = PayloadBuilder().WHERE(['name', '=', filter_name]).payload()
        result = await storage.query_tbl_with_payload("filter_users", payload)
        users = []
        for row in result["rows"]:
            users.append(row["user"])
        filter_detail.update({"users": users})
    except StorageServerError as ex:
        _LOGGER.exception("Get filter: %s, caught exception: %s", filter_name, str(ex.error))
        raise web.HTTPInternalServerError(reason=str(ex.error))
    except ValueError as ex:
        raise web.HTTPNotFound(reason=ex)
    except TypeError as ex:
        raise web.HTTPBadRequest(reason=ex)
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=ex)
    else:
        return web.json_response({'filter': filter_detail})


async def get_filters(request: web.Request) -> web.Response:
    """ GET list of filters

    :Example:
        curl -X GET http://localhost:8081/foglamp/filter
    """
    try:
        storage = connect.get_storage_async()
        result = await storage.query_tbl("filters")
        filters = result["rows"]
    except StorageServerError as ex:
        _LOGGER.exception("Get filters, caught exception: %s", str(ex.error))
        raise web.HTTPInternalServerError(reason=str(ex.error))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=ex)
    else:
        return web.json_response({'filters': filters})


async def get_filter_pipeline(request: web.Request) -> web.Response:
    """ GET filter pipeline

    :Example:
        curl -X GET http://localhost:8081/foglamp/filter/<user_name>/pipeline
    """
    user_name = request.match_info.get('user_name', None)
    try:
        storage = connect.get_storage_async()
        cf_mgr = ConfigurationManager(storage)

        # Fetch the filter items: get category items
        category_info = await cf_mgr.get_category_all_items(category_name=user_name)
        if category_info is None:
            raise ValueError("No such '{}' category found.".format(user_name))

        filter_value_from_storage = json.loads(category_info['filter']['value'])
    except KeyError:
        msg = "No filter pipeline exists for {}".format(user_name)
        _LOGGER.info(msg)
        raise web.HTTPNotFound(reason=msg)
    except StorageServerError as ex:
        _LOGGER.exception("Get pipeline: %s, caught exception: %s", user_name, str(ex.error))
        raise web.HTTPInternalServerError(reason=str(ex.error))
    except ValueError as ex:
        raise web.HTTPNotFound(reason=ex)
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=ex)
    else:
        return web.json_response({'result': filter_value_from_storage})


async def delete_filter(request: web.Request) -> web.Response:
    """ DELETE filter

    :Example:
        curl -X DELETE http://localhost:8081/foglamp/filter/<filter_name>
    """
    filter_name = request.match_info.get('filter_name', None)
    try:
        storage = connect.get_storage_async()

        # Check if it is a valid plugin
        payload = PayloadBuilder().WHERE(['name', '=', filter_name]).payload()
        result = await storage.query_tbl_with_payload("filters", payload)
        if len(result["rows"]) == 0:
            raise ValueError("No such filter '{}' found".format(filter_name))

        # Check if filter exists in any pipeline
        payload = PayloadBuilder().WHERE(['name', '=', filter_name]).payload()
        result = await storage.query_tbl_with_payload("filter_users", payload)
        if len(result["rows"]) != 0:
            raise TypeError("Filter '{}' found in pipelines".format(filter_name))

        # Delete filter from filters table
        payload = PayloadBuilder().WHERE(['name', '=', filter_name]).payload()
        await storage.delete_from_tbl("filters", payload)

        # Delete configuration for filter
        await _delete_configuration_category(storage, filter_name)
    except StorageServerError as ex:
        _LOGGER.exception("Delete filter: %s, caught exception: %s", filter_name, str(ex.error))
        raise web.HTTPInternalServerError(reason=str(ex.error))
    except ValueError as ex:
        raise web.HTTPNotFound(reason=ex)
    except TypeError as ex:
        raise web.HTTPBadRequest(reason=ex)
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=ex)
    else:
        return web.json_response({'result': "Filter {} deleted successfully".format(filter_name)})


async def delete_filter_pipeline(request: web.Request) -> web.Response:
    """ DELETE filter pipeline

    :Example:
        curl -X DELETE http://localhost:8081/foglamp/filter/<user_name>/pipeline
    """
    user_name = request.match_info.get('user_name', None)
    try:
        put_url = request.url
        data = '{"pipeline": []}'
        async with aiohttp.ClientSession() as session:
            async with session.put(put_url, data=data) as resp:
                status_code = resp.status
                jdoc = await resp.text()
                if status_code not in range(200, 209):
                    _LOGGER.error("Error code: %d, reason: %s, details: %s, url: %s", resp.status, resp.reason, jdoc,
                                  put_url)
                    raise StorageServerError(code=resp.status, reason=resp.reason, error=jdoc)
    except Exception:
        raise
    else:
        return web.json_response({'result': "Filter pipeline for {} deleted successfully".format(user_name)})


async def _delete_configuration_category(storage: StorageClientAsync, key: str) -> None:
    payload = PayloadBuilder().WHERE(['key', '=', key]).payload()
    await storage.delete_from_tbl('configuration', payload)

    # Removed key from configuration cache
    config_mgr = ConfigurationManager(storage)
    config_mgr._cacheManager.remove(key)


def _diff(lst1: List[str], lst2: List[str]) -> List[str]:
    return [v for v in lst2 if v not in lst1]


def _delete_keys_from_dict(dict_del: Dict, lst_keys: List[str], deleted_values: Dict = {}, parent: str = None) \
        -> Tuple[Dict, Dict]:
    """ Delete keys from the dict and add deleted key=value pairs to deleted_values dict"""
    for k in lst_keys:
        try:
            if parent is not None:
                if dict_del['type'] == 'JSON':
                    i_val = json.loads(dict_del[k]) if isinstance(dict_del[k], str) else json.loads(json.dumps(dict_del[k]))
                else:
                    i_val = dict_del[k]
                deleted_values.update({parent: i_val})
            del dict_del[k]
        except KeyError:
            pass
    for k, v in dict_del.items():
        if isinstance(v, dict):
            parent = k
            _delete_keys_from_dict(v, lst_keys, deleted_values, parent)
    return dict_del, deleted_values


async def _delete_child_filters(storage: StorageClientAsync, cf_mgr: ConfigurationManager, user_name: str,
                                new_list: List[str], old_list: List[str] = []) -> None:
    # Difference between pipeline and value from storage lists and then delete relationship as per diff
    delete_children = _diff(new_list, old_list)
    for child in delete_children:
        try:
            filter_child_category_name = "{}_{}".format(user_name, child)
            await cf_mgr.delete_child_category(user_name, filter_child_category_name)
        except:
            pass
        await _delete_configuration_category(storage, "{}_{}".format(user_name, child))
        payload = PayloadBuilder().WHERE(['name', '=', child]).AND_WHERE(['user', '=', user_name]).payload()
        await storage.delete_from_tbl("filter_users", payload)


async def _add_child_filters(storage: StorageClientAsync, cf_mgr: ConfigurationManager, user_name: str,
                             filter_list: List[str], old_list: List[str] = []) -> None:
    # Create children categories. Since create_category() does not expect "value" key to be
    # present in the payload, we need to remove all "value" keys BUT need to add back these
    # "value" keys to the new configuration.
    for filter_name in filter_list:
        filter_config = await cf_mgr.get_category_all_items(category_name="{}_{}".format(user_name, filter_name))
        # If "username_filter" category does not exist
        if filter_config is None:
            filter_config = await cf_mgr.get_category_all_items(category_name=filter_name)

            filter_desc = "Configuration of {} filter for user {}".format(filter_name, user_name)
            new_filter_config, deleted_values = _delete_keys_from_dict(filter_config, ['value'], deleted_values={}, parent=None)
            await cf_mgr.create_category(category_name="{}_{}".format(user_name, filter_name),
                                         category_description=filter_desc,
                                         category_value=new_filter_config,
                                         keep_original_items=True)
            if deleted_values != {}:
                await cf_mgr.update_configuration_item_bulk("{}_{}".format(user_name, filter_name), deleted_values)

        # Remove cat from cache
        if filter_name in cf_mgr._cacheManager.cache:
            cf_mgr._cacheManager.remove(filter_name)

    # Create children categories in category_children table
    children = ["{}_{}".format(user_name, _filter) for _filter in filter_list]
    await cf_mgr.create_child_category(category_name=user_name, children=children)
    # Add entries to filter_users table
    new_added = _diff(old_list, filter_list)
    for filter_name in new_added:
        payload = PayloadBuilder().INSERT(name=filter_name, user=user_name).payload()
        await storage.insert_into_tbl("filter_users", payload)
