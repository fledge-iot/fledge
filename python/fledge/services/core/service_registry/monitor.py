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

__author__ = "Ashwin Gopalakrishnan, Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


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
                    try:
                        audit = AuditLogger(connect.get_storage_async())
                        await audit.failure('SRVFL', {'name':service_record._name})
                    except Exception as ex:
                        self._logger.info("Failed to audit service failure %s", str(ex))
            await self._sleep(self._sleep_interval)

    async def _read_config(self):
        """Reads configuration"""
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
        cfg_manager = ConfigurationManager(storage_client)
        await cfg_manager.create_category('SMNTR', default_config, 'Service Monitor', display_name='Service Monitor')

        config = await cfg_manager.get_category_all_items('SMNTR')

        self._sleep_interval = int(config['sleep_interval']['value'])
        self._ping_timeout = int(config['ping_timeout']['value'])
        self._max_attempts = int(config['max_attempts']['value'])
        self._restart_failed = config['restart_failed']['value']

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
        try:
            self._monitor_loop_task.cancel()
        except asyncio.CancelledError:
            pass
