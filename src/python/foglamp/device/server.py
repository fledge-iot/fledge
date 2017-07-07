#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import asyncio

from foglamp.device.coap import controller as coap_controller

__author__    = "Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__   = "Apache 2.0"
__version__   = "${VERSION}"


def start():
    """Starts the device service"""
    coap_controller.start()
    asyncio.get_event_loop().run_forever()

if __name__ == "__main__":
    start()

