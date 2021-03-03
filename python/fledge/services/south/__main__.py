#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

"""South Service starter"""

from fledge.services.south.server import Server
from fledge.common import logger

__author__ = "Terris Linenbach, Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

if __name__ == '__main__':
    _logger = logger.setup("South")
    south_server = Server()
    south_server.run()

