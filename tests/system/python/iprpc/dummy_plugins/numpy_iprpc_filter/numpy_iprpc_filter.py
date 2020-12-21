# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" A dummy filter plugin to tests iprpc module in Fledge. """

import copy
import datetime
import logging

import numpy as np

import filter_ingest
from fledge.common import logger

__author__ = "Deepanshu Yadav"
__copyright__ = "Copyright (c) 2020 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_DEFAULT_CONFIG = {
    'plugin': {  # mandatory
        'description': 'Filter plugin to control periodic data forwarding',
        'type': 'string',
        'default': 'numpy_iprpc_filter',
        'readonly': 'true'
    },
    'enabled': {  # mandatory
        'description': 'Enable / disable this plugin',
        'type': 'boolean',
        'default': 'False',
        'displayName': 'Enable this plugin',
        'order': '1'
    }
}

_LOGGER = logger.setup(__name__, level=logging.INFO)
_state = None


def plugin_info():
    """ Returns information about the plugin.
    Args:
    Returns:
        dict: plugin information
    Raises:
    """
    _LOGGER.info("plugin_info called")
    return {
        'name': 'numpy_iprpc_filter',
        'version': '1.8.2',
        'mode': 'poll',
        'type': 'filter',
        'interface': '1.0.0',
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
    _LOGGER.info("plugin_init called")
    _config = config  # copy.deepcopy(config)
    _config['ingest_ref'] = ingest_ref
    _config['callback'] = callback

    return _config


async def plugin_ingest(handle, data):
    """ plugin_ingest -- forward data to our callback if we are within our period """

    filter_ingest.filter_ingest_callback(handle['callback'], handle['ingest_ref'], data)


def plugin_reconfigure(handle, new_config):
    """ Reconfigures the plugin
    Args:
        handle: handle returned by the plugin initialisation call
        new_config: JSON object representing the new configuration category for the category
    Returns:
        new_handle: new handle to be used in the future calls
    """
    _LOGGER.info("Old config for periodic_timer plugin={} \n new config={}".format(handle.config, new_config))
    plugin_shutdown(handle)
    new_handle = plugin_init(new_config)
    return new_handle


def plugin_shutdown(handle):
    """ Shutdowns the plugin doing required cleanup
    Args:
        handle: handle returned by the plugin initialisation call
    Returns:
        plugin shutdown
    """
    _LOGGER.info("Plugin shutdown ")
