# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Modify process_name for Python Async plugins from south to south_c"""

import aiohttp
import logging

from foglamp.common import logger
from foglamp.common.storage_client.exceptions import StorageServerError
from foglamp.common.storage_client.payload_builder import PayloadBuilder
from foglamp.common.storage_client.storage_client import StorageClientAsync
from foglamp.common.configuration_manager import ConfigurationManager

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_LOGGER = logger.setup(__name__, level=logging.INFO)
_HTTP = 'http'
_HOST = 'localhost'
_PORT = 8081


async def disable_service(service_name):
    try:
        put_url = "{}://{}:{}/foglamp/schedule/disable".format(_HTTP, _HOST, _PORT)
        data = '{"schedule_name": "%s"}' % service_name
        verify_ssl = False if _HTTP == 'http' else True
        connector = aiohttp.TCPConnector(verify_ssl=verify_ssl)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.put(put_url, data=data) as resp:
                status_code = resp.status
                jdoc = await resp.json()
                if status_code not in range(200, 209):
                    _LOGGER.error("Error code: %d, reason: %s, details: %s, url: %s", resp.status, resp.reason, jdoc,
                                  put_url)
                    raise StorageServerError(code=resp.status, reason=resp.reason, error=jdoc)
    except Exception:
        raise
    else:
        _LOGGER.info('Disabled Python South service [%s] to change process_name to south_c', service_name)


async def unregister_service(service_name, core_management_port, microservice_id):
    try:
        delete_url = "{}://{}:{}/foglamp/service/{}".format(_HTTP, _HOST, core_management_port, microservice_id)
        verify_ssl = False if _HTTP == 'http' else True
        connector = aiohttp.TCPConnector(verify_ssl=verify_ssl)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.delete(delete_url) as resp:
                status_code = resp.status
                jdoc = await resp.text()
                if status_code not in range(200, 209):
                    # In case of serviceRegistry.DoesNotExist, HTTPInternalServerError(500) is raised. Hence this
                    # scenario is being handled indirectly by RuntimeError.
                    raise RuntimeError(jdoc)
    except RuntimeError as ex:
        if 'DoesNotExist' in str(ex):
            pass
        else:
            _LOGGER.error('Exception [%s] at unregistering service %s', str(ex), service_name)
    else:
        _LOGGER.info('Unregistered service %s', service_name)


async def modify_process_name(service_name, core_management_host, core_management_port):
    storage = StorageClientAsync(core_management_host, core_management_port)

    try:
        payload = PayloadBuilder().SELECT("id").WHERE(['schedule_name', '=', service_name]).payload()
        result = await storage.query_tbl_with_payload('schedules', payload)
    except Exception:
        raise

    if int(result['count']):
        sch_id = result['rows'][0]['id']
    else:
        _LOGGER.error('No schedule id found for %s. Exiting...', service_name)
        raise RuntimeError('No schedule id found for %s. Exiting...', service_name)

    # Modify process name
    try:
        put_url = "{}://{}:{}/foglamp/schedule/{}".format(_HTTP, _HOST, _PORT, sch_id)
        data = '{"process_name": "south_c"}'
        verify_ssl = False if _HTTP == 'http' else True
        connector = aiohttp.TCPConnector(verify_ssl=verify_ssl)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.put(put_url, data=data) as resp:
                status_code = resp.status
                jdoc = await resp.text()
                if status_code not in range(200, 209):
                    _LOGGER.error("Error code: %d, reason: %s, details: %s, url: %s", resp.status, resp.reason, jdoc,
                                  put_url)
                    raise StorageServerError(code=resp.status, reason=resp.reason, error=jdoc)
    except Exception:
        raise
    else:
        _LOGGER.info('Modified process_name from "south" to "south_c" for Python South service [%s]: %s', service_name, jdoc)


async def reenable_service(service_name):
    try:
        put_url = "{}://{}:{}/foglamp/schedule/enable".format(_HTTP, _HOST, _PORT)
        data = '{"schedule_name": "%s"}' % service_name
        verify_ssl = False if _HTTP == 'http' else True
        connector = aiohttp.TCPConnector(verify_ssl=verify_ssl)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.put(put_url, data=data) as resp:
                status_code = resp.status
                jdoc = await resp.json()
                if status_code not in range(200, 209):
                    _LOGGER.error("Error code: %d, reason: %s, details: %s, url: %s", resp.status, resp.reason, jdoc,
                                  put_url)
                    raise StorageServerError(code=resp.status, reason=resp.reason, error=jdoc)
    except Exception:
        raise
    else:
        _LOGGER.info('Enabled Python South service [%s] after changing process_name to south_c', service_name)


async def change_to_south_c(service_name, microservice_management_host, core_management_host, core_management_port, microservice_id):
    global _HTTP, _HOST, _PORT

    storage = StorageClientAsync(core_management_host, core_management_port)
    configuration_manager = ConfigurationManager(storage)
    config = await configuration_manager.get_category_all_items('rest_api')

    is_rest_server_http_enabled = False if config['enableHttp']['value'] == 'false' else True
    port_from_config = config['httpPort']['value'] if is_rest_server_http_enabled \
        else config['httpsPort']['value']

    _HTTP = 'http' if is_rest_server_http_enabled else 'https'
    _HOST = microservice_management_host
    _PORT = int(port_from_config)

    await disable_service(service_name)
    await unregister_service(service_name, core_management_port, microservice_id)
    await modify_process_name(service_name,core_management_host, core_management_port)
    await reenable_service(service_name)
