# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import logging
import asyncio
import json

from aiohttp import web
from fledge.common import logger
from fledge.common.common import _FLEDGE_DATA


__author__ = "Deepanshu Yadav"
__copyright__ = "Copyright (c) 2022, Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    ----------------------------------------------------------
    | GET            | /fledge/health/storage               |
    ----------------------------------------------------------
"""
_LOGGER = logger.setup(__name__, level=logging.INFO)


async def get_storage_health(request: web.Request) -> web.Response:
    """
     Return the health of Storage service.
    Args:
       request: None

    Returns:
           Health of Storage service.
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

    # We need to find the address and management host for the Storage service.
    from fledge.services.core.service_registry.service_registry import ServiceRegistry
    from fledge.services.core.service_registry.exceptions import DoesNotExist
    try:
        services = ServiceRegistry.get(name="Fledge Storage")
        service = services[0]
    except DoesNotExist:
        _LOGGER.error("Cannot ping the storage service. It does not exist in service registry.")
        raise web.HTTPNotFound(reason="Cannot ping the storage service. It does not exist in service registry.")
    try:
        from fledge.common.service_record import ServiceRecord
        if service._status != ServiceRecord.Status.Running:
            msg = "The Storage service is not in Running state."
            raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))

        from fledge.common.microservice_management_client.microservice_management_client import \
            MicroserviceManagementClient

        mgt_client = MicroserviceManagementClient(service._address,
                                                  service._management_port)
        ping_response = await mgt_client.ping_service()

    except Exception as ex:
        msg = str(ex)
        _LOGGER.error("Could not ping Storage  due to {}".format(msg))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))

    try:

        ping_response['disk'] = {}
        disk_check_process = await asyncio.create_subprocess_shell('df -k ' + _FLEDGE_DATA,
                                                                   stdout=asyncio.subprocess.PIPE,
                                                                   stderr=asyncio.subprocess.PIPE)

        stdout, stderr = await disk_check_process.communicate()
        if disk_check_process.returncode != 0:
            msg = "Could get disk stats due to {}".format(str(stderr))
            _LOGGER.error(msg)
            raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))

        disk_stats = stdout.decode("utf-8")
        required_stats = disk_stats.split('\n')[1].split()
        used = int(required_stats[2])
        available = int(required_stats[3])
        usage = int(required_stats[4].replace("%", ''))
        status = 'green'
        if usage > 95:
            status = 'red'
        elif 90 < usage <= 95:
            status = 'yellow'

        # fill all the files values retrieved
        ping_response['disk']['used'] = used
        ping_response['disk']['usage'] = usage
        ping_response['disk']['available'] = available
        ping_response['disk']['status'] = status
        return web.json_response(ping_response)

    except Exception as ex:
        msg = "Could get disk stats due to {}".format(str(ex))
        _LOGGER.error(msg)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
