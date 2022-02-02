# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: https://fledge-iot.readthedocs.io
# FLEDGE_END

""" Example Notification delivery plugin """

import copy
import uuid
import logging
import json

from fledge.common import logger
from fledge.plugins.common import utils

__author__ = "Massimiliano Pinto"
__copyright__ = "Copyright (c) 2022 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_LOGGER = logger.setup(__name__, level=logging.DEBUG)

_DEFAULT_CONFIG = {
    'plugin': {
        'description': 'Send notification delivery plugin',
        'type': 'string',
        'default': 'send',
        'readonly': 'true'
    },
    'enable': {
        'description': 'Enable send plugin',
        'type': 'boolean',
        'default': 'false',
        'displayName': 'Enable',
        'order': "1"
    }
}

def plugin_info():
    """ Returns information about the plugin.
    Args:
    Returns:
        dict: plugin information
    Raises:
    """
    return {
        'name': 'send',
        'version': '1.7.1',
        'mode': 'none',
        'type': 'notificationDelivery',
        'interface': '1.0',
        'config': _DEFAULT_CONFIG
    }


def plugin_init(config):
    """ Initialise the plugin.
    Args:
        config: JSON configuration document for the South plugin configuration category
    Returns:
        data: JSON object to be used in future calls to the plugin
    Raises:
    """
    data = copy.deepcopy(config)

    return data

def plugin_reconfigure(handle, new_config):
    """ Reconfigures the plugin

    Args:
        handle: handle returned by the plugin initialisation call
        new_config: JSON object representing the new configuration category for the category
    Returns:
        new_handle: new handle to be used in the future calls
    """
    new_handle = copy.deepcopy(new_config)

    new_handle = plugin_init(new_config)
    return new_handle


def plugin_shutdown(handle):
    """ Shutdowns the plugin doing required cleanup, to be called prior to the South plugin service being shut down.

    Args:
        handle: handle returned by the plugin initialisation call
    Returns:
        plugin shutdown
    """
    _LOGGER.info('plugin_shutdown() called.')

def plugin_deliver(handle, deliveryName, notificationName, triggerReason, message):
    _LOGGER.debug("send delivery for " + str(notificationName))
    _LOGGER.debug("send message is " + str(message))
    _LOGGER.debug("send reason object type is " + str(type(triggerReason)))
    _LOGGER.debug("send reason " + str(triggerReason['reason']))

    # Get data that triggered the notification
    data = triggerReason['data']

    if type(data) == dict:
        for k in data.keys():
            _LOGGER.debug("=== type of key '" + str(k) + "' is " + str(type(data[k])))
            if type(data[k]) == dict:
                for j in data[k].keys():
                    _LOGGER.error("=== type of dict key '" + str(j) + "' is " + str(type(data[k][j])))
            else:
                _LOGGER.error("=== value of key '" + str(k) + "' is " + str(data[k]))

    return True
