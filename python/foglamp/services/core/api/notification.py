# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import json
import urllib.parse
import aiohttp
from aiohttp import web

from foglamp.common import utils
from foglamp.common import logger
from foglamp.common.service_record import ServiceRecord
from foglamp.common.storage_client.payload_builder import PayloadBuilder
from foglamp.common.storage_client.exceptions import StorageServerError
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.services.core import connect
from foglamp.services.core.service_registry.service_registry import ServiceRegistry
from foglamp.services.core.service_registry import exceptions as service_registry_exceptions
from foglamp.common.audit_logger import AuditLogger

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2018 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -------------------------------------------------------------------------------
    | GET                            | /foglamp/notification/plugin               |
    | GET POST PUT DELETE            | /foglamp/notification                      |
    -------------------------------------------------------------------------------
"""

_logger = logger.setup()
NOTIFICATION_TYPE = ["one shot", "retriggered", "toggled"]

async def get_plugin(request):
    """ GET lists of rule plugins and delivery plugins

    :Example:
        curl -X GET http://localhost:8081/foglamp/notification/plugin
    """
    try:
        notification_service = ServiceRegistry.get(s_type=ServiceRecord.Type.Notification.name)
        _address, _port = notification_service[0]._address, notification_service[0]._management_port
    except service_registry_exceptions.DoesNotExist:
        raise web.HTTPNotFound(reason="No Notification service available.")

    try:
        url = 'http://{}:{}/foglamp/notification/rules'.format(_address, _port)
        rule_plugins = json.loads(await _hit_get_url(url))

        url = 'http://{}:{}/foglamp/notification/delivery'.format(_address, _port)
        delivery_plugins = json.loads(await _hit_get_url(url))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=ex)
    else:
        return web.json_response({'rules': rule_plugins, 'delivery': delivery_plugins})


async def get_notification(request):
    """ GET an existing notification

    :Example:
        curl -X GET http://localhost:8081/foglamp/notification/<notification_name>
    """
    try:
        notif = request.match_info.get('notification_name', None)
        if notif is None:
            raise ValueError("Notification name is required.")

        notification = {}
        storage = connect.get_storage_async()
        config_mgr = ConfigurationManager(storage)
        notification_config = await config_mgr._read_category_val(notif)
        if notification_config:
            rule_config = await config_mgr._read_category_val("rule{}".format(notif))
            delivery_config = await config_mgr._read_category_val("delivery{}".format(notif))
            notification = {
                "name": notification_config['name']['value'],
                "description": notification_config['description']['value'],
                "rule": notification_config['rule']['value'],
                "ruleConfig": rule_config,
                "channel": notification_config['channel']['value'],
                "deliveryConfig": delivery_config,
                "notificationType": notification_config['notification_type']['value'],
                "enable": notification_config['enable']['value'],
            }
    except ValueError as ex:
        raise web.HTTPBadRequest(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=ex)
    else:
        return web.json_response({'notification': notification})


async def get_notifications(request):
    """ GET list of notifications

    :Example:
        curl -X GET http://localhost:8081/foglamp/notification
    """
    try:
        storage = connect.get_storage_async()
        config_mgr = ConfigurationManager(storage)
        all_notifications = await config_mgr._read_all_child_category_names("Notifications")
        notifications = []
        for notification in all_notifications:
            notification_config = await config_mgr._read_category_val(notification['child'])
            notification = {
                "name": notification_config['name']['value'],
                "rule": notification_config['rule']['value'],
                "channel": notification_config['channel']['value'],
                "notificationType": notification_config['notification_type']['value'],
                "enable": notification_config['enable']['value'],
            }
            notifications.append(notification)
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=ex)
    else:
        return web.json_response({'notifications': notifications})


async def post_notification(request):
    """
    Create a new notification to run a specific plugin

    :Example:
             curl -X POST http://localhost:8081/foglamp/notification -d '{"name": "Test Notification", "description":"Test Notification", "rule": "threshold", "channel": "email", "notification_type": "one shot", "enabled": false}'
             curl -X POST http://localhost:8081/foglamp/notification -d '{"name": "Test Notification", "description":"Test Notification", "rule": "threshold", "channel": "email", "notification_type": "one shot", "enabled": false, "rule_config": {}, "delivery_config": {}}'
    """
    try:
        notification_service = ServiceRegistry.get(s_type=ServiceRecord.Type.Notification.name)
        _address, _port = notification_service[0]._address, notification_service[0]._management_port
    except service_registry_exceptions.DoesNotExist:
        raise web.HTTPNotFound(reason="No Notification service available.")

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
        rule_config = data.get('rule_config', {})
        delivery_config = data.get('delivery_config', {})

        if name is None:
            raise ValueError('Missing name property in payload.')
        if description is None:
            raise ValueError('Missing description property in payload.')
        if rule is None:
            raise ValueError('Missing rule property in payload.')
        if channel is None:
            raise ValueError('Missing channel property in payload.')
        if notification_type is None:
            raise ValueError('Missing notification_type property in payload.')

        if utils.check_reserved(name) is False:
            raise ValueError('Invalid name property in payload.')
        if utils.check_reserved(rule) is False:
            raise ValueError('Invalid rule property in payload.')
        if utils.check_reserved(channel) is False:
            raise ValueError('Invalid channel property in payload.')
        if notification_type not in NOTIFICATION_TYPE:
            raise ValueError('Invalid notification_type property in payload.')

        if enabled is not None:
            if enabled not in ['true', 'false', True, False]:
                raise ValueError('Only "true", "false", true, false are allowed for value of enabled.')
        is_enabled = "true" if ((type(enabled) is str and enabled.lower() in ['true']) or (
            (type(enabled) is bool and enabled is True))) else "false"

        try:
            # Get default config for rule and channel plugins
            url = '{}/plugin'.format(request.url)
            list_plugins = json.loads(await _hit_get_url(url))
            rule_plugin_config = list_plugins['rules'][rule]
            delivery_plugin_config = list_plugins['delivery'][channel]
        except KeyError:
            raise ValueError("Invalid rule plugin:[{}] and/or delivery plugin:[{}] supplied.".format(rule, channel))

        # First create templates for notification and rule, channel plugins
        post_url = 'http://{}:{}/foglamp/notification/{}'.format(_address, _port, urllib.parse.quote(name))
        await _hit_post_url(post_url)  # Create Notification template
        post_url = 'http://{}:{}/foglamp/notification/{}/rule/{}'.format(_address, _port, urllib.parse.quote(name), urllib.parse.quote(rule))
        await _hit_post_url(post_url)  # Create Notification rule template
        post_url = 'http://{}:{}/foglamp/notification/{}/delivery/{}'.format(_address, _port, urllib.parse.quote(name), urllib.parse.quote(channel))
        await _hit_post_url(post_url)  # Create Notification delivery template

        # Create configurations
        storage = connect.get_storage_async()
        config_mgr = ConfigurationManager(storage)
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
                "options": NOTIFICATION_TYPE,
                "default": notification_type,
            },
            "enable": {
                "description": "Enabled",
                "type": "boolean",
                "default": is_enabled,
            }
        }
        await _create_configurations(storage, config_mgr, name, notification_config,
                                     rule, rule_plugin_config, rule_config,
                                     channel, delivery_plugin_config, delivery_config)
    except ValueError as ex:
        raise web.HTTPBadRequest(reason=str(ex))
    except Exception as e:
        raise web.HTTPInternalServerError(reason=str(e))
    else:
        return web.json_response({'result': "Notification {} created successfully".format(name)})


async def put_notification(request):
    """
    Update an existing notification

    :Example:
             curl -X PUT http://localhost:8081/foglamp/notification/<notification_name> -d '{"description":"Test Notification", "rule": "threshold", "channel": "email", "notification_type": "one shot", "enabled": false}'
             curl -X PUT http://localhost:8081/foglamp/notification/<notification_name> -d '{"description":"Test Notification", "rule": "threshold", "channel": "email", "notification_type": "one shot", "enabled": false, "rule_config": {}, "delivery_config": {}}'
    """
    try:
        notification_service = ServiceRegistry.get(s_type=ServiceRecord.Type.Notification.name)
        _address, _port = notification_service[0]._address, notification_service[0]._management_port
    except service_registry_exceptions.DoesNotExist:
        raise web.HTTPNotFound(reason="No Notification service available.")

    try:
        notif = request.match_info.get('notification_name', None)
        if notif is None:
            raise ValueError("Notification name is required for updation.")

        # TODO: Stop notification before update

        data = await request.json()
        if not isinstance(data, dict):
            raise ValueError('Data payload must be a valid JSON')

        description = data.get('description', None)
        rule = data.get('rule', None)
        channel = data.get('channel', None)
        notification_type = data.get('notification_type', None)
        enabled = data.get('enabled', None)
        rule_config = data.get('rule_config', {})
        delivery_config = data.get('delivery_config', {})

        storage = connect.get_storage_async()
        config_mgr = ConfigurationManager(storage)

        current_config = await config_mgr._read_category_val(notif)
        if description is None:
            description = current_config['description']['value']
        if rule is None:
            rule = current_config['rule']['value']
        if channel is None:
            channel = current_config['channel']['value']
        if notification_type is None:
            notification_type = current_config['notification_type']['value']

        if utils.check_reserved(notif) is False:
            raise ValueError('Invalid notification name parameter.')
        if utils.check_reserved(rule) is False:
            raise ValueError('Invalid rule property in payload.')
        if utils.check_reserved(channel) is False:
            raise ValueError('Invalid channel property in payload.')
        if notification_type not in NOTIFICATION_TYPE:
            raise ValueError('Invalid notification_type property in payload.')

        if enabled is not None:
            if enabled not in ['true', 'false', True, False]:
                raise ValueError('Only "true", "false", true, false are allowed for value of enabled.')
        is_enabled = "true" if ((type(enabled) is str and enabled.lower() in ['true']) or (
            (type(enabled) is bool and enabled is True))) else "false"

        try:
            # Get default config for rule and channel plugins
            url = str(request.url)
            url_parts = url.split("/foglamp/notification")
            url = '{}/foglamp/notification/plugin'.format(url_parts[0])
            list_plugins = json.loads(await _hit_get_url(url))
            rule_plugin_config = list_plugins['rules'][rule]
            delivery_plugin_config = list_plugins['delivery'][channel]
        except KeyError:
            raise ValueError("Invalid rule plugin:[{}] and/or delivery plugin:[{}] supplied.".format(rule, channel))

        # Update configurations
        notification_config = {
            "name": {
                "description": "The name of this notification",
                "type": "string",
                "default": notif,
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
                "options": NOTIFICATION_TYPE,
                "default": notification_type,
            },
            "enable": {
                "description": "Enabled",
                "type": "boolean",
                "default": is_enabled,
            }
        }
        await _update_configurations(config_mgr, notif, notification_config, rule_config, delivery_config)
    except ValueError as ex:
        raise web.HTTPBadRequest(reason=str(ex))
    except Exception as e:
        raise web.HTTPInternalServerError(reason=str(e))
    else:
        # TODO: Start notification after update
        return web.json_response({'result': "Notification {} updated successfully".format(notif)})


async def delete_notification(request):
    """ Delete an existing notification

    :Example:
        curl -X DELETE http://localhost:8081/foglamp/notification/<notification_name>
    """
    try:
        notification_service = ServiceRegistry.get(s_type=ServiceRecord.Type.Notification.name)
        _address, _port = notification_service[0]._address, notification_service[0]._management_port
    except service_registry_exceptions.DoesNotExist:
        raise web.HTTPNotFound(reason="No Notification service available.")

    try:
        notif = request.match_info.get('notification_name', None)
        if notif is None:
            raise ValueError("Notification name is required for deletion.")

        url = str(request.url)
        url_parts = url.split("/foglamp/notification")
        url = '{}/foglamp/notification/{}'.format(url_parts[0], urllib.parse.quote(notif))
        notification = json.loads(await _hit_get_url(url))

        # TODO: Stop notification before deletion

        # Removes the child categories for the rule and delivery plugins, Removes the category for the notification itself
        storage = connect.get_storage_async()
        config_mgr = ConfigurationManager(storage)
        await _delete_configuration(storage, config_mgr, notif)

        audit = AuditLogger(storage)
        await audit.information('NTFDL', notification)
    except ValueError as ex:
        raise web.HTTPBadRequest(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=str(ex))
    else:
        return web.json_response({'result': 'notification {} deleted successfully.'.format(notif)})


async def _hit_get_url(get_url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(get_url) as resp:
                status_code = resp.status
                jdoc = await resp.text()
                if status_code not in range(200, 209):
                    _logger.error("Error code: %d, reason: %s, details: %s, url: %s", resp.status, resp.reason, jdoc, get_url)
                    raise StorageServerError(code=resp.status, reason=resp.reason, error=jdoc)
    except Exception:
        raise
    else:
        return jdoc


async def _hit_post_url(post_url, data=None):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(post_url, data=data) as resp:
                status_code = resp.status
                jdoc = await resp.text()
                if status_code not in range(200, 209):
                    _logger.error("Error code: %d, reason: %s, details: %s, url: %s", resp.status, resp.reason, jdoc, post_url)
                    raise StorageServerError(code=resp.status, reason=resp.reason, error=jdoc)
    except Exception:
        raise
    else:
        return jdoc


async def _create_configurations(storage, config_mgr, name, notification_config,
                                 rule, rule_plugin_config, rule_config,
                                 channel, delivery_plugin_config, delivery_config):
    try:
        # Main notification - Create a main notification configuration category
        category_desc = notification_config['description']['default']
        await config_mgr.create_category(category_name=name,
                                         category_description=category_desc,
                                         category_value=notification_config,
                                         keep_original_items=True)
        # Create the parent category for all Notifications
        await config_mgr.create_category("Notifications", {}, "Notifications", True)
        await config_mgr.create_child_category("Notifications", [name])

        # Rule - Create a rule configuration category from the configuration defined in the rule plugin
        category_desc = rule_plugin_config['plugin']['description']
        category_name = "rule{}".format(name)
        await config_mgr.create_category(category_name=category_name,
                                         category_description=category_desc,
                                         category_value=rule_plugin_config,
                                         keep_original_items=True)
        # Create the child rule category
        await config_mgr.create_child_category(name, [category_name])

        # If rule_config is in POST data, then update the value for each config item
        if rule_config is not None:
            if not isinstance(rule_config, dict):
                raise ValueError('rule_config must be a JSON object')
            for k, v in rule_config.items():
                await config_mgr.set_category_item_value_entry("rule{}".format(name), k, v['value'])

        # Delivery - Create a delivery configuration category from the configuration defined in the delivery plugin
        category_desc = delivery_plugin_config['plugin']['description']
        category_name = "delivery{}".format(name)
        await config_mgr.create_category(category_name=category_name,
                                         category_description=category_desc,
                                         category_value=delivery_plugin_config,
                                         keep_original_items=True)
        # Create the child delivery category
        await config_mgr.create_child_category(name, [category_name])

        # If delivery_config is in POST data, then update the value for each config item
        if delivery_config is not None:
            if not isinstance(delivery_config, dict):
                raise ValueError('delivery_config must be a JSON object')
            for k, v in delivery_config.items():
                await config_mgr.set_category_item_value_entry("delivery{}".format(name), k, v['value'])
    except Exception as ex:
        _logger.exception("Failed to create notification configuration. %s", str(ex))
        await _delete_configuration(storage, config_mgr, name)  # Revert configuration entry
        raise web.HTTPInternalServerError(reason='Failed to create notification configuration.')


async def _update_configurations(config_mgr, name, notification_config, rule_config, delivery_config):
    try:
        # Update main notification
        category_desc = notification_config['description']['default']
        await config_mgr.create_category(category_name=name,
                                         category_description=category_desc,
                                         category_value=notification_config,
                                         keep_original_items=True)

        # Replace rule configuration
        if rule_config != {}:
            category_desc = rule_config['plugin']['description']
            category_name = "rule{}".format(name)
            await config_mgr._update_category(category_name=category_name,
                                             category_description=category_desc,
                                             category_val=rule_config)

        # Replace delivery configuration
        if delivery_config != {}:
            category_desc = delivery_config['plugin']['description']
            category_name = "delivery{}".format(name)
            await config_mgr._update_category(category_name=category_name,
                                             category_description=category_desc,
                                             category_val=delivery_config)
    except Exception as ex:
        _logger.exception("Failed to update notification configuration. %s", str(ex))
        raise web.HTTPInternalServerError(reason='Failed to update notification configuration.')


async def _delete_configuration(storage, config_mgr, name):
    current_config = await config_mgr._read_category_val(name)
    if not current_config:
        raise ValueError('No Configuration entry found for [{}]'.format(name))
    await _delete_configuration_category(storage, name)
    await _delete_configuration_category(storage, "rule{}".format(name))
    await _delete_configuration_category(storage, "delivery{}".format(name))
    await _delete_parent_child_configuration(storage, "Notifications", name)
    await _delete_parent_child_configuration(storage, name, "rule{}".format(name))
    await _delete_parent_child_configuration(storage, name, "delivery{}".format(name))

async def _delete_configuration_category(storage, key):
    payload = PayloadBuilder().WHERE(['key', '=', key]).payload()
    await storage.delete_from_tbl('configuration', payload)

    # Removed key from configuration cache
    config_mgr = ConfigurationManager(storage)
    config_mgr._cacheManager.remove(key)


async def _delete_parent_child_configuration(storage, parent, child):
    payload = PayloadBuilder().WHERE(['parent', '=', parent]).AND_WHERE(['child', '=', child]).payload()
    await storage.delete_from_tbl('category_children', payload)
