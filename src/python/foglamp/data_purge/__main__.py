#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Purge process starter"""

import sys

from foglamp.data_purge.purge import Purge
from foglamp import logger
from foglamp.parser import ArgumentParserError, Parser

__author__ = "Terris Linenbach, Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

if __name__ == '__main__':
    _logger = logger.setup("Purge")

    try:
        core_mgt_port = Parser.get('--port')
        core_mgt_address = Parser.get('--address')
    except ArgumentParserError:
        _logger.exception('Unable to parse command line argument')
        sys.exit(1)

    if core_mgt_port is None:
        _logger.warning("Required argument '--port' is missing")
    elif core_mgt_address is None:
        _logger.warning("Required argument '--address' is missing")
    else:
        purge = Purge(core_mgt_address, core_mgt_port)
        purge.start()
