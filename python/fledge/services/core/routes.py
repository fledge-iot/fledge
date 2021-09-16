# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

from fledge.services.core.api import auth
from fledge.services.core.api import audit as api_audit
from fledge.services.core.api import browser
from fledge.services.core.api import common as api_common
from fledge.services.core.api import configuration as api_configuration
from fledge.services.core.api import scheduler as api_scheduler
from fledge.services.core.api import statistics as api_statistics
from fledge.services.core.api import backup_restore
from fledge.services.core.api import update
from fledge.services.core.api import service
from fledge.services.core.api import certificate_store
from fledge.services.core.api import support
from fledge.services.core.api import task
from fledge.services.core.api import asset_tracker
from fledge.services.core.api import south
from fledge.services.core.api import north
from fledge.services.core.api import filters
from fledge.services.core.api import notification
from fledge.services.core.api.plugins import install as plugins_install, discovery as plugins_discovery
from fledge.services.core.api.plugins import update as plugins_update
from fledge.services.core.api.plugins import remove as plugins_remove
from fledge.services.core.api.snapshot import plugins as snapshot_plugins
from fledge.services.core.api.snapshot import table as snapshot_table
from fledge.services.core.api import package_log
from fledge.services.core.api.repos import configure as configure_repo


__author__ = "Ashish Jabble, Praveen Garg, Massimiliano Pinto, Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017-2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


def setup(app):
    app.router.add_route('GET', '/fledge/ping', api_common.ping)
    app.router.add_route('PUT', '/fledge/shutdown', api_common.shutdown)
    app.router.add_route('PUT', '/fledge/restart', api_common.restart)

    # user
    app.router.add_route('GET', '/fledge/user', auth.get_user)
    app.router.add_route('PUT', '/fledge/user', auth.update_me)
    app.router.add_route('PUT', '/fledge/user/{user_id}/password', auth.update_password)

    # role
    app.router.add_route('GET', '/fledge/user/role', auth.get_roles)

    # auth
    app.router.add_route('POST', '/fledge/login', auth.login)
    app.router.add_route('PUT', '/fledge/logout', auth.logout_me)

    # logout all active sessions
    app.router.add_route('PUT', '/fledge/{user_id}/logout', auth.logout)

    # admin
    app.router.add_route('POST', '/fledge/admin/user', auth.create_user)
    app.router.add_route('DELETE', '/fledge/admin/{user_id}/delete', auth.delete_user)
    app.router.add_route('PUT', '/fledge/admin/{user_id}', auth.update_user)
    app.router.add_route('PUT', '/fledge/admin/{user_id}/enable', auth.enable_user)
    app.router.add_route('PUT', '/fledge/admin/{user_id}/reset', auth.reset)

    # Configuration
    app.router.add_route('GET', '/fledge/category', api_configuration.get_categories)
    app.router.add_route('POST', '/fledge/category', api_configuration.create_category)
    app.router.add_route('GET', '/fledge/category/{category_name}', api_configuration.get_category)
    app.router.add_route('PUT', '/fledge/category/{category_name}', api_configuration.update_configuration_item_bulk)
    app.router.add_route('DELETE', '/fledge/category/{category_name}', api_configuration.delete_category)
    app.router.add_route('POST', '/fledge/category/{category_name}/children', api_configuration.create_child_category)
    app.router.add_route('GET', '/fledge/category/{category_name}/children', api_configuration.get_child_category)
    app.router.add_route('DELETE', '/fledge/category/{category_name}/children/{child_category}', api_configuration.delete_child_category)
    app.router.add_route('DELETE', '/fledge/category/{category_name}/parent', api_configuration.delete_parent_category)
    app.router.add_route('GET', '/fledge/category/{category_name}/{config_item}', api_configuration.get_category_item)
    app.router.add_route('PUT', '/fledge/category/{category_name}/{config_item}', api_configuration.set_configuration_item)
    app.router.add_route('POST', '/fledge/category/{category_name}/{config_item}', api_configuration.add_configuration_item)
    app.router.add_route('DELETE', '/fledge/category/{category_name}/{config_item}/value', api_configuration.delete_configuration_item_value)
    app.router.add_route('POST', '/fledge/category/{category_name}/{config_item}/upload', api_configuration.upload_script)
    # Scheduler
    # Scheduled_processes - As per doc
    app.router.add_route('GET', '/fledge/schedule/process', api_scheduler.get_scheduled_processes)
    app.router.add_route('POST', '/fledge/schedule/process', api_scheduler.post_scheduled_process)
    app.router.add_route('GET', '/fledge/schedule/process/{scheduled_process_name}', api_scheduler.get_scheduled_process)

    # Schedules - As per doc
    app.router.add_route('GET', '/fledge/schedule', api_scheduler.get_schedules)
    app.router.add_route('POST', '/fledge/schedule', api_scheduler.post_schedule)
    app.router.add_route('GET', '/fledge/schedule/type', api_scheduler.get_schedule_type)
    app.router.add_route('GET', '/fledge/schedule/{schedule_id}', api_scheduler.get_schedule)
    app.router.add_route('PUT', '/fledge/schedule/{schedule_id}/enable', api_scheduler.enable_schedule)
    app.router.add_route('PUT', '/fledge/schedule/{schedule_id}/disable', api_scheduler.disable_schedule)

    app.router.add_route('PUT', '/fledge/schedule/enable', api_scheduler.enable_schedule_with_name)
    app.router.add_route('PUT', '/fledge/schedule/disable', api_scheduler.disable_schedule_with_name)

    app.router.add_route('POST', '/fledge/schedule/start/{schedule_id}', api_scheduler.start_schedule)
    app.router.add_route('PUT', '/fledge/schedule/{schedule_id}', api_scheduler.update_schedule)
    app.router.add_route('DELETE', '/fledge/schedule/{schedule_id}', api_scheduler.delete_schedule)

    # Tasks - As per doc
    app.router.add_route('GET', '/fledge/task', api_scheduler.get_tasks)
    app.router.add_route('GET', '/fledge/task/state', api_scheduler.get_task_state)
    app.router.add_route('GET', '/fledge/task/latest', api_scheduler.get_tasks_latest)
    app.router.add_route('GET', '/fledge/task/{task_id}', api_scheduler.get_task)
    app.router.add_route('PUT', '/fledge/task/{task_id}/cancel', api_scheduler.cancel_task)

    # Service
    app.router.add_route('POST', '/fledge/service', service.add_service)
    app.router.add_route('GET', '/fledge/service', service.get_health)
    app.router.add_route('DELETE', '/fledge/service/{service_name}', service.delete_service)
    app.router.add_route('GET', '/fledge/service/available', service.get_available)
    app.router.add_route('GET', '/fledge/service/installed', service.get_installed)
    app.router.add_route('PUT', '/fledge/service/{type}/{name}/update', service.update_service)

    # Task
    app.router.add_route('POST', '/fledge/scheduled/task', task.add_task)
    app.router.add_route('DELETE', '/fledge/scheduled/task/{task_name}', task.delete_task)

    # South
    app.router.add_route('GET', '/fledge/south', south.get_south_services)

    # North
    app.router.add_route('GET', '/fledge/north', north.get_north_schedules)

    # assets
    browser.setup(app)

    # asset tracker
    app.router.add_route('GET', '/fledge/track', asset_tracker.get_asset_tracker_events)

    # Statistics - As per doc
    app.router.add_route('GET', '/fledge/statistics', api_statistics.get_statistics)
    app.router.add_route('GET', '/fledge/statistics/history', api_statistics.get_statistics_history)
    app.router.add_route('GET', '/fledge/statistics/rate', api_statistics.get_statistics_rate)

    # Audit trail - As per doc
    app.router.add_route('POST', '/fledge/audit', api_audit.create_audit_entry)
    app.router.add_route('GET', '/fledge/audit', api_audit.get_audit_entries)
    app.router.add_route('GET', '/fledge/audit/logcode', api_audit.get_audit_log_codes)
    app.router.add_route('GET', '/fledge/audit/severity', api_audit.get_audit_log_severity)

    # Backup & Restore - As per doc
    app.router.add_route('GET', '/fledge/backup', backup_restore.get_backups)
    app.router.add_route('POST', '/fledge/backup', backup_restore.create_backup)
    app.router.add_route('POST', '/fledge/backup/upload', backup_restore.upload_backup)
    app.router.add_route('GET', '/fledge/backup/status', backup_restore.get_backup_status)
    app.router.add_route('GET', '/fledge/backup/{backup_id}', backup_restore.get_backup_details)
    app.router.add_route('DELETE', '/fledge/backup/{backup_id}', backup_restore.delete_backup)
    app.router.add_route('GET', '/fledge/backup/{backup_id}/download', backup_restore.get_backup_download)
    app.router.add_route('PUT', '/fledge/backup/{backup_id}/restore', backup_restore.restore_backup)

    # Package Update on demand
    app.router.add_route('PUT', '/fledge/update', update.update_package)

    # certs store
    app.router.add_route('GET', '/fledge/certificate', certificate_store.get_certs)
    app.router.add_route('POST', '/fledge/certificate', certificate_store.upload)
    app.router.add_route('DELETE', '/fledge/certificate/{name}', certificate_store.delete_certificate)

    # Support bundle
    app.router.add_route('GET', '/fledge/support', support.fetch_support_bundle)
    app.router.add_route('GET', '/fledge/support/{bundle}', support.fetch_support_bundle_item)
    app.router.add_route('POST', '/fledge/support', support.create_support_bundle)

    # Get Syslog
    app.router.add_route('GET', '/fledge/syslog', support.get_syslog_entries)

    # Package logs
    app.router.add_route('GET', '/fledge/package/log', package_log.get_logs)
    app.router.add_route('GET', '/fledge/package/log/{name}', package_log.get_log_by_name)
    app.router.add_route('GET', '/fledge/package/{action}/status', package_log.get_package_status)

    # Plugins (install, discovery, update, delete)
    app.router.add_route('GET', '/fledge/plugins/installed', plugins_discovery.get_plugins_installed)
    app.router.add_route('GET', '/fledge/plugins/available', plugins_discovery.get_plugins_available)
    app.router.add_route('POST', '/fledge/plugins', plugins_install.add_plugin)
    app.router.add_route('PUT', '/fledge/plugins/{type}/{name}/update', plugins_update.update_plugin)
    app.router.add_route('DELETE', '/fledge/plugins/{type}/{name}', plugins_remove.remove_plugin)

    # Filters 
    app.router.add_route('POST', '/fledge/filter', filters.create_filter)
    app.router.add_route('PUT', '/fledge/filter/{user_name}/pipeline', filters.add_filters_pipeline)
    app.router.add_route('GET', '/fledge/filter/{user_name}/pipeline', filters.get_filter_pipeline)
    app.router.add_route('GET', '/fledge/filter/{filter_name}', filters.get_filter)
    app.router.add_route('GET', '/fledge/filter', filters.get_filters)
    app.router.add_route('DELETE', '/fledge/filter/{user_name}/pipeline', filters.delete_filter_pipeline)
    app.router.add_route('DELETE', '/fledge/filter/{filter_name}', filters.delete_filter)

    # Notification
    app.router.add_route('GET', '/fledge/notification', notification.get_notifications)
    app.router.add_route('GET', '/fledge/notification/plugin', notification.get_plugin)
    app.router.add_route('GET', '/fledge/notification/type', notification.get_type)
    app.router.add_route('GET', '/fledge/notification/{notification_name}', notification.get_notification)
    app.router.add_route('POST', '/fledge/notification', notification.post_notification)
    app.router.add_route('PUT', '/fledge/notification/{notification_name}', notification.put_notification)
    app.router.add_route('DELETE', '/fledge/notification/{notification_name}', notification.delete_notification)

    # Snapshot plugins
    app.router.add_route('GET', '/fledge/snapshot/plugins', snapshot_plugins.get_snapshot)
    app.router.add_route('POST', '/fledge/snapshot/plugins', snapshot_plugins.post_snapshot)
    app.router.add_route('PUT', '/fledge/snapshot/plugins/{id}', snapshot_plugins.put_snapshot)
    app.router.add_route('DELETE', '/fledge/snapshot/plugins/{id}', snapshot_plugins.delete_snapshot)

    # Snapshot config
    app.router.add_route('GET', '/fledge/snapshot/category', snapshot_table.get_snapshot)
    app.router.add_route('POST', '/fledge/snapshot/category', snapshot_table.post_snapshot)
    app.router.add_route('PUT', '/fledge/snapshot/category/{id}', snapshot_table.put_snapshot)
    app.router.add_route('DELETE', '/fledge/snapshot/category/{id}', snapshot_table.delete_snapshot)
    app.router.add_route('GET', '/fledge/snapshot/schedule', snapshot_table.get_snapshot)
    app.router.add_route('POST', '/fledge/snapshot/schedule', snapshot_table.post_snapshot)
    app.router.add_route('PUT', '/fledge/snapshot/schedule/{id}', snapshot_table.put_snapshot)
    app.router.add_route('DELETE', '/fledge/snapshot/schedule/{id}', snapshot_table.delete_snapshot)

    # Repo configure
    app.router.add_route('POST', '/fledge/repository', configure_repo.add_package_repo)

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
