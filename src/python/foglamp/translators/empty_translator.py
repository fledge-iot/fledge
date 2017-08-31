#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Empty translator"""

# Module information
__author__ = "${FULL_NAME}"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_MODULE_NAME = "Empty translator"


def retrieve_plugin_info(_stream_id):
    """ Empty translator

    Returns:
        plugin_info
    Raises:
    Todo:
    """

    plugin_info = {
        'name': _MODULE_NAME,
        'version': "1.0.0",
        'type': "translator",
        'interface': "1.0",
        'config': ""
    }

    return plugin_info


def plugin_init():
    """ Empty translator """


def plugin_shutdown():
    """ Empty translator """


if __name__ == "__main__":
    pass
