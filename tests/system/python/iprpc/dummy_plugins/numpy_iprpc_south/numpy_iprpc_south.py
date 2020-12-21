# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" A dummy south plugin to ingest random values in Fledge using numpy """

import copy
import logging

import numpy as np

from fledge.common import logger
from fledge.plugins.common import utils

__author__ = "Deepanshu Yadav"
__copyright__ = "Copyright (c) 2020 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_DEFAULT_CONFIG = {
    'plugin': {
        'description': 'A dummy south plugin to ingest random values in Fledge using numpy',
        'type': 'string',
        'default': 'numpy_iprpc_south',
        'readonly': 'true'
    },
    'assetName': {
        'description': 'Name of Asset',
        'type': 'string',
        'default': 'np_random',
        'displayName': 'Asset name',
        'mandatory': 'true'
    }
}

_LOGGER = logger.setup(__name__, level=logging.INFO)
index = -1
sine = [
        0.0,
        0.104528463,
        0.207911691,
        0.309016994,
        0.406736643,
        0.5,
        0.587785252,
        0.669130606,
        0.743144825,
        0.809016994,
        0.866025404,
        0.913545458,
        0.951056516,
        0.978147601,
        0.994521895,
        1.0,
        0.994521895,
        0.978147601,
        0.951056516,
        0.913545458,
        0.866025404,
        0.809016994,
        0.743144825,
        0.669130606,
        0.587785252,
        0.5,
        0.406736643,
        0.309016994,
        0.207911691,
        0.104528463,
        1.22515E-16,
        -0.104528463,
        -0.207911691,
        -0.309016994,
        -0.406736643,
        -0.5,
        -0.587785252,
        -0.669130606,
        -0.743144825,
        -0.809016994,
        -0.866025404,
        -0.913545458,
        -0.951056516,
        -0.978147601,
        -0.994521895,
        -1.0,
        -0.994521895,
        -0.978147601,
        -0.951056516,
        -0.913545458,
        -0.866025404,
        -0.809016994,
        -0.743144825,
        -0.669130606,
        -0.587785252,
        -0.5,
        -0.406736643,
        -0.309016994,
        -0.207911691,
        -0.104528463
    ]


def generate_data():
    global index
    while index >= -1:
        # index exceeds, reset to default
        if index >= 59:
            index = -1
        index += 1
        yield sine[index]


def plugin_info():
    """ Returns information about the plugin.
    Args:
    Returns:
        dict: plugin information
    Raises:
    """
    return {
        'name': 'Numpy Iprpc Poll plugin',
        'version': '1.8.2',
        'mode': 'poll',
        'type': 'south',
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


def plugin_poll(handle):
    """ Extracts data from the sensor and returns it in a JSON document as a Python dict.
    Available for poll mode only.
    Args:
        handle: handle returned by the plugin initialisation call
    Returns:
        returns a sensor reading in a JSON document, as a Python dict, if it is available
        None - If no reading is available
    Raises:
        Exception
    """
    try:
        time_stamp = utils.local_timestamp()
        data = {'asset':  handle['assetName']['value'],
                'timestamp': time_stamp,
                'readings': {"random":  next(generate_data())}}
    except (Exception, RuntimeError) as ex:
        _LOGGER.exception("Exception is {}".format(str(ex)))
        raise ex
    else:
        return data


def plugin_reconfigure(handle, new_config):
    """ Reconfigures the plugin

    Args:
        handle: handle returned by the plugin initialisation call
        new_config: JSON object representing the new configuration category for the category
    Returns:
        new_handle: new handle to be used in the future calls
    """
    _LOGGER.info("Old config for sinusoid plugin {} \n new config {}".format(handle, new_config))
    new_handle = copy.deepcopy(new_config)
    return new_handle


def plugin_shutdown(handle):
    """ Shutdowns the plugin doing required cleanup, to be called prior to the South plugin service being shut down.

    Args:
        handle: handle returned by the plugin initialisation call
    Returns:
        plugin shutdown
    """
    _LOGGER.info('numpy south plugin shut down.')
