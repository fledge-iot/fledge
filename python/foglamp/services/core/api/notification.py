# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import asyncio
import datetime
from aiohttp import web
import uuid

from foglamp.common import utils
from foglamp.common import logger
from foglamp.common.service_record import ServiceRecord
from foglamp.common.storage_client.payload_builder import PayloadBuilder
from foglamp.common.storage_client.exceptions import StorageServerError
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.services.core import server
from foglamp.services.core import connect
from foglamp.services.core.api import utils as apiutils
from foglamp.services.core.scheduler.entities import StartUpSchedule
from foglamp.services.core.service_registry.service_registry import ServiceRegistry
from foglamp.services.core.service_registry import exceptions as service_registry_exceptions


__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -------------------------------------------------------------------------------
    | POST PUT GET DELETE            | /foglamp/notification                      |
    -------------------------------------------------------------------------------
"""

_logger = logger.setup()


async def get_notification(request):
    """ GET an existing notification or list of notifications from Service registry

    :Example:
        curl -X GET http://localhost:8081/foglamp/notification
        curl -X GET http://localhost:8081/foglamp/notification/<notification name>
    """

    try:
        notif = request.match_info.get('notification_name', None)
        all_notifications = False
        if notif is None or notif.strip() == '':
            all_notifications = True

        try:
            if all_notifications is True:
                notifications = ServiceRegistry.get(s_type=ServiceRecord.Type.Notification)
            else:
                notifications = ServiceRegistry.get(name=notif)
        except service_registry_exceptions.DoesNotExist:
            pass
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=ex)
    else:
        return web.json_response({'result': notifications})


async def delete_notification(request):
    """ Delete an existing notification

    :Example:
        curl -X DELETE http://localhost:8081/foglamp/notification/<notification name>
    """

    try:
        notif = request.match_info.get('notification_name', None)

        if notif is None or notif.strip() == '':
            raise web.HTTPBadRequest(reason='Missing notification_name in requested URL')

        storage = connect.get_storage_async()
        config_mgr = ConfigurationManager(storage)

        result = await get_schedule(storage, notif)
        if result['count'] == 0:
            raise web.HTTPBadRequest(reason='A notification with this name does not exist.')

        notif_schedule = result['rows'][0]
        sch_id = uuid.UUID(notif_schedule['id'])
        if notif_schedule['enabled'].lower() == 't':
            # disable it
            await server.Server.scheduler.disable_schedule(sch_id)
        # delete it
        await server.Server.scheduler.delete_schedule(sch_id)

        # delete all configuration for the notification name
        await delete_configuration(storage, config_mgr, notif)

        try:
            ServiceRegistry.get(name=notif)
        except service_registry_exceptions.DoesNotExist:
            pass
        else:
            # shutdown of notification does not actually remove it from notification registry via unregister (it just set its
            # status to Shutdown)
            while True:
                notifs = ServiceRegistry.get(name=notif)
                if notifs[0]._status == ServiceRecord.Status.Shutdown:
                    ServiceRegistry.remove_from_registry(notifs[0]._id)
                    break
                else:
                    await asyncio.sleep(1.0)
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=ex)
    else:
        return web.json_response({'result': 'notification {} deleted successfully.'.format(notif)})


async def add_notification(request):
    """
    Create a new notification to run a specific plugin

    :Example:
             curl -X POST http://localhost:8081/foglamp/notification -d '{"name": "Test Notification", "description":"Test Notification", "rule": "testrule", "channel": "email", "notification_type": "one shot", "enabled": false}'
             curl -X POST http://localhost:8081/foglamp/notification -d '{"name": "Test Notification", "description":"Test Notification", "rule": "testrule", "channel": "email", "notification_type": "one shot", "enabled": false, "ruleConfig": {}, "deliveryConfig": {}}'
    """
    try:
        data = await request.json()
        if not isinstance(data, dict):
            raise ValueError('Data payload must be a valid JSON')

        name = data.get('name', None)
        description = data.get('description', None)
        rule = data.get('rule', None)
        channel = data.get('channel', None)
        notification_type = data.get('notification_type', None)
        enabled = data.get('enabled', None)
        rule_config = data.get('ruleConfig', None)
        delivery_config = data.get('deliveryConfig', None)

        if name is None:
            raise web.HTTPBadRequest(reason='Missing name property in payload.')
        if description is None:
            raise web.HTTPBadRequest(reason='Missing description property in payload.')
        if rule is None:
            raise web.HTTPBadRequest(reason='Missing rule property in payload.')
        if channel is None:
            raise web.HTTPBadRequest(reason='Missing channel property in payload.')
        if notification_type is None:
            raise web.HTTPBadRequest(reason='Missing notification_type property in payload.')

        if utils.check_reserved(name) is False:
            raise web.HTTPBadRequest(reason='Invalid name property in payload.')
        if utils.check_reserved(rule) is False:
            raise web.HTTPBadRequest(reason='Invalid rule property in payload.')
        if utils.check_reserved(channel) is False:
            raise web.HTTPBadRequest(reason='Invalid channel property in payload.')
        if notification_type not in ["one shot", "retriggered", "toggled"]:
            raise web.HTTPBadRequest(reason='Invalid notification_type property in payload.')

        if enabled is not None:
            if enabled not in ['true', 'false', True, False]:
                raise web.HTTPBadRequest(reason='Only "true", "false", true, false are allowed for value of enabled.')
        is_enabled = True if ((type(enabled) is str and enabled.lower() in ['true']) or (
            (type(enabled) is bool and enabled is True))) else False

        storage = connect.get_storage_async()
        config_mgr = ConfigurationManager(storage)
        process_name = 'notification_c'
        script = '["services/notification_c"]'

        # First check if valid plugins have been supplied
        rule_plugin_config, delivery_plugin_config = await check_plugins(rule, channel)

        # then check that the schedule name is not already registered
        count = await check_schedules(storage, name)
        if count != 0:
            raise web.HTTPBadRequest(reason='A notification with this name already exists.')

        # Create scheduled process
        await create_scheduled_process(storage, process_name, script)

        # Create configurations
        notification_config = {
            "name": {
                "description": "The name of this notification",
                "type": "string",
                "default": name,
            },
            "description": {
                "description": "Description of this notification",
                "type": "string",
                "default": description,
            },
            "rule": {
                "description": "Rule to evaluate",
                "type": "string",
                "default": rule,
            },
            "channel": {
                "description": "Channel to send alert on",
                "type": "string",
                "default": channel,
            },
            "notification_type": {
                "description": "Type of notification",
                "type": "enumeration",
                "options": ["one shot", "retriggered", "toggled"],
                "default": notification_type,
            },
            "enable": {
                "description": "Enabled",
                "type": "boolean",
                "default": "true" if enabled else "false",
            }
        }
        await create_configurations(storage, config_mgr, name, notification_config,
                                    rule, rule_plugin_config, rule_config,
                                    channel, delivery_plugin_config, delivery_config)

        # Create schedule
        schedule = await create_schedule(storage, config_mgr, name, process_name, is_enabled)
    except ValueError as e:
        raise web.HTTPBadRequest(reason=str(e))
    else:
        return web.json_response({'name': name, 'id': str(schedule.schedule_id)})


async def update_notification(request):
    """
    Update an existing notification

    :Example:
             curl -X POST http://localhost:8081/foglamp/notification -d '{"name": "Test Notification", "description":"Test Notification", "rule": "testrule", "channel": "email", "notification_type": "one shot", "enabled": false}'
             curl -X POST http://localhost:8081/foglamp/notification -d '{"name": "Test Notification", "description":"Test Notification", "rule": "testrule", "channel": "email", "notification_type": "one shot", "enabled": false, "ruleConfig": {}, "deliveryConfig": {}}'
    """
    try:
        data = await request.json()
        if not isinstance(data, dict):
            raise ValueError('Data payload must be a valid JSON')

        name = data.get('name', None)
        description = data.get('description', None)
        rule = data.get('rule', None)
        channel = data.get('channel', None)
        notification_type = data.get('type', None)
        enabled = data.get('enabled', None)
        rule_config = data.get('ruleConfig', None)
        delivery_config = data.get('deliveryConfig', None)

        storage = connect.get_storage_async()
        config_mgr = ConfigurationManager(storage)
        process_name = 'notification_c'
        script = '["services/notification_c"]'

        if name is None:
            raise web.HTTPBadRequest(reason='Missing name property in payload.')

        # then check that the schedule name exists
        count = await check_schedules(storage, name)
        if count == 0:
            raise web.HTTPBadRequest(reason='A notification with this name DOES NOT exist.')

        current_config = await config_mgr._read_category_val(name)
        if description is None:
            description = current_config['description']['value']
        if rule is None:
            rule = current_config['rule']['value']
        if channel is None:
            channel = current_config['channel']['value']
        if notification_type is None:
            notification_type = current_config['notification_type']['value']

        if utils.check_reserved(name) is False:
            raise web.HTTPBadRequest(reason='Invalid name property in payload.')
        if utils.check_reserved(rule) is False:
            raise web.HTTPBadRequest(reason='Invalid rule property in payload.')
        if utils.check_reserved(channel) is False:
            raise web.HTTPBadRequest(reason='Invalid channel property in payload.')
        if notification_type not in ["one shot", "retriggered", "toggled"]:
            raise web.HTTPBadRequest(reason='Invalid notification_type property in payload.')

        if enabled is not None:
            if enabled not in ['true', 'false', True, False]:
                raise web.HTTPBadRequest(reason='Only "true", "false", true, false are allowed for value of enabled.')
        is_enabled = True if ((type(enabled) is str and enabled.lower() in ['true']) or (
            (type(enabled) is bool and enabled is True))) else False

        # First check if valid plugins have been supplied
        rule_plugin_config, delivery_plugin_config = await check_plugins(rule, channel)

        # Update configurations
        notification_config = {
            "name": {
                "description": "The name of this notification",
                "type": "string",
                "default": name,
            },
            "description": {
                "description": "Description of this notification",
                "type": "string",
                "default": description,
            },
            "rule": {
                "description": "Rule to evaluate",
                "type": "string",
                "default": rule,
            },
            "channel": {
                "description": "Channel to send alert on",
                "type": "string",
                "default": channel,
            },
            "notification_type": {
                "description": "Type of notification",
                "type": "enumeration",
                "options": ["one shot", "retriggered", "toggled"],
                "default": notification_type,
            },
            "enable": {
                "description": "Enabled",
                "type": "boolean",
                "default": "true" if enabled else "false",
            }
        }
        await create_configurations(storage, config_mgr, name, notification_config,
                                    rule, rule_plugin_config, rule_config,
                                    channel, delivery_plugin_config, delivery_config)

        # Update schedule
        schedule = await create_schedule(storage, config_mgr, name, process_name, is_enabled)
    except ValueError as e:
        raise web.HTTPBadRequest(reason=str(e))
    else:
        return web.json_response({'name': name, 'id': str(schedule.schedule_id)})


async def check_scheduled_processes(storage, process_name):
    payload = PayloadBuilder().SELECT("name").WHERE(['name', '=', process_name]).payload()
    result = await storage.query_tbl_with_payload('scheduled_processes', payload)
    return result['count']


async def check_schedules(storage, schedule_name):
    payload = PayloadBuilder().SELECT("schedule_name").WHERE(['schedule_name', '=', schedule_name]).payload()
    result = await storage.query_tbl_with_payload('schedules', payload)
    return result['count']


async def get_schedule(storage, schedule_name):
    payload = PayloadBuilder().SELECT(["id", "enabled"]).WHERE(['schedule_name', '=', schedule_name]).payload()
    result = await storage.query_tbl_with_payload('schedules', payload)
    return result


async def delete_configuration(storage, config_mgr, name):
    current_config = await config_mgr._read_category_val(name)
    if not current_config:
        return
    rule = current_config['rule']['value']
    channel = current_config['channel']['value']

    await delete_configuration_category(storage, name)
    await delete_configuration_category(storage, "rule{}".format(rule))
    await delete_configuration_category(storage, "delivery{}".format(channel))
    await delete_parent_child_configuration(storage, "Notifications", name)
    await delete_parent_child_configuration(storage, name, rule)
    await delete_parent_child_configuration(storage, name, channel)


async def delete_configuration_category(storage, key):
    payload = PayloadBuilder().WHERE(['key', '=', key]).payload()
    await storage.delete_from_tbl('configuration', payload)

    # Removed key from configuration cache
    config_mgr = ConfigurationManager(storage)
    config_mgr._cacheManager.remove(key)


async def delete_parent_child_configuration(storage, parent, child):
    payload = PayloadBuilder().WHERE(['parent', '=', parent]).AND_WHERE(['child', '=', child]).payload()
    await storage.delete_from_tbl('category_children', payload)


async def check_plugins(rule, channel):
    # Below line is purely for testing the API. Will be removed once support is available from C++ code for rule and delivery plugins,
    return {"plugin": {"description": "rule", "type": "string", "default": "rule"}}, {"plugin": {"description": "delivery", "type": "string", "default": "delivery"}}

    # Check if a valid rule plugin has been provided
    try:
        # Checking for C-type plugins
        plugin_info = apiutils.get_rule_plugin_info(rule)
        if plugin_info['type'] != 'notificationRule':
            msg = "Rule Plugin of {} type is not supported".format(plugin_info['type'])
            _logger.exception(msg)
            return web.HTTPBadRequest(reason=msg)
        rule_plugin_config = plugin_info['config']
        if not rule_plugin_config:
            _logger.exception("Rule Plugin %s import problem", rule)
            raise web.HTTPNotFound(reason='Rule Plugin "{}" import problem.'.format(rule))
    except Exception as ex:
        _logger.exception("Failed to fetch rule plugin configuration. %s", str(ex))
        raise web.HTTPInternalServerError(reason='Failed to fetch rule plugin configuration')

    # Check if a valid delivery plugin has been provided
    try:
        # Checking for C-type plugins
        plugin_info = apiutils.get_delivery_plugin_info(channel)
        if plugin_info['type'] != 'notificationDelivery':
            msg = "Delivery Plugin of {} type is not supported".format(plugin_info['type'])
            _logger.exception(msg)
            return web.HTTPBadRequest(reason=msg)
        delivery_plugin_config = plugin_info['config']
        if not delivery_plugin_config:
            _logger.exception("Delivery Plugin %s import problem", channel)
            raise web.HTTPNotFound(reason='Delivery Plugin "{}" import problem.'.format(channel))
    except Exception as ex:
        _logger.exception("Failed to fetch delivery plugin configuration. %s", str(ex))
        raise web.HTTPInternalServerError(reason='Failed to fetch delivery plugin configuration')
    return rule_plugin_config, delivery_plugin_config


async def create_scheduled_process(storage, process_name, script):
    # Check that the process name is not already registered
    count = await check_scheduled_processes(storage, process_name)
    if count == 0:
        # Now first create the scheduled process entry for the new service
        payload = PayloadBuilder().INSERT(name=process_name, script=script).payload()
        try:
            await storage.insert_into_tbl("scheduled_processes", payload)
        except StorageServerError as ex:
            _logger.exception("Failed to create scheduled process. %s", ex.error)
            raise web.HTTPInternalServerError(reason='Failed to create notification.')
        except Exception as ex:
            _logger.exception("Failed to create scheduled process. %s", str(ex))
            raise web.HTTPInternalServerError(reason='Failed to create notification.')


async def create_configurations(storage, config_mgr, name, notification_config,
                                rule, rule_plugin_config, rule_config,
                                channel, delivery_plugin_config, delivery_config):
    # If successful then create a configuration entry from plugin configuration
    try:
        # ---------------- Main notification - Create a main notification configuration category
        category_desc = notification_config['description']['default']
        await config_mgr.create_category(category_name=name,
                                         category_description=category_desc,
                                         category_value=notification_config,
                                         keep_original_items=True)
        # Create the parent category for all Notifications
        await config_mgr.create_category("Notifications", {}, "Notifications", True)
        refresh_cache = await config_mgr.get_category_all_items(category_name="Notifications")  # TODO: remove this asap
        await config_mgr.create_child_category("Notifications", [name])

        # ----------------Rule - Create a rule configuration category from the configuration defined in the rule plugin
        category_desc = rule_plugin_config['plugin']['description']
        category_name = "rule{}".format(name)
        await config_mgr.create_category(category_name=category_name,
                                         category_description=category_desc,
                                         category_value=rule_plugin_config,
                                         keep_original_items=True)
        # Create the child rule category
        await config_mgr.create_child_category(name, [category_name])

        # If ruleConfig is in POST data, then update the value for each config item
        if rule_config is not None:
            if not isinstance(rule_config, dict):
                raise ValueError('ruleConfig must be a JSON object')
            for k, v in rule_config.items():
                await config_mgr.set_category_item_value_entry(rule, k, v['value'])

        # ---------------- Delivery - Create a delivery configuration category from the configuration defined in the delivery plugin
        category_desc = delivery_plugin_config['plugin']['description']
        category_name = "delivery{}".format(name)
        await config_mgr.create_category(category_name=category_name,
                                         category_description=category_desc,
                                         category_value=delivery_plugin_config,
                                         keep_original_items=True)
        # Create the child delivery category
        await config_mgr.create_child_category(name, [category_name])

        # If deliveryConfig is in POST data, then update the value for each config item
        if delivery_config is not None:
            if not isinstance(delivery_config, dict):
                raise ValueError('deliveryConfig must be a JSON object')
            for k, v in delivery_config.items():
                await config_mgr.set_category_item_value_entry(channel, k, v['value'])
    except Exception as ex:
        await delete_configuration(storage, config_mgr, name)  # Revert configuration entry
        _logger.exception("Failed to create notification configuration. %s", str(ex))
        raise web.HTTPInternalServerError(reason='Failed to create notification configuration.')


async def create_schedule(storage, config_mgr, name, process_name, is_enabled):
    # If all successful then lastly add a schedule to run the new service at startup
    try:
        schedule = StartUpSchedule()
        schedule.name = name
        schedule.process_name = process_name
        schedule.repeat = datetime.timedelta(0)
        schedule.exclusive = True
        #  if "enabled" is supplied, it gets activated in save_schedule() via is_enabled flag
        schedule.enabled = False

        # Save schedule
        await server.Server.scheduler.save_schedule(schedule, is_enabled)
        schedule = await server.Server.scheduler.get_schedule_by_name(name)
    except StorageServerError as ex:
        await delete_configuration(storage, config_mgr, name)  # Revert configuration entry
        _logger.exception("Failed to create schedule. %s", ex.error)
        raise web.HTTPInternalServerError(reason='Failed to create notification.')
    except Exception as ex:
        await delete_configuration(storage, config_mgr, name)  # Revert configuration entry
        _logger.exception("Failed to create schedule. %s", str(ex))
        raise web.HTTPInternalServerError(reason='Failed to create notification.')
    return schedule
