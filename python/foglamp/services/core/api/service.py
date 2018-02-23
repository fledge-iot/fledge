# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from aiohttp import web
from foglamp.services.core.service_registry.service_registry import ServiceRegistry




__author__ = "Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_help = """
    -------------------------------------------------------------------------------
    | GET             | /foglamp/service                                          |
    -------------------------------------------------------------------------------
"""


#################################
#  Service
#################################


async def get_health(request):
    """
    Args:
        request:

    Returns:
            health of all registered services

    :Example:
            curl -X GET http://localhost:8081/foglamp/service
    """
    sr_list = list()
    for service_record in ServiceRegistry.all():
        sr_list.append(
                {
                    'name' : service_record._name,
                    'type' : service_record._type,
                    'address' : service_record._address,
                    'management_port' : service_record._management_port,
                    'service_port' : service_record._port,
                    'protocol' : service_record._protocol,
                    'status': 'running'
                }
    response = {'services' : sr_list}
    return web.json_response(response)

