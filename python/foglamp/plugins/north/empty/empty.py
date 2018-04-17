#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Empty North Plugin"""

# Module information
__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2017,2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_MODULE_NAME = "Empty North Plugin"

import foglamp.plugins.north.common.common as plugin_common
import foglamp.plugins.north.common.exceptions as plugin_exceptions

from foglamp.common import logger


def plugin_info():
    """ Empty North Plugin

    Returns:
        plugin_info
    """

    _plugin_info = {
        'name': _MODULE_NAME,
        'version': "1.0.0",
        'type': "north",
        'interface': "1.0",
        'config': "none"
    }

    return _plugin_info


def plugin_init(data):
    """ Empty North Plugin """

    _config = {}

    return _config


def plugin_send(raw_data, stream_id):
    """ Empty North Plugin """

    is_data_sent = True
    new_position = 0
    num_sent = 0

    return is_data_sent, new_position, num_sent


def plugin_shutdown():
    """ Empty North Plugin """
    pass


def plugin_reconfigure():
    """ Empty North Plugin """
    pass


if __name__ == "__main__":
    pass
