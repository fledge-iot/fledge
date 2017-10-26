#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import argparse
import sys

from foglamp.device.server import Server
from foglamp import logger

"""Starts the device server"""

__author__ = "Terris Linenbach"
__copyright_ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_logger = logger.setup("Device", level=20)

parser = argparse.ArgumentParser(prog='Device Service')
parser.description = 'FogLAMP %(prog)s'
parser.epilog = 'FogLAMP %(prog)s'
# parser.add_argument('-v', '--version', action='version', version='%(prog)s {0!s}'.format(1.0))
parser.add_argument('--name', required=True)
parser.add_argument('--address',  required=True)
parser.add_argument('--port',  required=True)


namespace = parser.parse_args(sys.argv[1:])

name = namespace.name
core_management_host = namespace.address
core_management_port = int(namespace.port)

_logger.info(name, core_management_host, core_management_port)
Server.start(name, core_management_host, core_management_port)
