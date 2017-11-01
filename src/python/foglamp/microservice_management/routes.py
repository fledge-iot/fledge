# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


from foglamp.microservice_management.service_registry import service_registry

__author__ = "Ashish Jabble, Praveen Garg, Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


def setup(app,is_core=False):

    # Basic api common to all microservices
    app.router.add_route('GET', '/foglamp/service/ping', service_registry.ping)
    # TODO: shutdown
    app.router.add_route('POST', '/foglamp/service/shutdown', service_registry.shutdown)
    # TODO: notify_change
    app.router.add_route('POST', '/foglamp/change', service_registry.notify_change)

    # api common to core only
    if is_core is True:
        # Service Registration
        app.router.add_route('POST', '/foglamp/service', service_registry.register)
        app.router.add_route('DELETE', '/foglamp/service/{service_id}', service_registry.unregister)
        app.router.add_route('GET', '/foglamp/service', service_registry.get_service)
        # Configuration Change Interest Registration
        # TODO: register_interest
        app.router.add_route('POST', '/foglamp/service/interest', service_registry.register_interest)
        # TODO: undergister_interest
        app.router.add_route('DELETE', '/foglamp/service/interest/{service_id}', service_registry.unregister_interest)

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

