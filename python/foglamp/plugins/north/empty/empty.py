# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" North Plugin template """

import foglamp.plugins.north.common.common as plugin_common
import foglamp.plugins.north.common.exceptions as plugin_exceptions

from foglamp.common import logger

__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2017,2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_MODULE_NAME = "Empty North Plugin"

_DEFAULT_CONFIG = {}

_logger = logger.setup(__name__)


def plugin_info():
    """ Returns information about the plugin.

     Args:
     Returns:
         _plugin_info: python dictionary containing the plugin information
     Raises:
     """

    _plugin_info = {
        'name': _MODULE_NAME,
        'version': "1.0.0",
        'type': "north",
        'interface': "1.0",
        'config': _DEFAULT_CONFIG
    }

    return _plugin_info


def plugin_init(config):
    """ Initialise the plugin.

    Args:
        config: JSON configuration document
    Returns:
        handle: JSON object to be used in future calls to the plugin
    Raises:
    """

    handle = config

    return handle


async def plugin_send(handle, data_to_send, stream_id):
    """ Sends the data to the destination implementing the required protocol

    Args:
        handle: handle returned by the plugin initialisation call
        data_to_send: Data to send as a python list/dictionary
        stream_id:

    Returns:
        is_data_sent: True if the data were sent
        new_position: Id of the position already sent
        num_sent: Number of asset codes sent

    Raises:
        DataSendError
    """

    try:
        is_data_sent = True
        new_position = 0
        num_sent = 0

    except Exception as ex:
        raise plugin_exceptions.DataSendError(ex)

    return is_data_sent, new_position, num_sent


def plugin_reconfigure(handle, new_config):
    """ Reconfigures the plugin, it should be called when the configuration of the plugin is changed during the
        operation of the North task.
        The new configuration category should be passed.

    Args:
        handle: handle returned by the plugin initialisation call
        new_config: JSON object representing the new configuration category for the category

    Returns:
        new_handle: new handle to be used in the future calls

    Raises:
    """

    new_handle = handle

    return handle


def plugin_shutdown(handle):
    """ Shutdowns the plugin doing required cleanup, to be called prior to the North task being shut down.

    Args:
        handle: handle returned by the plugin initialisation call

    Returns:
    Raises:
    """

    pass


if __name__ == "__main__":
    pass
