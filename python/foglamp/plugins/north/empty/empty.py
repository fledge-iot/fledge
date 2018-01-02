#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Empty North Plugin"""

# Module information
__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_MODULE_NAME = "Empty North Plugin"

import foglamp.plugins.north.common.common as plugin_common
import foglamp.plugins.north.common.exceptions as plugin_exceptions

from foglamp.common import logger


def plugin_retrieve_info(stream_id):
    """ Empty North Plugin

    Returns:
        plugin_info
    """

    plugin_info = {
        'name': _MODULE_NAME,
        'version': "1.0.0",
        'type': "north",
        'interface': "1.0",
        'config': stream_id
    }

    return plugin_info


def plugin_init():
    """ Empty North Plugin """


def plugin_send(raw_data, stream_id):
    """ Empty North Plugin """

    data_sent = ()
    new_position = 0
    num_sent = 0

    return data_sent, new_position, num_sent


def plugin_shutdown():
    """ Empty North Plugin """


if __name__ == "__main__":
    pass
