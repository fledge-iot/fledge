# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

__author__ = "Ashish Jabble, Praveen Garg, Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


def setup(app, obj, is_core=False):
    """ Common method to setup the microservice management api.
    Args:
        obj (an instance, or a class, with the implementation of the needed methods for each route below)
        is_core: if True, routes are being set for Core Management API only
    """
    
    # Basic api common to all microservices
    app.router.add_route('GET', '/fledge/service/ping', obj.ping)
    app.router.add_route('POST', '/fledge/service/shutdown', obj.shutdown)
    app.router.add_route('POST', '/fledge/change', obj.change)

    if is_core:
        # Configuration
        app.router.add_route('GET', '/fledge/service/category', obj.get_configuration_categories)
        app.router.add_route('POST', '/fledge/service/category', obj.create_configuration_category)
        app.router.add_route('GET', '/fledge/service/category/{category_name}', obj.get_configuration_category)
        app.router.add_route('DELETE', '/fledge/service/category/{category_name}', obj.delete_configuration_category)
        app.router.add_route('GET', '/fledge/service/category/{category_name}/children', obj.get_child_category)
        app.router.add_route('POST', '/fledge/service/category/{category_name}/children', obj.create_child_category)
        app.router.add_route('GET', '/fledge/service/category/{category_name}/{config_item}', obj.get_configuration_item)
        app.router.add_route('PUT', '/fledge/service/category/{category_name}/{config_item}', obj.update_configuration_item)
        app.router.add_route('DELETE', '/fledge/service/category/{category_name}/{config_item}/value', obj.delete_configuration_item)

        # Service Registration
        app.router.add_route('POST', '/fledge/service', obj.register)
        app.router.add_route('DELETE', '/fledge/service/{service_id}', obj.unregister)
        app.router.add_route('GET', '/fledge/service', obj.get_service)

        # Interest Registration
        app.router.add_route('POST', '/fledge/interest', obj.register_interest)
        app.router.add_route('DELETE', '/fledge/interest/{interest_id}', obj.unregister_interest)
        app.router.add_route('GET', '/fledge/interest', obj.get_interest)

        # Asset Tracker
        app.router.add_route('GET', '/fledge/track', obj.get_track)
        app.router.add_route('POST', '/fledge/track', obj.add_track)

        # Audit Log
        app.router.add_route('POST', '/fledge/audit', obj.add_audit)

        # enable/disable schedule
        app.router.add_route('PUT', '/fledge/schedule/{schedule_id}/enable', obj.enable_disable_schedule)

        # Internal refresh cache
        app.router.add_route('PUT', '/fledge/cache', obj.refresh_cache)

    # enable cors support
    enable_cors(app)


def enable_cors(app):
    """ implements Cross Origin Resource Sharing (CORS) support """
    import aiohttp_cors

    # Configure default CORS settings.
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_methods=["GET", "POST", "PUT", "DELETE"],
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
