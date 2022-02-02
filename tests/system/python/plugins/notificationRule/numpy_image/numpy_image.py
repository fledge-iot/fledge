# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: https://fledge-iot.readthedocs.io
# FLEDGE_END

""" Notification Rule plugin module to handle images with Numpy """

import os

import copy
import logging
from fledge.common import logger
import datetime
from fledge.plugins.common import utils
import numpy
import json

__author__ = "Massimiliano Pinto"
__copyright__ = "Copyright (c) 2022 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_DEFAULT_CONFIG = {
    'plugin': {
        'description': 'Numpy image processing rule plugin',
        'type': 'string',
        'default': 'numpy_image',
        'readonly': 'true'
    },
    'assetName': {
        'description': 'Name of asset',
        'type': 'string',
        'default': 'sinusoid',
        'displayName': 'Asset name to monitor'
    }
}

_LOGGER = logger.setup(__name__, level=logging.DEBUG)

def plugin_info():
    """ Returns information about the plugin.
    Args:
    Returns:
        dict: plugin information
    Raises:
    """
    _LOGGER.info("plugin_info() called")
    return {
        'name': 'numpy_image',
        'version': '1.7.0',
        'mode': 'poll',
        'type': 'notificationRule',
        'interface': '1.0.0',
        'config': _DEFAULT_CONFIG
    }


def plugin_init(config):
    """ Initialise the plugin.
    Args:
        config: JSON configuration document for the plugin configuration category
    Returns:
        data: JSON object to be used in future calls to the plugin
    Raises:
    """

    _LOGGER.info("plugin_init() called: config={}".format(config))
    try:
        handle = copy.deepcopy(config)
        handle['state'] = False
    except Exception as ex:
        _LOGGER.exception('Error in initializing plugin {}'.format(str(ex)))
        raise

    return handle


def plugin_triggers(handle):
    """ Returns assets to monitor for numpy_image
    Args:
        handle: handle returned by the plugin initialisation call
    Returns:
        Returns the dict with asset name(s) under which numpy_image data is available.
        This would be used to subscribe to such data from storage service
    """
    d = {'triggers': [{'asset': handle['assetName']['value']}]}
    _LOGGER.debug("plugin_triggers() called: triggers={}".format(d))
    return d


def plugin_eval(handle, data):
    """ Evaluates whether it is a bad bearing by running vibration data thru' ML model
    Args:
        handle: handle returned by the plugin initialisation call
        data: dict with the readings, containing vibration data for bearings
    Returns:
        Returns a bool indicating whether the bearing is bad
    """

    ret_val = False
    try:
        if type(data) == dict:
            for k in data.keys():
                if type(data[k]) == dict:
                    for j in data[k].keys():
                        if type(data[k][j]) != str:
                            t_type = type(data[k][j])
                            if t_type == numpy.ndarray:
                                #_LOGGER.error("=== (2.4) numpy.ndarray here")
                                arr = data[k][j]
                                #_LOGGER.error("=== (2.4) numpy.ndarray check: " + str(type(arr)))
                                #_LOGGER.error("=== (2.4.1) numpy.ndarray has dims " + str(arr.ndim))
                                #_LOGGER.error("=== (2.4.2) numpy.ndarray has size " + str(arr.size))
                                #_LOGGER.error("=== (2.4.3) numpy.ndarray has shape " + str(arr.shape))
                                #_LOGGER.error("=== (2.4.4) numpy.ndarray has stored types " + str(arr.dtype))
                                _LOGGER.error("*** (2.4.5) numpy.ndarray has numpy.count_nonzero:" + str(numpy.count_nonzero(arr)))
                                if numpy.count_nonzero(arr) > 145200:
                                    ret_val = True
                else:
                    _LOGGER.debug("plugin_eval(): key '" + str(k) + "' is not a dict")

    except Exception as ex:
        _LOGGER.exception('Error in plugin_eval():  {}'.format(str(ex)))

    handle["state"] = ret_val

    _LOGGER.error("plugin_eval() returns " + str(ret_val))

    return ret_val

def plugin_reason(handle):
    """ Returns reason string for the last time plugin_eval returned True
    Args:
        handle: handle returned by the plugin initialisation call
    Returns:
        Returns a simple dict with 'reason' field indicating the reason for last 'plugin_eval' call returning True
    """
    s = "triggered" if handle["state"] == True else "cleared"
    timestamp = utils.local_timestamp()
    _LOGGER.debug("plugin_reason() called: reason={}".format(s))
    return {'reason': s, 'asset': [handle['assetName']['value']], 'timestamp': timestamp}


def plugin_reconfigure(handle, new_config):
    """ Reconfigures the plugin
    Args:
        handle: handle returned by the plugin initialisation call
        new_config: JSON object representing the new configuration category for the category
    Returns:
        new_handle: new handle to be used in the future calls
    """
    _LOGGER.debug("plugin_reconfigur() Old config for plugin={} \n new config={}".format(handle, new_config))

    # Shutdown plugin
    plugin_shutdown(handle)

    # Call init with new configuration
    new_handle = plugin_init(new_config)

    return new_handle


def plugin_shutdown(handle):
    """ Shutdowns the plugin doing required cleanup
    Args:
        handle: handle returned by the plugin initialisation call
    Returns:
        plugin shutdown
    """

    _LOGGER.debug("plugin_ shutdown() called.")

    # Remove any data here
