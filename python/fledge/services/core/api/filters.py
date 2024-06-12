# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import json
import copy
import aiohttp
from aiohttp import web
from typing import List, Dict, Tuple

from fledge.common import utils
from fledge.common.common import _FLEDGE_ROOT
from fledge.common.configuration_manager import ConfigurationManager
from fledge.common.logger import FLCoreLogger
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.common.storage_client.exceptions import StorageServerError
from fledge.common.storage_client.storage_client import StorageClientAsync

from fledge.services.core import connect
from fledge.services.core.api import utils as apiutils
from fledge.services.core.api.plugins import common

__author__ = "Massimiliano Pinto, Amarendra K Sinha"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    ---------------------------------------------------------------------------
    | POST GET        | /fledge/filter                                       |
    | PUT GET DELETE  | /fledge/filter/{user_name}/pipeline                  |
    | GET DELETE      | /fledge/filter/{filter_name}                         |
    ---------------------------------------------------------------------------
"""
_LOGGER = FLCoreLogger().get_logger(__name__)


async def create_filter(request: web.Request) -> web.Response:
    """
    Create a new filter with a specific plugin
    :Example:
     curl -X POST http://localhost:8081/fledge/filter -d '{"name": "North_Readings_to_PI_scale_stage_1Filter", "plugin": "scale"}'
     curl -X POST http://localhost:8081/fledge/filter -d '{"name": "North_Readings_to_PI_scale_stage_1Filter", "plugin": "scale", "filter_config": {"offset":"1","enable":"true"}}'

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

        # Load C/Python filter plugin info
        try:
            # Try fetching Python filter
            plugin_module_path = "{}/python/fledge/plugins/filter/{}".format(_FLEDGE_ROOT, plugin_name)
            loaded_plugin_info = common.load_and_fetch_python_plugin_info(plugin_module_path, plugin_name, "filter")
        except FileNotFoundError as ex:
            # Load C filter plugin
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
            raise ValueError("No such '{}' filter found.".format(filter_name))
        else:
            return web.json_response({'filter': filter_name, 'description': filter_desc, 'value': category_info})
    except ValueError as err:
        msg = str(err)
        raise web.HTTPNotFound(reason=msg)
    except TypeError as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=msg)
    except StorageServerError as ex:
        msg = ex.error
        await _delete_configuration_category(storage, filter_name)  # Revert configuration entry
        _LOGGER.exception("Failed to create filter with: {}".format(msg))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        _LOGGER.error(ex, "Add filter failed.")
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))


async def add_filters_pipeline(request: web.Request) -> web.Response:
    """
    Add filter names to "filter" item in {user_name}

    PUT /fledge/filter/{user_name}/pipeline

    'pipeline' is the array of filter category names to set
    into 'filter' default/value properties

    :Example: set 'pipeline' for user 'NorthReadings_to_PI'
    curl -X PUT http://localhost:8081/fledge/filter/NorthReadings_to_PI/pipeline -d '["Scale10Filter", "Python_assetCodeFilter"]'

    Configuration item 'filter' is added to {user_name}
    or updated with the pipeline list

    Returns the filter pipeline on success:
    {"pipeline": ["Scale10Filter", "Python_assetCodeFilter"]}

    Query string parameters:
    - append_filter=true|false       Default false
    - allow_duplicates=true|false    Default true

    :Example:
    curl -X PUT http://localhost:8081/fledge/filter/NorthReadings_to_PI/pipeline?append_filter=true|false -d
    '{
        "pipeline": ["Scale10Filter", "Python_assetCodeFilter"],
    }'
    curl -X PUT http://localhost:8081/fledge/filter/NorthReadings_to_PI/pipeline?allow_duplicates=true|false -d
    '{
        "pipeline": ["Scale10Filter", "Python_assetCodeFilter"],
    }'
    curl -X PUT 'http://localhost:8081/fledge/filter/NorthReadings_to_PI/pipeline?append_filters=true&allow_duplicates=true|false' -d
    '{
        "pipeline": ["Scale10Filter", "Python_assetCodeFilter"],
    }'

    Delete pipeline:
    curl -X PUT -d '{"pipeline": []}' http://localhost:8081/fledge/filter/NorthReadings_to_PI/pipeline

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

        async def _get_filter(f_name):
            payload = PayloadBuilder().WHERE(['name', '=', f_name]).payload()
            f_result = await storage.query_tbl_with_payload("filters", payload)
            if len(f_result["rows"]) == 0:
                raise ValueError("No such '{}' filter found in filters table.".format(f_name))

        # Check and validate if all filters in the list exists in filters table
        for _filter in filter_list:
            if isinstance(_filter, list):
                for f in _filter:
                    await _get_filter(f)
            else:
                await _get_filter(_filter)
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
            new_item = dict(
                {config_item: {'description': 'Filter pipeline', 'type': 'JSON', 'default': {}, 'readonly': 'true'}})
            new_item[config_item]['default'] = json.dumps({'pipeline': filter_list})
            await _add_child_filters(storage, cf_mgr, user_name, filter_list)
            await cf_mgr.create_category(category_name=user_name, category_value=new_item, keep_original_items=True)

        # Fetch up-to-date category item
        result = await cf_mgr.get_category_item(user_name, config_item)
        if result is None:
            message = "No detail found for user: {} and filter: {}".format(user_name, config_item)
            raise ValueError(message)
        else:
            # Create Parent-child relation for standalone filter category with service/username
            # And that way we have the ability to remove the category when we delete the service
            f_c = []
            f_c2 = []
            for _filter in filter_list:
                if isinstance(_filter, list):
                    for f in _filter:
                        f_c.append(f)
                else:
                    f_c2.append(_filter)
                if f_c:
                    await cf_mgr.create_child_category(user_name, f_c)
                if f_c2:
                    await cf_mgr.create_child_category(user_name, f_c2)
            return web.json_response(
                {'result': "Filter pipeline {} updated successfully".format(json.loads(result['value']))})
    except ValueError as err:
        msg = str(err)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except TypeError as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except StorageServerError as e:
        msg = e.error
        _LOGGER.exception("Add filters pipeline, caught storage error: {}".format(msg))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        _LOGGER.error(ex, "Add filters pipeline failed.")
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))


async def get_filter(request: web.Request) -> web.Response:
    """ GET filter detail

    :Example:
        curl -X GET http://localhost:8081/fledge/filter/<filter_name>
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
        msg = ex.error
        _LOGGER.exception("Failed to get filter name: {}. Storage error occurred: {}".format(filter_name, msg))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    except ValueError as err:
        raise web.HTTPNotFound(reason=str(err))
    except TypeError as err:
        raise web.HTTPBadRequest(reason=str(err))
    except Exception as ex:
        msg = str(ex)
        _LOGGER.error(ex, "Get {} filter failed.".format(filter_name))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({'filter': filter_detail})


async def get_filters(request: web.Request) -> web.Response:
    """ GET list of filters

    :Example:
        curl -X GET http://localhost:8081/fledge/filter
    """
    try:
        storage = connect.get_storage_async()
        result = await storage.query_tbl("filters")
        filters = result["rows"]
    except StorageServerError as ex:
        msg = ex.error
        _LOGGER.exception("Get all filters, caught storage exception: {}".format(msg))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        _LOGGER.error(ex, "Get all filters failed.")
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({'filters': filters})


async def get_filter_pipeline(request: web.Request) -> web.Response:
    """ GET filter pipeline

    :Example:
        curl -X GET http://localhost:8081/fledge/filter/<user_name>/pipeline
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
        msg = "No filter pipeline exists for {}.".format(user_name)
        raise web.HTTPNotFound(reason=msg)
    except StorageServerError as ex:
        msg = ex.error
        _LOGGER.exception("Failed to delete filter pipeline {}. Storage error occurred: {}".format(user_name, msg))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    except ValueError as err:
        raise web.HTTPNotFound(reason=str(err))
    except Exception as ex:
        msg = str(ex)
        _LOGGER.error(ex, "Get filter pipeline failed.")
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({'result': filter_value_from_storage})


async def delete_filter(request: web.Request) -> web.Response:
    """ DELETE filter

    :Example:
        curl -X DELETE http://localhost:8081/fledge/filter/<filter_name>
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

        # Update deprecated timestamp in asset_tracker
        """
        TODO: FOGL-6749
        Once rows affected with 0 case handled at Storage side
        then we will need to update the query with AND_WHERE(['deprecated_ts', 'isnull'])
        At the moment deprecated_ts is updated even in notnull case.
        Also added SELECT query before UPDATE to avoid BadCase when there is no asset track entry exists for the filter.
        This should also be removed when given JIRA is fixed.
        """
        select_payload = PayloadBuilder().SELECT("deprecated_ts").WHERE(['plugin', '=', filter_name]).payload()
        get_result = await storage.query_tbl_with_payload('asset_tracker', select_payload)
        if 'rows' in get_result:
            response = get_result['rows']
            if response:
                # AND_WHERE(['deprecated_ts', 'isnull']) once FOGL-6749 is done
                current_time = utils.local_timestamp()
                update_payload = PayloadBuilder().SET(deprecated_ts=current_time).WHERE(
                    ['plugin', '=', filter_name]).payload()
                await storage.update_tbl("asset_tracker", update_payload)
    except StorageServerError as ex:
        msg = ex.error
        _LOGGER.exception("Delete {} filter, caught storage exception: {}".format(filter_name, msg))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    except ValueError as err:
        raise web.HTTPNotFound(reason=str(err))
    except TypeError as err:
        raise web.HTTPBadRequest(reason=str(err))
    except Exception as ex:
        msg = str(ex)
        _LOGGER.error(ex, "Delete {} filter failed.".format(filter_name))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({'result': "Filter {} deleted successfully.".format(filter_name)})


async def delete_filter_pipeline(request: web.Request) -> web.Response:
    """ DELETE filter pipeline

    :Example:
        curl -X DELETE http://localhost:8081/fledge/filter/<user_name>/pipeline
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
                    _LOGGER.error("Delete {} filter pipeline; Error code: {}, reason: {}, details: {}, url: {}"
                                  "".format(user_name, resp.status, resp.reason, jdoc, put_url))
                    raise StorageServerError(code=resp.status, reason=resp.reason, error=jdoc)
    except Exception:
        raise
    else:
        return web.json_response({'result': "Filter pipeline for {} deleted successfully".format(user_name)})


async def _delete_configuration_category(storage: StorageClientAsync, key: str) -> None:
    payload = PayloadBuilder().WHERE(['key', '=', key]).payload()
    await storage.delete_from_tbl('configuration', payload)

    # Removed category from configuration cache and other related stuff e.g. script files
    config_mgr = ConfigurationManager(storage)
    config_mgr.delete_category_related_things(key)
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
                    i_val = json.loads(dict_del[k]) if isinstance(dict_del[k], str) else json.loads(
                        json.dumps(dict_del[k]))
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
    async def _delete_relationship(cat_name):
        try:
            filter_child_category_name = "{}_{}".format(user_name, cat_name)
            await cf_mgr.delete_child_category(user_name, filter_child_category_name)
            await cf_mgr.delete_child_category("{} Filters".format(user_name), filter_child_category_name)
        except:
            pass
        await _delete_configuration_category(storage, "{}_{}".format(user_name, cat_name))
        payload = PayloadBuilder().WHERE(['name', '=', cat_name]).AND_WHERE(['user', '=', user_name]).payload()
        await storage.delete_from_tbl("filter_users", payload)

    for child in delete_children:
        if isinstance(child, list):
            for c in child:
                await _delete_relationship(c)
        else:
            await _delete_relationship(child)

async def _add_child_filters(storage: StorageClientAsync, cf_mgr: ConfigurationManager, user_name: str,
                             filter_list: List[str], old_list: List[str] = []) -> None:
    # Create children categories. Since create_category() does not expect "value" key to be
    # present in the payload, we need to remove all "value" keys BUT need to add back these
    # "value" keys to the new configuration.

    async def _create_filter_category(filter_cat_name):
        filter_config = await cf_mgr.get_category_all_items(category_name="{}_{}".format(
            user_name, filter_cat_name))
        # If "username_filter" category does not exist
        if filter_config is None:
            filter_config = await cf_mgr.get_category_all_items(category_name=filter_cat_name)

            filter_desc = "Configuration of {} filter for user {}".format(filter_cat_name, user_name)
            new_filter_config, deleted_values = _delete_keys_from_dict(filter_config, ['value'],
                                                                       deleted_values={}, parent=None)
            await cf_mgr.create_category(category_name="{}_{}".format(user_name, filter_cat_name),
                                         category_description=filter_desc,
                                         category_value=new_filter_config,
                                         keep_original_items=True)
            if deleted_values != {}:
                await cf_mgr.update_configuration_item_bulk("{}_{}".format(
                    user_name, filter_cat_name), deleted_values)

        # Remove cat from cache
        if filter_cat_name in cf_mgr._cacheManager.cache:
            cf_mgr._cacheManager.remove(filter_cat_name)

    # Create filter category
    for _fn in filter_list:
        if isinstance(_fn, list):
            for f in _fn:
                await _create_filter_category(f)
        else:
            await _create_filter_category(_fn)

    # Create children categories in category_children table
    children = []
    for _filter in filter_list:
        if isinstance(_filter, list):
            for f in _filter:
                child_cat_name = "{}_{}".format(user_name, f)
                children.append(child_cat_name)
        else:
            child_cat_name = "{}_{}".format(user_name, _filter)
            children.append(child_cat_name)
        await cf_mgr.create_child_category(category_name=user_name, children=children)
    # Add entries to filter_users table
    new_added = _diff(old_list, filter_list)
    for filter_name in new_added:
        payload = None
        if isinstance(filter_name, list):
            for f in filter_name:
                payload = PayloadBuilder().INSERT(name=f, user=user_name).payload()
        else:
            payload = PayloadBuilder().INSERT(name=filter_name, user=user_name).payload()
        if payload is not None:
            await storage.insert_into_tbl("filter_users", payload)
