# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import json
import copy
import aiohttp
from aiohttp import web

from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.services.core import connect
from foglamp.services.core.api import utils as apiutils
from foglamp.common import logger
from foglamp.common.storage_client.payload_builder import PayloadBuilder
from foglamp.common.storage_client.exceptions import StorageServerError

__author__ = "Massimiliano Pinto, Amarendra K Sinha"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    ---------------------------------------------------------------------------
    | POST            | /foglamp/filter                                       |
    | PUT             | /foglamp/filter/{service_name}/pipeline               |
    | GET             | /foglamp/filter/{service_name}/pipeline               |
    | GET             | /foglamp/filter/{filter_name}                         |
    | GET             | /foglamp/filter                                       |
    | DELETE          | /foglamp/filter/{service_name}/pipeline               |
    | DELETE          | /foglamp/filter/{filter_name}                         |
    ---------------------------------------------------------------------------
"""

_LOGGER = logger.setup("filter")


async def create_filter(request):
    """
    Create a new filter with a specific plugin
    
    :Example:
     curl -X POST http://localhost:8081/foglamp/filter -d 
     '{
        "name": "North_Readings_to_PI_scale_stage_1Filter",
        "plugin": "scale"
     }'

     curl -X POST http://localhost:8081/foglamp/filter -d 
     '{
        "name": "North_Readings_to_PI_scale_stage_1Filter",
        "plugin": "scale",
        "filter_config": {}
     }'

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
        # Get input data
        data = await request.json()
        # Get filter name
        filter_name = data.get('name', None)
        # Get plugin name
        plugin_name = data.get('plugin', None)
        filter_config = data.get('filter_config', {})

        # Check we have needed input data
        if not filter_name or not plugin_name:
            raise web.HTTPBadRequest(reason='Filter name or plugin name are required.')

        # Set filter description
        filter_desc = 'Configuration of \'' + filter_name + '\' filter for plugin \'' + plugin_name + '\''
        # Get configuration manager instance
        storage = connect.get_storage_async()
        cf_mgr = ConfigurationManager(storage)
        # Load the specified plugin and get plugin data
        loaded_plugin_info = apiutils.get_plugin_info(plugin_name)

        # Get plugin default configuration (dict)
        if not loaded_plugin_info or 'config' not in loaded_plugin_info:
            message = "Can not get 'plugin_info' detail from plugin '%s'" % plugin_name
            _LOGGER.exception("Add filter error: " + message)
            raise web.HTTPNotFound(reason=message)
            
        plugin_config = loaded_plugin_info['config']
        # Get plugin type (string)
        loaded_plugin_type = loaded_plugin_info['type']
        # Get plugin name (string)
        loaded_plugin_name = plugin_config['plugin']['default']

        # Check first whether filter name already exists
        category_info = await cf_mgr.get_category_all_items(category_name=filter_name)
        if category_info is not None:
            # Filter name already exists: return error
            message = "Filter '%s' already exists." % filter_name
            raise web.HTTPBadRequest(reason=message)

        # Sanity checks
        if plugin_name != loaded_plugin_name or loaded_plugin_type != 'filter':
            error_message = "Loaded plugin '{0}', type '{1}', doesn't match " + \
                            "the specified one '{2}', type 'filter'"
            raise ValueError(error_message.format(loaded_plugin_name,
                                                  loaded_plugin_type,
                                                  plugin_name))

        #################################################
        # Set string value for 'default' if type is JSON
        # This is required by the configuration manager
        ################################################# 
        for key, value in plugin_config.items():
            if value['type'] == 'JSON':
                value['default'] = json.dumps(value['default'])

        await cf_mgr.create_category(category_name=filter_name,
                                     category_description=filter_desc,
                                     category_value=plugin_config,
                                     keep_original_items=True)

        # If filter_config is in POST data, then update the value for each config item
        if filter_config is not None:
            if not isinstance(filter_config, dict):
                raise ValueError('filter_config must be a JSON object')
            for k, v in filter_config.items():
                await cf_mgr.set_category_item_value_entry(filter_name, k, v['value'])

        # Create entry in filters table
        payload = PayloadBuilder().INSERT(name=filter_name, plugin=plugin_name).payload()
        await storage.insert_into_tbl("filters", payload)

        # Fetch the new created filter: get category items
        category_info = await cf_mgr.get_category_all_items(category_name=filter_name)
        if category_info is None:
            message = "No such '%s' filter found" % filter_name
            raise ValueError(message)
        else:
            # Success: return new filter content
            return web.json_response({'result': "Filter {} created successfully".format({'filter': filter_name,
                                      'description': filter_desc,
                                      'value': category_info})})
    except ValueError as ex:
        _LOGGER.exception("Add filter, caught exception: " + str(ex))
        raise web.HTTPNotFound(reason=str(ex))
    except StorageServerError as ex:
        await _delete_configuration_category(storage, filter_name)  # Revert configuration entry
        _LOGGER.exception("Failed to create schedule. %s", ex.error)
        raise web.HTTPInternalServerError(reason='Failed to create service.')
    except Exception as ex:
        _LOGGER.exception("Add filter, caught exception: " + str(ex))
        raise web.HTTPInternalServerError(reason=str(ex))


async def add_filters_pipeline(request):
    """
    Add filter names to "filter" item in {service_name}

    PUT /foglamp/filter/{service_name}/pipeline
 
    'pipeline' is the array of filter category names to set
    into 'filter' default/value properties

    :Example: set 'pipeline' for service 'NorthReadings_to_PI'
    curl -X PUT http://localhost:8081/foglamp/filter/NorthReadings_to_PI/pipeline -d 
    '{
        "pipeline": ["Scale10Filter", "Python_assetCodeFilter"],
    }'

    Configuration item 'filter' is added to {service_name}
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
    parent category {service_name}
    """
    try:
        # Get inout data
        data = await request.json()
        # Get filters list
        filter_list = data.get('pipeline', None)
        # Get filter name
        service_name = request.match_info.get('service_name', None)
        # Item name to add/update
        config_item = "filter"

        # Check input data
        if not service_name:
            raise web.HTTPBadRequest(reason='Service name is required')

        # Empty list [] is allowed as it clears the pipeline
        # curl -X PUT http://localhost:8081/foglamp/filter/ServiceName/pipeline -d '{"pipeline": []}'
        # Check filter_list is a list only if filter_list in not None
        if filter_list is not None and not isinstance(filter_list, list):
            raise web.HTTPBadRequest(reason='Pipeline must be a list of filters or an empty value')

        # Get configuration manager instance
        storage = connect.get_storage_async()
        cf_mgr = ConfigurationManager(storage)

        # Fetch the filter items: get category items
        category_info = await cf_mgr.get_category_all_items(category_name=service_name)
        if category_info is None:
            # Error service__name doesn't exist
            message = "No such '%s' category found." % service_name
            raise web.HTTPNotFound(reason=message)

        # Check whether config_item already exists
        if config_item in category_info:
            # We just need to update the value of config_item
            # with the "pipeline" property
            # Check whether we want to replace or update the list
            # or we allow duplicate entries in the list
            # Default: append and allow duplicates
            append_filter = 'false'
            allow_duplicates = 'true'
            if 'append_filter' in request.query and request.query['append_filter'] != '':
                append_filter = request.query['append_filter'].lower()
                if append_filter not in ['true', 'false']:
                    raise ValueError("Only 'true' and 'false' are allowed for "
                                     "append_filter. {} given.".format(append_filter))
            if 'allow_duplicates' in request.query and request.query['allow_duplicates'] != '':
                allow_duplicates = request.query['allow_duplicates'].lower()
                if allow_duplicates not in ['true', 'false']:
                    raise ValueError("Only 'true' and 'false' are allowed for "
                                     "allow_duplicates. {} given.".format(allow_duplicates))

            # If filter list is empty don't check current list value
            # Empty list [] clears current pipeline
            if append_filter == 'true' and filter_list:
                # 'value' holds the string version of a list: convert it first  
                current_value = json.loads(category_info[config_item]['value'])
                # Save current list (deepcopy)
                new_list = copy.deepcopy(current_value['pipeline'])
                # iterate inout filters list
                for _filter in filter_list:
                    # Check whether we need to add this filter
                    if allow_duplicates == 'true' or _filter not in current_value['pipeline']:
                        # Add the new filter to new_list
                        new_list.append(_filter)
            else:
                # Overwriting the list: use input list
                new_list = filter_list

            filter_value_from_storage = json.loads(category_info['filter']['value'])

            def diff(lst1, lst2):
                return [v for v in lst2 if v not in lst1]

            def new_items(lst1, lst2):
                return [v for v in lst1 if v not in lst2]

            # Difference b/w two(pipeline and value from storage) lists and then delete relationship as per diff
            delete_children = diff(new_list, filter_value_from_storage['pipeline'])
            for l in delete_children:
                await cf_mgr.delete_child_category(service_name, l)
                # Delete entries in filter_users table
                payload = PayloadBuilder().WHERE(['name', '=', l]).AND_WHERE(['user', '=', service_name]).payload()
                await storage.delete_from_tbl("filter_users", payload)

            # Set the pipeline value with the 'new_list' of filters
            await cf_mgr.set_category_item_value_entry(service_name,
                                                       config_item,
                                                       {'pipeline': new_list})
            # Create new entries in filter_users table
            new_added = new_items(new_list, filter_value_from_storage['pipeline'])
            for filter_name in new_added:
                payload = PayloadBuilder().INSERT(name=filter_name, user=service_name).payload()
                await storage.insert_into_tbl("filter_users", payload)
        else:
            # Create new item 'config_item'
            new_item = dict({config_item: {
                'description': 'Filter pipeline',
                'type': 'JSON',
                'default': '{}'
            }
            })
            # Add the "pipeline" array as a string
            new_item[config_item]['default'] = json.dumps({'pipeline': filter_list})
            # Update the filter category entry
            await cf_mgr.create_category(category_name=service_name,
                                         category_value=new_item,
                                         keep_original_items=True)
            # Create entries in filter_users table
            for filter_name in filter_list:
                payload = PayloadBuilder().INSERT(name=filter_name, user=service_name).payload()
                await storage.insert_into_tbl("filter_users", payload)


        # Fetch up-to-date category items
        result = await cf_mgr.get_category_item(service_name, config_item)
        if result is None:
            # Error config_item doesn't exist
            message = "No detail found for the category_name: {} " \
                      "and config_item: {}".format(service_name, config_item)
            raise web.HTTPNotFound(reason=message)

        else:
            # Add filters as child categories of parent category name
            await cf_mgr.create_child_category(service_name, filter_list)

            # Return the filters pipeline 
            return web.json_response({'result': "Filter pipeline {} created successfully".format(json.loads(result['value']))})
    except ValueError as ex:
        _LOGGER.exception("Add filters pipeline, caught exception: " + str(ex))
        raise web.HTTPNotFound(reason=str(ex))
    except StorageServerError as ex:
        _LOGGER.exception("Add filters pipeline, caught exception: " + str(ex))
        raise web.HTTPInternalServerError(reason=str(ex))
    except Exception as ex:
        _LOGGER.exception("Add filters pipeline, caught exception: " + str(ex))
        raise web.HTTPInternalServerError(reason=str(ex))


async def get_filter(request):
    """ GET filter detail

    :Example:
        curl -X GET http://localhost:8081/foglamp/filter/<filter_name>
    """
    filter_name = request.match_info.get('filter_name', None)
    try:
        storage = connect.get_storage_async()
        filter_detail = {}

        # Fetch filter detail
        payload = PayloadBuilder().WHERE(['name', '=', filter_name]).payload()
        result = await storage.query_tbl_with_payload("filters", payload)
        if len(result["rows"]) == 0:
            raise web.HTTPNotFound(reason="No such filter '{}' found".format(filter_name))
        row = result["rows"][0]
        filter_detail.update({"name": row["name"], "plugin": row["plugin"]})

        # Fetch service names which are using this filter
        payload = PayloadBuilder().WHERE(['name', '=', filter_name]).payload()
        result = await storage.query_tbl_with_payload("filter_users", payload)
        users = []
        for row in result["rows"]:
            users.append(row["user"])
        filter_detail.update({"users": users})
    except StorageServerError as ex:
        _LOGGER.exception("Get filter: {}, caught exception: ".format(filter_name) + str(ex))
        raise web.HTTPInternalServerError(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=ex)
    else:
        return web.json_response({'filter': filter_detail})


async def get_filters(request):
    """ GET list of filters

    :Example:
        curl -X GET http://localhost:8081/foglamp/filter
    """
    try:
        storage = connect.get_storage_async()
        result = await storage.query_tbl("filters")
        filters = result["rows"]
    except StorageServerError as ex:
        _LOGGER.exception("Get filters, caught exception: " + str(ex))
        raise web.HTTPInternalServerError(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=ex)
    else:
        return web.json_response({'filters': filters})


async def get_filter_pipeline(request):
    """ GET filter pipeline

    :Example:
        curl -X GET http://localhost:8081/foglamp/filter/<service_name>/pipeline
    """
    service_name = request.match_info.get('service_name', None)
    if service_name is None:
        raise web.HTTPNotFound(reason="Service name name is required.")
    try:
        storage = connect.get_storage_async()
        cf_mgr = ConfigurationManager(storage)

        # Fetch the filter items: get category items
        category_info = await cf_mgr.get_category_all_items(category_name=service_name)
        if category_info is None:
            # Error service__name doesn't exist
            message = "No such '%s' category found." % service_name
            return web.HTTPNotFound(reason=message)

        filter_value_from_storage = json.loads(category_info['filter']['value'])
    except KeyError as ex:
        _LOGGER.exception("Get pipeline: {}, no filter exists: ".format(service_name) + str(ex))
        raise web.HTTPNotFound(reason="Get pipeline: {}, no filter exists: ".format(service_name) + str(ex))
    except StorageServerError as ex:
        _LOGGER.exception("Get pipeline: {}, caught exception: ".format(service_name) + str(ex))
        raise web.HTTPInternalServerError(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=ex)
    else:
        return web.json_response({'result': filter_value_from_storage})


async def delete_filter(request):
    """ DELETE filter

    :Example:
        curl -X DELETE http://localhost:8081/foglamp/filter/<filter_name>
    """
    filter_name = request.match_info.get('filter_name', None)
    if filter_name is None:
        raise web.HTTPNotFound(reason="Filter name is required.")
    try:
        storage = connect.get_storage_async()

        # Check if it is a valid plugin
        payload = PayloadBuilder().WHERE(['name', '=', filter_name]).payload()
        result = await storage.query_tbl_with_payload("filters", payload)
        if len(result["rows"]) == 0:
            raise web.HTTPNotFound(reason="No such filter '{}' found".format(filter_name))

        # Check if filter exists in any pipeline
        payload = PayloadBuilder().WHERE(['name', '=', filter_name]).payload()
        result = await storage.query_tbl_with_payload("filter_users", payload)
        if len(result["rows"]) != 0:
            raise web.HTTPBadRequest(reason="Filter '{}' found in pipelines".format(filter_name))

        # Delete filter from filters table
        payload = PayloadBuilder().WHERE(['name', '=', filter_name]).payload()
        await storage.delete_from_tbl("filters", payload)

        # Delete configuration for filter
        _delete_configuration_category(storage, filter_name)
    except StorageServerError as ex:
        _LOGGER.exception("Get filter: {}, caught exception: ".format(filter_name) + str(ex))
        raise web.HTTPInternalServerError(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=ex)
    else:
        return web.json_response({'result': "Filter {} deleted successfully".format(filter_name)})


async def delete_filter_pipeline(request):
    """ DELETE filter pipeline

    :Example:
        curl -X DELETE http://localhost:8081/foglamp/filter/<service_name>/pipeline
    """
    service_name = request.match_info.get('service_name', None)
    if service_name is None:
        raise web.HTTPNotFound(reason="Service name is required.")
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
        return web.json_response({'result': "Filter pipline for service {} deleted successfully".format(service_name)})


async def _delete_configuration_category(storage, key):
    payload = PayloadBuilder().WHERE(['key', '=', key]).payload()
    await storage.delete_from_tbl('configuration', payload)

    # Removed key from configuration cache
    config_mgr = ConfigurationManager(storage)
    config_mgr._cacheManager.remove(key)
