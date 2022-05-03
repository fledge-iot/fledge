# -*- coding: utf-8 -*-
# FOGLAMP_BEGIN
# See: https://foglamp-foglamp-documentation.readthedocs-hosted.com
# FOGLAMP_END

""" Plugin module which adds a square block of specific monochrome shade on images """

import os
import logging
import datetime
import filter_ingest
import traceback
import copy
import json 
import numpy as np

from fledge.common import logger

# local logger
_LOGGER = logger.setup(__name__, level=logging.DEBUG)


_DEFAULT_CONFIG = {
    'plugin': {        # mandatory  filter
        'description': 'Filter that overlays a square block on image',
        'type': 'string',
        'default': 'imageblock',
        'readonly': 'true'
    },
    'enable': {    # recommended filter
        'description': 'Enable imageblock filter plugin',
        'type': 'boolean',
        'default': 'false',
        'displayName': 'Enabled',
        'order': "1"
    },
    'block_color': {
        'description': 'Block color (0-255)',
        'type': 'integer',
        'default': '255',
        'displayName': 'Block color',
        'order': '2'
    }
}


def plugin_info():
    """ Returns information about the plugin.
    Args:
    Returns:
        dict: plugin information
    Raises:
    """
    _LOGGER.info("imageblock - plugin_info called")
    return {
        'name': 'imageblock',
        'version': '1.9.2',
        'mode': 'none',
        'type': 'filter',
        'interface': '1.0',
        'config': _DEFAULT_CONFIG
    }


def plugin_init(config, ingest_ref, callback):
    """ Initialise the plugin.
    Args:
        config: JSON configuration document for the plugin configuration category
    Returns:
        data: JSON object to be used in future calls to the plugin
    Raises:
    """

    _LOGGER.info("imageblock - plugin_init called")
    try:
        _config = copy.deepcopy(config)
        _config['ingest_ref'] = ingest_ref
        _config['callback'] = callback
    except:
        _LOGGER.info("could not create configuration")
        raise
    return _config


def plugin_ingest(handle, data):
    """ plugin_ingest -- log data we receive """

    if handle['enable']['value'] == 'false':
        _LOGGER.debug("imageblock - plugin_ingest: enable=FALSE, not processing data, forwarding received data")
        filter_ingest.filter_ingest_callback(handle['callback'], handle['ingest_ref'], data)
        return

    _LOGGER.debug("imageblock - plugin_ingest: INPUT: type(data)={}, data={}".format(type(data), data))
    color = int(handle['block_color']['value'])
    
    try:
        
        if type(data) == dict:
            data = [data]

        for entry in data:
            _LOGGER.debug("np.pi={}, type(entry) = {}".format(np.pi, type(entry)))

            for k in entry['readings'].keys():
                v = entry['readings'][k]
                _LOGGER.debug("k={}, type(v)={}, v.shape={}, v={}".format(k, type(v), v.shape, v))
                
                import random
                center = random.randint(v.shape[0]//4,v.shape[0]//4*3+1)
                sz = random.randint(10,v.shape[0]//4-10)
                _LOGGER.debug("imageblock - plugin_ingest: center={}, sz={}, color={}".format(center, sz, color))
                v[center-sz:center+sz,center-sz:center+sz] = color
                entry['readings'][k] = v
        
        _LOGGER.debug("After adding a small block, pixel values: OUTPUT: data={}".format(data))

        filter_ingest.filter_ingest_callback(handle['callback'], handle['ingest_ref'], data)

    except Exception as ex:
        _LOGGER.error("imageblock writer exception {}".format(traceback.format_exc()))
        raise


def plugin_reconfigure(handle, new_config):
    """ Reconfigures the plugin
    Args:
        handle: handle returned by the plugin initialisation call
        new_config: JSON object representing the new configuration category for the category
    Returns:
        new_handle: new handle to be used in the future calls
    """

    _LOGGER.info("imageblock - Old config for  plugin {} \n new config {}".format(handle, new_config))
    plugin_shutdown(handle)
    # plugin_init
    new_handle = plugin_init(new_config, handle['ingest_ref'], handle['callback'])
    return new_handle


def plugin_shutdown(handle):
    """ Shut down the plugin.
    Args:
        handle: JSON configuration document for the plugin configuration category
    Returns:
        data: JSON object to be used in future calls to the plugin
    Raises:
    """
    _LOGGER.info("imageblock Shutdown")

