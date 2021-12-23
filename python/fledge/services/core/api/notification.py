# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import json
import urllib.parse
import aiohttp
from aiohttp import web

from fledge.common import utils
from fledge.common import logger
from fledge.common.service_record import ServiceRecord
from fledge.common.storage_client.exceptions import StorageServerError
from fledge.common.configuration_manager import ConfigurationManager
from fledge.services.core import connect
from fledge.services.core.service_registry.service_registry import ServiceRegistry
from fledge.services.core.service_registry import exceptions as service_registry_exceptions
from fledge.common.audit_logger import AuditLogger

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2018 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -----------------------------------------------------------------------------------------------------
    | GET                            | /fledge/notification/plugin                                      |
    | GET POST PUT DELETE            | /fledge/notification                                             |
    | GET POST                       | /fledge/notification/{name}/delivery                             |
    | GET DELETE                     | /fledge/notification/{notification_name}/delivery/{channel_name} |
    -----------------------------------------------------------------------------------------------------
"""

_logger = logger.setup()
NOTIFICATION_TYPE = ["one shot", "retriggered", "toggled"]


async def get_plugin(request):
    """ GET lists of rule plugins and delivery plugins

    :Example:
        curl -X GET http://localhost:8081/fledge/notification/plugin
    """
    try:
        notification_service = ServiceRegistry.get(s_type=ServiceRecord.Type.Notification.name)
        _address, _port = notification_service[0]._address, notification_service[0]._port
    except service_registry_exceptions.DoesNotExist:
        raise web.HTTPNotFound(reason="No Notification service available.")

    try:
        url = 'http://{}:{}/notification/rules'.format(_address, _port)
        rule_plugins = json.loads(await _hit_get_url(url))

        url = 'http://{}:{}/notification/delivery'.format(_address, _port)
        delivery_plugins = json.loads(await _hit_get_url(url))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=ex)
    else:
        return web.json_response({'rules': rule_plugins, 'delivery': delivery_plugins})


async def get_type(request):
    """ GET the list of available notification types

    :Example:
        curl -X GET http://localhost:8081/fledge/notification/type
    """
    return web.json_response({'notification_type': NOTIFICATION_TYPE})


async def get_notification(request):
    """ GET an existing notification

    :Example:
        curl -X GET http://localhost:8081/fledge/notification/<notification_name>
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
                "retriggerTime": notification_config['retrigger_time']['value'],
                "enable": notification_config['enable']['value'],
            }
        else:
            raise ValueError("The Notification: {} does not exist.".format(notif))
    except ValueError as ex:
        raise web.HTTPBadRequest(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=ex)
    else:
        return web.json_response({'notification': notification})


async def get_notifications(request):
    """ GET list of notifications

    :Example:
        curl -X GET http://localhost:8081/fledge/notification
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
                "retriggerTime": notification_config['retrigger_time']['value'],
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
             curl -X POST http://localhost:8081/fledge/notification -d '{"name": "Test Notification", "description":"Test Notification", "rule": "threshold", "channel": "email", "notification_type": "one shot", "enabled": false}'
             curl -X POST http://localhost:8081/fledge/notification -d '{"name": "Test Notification", "description":"Test Notification", "rule": "threshold", "channel": "email", "notification_type": "one shot", "enabled": false, "rule_config": {}, "delivery_config": {}}'
    """
    try:
        notification_service = ServiceRegistry.get(s_type=ServiceRecord.Type.Notification.name)
        _address, _port = notification_service[0]._address, notification_service[0]._port
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
        retrigger_time = data.get('retrigger_time', None)

        try:
            if retrigger_time:
                if float(retrigger_time) > 0 and float(retrigger_time).is_integer():
                    pass
                else:
                    raise ValueError
        except ValueError:
            raise ValueError('Invalid retrigger_time property in payload.')

        if name is None or name.strip() == "":
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

        storage = connect.get_storage_async()
        config_mgr = ConfigurationManager(storage)
        curr_config = await config_mgr.get_category_all_items(name)

        if curr_config is not None:
            raise ValueError("A Category with name {} already exists.".format(name))

        try:
            # Get default config for rule and channel plugins
            url = '{}/plugin'.format(request.url)
            try:
                # When authentication is mandatory we need to pass token in request header
                auth_token = request.token
            except AttributeError:
                auth_token = None

            list_plugins = json.loads(await _hit_get_url(url, auth_token))
            r = list(filter(lambda rules: rules['name'] == rule, list_plugins['rules']))
            c = list(filter(lambda channels: channels['name'] == channel, list_plugins['delivery']))
            if len(r) == 0 or len(c) == 0: raise KeyError
            rule_plugin_config = r[0]['config']
            delivery_plugin_config = c[0]['config']
        except KeyError:
            raise ValueError("Invalid rule plugin {} and/or delivery plugin {} supplied.".format(rule, channel))

        # Verify if rule_config contains valid keys
        if rule_config != {}:
            for k, v in rule_config.items():
                if k not in rule_plugin_config:
                    raise ValueError("Invalid key {} in rule_config {} supplied for plugin {}.".format(k, rule_config, rule))

        # Verify if delivery_config contains valid keys
        if delivery_config != {}:
            for k, v in delivery_config.items():
                if k not in delivery_plugin_config:
                    raise ValueError(
                        "Invalid key {} in delivery_config {} supplied for plugin {}.".format(k, delivery_config, channel))

        # First create templates for notification and rule, channel plugins
        post_url = 'http://{}:{}/notification/{}'.format(_address, _port, urllib.parse.quote(name))
        await _hit_post_url(post_url)  # Create Notification template
        post_url = 'http://{}:{}/notification/{}/rule/{}'.format(_address, _port, urllib.parse.quote(name),
                                                                         urllib.parse.quote(rule))
        await _hit_post_url(post_url)  # Create Notification rule template
        post_url = 'http://{}:{}/notification/{}/delivery/{}'.format(_address, _port, urllib.parse.quote(name),
                                                                             urllib.parse.quote(channel))
        await _hit_post_url(post_url)  # Create Notification delivery template

        # Create configurations
        notification_config = {
            "description": description,
            "rule": rule,
            "channel": channel,
            "notification_type": notification_type,
            "enable": is_enabled,
        }
        if retrigger_time:
            notification_config["retrigger_time"] = retrigger_time

        await _update_configurations(config_mgr, name, notification_config, rule_config, delivery_config)

        audit = AuditLogger(storage)
        await audit.information('NTFAD', {"name": name})
    except ValueError as ex:
        raise web.HTTPBadRequest(reason=str(ex))
    except Exception as e:
        raise web.HTTPInternalServerError(reason=str(e))
    else:
        return web.json_response({'result': "Notification {} created successfully".format(name)})


class NotFoundError(Exception):
    pass


async def put_notification(request):
    """
    Update an existing notification

    :Example:
             curl -X PUT http://localhost:8081/fledge/notification/<notification_name> -d '{"description":"Test Notification modified"}'
             curl -X PUT http://localhost:8081/fledge/notification/<notification_name> -d '{"rule": "threshold", "channel": "email"}'
             curl -X PUT http://localhost:8081/fledge/notification/<notification_name> -d '{"notification_type": "one shot", "enabled": false}'
             curl -X PUT http://localhost:8081/fledge/notification/<notification_name> -d '{"enabled": false}'
             curl -X PUT http://localhost:8081/fledge/notification/<notification_name> -d '{"retrigger_time":"30"}'
             curl -X PUT http://localhost:8081/fledge/notification/<notification_name> -d '{"description":"Test Notification", "rule": "threshold", "channel": "email", "notification_type": "one shot", "enabled": false, "rule_config": {}, "delivery_config": {}}'
    """
    try:
        notification_service = ServiceRegistry.get(s_type=ServiceRecord.Type.Notification.name)
        _address, _port = notification_service[0]._address, notification_service[0]._port
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
        retrigger_time = data.get('retrigger_time', None)

        try:
            if retrigger_time:
                if float(retrigger_time) > 0 and float(retrigger_time).is_integer():
                    pass
                else:
                    raise ValueError
        except ValueError:
            raise ValueError('Invalid retrigger_time property in payload.')

        if utils.check_reserved(notif) is False:
            raise ValueError('Invalid notification instance name.')
        if rule is not None and utils.check_reserved(rule) is False:
            raise ValueError('Invalid rule property in payload.')
        if channel is not None and utils.check_reserved(channel) is False:
            raise ValueError('Invalid channel property in payload.')
        if notification_type is not None and notification_type not in NOTIFICATION_TYPE:
            raise ValueError('Invalid notification_type property in payload.')

        if enabled is not None:
            if enabled not in ['true', 'false', True, False]:
                raise ValueError('Only "true", "false", true, false are allowed for value of enabled.')
        is_enabled = "true" if ((type(enabled) is str and enabled.lower() in ['true']) or (
            (type(enabled) is bool and enabled is True))) else "false"

        storage = connect.get_storage_async()
        config_mgr = ConfigurationManager(storage)

        current_config = await config_mgr._read_category_val(notif)

        if current_config is None:
            raise NotFoundError('No {} notification instance found'.format(notif))

        rule_changed = True if rule is not None and rule != current_config['rule']['value'] else False
        channel_changed = True if channel is not None and channel != current_config['channel']['value'] else False

        try:
            # Get default config for rule and channel plugins
            url = str(request.url)
            url_parts = url.split("/fledge/notification")
            url = '{}/fledge/notification/plugin'.format(url_parts[0])
            try:
                # When authentication is mandatory we need to pass token in request header
                auth_token = request.token
            except AttributeError:
                auth_token = None

            list_plugins = json.loads(await _hit_get_url(url, auth_token))
            search_rule = rule if rule_changed else current_config['rule']['value']
            r = list(filter(lambda rules: rules['name'] == search_rule, list_plugins['rules']))
            if len(r) == 0:
                raise KeyError
            rule_plugin_config = r[0]['config']

            search_channel = channel if channel_changed else current_config['channel']['value']
            c = list(filter(lambda channels: channels['name'] == search_channel, list_plugins['delivery']))
            if len(c) == 0:
                raise KeyError
            delivery_plugin_config = c[0]['config']
        except KeyError:
            raise ValueError("Invalid rule plugin:{} and/or delivery plugin:{} supplied.".format(rule, channel))

        # Verify if rule_config contains valid keys
        if rule_config != {}:
            for k, v in rule_config.items():
                if k not in rule_plugin_config:
                    raise ValueError("Invalid key:{} in rule plugin:{}".format(k, rule_plugin_config))

        # Verify if delivery_config contains valid keys
        if delivery_config != {}:
            for k, v in delivery_config.items():
                if k not in delivery_plugin_config:
                    raise ValueError(
                        "Invalid key:{} in delivery plugin:{}".format(k, delivery_plugin_config))

        if rule_changed:  # A new rule has been supplied
            category_desc = rule_plugin_config['plugin']['description']
            category_name = "rule{}".format(notif)
            await config_mgr.create_category(category_name=category_name,
                                             category_description=category_desc,
                                             category_value=rule_plugin_config,
                                             keep_original_items=False)
        if channel_changed:  # A new delivery has been supplied
            category_desc = delivery_plugin_config['plugin']['description']
            category_name = "delivery{}".format(notif)
            await config_mgr.create_category(category_name=category_name,
                                             category_description=category_desc,
                                             category_value=delivery_plugin_config,
                                             keep_original_items=False)
        notification_config = {}
        if description is not None:
            notification_config.update({"description": description})
        if rule is not None:
            notification_config.update({"rule": rule})
        if channel is not None:
            notification_config.update({"channel": channel})
        if notification_type is not None:
            notification_config.update({"notification_type": notification_type})
        if enabled is not None:
            notification_config.update({"enable": is_enabled})
        if retrigger_time:
            notification_config["retrigger_time"] = retrigger_time
        await _update_configurations(config_mgr, notif, notification_config, rule_config, delivery_config)
    except ValueError as e:
        raise web.HTTPBadRequest(reason=str(e))
    except NotFoundError as e:
        raise web.HTTPNotFound(reason=str(e))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=str(ex))
    else:
        # TODO: Start notification after update
        return web.json_response({'result': "Notification {} updated successfully".format(notif)})


async def delete_notification(request):
    """ Delete an existing notification

    :Example:
        curl -X DELETE http://localhost:8081/fledge/notification/<notification_name>
    """
    try:
        notification_service = ServiceRegistry.get(s_type=ServiceRecord.Type.Notification.name)
        _address, _port = notification_service[0]._address, notification_service[0]._port
    except service_registry_exceptions.DoesNotExist:
        raise web.HTTPNotFound(reason="No Notification service available.")

    try:
        notif = request.match_info.get('notification_name', None)
        if notif is None:
            raise ValueError("Notification name is required for deletion.")

        # Stop & remove notification
        url = 'http://{}:{}/notification/{}'.format(_address, _port, urllib.parse.quote(notif))

        notification = json.loads(await _hit_delete_url(url))

        # Removes the child categories for the rule and delivery plugins, Removes the category for the notification itself
        storage = connect.get_storage_async()
        config_mgr = ConfigurationManager(storage)

        await config_mgr.delete_category_and_children_recursively(notif)

        audit = AuditLogger(storage)
        await audit.information('NTFDL', {"name": notif})
    except ValueError as ex:
        raise web.HTTPBadRequest(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=str(ex))
    else:
        return web.json_response({'result': 'Notification {} deleted successfully.'.format(notif)})


async def _hit_get_url(get_url, token=None):
    headers = {"Authorization": token} if token else None
    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
            async with session.get(get_url, headers=headers) as resp:
                status_code = resp.status
                jdoc = await resp.text()
                if status_code not in range(200, 209):
                    _logger.error("Error code: %d, reason: %s, details: %s, url: %s", resp.status, resp.reason, jdoc,
                                  get_url)
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
                    _logger.error("Error code: %d, reason: %s, details: %s, url: %s", resp.status, resp.reason, jdoc,
                                  post_url)
                    raise StorageServerError(code=resp.status, reason=resp.reason, error=jdoc)
    except Exception:
        raise
    else:
        return jdoc


async def _update_configurations(config_mgr, name, notification_config, rule_config, delivery_config):
    try:
        # Update main notification
        if notification_config != {}:
            await config_mgr.update_configuration_item_bulk(name, notification_config)
        # Replace rule configuration
        if rule_config != {}:
            category_name = "rule{}".format(name)
            await config_mgr.update_configuration_item_bulk(category_name, rule_config)
        # Replace delivery configuration
        if delivery_config != {}:
            category_name = "delivery{}".format(name)
            await config_mgr.update_configuration_item_bulk(category_name, delivery_config)
    except Exception as ex:
        _logger.exception("Failed to update notification configuration. %s", str(ex))
        raise web.HTTPInternalServerError(reason='Failed to update notification configuration. {}'.format(ex))


async def _hit_delete_url(delete_url, data=None):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.delete(delete_url, data=data) as resp:
                status_code = resp.status
                jdoc = await resp.text()
                if status_code not in range(200, 209):
                    _logger.error("Error code: %d, reason: %s, details: %s, url: %s",
                                  resp.status,
                                  resp.reason,
                                  jdoc,
                                  delete_url)
                    raise StorageServerError(code=resp.status,
                                             reason=resp.reason,
                                             error=jdoc)
    except Exception:
        raise
    else:
        return jdoc


async def _get_channels(cfg_mgr: ConfigurationManager, notify_instance: str) -> list:
    """ Retrieve all  channels
        the first having the naming : delivery +  "NotificationName"
        the extras                  : "NotificationName" + _channel_ + "DeliveryName"
    :Example:
        deliveryTooHot1 (mqtt)
        TooHot1_channel_asset_2
        TooHot1_channel_mqtt_3

    """

    naming_first = "delivery{}".format(notify_instance)
    list_first = await _get_channels_type(cfg_mgr, notify_instance, naming_first, False)

    naming_extra = "{}_channel_".format(notify_instance)
    list_extra = await _get_channels_type(cfg_mgr, notify_instance, naming_extra, True)

    full_list = []

    full_list.extend(list_first)
    full_list.extend(list_extra)

    return full_list


async def _get_channels_type(cfg_mgr: ConfigurationManager, notify_instance: str, prefix: str, extra: bool) -> list:
    """ Retrieve a type of channel
    """

    all_categories = await cfg_mgr.get_all_category_names()

    categories = [c[0] for c in all_categories if c[0].startswith(prefix)]
    channel_names = []

    if categories:
        for ch in categories:
            if ch.startswith(prefix):

                category_info = await cfg_mgr._read_category(ch)

                if extra:
                    try:
                        #// FIXME_I:
                        #delivery_name = ch[len(prefix):] + "/" + category_info['value']['plugin']['value']
                        delivery_name = ch[len(prefix):]
                    except:
                        delivery_name = ch[len(prefix):]
                else:
                    try:
                        delivery_name = ch + "/" + category_info['value']['plugin']['value']
                    except:
                        delivery_name = ch

                channel_names.append(delivery_name)

    return channel_names


async def get_delivery_channels(request: web.Request) -> web.Response:
    """ Retrieve a list of all the additional notification channels for the given notification

    :Example:
        curl -sX GET http://localhost:8081/fledge/notification/overspeed/delivery
    """
    try:
        notification_instance_name = request.match_info.get('notification_name', None)
        storage = connect.get_storage_async()
        config_mgr = ConfigurationManager(storage)
        notification_config = await config_mgr._read_category_val(notification_instance_name)
        if notification_config:
            channels = await _get_channels(config_mgr, notification_instance_name)
        else:
            raise NotFoundError("{} notification instance does not exist".format(notification_instance_name))
    except NotFoundError as err:
        msg = str(err)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({"channels": channels})


async def post_delivery_channel(request: web.Request) -> web.Response:
    """ Add a new delivery channel to an existing notification
        :Example:
            curl -sX POST http://localhost:8081/fledge/notification/overspeed/delivery -d '{"name": "coolant", "config": {"action": {"description": "Perform a control action to turn pump", "type": "boolean", "default": "false"}}}'
    """
    try:
        notification_instance_name = request.match_info.get('notification_name', None)

        data = await request.json()
        channel_name = data.get('name', None)
        channel_description = data.get('description', "{} delivery channel".format(channel_name))
        channel_config = data.get('config', {})


        if channel_name is None:
            raise ValueError('Missing name property in payload')
        channel_name = channel_name.strip()
        if channel_name == "":
            raise ValueError('Name should not be empty')
        if utils.check_reserved(channel_name) is False:
            raise ValueError('name should not use reserved words')
        if not isinstance(channel_config, dict):
            raise ValueError('config must be a valid JSON')
        storage = connect.get_storage_async()
        config_mgr = ConfigurationManager(storage)
        notification_config = await config_mgr._read_category_val(notification_instance_name)

        if notification_config:

            channel_name = "{}_channel_{}".format(notification_instance_name, channel_name)
            # Create category
            await config_mgr.create_category(category_name=channel_name, category_description=channel_description,
                                             category_value=channel_config)

            category_info = await config_mgr.get_category_all_items(category_name=channel_name)

            if category_info is None:
                raise NotFoundError('No such {} category found'.format(channel_name))
            # Create parent-child relationship
            await config_mgr.create_child_category(notification_instance_name, [channel_name])

        else:
            raise NotFoundError("{} notification instance does not exist".format(notification_instance_name))
    except ValueError as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except NotFoundError as err:
        msg = str(err)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({"category": channel_name, "description": channel_description,
                                  "config": channel_config})


async def get_delivery_channel_configuration(request: web.Request) -> web.Response:
    """ Retrieve the configuration of a delivery channel

    :Example:
        curl -sX GET http://localhost:8081/fledge/notification/overspeed/delivery/coolant
    """
    notification_instance_name = request.match_info.get('notification_name', None)
    channel_name = request.match_info.get('channel_name', None)
    storage = connect.get_storage_async()
    config_mgr = ConfigurationManager(storage)
    try:
        category_name = "{}_channel_{}".format(notification_instance_name, channel_name)
        notification_config = await config_mgr._read_category_val(notification_instance_name)
        if notification_config:
            channels = await _get_channels(config_mgr, notification_instance_name)
            if channel_name in channels:
                channel_config = await config_mgr._read_category_val(category_name)
            else:
                raise NotFoundError("{} channel does not exist".format(channel_name))
        else:
            raise NotFoundError("{} notification instance does not exist".format(notification_instance_name))
    except NotFoundError as err:
        msg = str(err)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({"config": channel_config})


async def delete_delivery_channel(request: web.Request) -> web.Response:
    """ Remove a delivery channel

    :Example:
        curl -sX DELETE http://localhost:8081/fledge/notification/overspeed/delivery/coolant
    """
    notification_instance_name = request.match_info.get('notification_name', None)
    channel_name = request.match_info.get('channel_name', None)
    storage = connect.get_storage_async()
    config_mgr = ConfigurationManager(storage)
    try:
        category_name = "{}_channel_{}".format(notification_instance_name, channel_name)
        notification_config = await config_mgr._read_category_val(notification_instance_name)

        if notification_config:
            channels = await _get_channels(config_mgr, notification_instance_name)

            if channel_name in channels:
                await config_mgr.delete_category_and_children_recursively(category_name)
                # Get channels list again as relation gets deleted above
                channels = await _get_channels(config_mgr, notification_instance_name)
            else:
                raise NotFoundError("{} channel does not exist".format(channel_name))
        else:
            raise NotFoundError("{} notification instance does not exist".format(notification_instance_name))
    except NotFoundError as err:
        msg = str(err)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({"channels": channels})
