# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import json
import copy
from aiohttp import web
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.services.core import connect
from foglamp.services.core.api import utils as apiutils
from foglamp.common import logger

__author__ = "Massimiliano Pinto"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    ---------------------------------------------------------------------------
    | POST            | /foglamp/filter                                       |
    | PUT             | /foglamp/filter/{service_name}/pipeline               |
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

    'name' is the filter name
    'plugin' is the filter plugin name

    The plugin is loaded and default config from 'plugin_info'
    is fetched.

    A new config category 'name' is created:
    items are:
       - 'plugin'
       - all items from default plugin config

    NOTE: The 'create_category' call is made with keep_original_items = True

    """
    try:
        # Get inpout data
        data = await request.json()
        # Get filter name
        filter_name = data.get('name', None)
        # Get plugin name
        plugin_name = data.get('plugin', None)

        # Check we have needed input data
        if not filter_name or not plugin_name:
            return web.HTTPBadRequest(reason='Filter name or plugin name are required.')

        # Set filter description
        filter_desc = 'Configuration of \'' + filter_name + '\' filter for plugin \'' + plugin_name + '\''
        # Get configuration manager instance
        cf_mgr = ConfigurationManager(connect.get_storage_async())
        # Load the specified plugin and get plugin data
        loaded_plugin_info = apiutils.get_plugin_info(plugin_name)
        # Get plugin default configuration (dict)
        if not loaded_plugin_info or 'config' not in loaded_plugin_info:
            message = "Can not get 'plugin_info' detail from plugin '%s'" % plugin_name
            _LOGGER.exception("Add filter error: " + message)
            return web.HTTPNotFound(reason=message)
            
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
            return web.HTTPBadRequest(reason=message)

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
                                     category_value=plugin_config)

        # Fetch the new created filter: get category items
        category_info = await cf_mgr.get_category_all_items(category_name=filter_name)
        if category_info is None:
            message = "No such '%s' filter found" % filter_name
            raise ValueError(message)
        else:
            # Success: return new filter content
            return web.json_response({'filter': filter_name,
                                      'description': filter_desc,
                                      'value': category_info})

    except ValueError as ex:
        _LOGGER.exception("Add filter, caught exception: " + str(ex))
        raise web.HTTPNotFound(reason=str(ex))
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
    - append_filter=true|false       Default true
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
             return web.HTTPBadRequest(reason='Service name is required')

        # Empty list [] is allowed as it clears the pipeline
        # curl -X PUT http://localhost:8081/foglamp/filter/ServiceName/pipeline -d '{"pipeline": []}'
        # Check filter_list is alist only if filter_list in not None
        if filter_list is not None and not isinstance(filter_list, list):
             return web.HTTPBadRequest(reason='Pipeline must be a list of filters or an empty value')

        # Get configuration manager instance
        cf_mgr = ConfigurationManager(connect.get_storage_async())

        # Fetch the filter items: get category items
        category_info = await cf_mgr.get_category_all_items(category_name=service_name)
        if category_info is None:
            # Error service__name doesn't exist
            message = "No such '%s' category found." % service_name
            return web.HTTPNotFound(reason=message)

        # Check whether config_item already exists
        if config_item in category_info:
            # We just need to update the value of config_item
            # with the "pipeline" property
            # Check whether we want to replace or update the list
            # or we allow duplicate entries in the list
            # Default: append and allow duplicates
            append_filter = 'true'
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
                    if allow_duplicates == 'true' or (_filter not in current_value['pipeline']):
                        # Add the new filter to new_list
                        new_list.append(_filter)
            else:
                # Overwriting the list: use input list
                new_list = filter_list

            # Set the pipeline value with the 'new_list' of filters
            await cf_mgr.set_category_item_value_entry(service_name,
                                                       config_item,
                                                       {'pipeline': new_list})
        else:
            # Create new item 'config_item'
            new_item = dict({config_item: {
                'description': 'Filter pipeline',
                'type': 'JSON',
                'default': {}
            }
            })

            # Add the "pipeline" array as a string
            new_item[config_item]['default'] = json.dumps({'pipeline': filter_list})

            # Update the filter category entry
            await cf_mgr.create_category(category_name=service_name,
                                         category_value=new_item,
                                         keep_original_items=True)

        # Fetch up-to-date category items
        result = await cf_mgr.get_category_item(service_name, config_item)
        if result is None:
            # Error config_item doesn't exist
            message = "No detail found for the category_name: {} " \
                      "and config_item: {}".format(service_name, config_item)
            return web.HTTPNotFound(reason=message)

        else:
            # Add filters as child categories of parent category name
            await cf_mgr.create_child_category(service_name, filter_list)

            # Return the filters pipeline 
            return web.json_response(json.loads(result['value']))

    except ValueError as ex:
        _LOGGER.exception("Add filters pipeline, caught exception: " + str(ex))
        raise web.HTTPNotFound(reason=str(ex))
    except Exception as ex:
        _LOGGER.exception("Add filters pipeline, caught exception: " + str(ex))
        raise web.HTTPInternalServerError(reason=str(ex))
