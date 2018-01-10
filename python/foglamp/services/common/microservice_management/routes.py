# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

__author__ = "Ashish Jabble, Praveen Garg, Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


def setup(app, obj):
    """ Common method to setup the microservice management api.
    Args:
        obj (an instance, or a class, with the implementation of the needed methods for each route below)
    """
    
    # Basic api common to all microservices
    app.router.add_route('GET', '/foglamp/service/ping', obj.ping)
    app.router.add_route('POST', '/foglamp/service/shutdown', obj.shutdown)
    app.router.add_route('POST', '/foglamp/change', obj.change)
    # Service Registration
    app.router.add_route('POST', '/foglamp/service', obj.register)
    app.router.add_route('DELETE', '/foglamp/service/{service_id}', obj.unregister)
    app.router.add_route('GET', '/foglamp/service', obj.get_service)
    # Interest Registration
    app.router.add_route('POST', '/foglamp/interest', obj.register_interest)
    app.router.add_route('DELETE', '/foglamp/interest/{interest_id}', obj.unregister_interest)

    # enable cors support
    enable_cors(app)


def enable_cors(app):
    """ implements Cross Origin Resource Sharing (CORS) support """
    import aiohttp_cors

    # Configure default CORS settings.
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })

    # Configure CORS on all routes.
    for route in list(app.router.routes()):
        cors.add(route)


def enable_debugger(app):
    """ provides a debug toolbar for server requests """
    import aiohttp_debugtoolbar

    # dev mode only
    # this will be served at API_SERVER_URL/_debugtoolbar
    aiohttp_debugtoolbar.setup(app)
