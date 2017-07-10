# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import asyncio
from foglamp.admin_api.app_builder import build

__author__    = "Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__   = "Apache 2.0"
__version__   = "${VERSION}"


def start():
    loop = asyncio.get_event_loop()
    f = loop.create_server(build().make_handler(), '0.0.0.0', 8081)
    loop.create_task(f)
    asyncio.get_event_loop().run_forever()

