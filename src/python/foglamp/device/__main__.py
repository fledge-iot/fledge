#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import sys

from foglamp.device.server import Server

"""Starts the device server"""

__author__ = "Terris Linenbach"
__copyright_ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


# TODO: Support --help, --name plugin, etc.
try:
    plugin = sys.argv[1]
    index = plugin.find('--name=')
    if index == -1:
        plugin = None
    else:
        plugin = plugin
except IndexError:
    plugin = None

if plugin is None:
    # TODO: delete this
    plugin = 'CoAP'

if plugin is None:
    # TODO: Output to STDERR
    print("Required argument 'name' is missing")
    # TODO: exit 1
else:
    Server.start(plugin)
