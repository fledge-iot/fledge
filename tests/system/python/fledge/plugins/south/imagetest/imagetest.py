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
    },
    'depth': {
        'description': 'Bits per pixel',
        'type': 'enumeration',
        'options' : [ '8', '16', '24' ],
        'default': '8',
        'displayName': 'Depth',
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
        depth = int(handle['depth']['value'])
        _LOGGER.info(" depth from config {} \n".format(str(depth)))

        if depth == 8:

            image = np.full((256,256), 0 , dtype=np.uint8)

            for i in range(0, 256):
                for j in range(0,256):
                        image[i][j] = i 
        
            data = {'asset':  handle['assetName']['value'], 'timestamp': time_stamp, 'readings': {"image": image}}
        elif depth == 16:
            image = np.full((256, 256), 0, dtype=np.uint16)
            for i in range(0, 256):
                for j in range(0, 256):
                    image[i][j] = i*i

            data = {'asset':  handle['assetName']['value'], 'timestamp': time_stamp, 'readings': {"image": image}}
        elif depth == 24:
            image = np.full((256, 256, 3), 0, dtype=np.uint8)
            for i in range(0, 32):
                for j in range(0, 256):
                    for k in range(0,3):
                        if k%3 == 0:
                            image[i][j][k] =  i*8
                        else:
                            image[i][j][k] = 0

            for i in range (32,64):
                for j in range(0,256):
                    for k in range(0,3):
                        if  k%3 == 0:
                            image[i][j][k] = 0         #R
                        elif k%3 == 1:
                            image[i][j][k] = (i%32)*8  #G
                        else:
                            image[i][j][k] = 0         #B

            for i in range(64,96):
                for j in range(0,256):    
                    for k in range(0,3):
                        if k%3 == 0:
                            image[i][j][k] = 0            #R
                        elif k%3 == 1:
                            image[i][j][k] = 0            #G
                        else:
                            image[i][j][k] = (i%32)*8     #B


            for i in range(96,128):
                for  j in range(0,256):
                    for k in range(0,3):
                        image[i][j][k] = (i%32)*8

            for i in range(128,256):
                for j in range(0,256):
                    for k in range(0,3):
                        if k%3 == 0:
                            image[i][j][k] = (i%128) * 4                  #R
                        elif k%3 == 1:
                            image[i][j][k] = 255 - ( ( i%128) * 4 )      #G
                        else:
                            image[i][j][k] = j                           #B

            data = {'asset':  handle['assetName']['value'], 'timestamp': time_stamp, 'readings': {"image": image}}
        else:
            pass
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
