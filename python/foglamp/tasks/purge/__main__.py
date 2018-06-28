#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Purge process starter"""

import asyncio
from foglamp.tasks.purge.purge import Purge
from foglamp.common import logger

__author__ = "Terris Linenbach, Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

if __name__ == '__main__':
    _logger = logger.setup("Purge")
    loop = asyncio.get_event_loop()
    purge_process = Purge()
    loop.run_until_complete(purge_process.run())
