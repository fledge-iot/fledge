# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import logging
import json
import asyncio
import shutil

from aiohttp import web
from fledge.common import logger
import os


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
FLEDGE_DATA = os.path.join(os.environ('FLEDGE_ROOT'), 'data')


async def get_storage_health(request: web.Request) -> web.Response:
    """
    Args:
       request:

    Returns:
           Health of Storage service.

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
        return
    else:
        try:
            from fledge.common.service_record import ServiceRecord

            if service._status == ServiceRecord.Status.Running:

                from fledge.common.microservice_management_client.microservice_management_client import \
                    MicroserviceManagementClient

                mgt_client = MicroserviceManagementClient(service._address,
                                                          service._management_port)
                json_response = await mgt_client.ping_service()
                _LOGGER.info("The response is {}".format(json_response))

        except Exception as ex:
            _LOGGER.error("Could not ping Storage  due to {}".format(str(ex)))
            return

    try:
        disk_stat = shutil.disk_usage(FLEDGE_DATA)

        json_response['disk'] = {}
        json_response['disk']['status'] = 'green'
        json_response['disk']['used'] = disk_stat[0]
        json_response['disk']['usage'] = disk_stat[1]
        json_response['disk']['available'] = disk_stat[2]

        return web.json_response(json_response)
    except Exception as ex:
        _LOGGER.error("Could get disk stats due to {}".format(str(ex)))
        return
