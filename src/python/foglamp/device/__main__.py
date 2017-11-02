#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import sys

from foglamp.device.server import Server
from foglamp.parser import Parser
from foglamp.parser import ArgumentParserError
from foglamp import logger

"""Starts the device server"""

__author__ = "Terris Linenbach"
__copyright_ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_logger = logger.setup("Device", level=20)

try:
    plugin = Parser.get('--name')
    core_mgt_port = Parser.get('--port')
    core_mgt_address = Parser.get('--address')
except ArgumentParserError:
    _logger.exception('Unable to parse command line argument')
    sys.exit(1)

if plugin is None:
    _logger.warning("Required argument '--name' is missing")
elif core_mgt_port is None:
    _logger.warning("Required argument '--port' is missing")
elif core_mgt_address is None:
    _logger.warning("Required argument '--address' is missing")
else:
    Server.start(plugin, core_mgt_address, core_mgt_port)
