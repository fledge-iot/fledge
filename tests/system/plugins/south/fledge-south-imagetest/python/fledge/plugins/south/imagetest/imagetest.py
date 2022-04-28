# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Module for ImageTest poll mode plugin """

import copy
import logging
import numpy as np

from fledge.common import logger
from fledge.plugins.common import utils

__author__ = "Mark Riddoch"
__copyright__ = "Copyright (c) 2022 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_DEFAULT_CONFIG = {
    'plugin': {
        'description': 'ImageTest Poll Plugin which implements a test',
        'type': 'string',
        'default': 'imagetest',
        'readonly': 'true'
    },
    'assetName': {
        'description': 'Name of Asset',
        'type': 'string',
        'default': 'image',
        'displayName': 'Asset name',
        'mandatory': 'true'
    }
}

_LOGGER = logger.setup(__name__, level=logging.INFO)


def plugin_info():
    """ Returns information about the plugin.
    Args:
    Returns:
        dict: plugin information
    Raises:
    """
    return {
        'name': 'ImageTest Poll plugin',
        'version': '1.9.2',
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
        image = np.full((64, 64), 0, dtype=np.uint8)
        for i in range(0, 63):
            image[i][30] = i * 4;
            image[i][31] = i * 4;
            image[i][33] = i * 4;
            image[i][34] = i * 4;
            image[30][i] = i * 4;
            image[31][i] = i * 4;
            image[33][i] = i * 4;
            image[34][i] = i * 4;
            for j in range(0, 15):
                image[j][i] = floor(i / 4) * 16
            for j in range(49, 63):
                image[j][i] = floor(i / 4) * 16
            image[16][i] = 255
            image[32][i] = 255
            image[48][i] = 255
            image[i][16] = 255
            image[i][32] = 255
            image[i][48] = 255
        data = {'asset':  handle['assetName']['value'], 'timestamp': time_stamp, 'readings': {"image": image}}
    except (Exception, RuntimeError) as ex:
        _LOGGER.exception("Imagetest exception: {}".format(str(ex)))
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
    _LOGGER.info("Old config for imagetest plugin {} \n new config {}".format(handle, new_config))
    new_handle = copy.deepcopy(new_config)
    return new_handle


def plugin_shutdown(handle):
    """ Shutdowns the plugin doing required cleanup, to be called prior to the South plugin service being shut down.

    Args:
        handle: handle returned by the plugin initialisation call
    Returns:
        plugin shutdown
    """
    _LOGGER.info('imagetest plugin shut down.')
