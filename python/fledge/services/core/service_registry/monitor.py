# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

"""Fledge Monitor module"""

import asyncio
import aiohttp
import json
from fledge.common import logger
from fledge.common.audit_logger import AuditLogger
from fledge.common.configuration_manager import ConfigurationManager
from fledge.services.core.service_registry.service_registry import ServiceRegistry
from fledge.common.service_record import ServiceRecord
from fledge.services.core import connect
from fledge.common.acl_manager import ACLManager
from fledge.common.alert_manager import AlertManager

__author__ = "Ashwin Gopalakrishnan, Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class MonitorRegistry:
    """Registry to manage monitor instances"""
    _monitors = {}
    
    @classmethod
    def register(cls, monitor_id, monitor_instance):
        """Register a monitor instance with the given ID
        
        Args:
            monitor_id (str): Identifier for the monitor instance
            monitor_instance (Monitor): The monitor instance to register
        """
        cls._monitors[monitor_id] = monitor_instance
    
    @classmethod
    def get(cls, monitor_id='default'):
        """Get a monitor instance by ID
        
        Args:
            monitor_id (str): Identifier for the monitor instance
            
        Returns:
            Monitor: The monitor instance, or None if not found
        """
        return cls._monitors.get(monitor_id)
    
    @classmethod
    def unregister(cls, monitor_id='default'):
        """Unregister a monitor instance by ID
        
        Args:
            monitor_id (str): Identifier for the monitor instance to remove
        """
        return cls._monitors.pop(monitor_id, None)
    
    @classmethod
    def get_all(cls):
        """Get all registered monitor instances
        
        Returns:
            dict: Dictionary of all registered monitors
        """
        return cls._monitors.copy()


class Monitor(object):

    _DEFAULT_SLEEP_INTERVAL = 5
    """The time (in seconds) to sleep between health checks"""

    _DEFAULT_PING_TIMEOUT = 1
    """Timeout for a response from any given micro-service"""

    _DEFAULT_MAX_ATTEMPTS = 15

    _DEFAULT_RESTART_FAILED = "auto"
    """Restart failed microservice - manual/auto"""

    _logger = None

    def __init__(self):
        self._logger = logger.setup(__name__)

        self._monitor_loop_task = None  # type: asyncio.Task
        """Task for :meth:`_monitor_loop`, to ensure it has finished"""
        self._sleep_interval = None  # type: int
        """The time (in seconds) to sleep between health checks"""
        self._ping_timeout = None  # type: int
        """Timeout for a response from any given micro-service"""
        self._max_attempts = None  # type: int
        """Number of max attempts for finding a heartbeat of service"""
        self._restart_failed = None  # type: str
        """Restart failed microservice - manual/auto"""

        self.restarted_services = []
        self._acl_handler = None
        # Support bundle config
        self._support_bundle_config = None
        # Alert manager instance to raise alerts
        self._alert_manager = None
        # Configuration manager instance
        self._cfg_manager = None

    async def _sleep(self, sleep_time):
        await asyncio.sleep(sleep_time)

    async def _monitor_loop(self):
        """async Monitor loop to monitor registered services"""
        # check health of all micro-services every N seconds
        round_cnt = 0
        check_count = {}  # dict to hold current count of current status.
                          # In case of ok and running status, count will always be 1.
                          # In case of of non running statuses, count shows since when this status is set.
        while True:
            round_cnt += 1
            self._logger.debug("Starting next round#{} of service monitoring, sleep/i:{} ping/t:{} max/a:{}".format(
                round_cnt, self._sleep_interval, self._ping_timeout, self._max_attempts))
            for service_record in ServiceRegistry.all():
                if service_record._id not in check_count:
                    check_count.update({service_record._id: 1})

                # Try ping if service status is either running or doubtful (i.e. give service a chance to recover)
                if service_record._status not in [ServiceRecord.Status.Running,
                                                  ServiceRecord.Status.Unresponsive,
                                                  ServiceRecord.Status.Failed,
                                                  ServiceRecord.Status.Restart]:
                    continue

                self._logger.debug("Service: {} Status: {}".format(service_record._name, service_record._status))

                if service_record._status == ServiceRecord.Status.Failed:
                    if self._restart_failed == "auto":
                        if service_record._id not in self.restarted_services:
                            self.restarted_services.append(service_record._id)
                            asyncio.ensure_future(self.restart_service(service_record))
                    continue

                if service_record._status == ServiceRecord.Status.Restart:
                     if service_record._id not in self.restarted_services:
                         self.restarted_services.append(service_record._id)
                         asyncio.ensure_future(self.restart_service(service_record))
                     continue

                try:
                    url = "{}://{}:{}/fledge/service/ping".format(
                        service_record._protocol, service_record._address, service_record._management_port)
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, timeout=self._ping_timeout) as resp:
                            text = await resp.text()
                            res = json.loads(text)
                            if res["uptime"] is None:
                                raise ValueError('res.uptime is None')
                            # Set the 'debug' status for non-empty values, applicable only to
                            # Southbound and Northbound services
                            if service_record._type in ('Southbound', 'Northbound'):
                                debugger_value = res.get("debug", {})
                                if not isinstance(debugger_value, dict):
                                    self._logger.warning("Invalid debug value '{}' in service '{}': "
                                                       "Expected a dictionary, but received a {}.".format(
                                        debugger_value, service_record._name, type(debugger_value).__name__))
                                    debugger_value = {}
                                service_record._debug = debugger_value
                except (asyncio.TimeoutError, aiohttp.client_exceptions.ServerTimeoutError) as ex:
                    service_record._status = ServiceRecord.Status.Unresponsive
                    check_count[service_record._id] += 1
                    self._logger.info("ServerTimeoutError: %s, %s", str(ex), service_record.__repr__())
                except aiohttp.client_exceptions.ClientConnectorError as ex:
                    service_record._status = ServiceRecord.Status.Unresponsive
                    check_count[service_record._id] += 1
                    self._logger.info("ClientConnectorError: %s, %s", str(ex), service_record.__repr__())
                except ValueError as ex:
                    service_record._status = ServiceRecord.Status.Unresponsive
                    check_count[service_record._id] += 1
                    self._logger.info("Invalid response: %s, %s", str(ex), service_record.__repr__())
                except Exception as ex:
                    service_record._status = ServiceRecord.Status.Unresponsive
                    check_count[service_record._id] += 1
                    self._logger.info("Exception occurred: %s, %s", str(ex), service_record.__repr__())
                else:
                    service_record._status = ServiceRecord.Status.Running

                    self._logger.debug("Resolving pending notification for ACL change "
                                       "for service {} ".format(service_record._name))
                    if not self._acl_handler:
                        self._acl_handler = ACLManager(connect.get_storage_async())
                    await self._acl_handler.\
                        resolve_pending_notification_for_acl_change(service_record._name)

                    check_count[service_record._id] = 1

                if check_count[service_record._id] > self._max_attempts:
                    ServiceRegistry.mark_as_failed(service_record._id)
                    check_count[service_record._id] = 0
                    if self._support_bundle_config['auto_support_bundle']['value'] == 'true':
                        self._logger.info("Service %s failed, creating automated support bundle",
                                          service_record._name)
                        asyncio.create_task(self.create_automated_support_bundle(service_record._name))
                    try:
                        audit = AuditLogger(connect.get_storage_async())
                        await audit.failure('SRVFL', {'name':service_record._name})
                    except Exception as ex:
                        self._logger.info("Failed to audit service failure %s", str(ex))
            await self._sleep(self._sleep_interval)

    async def create_automated_support_bundle(self, service_name):
        """Create support bundle asynchronously when service fails"""
        try:
            from fledge.services.core.support import SupportBuilder
            from fledge.common.common import _FLEDGE_DATA, _FLEDGE_ROOT
            support_dir = _FLEDGE_DATA + "/support" if _FLEDGE_DATA else _FLEDGE_ROOT + "/data/support"
            builder = SupportBuilder(support_dir, self._support_bundle_config)
            bundle_name = await builder.build(service_name)
            # Raise alert about support bundle creation
            await self.raise_support_bundle_alert(service_name, bundle_name)
            self._logger.info("Support bundle created: {} for failed service: {}".format(bundle_name, service_name))
        except Exception as ex:
            self._logger.error(ex, "Failed to create support bundle for {}".format(service_name))
    
    async def raise_support_bundle_alert(self, service_name, bundle_name):
        """Raise alert for automated support bundle creation"""
        if not self._alert_manager:
            self._alert_manager = AlertManager(connect.get_storage_async())
        # Don't create alert if already exists
        key = f"{service_name}-support-bundle"
        alert = None
        try:
            alert = await self._alert_manager.get_by_key(key)
        except KeyError:
            pass

        if alert is not None:
            self._logger.debug("Alert for support bundle already exists for service: {}".format(service_name))
            return

        try:
            param = {
                "key": key,
                "message": f"Support bundle created for failed service '{service_name}'",
                "urgency": "2"  # High urgency
            }
            await self._alert_manager.add(param)
        except Exception as ex:
            self._logger.error(ex, "Failed to raise an alert on support bundle creation for {} service.".format(service_name))

    async def _handle_config_change(self, category_name):
        """Handle configuration changes for monitored categories"""
        self._logger.info("Processing configuration change for category: {}".format(category_name))
        
        try:
            if category_name == 'SMNTR':
                await self._reload_monitor_config()
            elif category_name == 'SUPPORT_BUNDLE':
                await self._reload_support_bundle_config()
        except Exception as ex:
            self._logger.error("Failed to handle configuration change for {}: {}".format(category_name, str(ex)))

    async def _reload_monitor_config(self):
        """Reload SMNTR configuration and update monitor parameters"""
        self._logger.info("Reloading SMNTR configuration...")
        
        config = await self._cfg_manager.get_category_all_items('SMNTR')
        
        # Store old values for logging
        old_values = {
            'sleep_interval': self._sleep_interval,
            'ping_timeout': self._ping_timeout,
            'max_attempts': self._max_attempts,
            'restart_failed': self._restart_failed
        }
        
        # Update with new values
        self._sleep_interval = int(config['sleep_interval']['value'])
        self._ping_timeout = int(config['ping_timeout']['value'])
        self._max_attempts = int(config['max_attempts']['value'])
        self._restart_failed = config['restart_failed']['value']
        
        # Log changes
        changes = []
        if old_values['sleep_interval'] != self._sleep_interval:
            changes.append("Sleep interval: {} -> {}".format(old_values['sleep_interval'], self._sleep_interval))
        if old_values['ping_timeout'] != self._ping_timeout:
            changes.append("Ping timeout: {} -> {}".format(old_values['ping_timeout'], self._ping_timeout))
        if old_values['max_attempts'] != self._max_attempts:
            changes.append("Max attempts: {} -> {}".format(old_values['max_attempts'], self._max_attempts))
        if old_values['restart_failed'] != self._restart_failed:
            changes.append("Restart failed: {} -> {}".format(old_values['restart_failed'], self._restart_failed))
            
        if changes:
            self._logger.info("SMNTR configuration changes applied: {}".format(", ".join(changes)))
        else:
            self._logger.debug("SMNTR configuration reloaded with no changes")

    async def _reload_support_bundle_config(self):
        """Reload SUPPORT_BUNDLE configuration"""
        self._logger.info("Reloading SUPPORT_BUNDLE configuration...")
        
        old_auto_bundle = self._support_bundle_config.get('auto_support_bundle', {}).get('value', 'false') if self._support_bundle_config else 'false'
        
        self._support_bundle_config = await self._cfg_manager.get_category_all_items('SUPPORT_BUNDLE')
        
        new_auto_bundle = self._support_bundle_config.get('auto_support_bundle', {}).get('value', 'false')
        
        if old_auto_bundle != new_auto_bundle:
            self._logger.info("SUPPORT_BUNDLE configuration changed - Auto support bundle: {} -> {}".format(old_auto_bundle, new_auto_bundle))
        else:
            self._logger.debug("SUPPORT_BUNDLE configuration reloaded with no changes")

    async def _register_config_interests(self):
        """Register interest for configuration changes"""
        try:
            # Register for SMNTR configuration changes
            self._cfg_manager.register_interest('SMNTR', 'fledge.services.core.service_registry.monitor')
            self._logger.info("Registered interest for SMNTR configuration changes")
            
            # Register for SUPPORT_BUNDLE configuration changes
            self._cfg_manager.register_interest('SUPPORT_BUNDLE', 'fledge.services.core.service_registry.monitor')
            self._logger.info("Registered interest for SUPPORT_BUNDLE configuration changes")
            
        except Exception as ex:
            self._logger.error("Failed to register configuration interests: {}".format(str(ex)))

    
    async def _read_config(self):
        """Reads configuration"""
        # Register this instance with the registry
        MonitorRegistry.register('default', self)
        
        default_config = {
            "sleep_interval": {
                "description": "Time in seconds to sleep between health checks. (must be greater than 5)",
                "type": "integer",
                "default": str(self._DEFAULT_SLEEP_INTERVAL),
                "displayName": "Health Check Interval (In seconds)",
                "minimum": "5"
            },
            "ping_timeout": {
                "description": "Timeout for a response from any given micro-service. (must be greater than 0)",
                "type": "integer",
                "default": str(self._DEFAULT_PING_TIMEOUT),
                "displayName": "Ping Timeout",
                "minimum": "1",
                "maximum": "5"
            },
            "max_attempts": {
                "description": "Maximum number of attempts for finding a heartbeat of service",
                "type": "integer",
                "default": str(self._DEFAULT_MAX_ATTEMPTS),
                "displayName": "Max Attempts To Check Heartbeat",
                "minimum": "1"
            },
            "restart_failed": {
                "description": "Restart failed microservice - manual/auto",
                "type": "enumeration",
                'options': ['auto', 'manual'],
                "default": self._DEFAULT_RESTART_FAILED,
                "displayName": "Restart Failed"
            }
        }

        storage_client = connect.get_storage_async()
        self._cfg_manager = ConfigurationManager(storage_client)
        await self._cfg_manager.create_category('SMNTR', default_config, 'Service Monitor', display_name='Service Monitor')

        config = await self._cfg_manager.get_category_all_items('SMNTR')
        self._support_bundle_config = await self._cfg_manager.get_category_all_items('SUPPORT_BUNDLE')

        self._sleep_interval = int(config['sleep_interval']['value'])
        self._ping_timeout = int(config['ping_timeout']['value'])
        self._max_attempts = int(config['max_attempts']['value'])
        self._restart_failed = config['restart_failed']['value']

        # Register for configuration change notifications
        await self._register_config_interests()

    async def restart_service(self, service_record):
        from fledge.services.core import server  # To avoid cyclic import as server also imports monitor
        schedule = await server.Server.scheduler.get_schedule_by_name(service_record._name)
        await server.Server.scheduler.queue_task(schedule.schedule_id)
        self.restarted_services.remove(service_record._id)
        # Raise an alert during restart service
        await self.raise_an_alert(server.Server, service_record._name)

    async def raise_an_alert(self, obj, svc_name):
        async def _new_alert_entry(restart_count=1):
            param = {"key": svc_name, "message": 'The Service {} restarted {} times'.format(
                svc_name, restart_count), "urgency": "3"}
            await obj._alert_manager.add(param)

        try:
            alert = await obj._alert_manager.get_by_key(svc_name)
            message = alert['message'].strip()
            key = alert['key']
            if message.startswith('The Service {} restarted'.format(key)) and message.endswith("times"):
                result = [int(s) for s in message.split() if s.isdigit()]
                if result:
                    await obj._alert_manager.delete(key)
                    await _new_alert_entry(result[-1:][0] + 1)
                else:
                    await _new_alert_entry()
            else:
                await _new_alert_entry()
        except KeyError:
            await _new_alert_entry()
        except Exception as ex:
            self._logger.error(ex, "Failed to raise an alert on restarting {} service.".format(svc_name))

    async def start(self):
        await self._read_config()
        self._monitor_loop_task = asyncio.ensure_future(self._monitor_loop())

    async def stop(self):
        """Clean up when stopping the monitor"""
        # Unregister from registry
        MonitorRegistry.unregister('default')
        
        try:
            # Unregister configuration interests
            if self._cfg_manager:
                self._cfg_manager.unregister_interest('SMNTR', 'fledge.services.core.service_registry.monitor')
                self._cfg_manager.unregister_interest('SUPPORT_BUNDLE', 'fledge.services.core.service_registry.monitor')
                self._logger.info("Unregistered configuration interests")
        except Exception as ex:
            self._logger.error("Error unregistering config interests: {}".format(str(ex)))
            
        try:
            self._monitor_loop_task.cancel()
        except asyncio.CancelledError:
            pass


# Module-level callback function required by ConfigurationManager
async def run(category_name):
    """Module-level callback function for configuration changes
    
    This function is called by ConfigurationManager when registered categories change.
    It delegates to the monitor instance to handle the actual configuration update.
    
    Args:
        category_name (str): The name of the category that changed
    """
    monitor = MonitorRegistry.get('default')
    
    if monitor is None:
        # Monitor instance not available - this could happen during startup/shutdown
        # We can't use the monitor's logger since we don't have the instance
        # Using the module-level logger setup instead
        _logger = logger.setup(__name__)
        _logger.warning("Monitor instance not available for config change callback")
        return
        
    try:
        await monitor._handle_config_change(category_name)
    except Exception as ex:
        monitor._logger.error("Error in configuration change callback for {}: {}".format(category_name, str(ex)))
