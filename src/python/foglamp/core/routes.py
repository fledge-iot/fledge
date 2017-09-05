# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from aiohttp import web

from foglamp.core.api import audit as api_audit
from foglamp.core.api import browser
from foglamp.core.api import common as api_common
from foglamp.core.api import configuration as api_configuration
from foglamp.core.api import scheduler as api_scheduler
from foglamp.core.api import statistics as api_statistics
from foglamp.core.service_registry import service_registry

__author__ = "Ashish Jabble, Praveen Garg"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


def setup(app):
    # app.router.add_route('POST', '/foglamp/a-post-req', api_a_post_req, expect_handler = aiohttp.web.Request.json)
    app.router.add_route('GET', '/foglamp/ping', api_common.ping)

    # Configuration
    app.router.add_route('GET', '/foglamp/categories', api_configuration.get_categories)
    app.router.add_route('GET', '/foglamp/category/{category_name}', api_configuration.get_category)
    app.router.add_route('GET', '/foglamp/category/{category_name}/{config_item}', api_configuration.get_category_item)
    app.router.add_route('PUT', '/foglamp/category/{category_name}/{config_item}', api_configuration.set_configuration_item,
                         expect_handler=web.Request.json)
    app.router.add_route('DELETE', '/foglamp/category/{category_name}/{config_item}', api_configuration.set_configuration_item)

    # Scheduler
    # Scheduled_processes - As per doc
    app.router.add_route('GET', '/foglamp/schedule/process', api_scheduler.get_scheduled_processes)
    app.router.add_route('GET', '/foglamp/schedule/process/{scheduled_process_name}', api_scheduler.get_scheduled_process)

    # Schedules - As per doc
    app.router.add_route('GET', '/foglamp/schedule', api_scheduler.get_schedules)
    app.router.add_route('POST', '/foglamp/schedule', api_scheduler.post_schedule)
    app.router.add_route('GET', '/foglamp/schedule/type', api_scheduler.get_schedule_type)
    app.router.add_route('GET', '/foglamp/schedule/{schedule_id}', api_scheduler.get_schedule)
    app.router.add_route('POST', '/foglamp/schedule/start/{schedule_id}', api_scheduler.start_schedule)
    app.router.add_route('PUT', '/foglamp/schedule/{schedule_id}', api_scheduler.update_schedule)
    app.router.add_route('DELETE', '/foglamp/schedule/{schedule_id}', api_scheduler.delete_schedule)

    # Tasks - As per doc
    app.router.add_route('GET', '/foglamp/task', api_scheduler.get_tasks)
    app.router.add_route('GET', '/foglamp/task/state', api_scheduler.get_task_state)
    app.router.add_route('GET', '/foglamp/task/latest', api_scheduler.get_tasks_latest)
    app.router.add_route('GET', '/foglamp/task/{task_id}', api_scheduler.get_task)
    app.router.add_route('PUT', '/foglamp/task/cancel/{task_id}', api_scheduler.cancel_task)

    browser.setup(app)

    # Statistics - As per doc
    app.router.add_route('GET', '/foglamp/statistics', api_statistics.get_statistics)
    app.router.add_route('GET', '/foglamp/statistics/history', api_statistics.get_statistics_history)

    # Audit trail - As per doc
    app.router.add_route('GET', '/foglamp/audit', api_audit.get_audit_entries)
    app.router.add_route('GET', '/foglamp/audit/logcode', api_audit.get_audit_log_codes)
    app.router.add_route('GET', '/foglamp/audit/severity', api_audit.get_audit_log_severity)

    # Micro Service support - Core
    app.router.add_route('GET', '/foglamp/service/ping', service_registry.ping)

    app.router.add_route('POST', '/foglamp/service', service_registry.register)
    app.router.add_route('DELETE', '/foglamp/service/{service_id}', service_registry.unregister)
    app.router.add_route('GET', '/foglamp/service', service_registry.get_service)

    # TODO: shutdown, register_interest, unregister_interest and notify_changes - pending
    app.router.add_route('POST', '/foglamp/service/shutdown', service_registry.shutdown)
    app.router.add_route('POST', '/foglamp/service/interest', service_registry.register_interest)
    app.router.add_route('DELETE', '/foglamp/service/interest/{service_id}', service_registry.unregister_interest)
    app.router.add_route('POST', '/foglamp/change', service_registry.notify_change)

    # enable cors support
    enable_cors(app)

    # enable a live debugger (watcher) for requests, see https://github.com/aio-libs/aiohttp-debugtoolbar
    # this will neutralize error middleware
    # Note: pip install aiohttp_debugtoolbar

    # enable_debugger(app)


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

