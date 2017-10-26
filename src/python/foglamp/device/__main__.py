#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import sys

from foglamp.device.server import Server
from foglamp import logger
from foglamp import arg_parser

"""Starts the device server"""

__author__ = "Terris Linenbach"
__copyright_ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_logger = logger.setup("Device", level=20)

req_args = ["--name", "--address", "--port"]
optional_args = None

namespace = arg_parser.setup(
    "Device", required_args=req_args, optional_args=None, argv=sys.argv[1:])
name = namespace.name
core_management_host = namespace.address
core_management_port = int(namespace.port)

_logger.info(name, core_management_host, core_management_port)
Server.start(name, core_management_host, core_management_port)
