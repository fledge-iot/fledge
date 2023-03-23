# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import asyncio
import time
import json
import logging
import socket
import subprocess

from aiohttp import web
from functools import lru_cache

from fledge.common import logger
from fledge.services.core import server
from fledge.services.core.api.statistics import get_statistics
from fledge.services.core import connect
from fledge.common.configuration_manager import ConfigurationManager
from fledge.services.core.service_registry.service_registry import ServiceRegistry
from fledge.common.service_record import ServiceRecord
from fledge.common.common import _FLEDGE_ROOT

__author__ = "Amarendra K. Sinha, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

__start_time = time.time()

_logger = logger.setup(__name__, level=logging.INFO)

_help = """
    -------------------------------------------------------------------------------
    | GET             | /fledge/ping                                             |
    | PUT             | /fledge/shutdown                                         |
    | PUT             | /fledge/restart                                          |
    -------------------------------------------------------------------------------
"""


@lru_cache(maxsize=1, typed=True)
def get_version() -> str:
    with open(_FLEDGE_ROOT + '/VERSION') as f:
        # Read only the first line of a VERSION file and grab the release version number
        return f.readline().split('=')[1].strip()


async def ping(request):
    """
    Args:
       request:

    Returns:
           basic health information json payload

    :Example:
           curl -X GET http://localhost:8081/fledge/ping
    """

    try:
        auth_token = request.token
    except AttributeError:
        if request.is_auth_optional is False:
            cfg_mgr = ConfigurationManager(connect.get_storage_async())
            category_item = await cfg_mgr.get_category_item('rest_api', 'allowPing')
            allow_ping = True if category_item['value'].lower() == 'true' else False
            if allow_ping is False:
                _logger.warning("A valid token required to ping; as auth is mandatory & allow ping is set to false.")
                raise web.HTTPUnauthorized()

    since_started = time.time() - __start_time

    stats_request = request.clone(rel_url='fledge/statistics')
    data_read, data_sent, data_purged = await get_stats(stats_request)

    host_name = socket.gethostname()
    # all addresses for the host
    all_ip_addresses_cmd_res = subprocess.run(['hostname', '-I'], stdout=subprocess.PIPE)
    ip_addresses = all_ip_addresses_cmd_res.stdout.decode('utf-8').replace("\n", "").strip().split(" ")

    svc_name = server.Server._service_name

    def services_health_litmus_test():
        all_svc_status = [ServiceRecord.Status(int(service_record._status)).name.upper()
                          for service_record in ServiceRegistry.all()]
        if 'FAILED' in all_svc_status:
            return 'red'
        elif 'UNRESPONSIVE' in all_svc_status:
            return 'amber'
        return 'green'

    status_color = services_health_litmus_test()
    safe_mode = True if server.Server.running_in_safe_mode else False
    version = get_version()
    return web.json_response({'uptime': int(since_started),
                              'dataRead': data_read,
                              'dataSent': data_sent,
                              'dataPurged': data_purged,
                              'authenticationOptional': request.is_auth_optional,
                              'serviceName': svc_name,
                              'hostName': host_name,
                              'ipAddresses': ip_addresses,
                              'health': status_color,
                              'safeMode': safe_mode,
                              'version': version
                              })


async def get_stats(req):
    """
    :param req: a clone of 'fledge/statistics' endpoint request
    :return:  data_read, data_sent, data_purged
    """

    res = await get_statistics(req)
    stats = json.loads(res.body.decode())

    def filter_stat(k):

        """
        there is no statistics about 'Readings Sent' at the start of Fledge
        so the specific exception is caught and 0 is returned to avoid the error 'index out of range'
        calling the API ping.
        """
        try:
            v = [s['value'] for s in stats if s['key'] == k]
            value = int(v[0])
        except IndexError:
            value = 0

        return value

    data_read = filter_stat('READINGS')
    data_sent = filter_stat('Readings Sent')
    data_purged = filter_stat('PURGED')

    return data_read, data_sent, data_purged


async def shutdown(request):
    """
    Args:
        request:

    Returns:

    :Example:
            curl -X PUT http://localhost:8081/fledge/shutdown
    """

    try:
        loop = request.loop
        loop.call_later(2, do_shutdown, request)
        return web.json_response({'message': 'Fledge shutdown has been scheduled. '
                                             'Wait for few seconds for process cleanup.'})
    except TimeoutError as err:
        raise web.HTTPRequestTimeout(reason=str(err))
    except Exception as ex:
        msg = str(ex)
        _logger.error("Error while stopping Fledge server: {}".format(msg))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))


def do_shutdown(request):
    _logger.info("Executing controlled shutdown")
    try:
        loop = request.loop
        asyncio.ensure_future(server.Server.shutdown(request), loop=loop)
    except RuntimeError as e:
        _logger.error("Error while stopping Fledge server: {}".format(str(e)))
        raise


async def restart(request):
    """
    :Example:
            curl -X PUT http://localhost:8081/fledge/restart
    """

    try:
        _logger.info("Executing controlled shutdown and start")
        asyncio.ensure_future(server.Server.restart(request), loop=request.loop)
        return web.json_response({'message': 'Fledge restart has been scheduled.'})
    except TimeoutError as err:
        msg = str(err)
        raise web.HTTPRequestTimeout(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        _logger.error("Error while stopping Fledge server: {}".format(msg))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
