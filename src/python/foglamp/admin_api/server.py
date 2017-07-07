#!/usr/bin/env python3

import asyncio
from foglamp.admin_api import controller
 
__author__    = "Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__   = "Apache 2.0"
__version__   = "${VERSION}"


def start():
    """Starts the service"""
    controller.start()
    asyncio.get_event_loop().run_forever()


