#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from aiohttp import web

from foglamp.core import routes
from foglamp.core import middleware

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


def make_app():
    """create the server"""
    app = web.Application(middlewares=[middleware.error_middleware])
    routes.setup(app)
    return app


def start():
    """starts the server"""
    # https://aiohttp.readthedocs.io/en/stable/_modules/aiohttp/web.html#run_app
    web.run_app(make_app(), host='0.0.0.0', port=8082)


if __name__ == "__main__":
    start()
