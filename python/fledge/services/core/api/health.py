# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import logging
import asyncio
import json

from aiohttp import web
from fledge.common import logger
from fledge.common.common import _FLEDGE_DATA, _FLEDGE_ROOT


__author__ = "Deepanshu Yadav"
__copyright__ = "Copyright (c) 2022, Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    ----------------------------------------------------------
    | GET            | /fledge/health/storage               |
    | GET            | /fledge/health/logging               |
    ----------------------------------------------------------
"""
_LOGGER = logger.setup(__name__, level=logging.INFO)


async def get_disc_usage(given_dir):
    """
       Helper function that calculates used, available, usage(in %) for a given directory in file system.
       Returns a tuple of used(in KB's integer), available(in KB's integer), usage(in %)
    """
    disk_check_process = await asyncio.create_subprocess_shell('df -k ' + given_dir,
                                                               stdout=asyncio.subprocess.PIPE,
                                                               stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await disk_check_process.communicate()
    if disk_check_process.returncode != 0:
        stderr = stderr.decode("utf-8")
        msg = "Failed to get disk stats! {}".format(str(stderr))
        _LOGGER.error(msg)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))

    # Following output is parsed.
    """
        Filesystem     1K-blocks     Used Available Use% Mounted on
        /dev/sda5      122473072 95449760  20755872  83% /

    """
    disk_stats = stdout.decode("utf-8")
    required_stats = disk_stats.split('\n')[1].split()
    used = int(required_stats[2])
    available = int(required_stats[3])
    usage = int(required_stats[4].replace("%", ''))

    return used, available, usage


async def get_logging_health(request: web.Request) -> web.Response:
    """
     Return the health of logging.
    Args:
       request: None

    Returns:
           Return the health of logging.
           Sample Response :

           {
              "disk": {
                "usage": 63,
                "used": 42936800,
                "available": 25229400
              },
              "levels": [
                {
                    "name" : "Sine",
                    "level" : "info"
                },
                {
                    "name" : "OMF",
                    "level" : "debug"
                }
              ]
           }

    :Example:
           curl -X GET http://localhost:8081/fledge/health/logging
    """
    response = {}
    try:
        from fledge.services.core.api import service as serv_api
        from fledge.common.configuration_manager import ConfigurationManager
        from fledge.services.core import connect

        services_info = serv_api.get_service_records()
        levels_array = []
        excluded_services = ["Storage", "Core"]
        for services_info in services_info['services']:
            if services_info['type'] not in excluded_services:
                service_name = services_info["name"]
                cf_mgr = ConfigurationManager(connect.get_storage_async())
                category_name = service_name + "Advanced"
                config_item = "logLevel"
                category_item = await cf_mgr.get_category_item(category_name, config_item)
                log_level = category_item["value"]
                level_dict = dict()
                level_dict["name"] = service_name
                level_dict["level"] = log_level
                levels_array.append(level_dict)

        response["levels"] = levels_array
    except Exception as ex:
        msg = "Could not fetch service information.{}".format(str(ex))
        _LOGGER.error(msg)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))

    try:
        response['disk'] = {}
        used, available, usage = await get_disc_usage('/var/log')
        # fill all the fields after values are retrieved
        response['disk']['used'] = used
        response['disk']['usage'] = usage
        response['disk']['available'] = available

    except Exception as ex:
        msg = "Failed to get disk stats for /var/log !{}".format(str(ex))
        _LOGGER.error(msg)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response(response)


async def get_storage_health(request: web.Request) -> web.Response:
    """
     Return the health of Storage service & data directory.
    Args:
       request: None

    Returns:
           Return the health of Storage service & data directory.
           Sample Response :

           {
              "uptime": 33,
              "name": "Fledge Storage",
              "statistics": {
                "commonInsert": 30,
                "commonSimpleQuery": 3,
                "commonQuery": 91,
                "commonUpdate": 2,
                "commonDelete": 1,
                "readingAppend": 0,
                "readingFetch": 0,
                "readingQuery": 1,
                "readingPurge": 0
              },
              "disk": {
                "used": 95287524,
                "usage": 82,
                "available": 20918108,
                "status": "green"
              }
           }

    :Example:
           curl -X GET http://localhost:8081/fledge/health/storage
    """
    # Find the address and management host for the Storage service.
    from fledge.services.core.service_registry.service_registry import ServiceRegistry
    from fledge.services.core.service_registry.exceptions import DoesNotExist
    try:
        services = ServiceRegistry.get(name="Fledge Storage")
        service = services[0]
    except DoesNotExist:
        msg = "Cannot ping the storage service. It does not exist in service registry."
        _LOGGER.error(msg)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    try:
        from fledge.common.service_record import ServiceRecord
        if service._status != ServiceRecord.Status.Running:
            msg = "The Storage service is not in Running state."
            raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))

        from fledge.common.microservice_management_client.microservice_management_client import \
            MicroserviceManagementClient

        mgt_client = MicroserviceManagementClient(service._address,
                                                  service._management_port)
        response = await mgt_client.ping_service()

    except Exception as ex:
        msg = str(ex)
        _LOGGER.error("Could not ping Storage  due to {}".format(msg))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))

    try:
        response['disk'] = {}
        data_dir_path = _FLEDGE_DATA if _FLEDGE_DATA else _FLEDGE_ROOT + '/data'
        used, available, usage = await get_disc_usage(data_dir_path)
        status = 'green'
        if usage > 95:
            status = 'red'
        elif 90 < usage <= 95:
            status = 'yellow'

        # fill all the fields after values are retrieved
        response['disk']['used'] = used
        response['disk']['usage'] = usage
        response['disk']['available'] = available
        response['disk']['status'] = status
    except Exception as ex:
        msg = "Failed to get disk stats! {}".format(str(ex))
        _LOGGER.error(msg)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response(response)
