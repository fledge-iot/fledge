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

_logger = logger.setup("SouthBound Device", level=20)
# TODO: Support --help, --name plugin, etc.

parser = argparse.ArgumentParser(prog='SouthBound Device')
parser.description = '%(prog)s -- Device Service'
parser.epilog = 'Sensor/device interface of FogLAMP'
# parser.add_argument('-v', '--version', action='version', version='%(prog)s {0!s}'.format(1.0))
parser.add_argument('--name', default='CoAP')
parser.add_argument('--port',  required=True, help='Core Management Port')


namespace = parser.parse_args(sys.argv[1:])

plugin = '{0}'.format(namespace.name)

core_management_port = int(namespace.port)

print(plugin, core_management_port)


Server.start(plugin, core_management_port)
