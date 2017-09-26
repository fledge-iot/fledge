# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from aiohttp import web

from foglamp.core.api import statistics_db_services

__author__ = "Amarendra K. Sinha, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_help = """
    -------------------------------------------------------------------------------
    | GET             | /foglamp/statistics                                       |
    | GET             | /foglamp/statistics/history                               |
    -------------------------------------------------------------------------------
"""


#################################
#  Statistics
#################################


async def get_statistics(request):
    """
    Args:
        request:

    Returns:
            a general set of statistics

    :Example:
            curl -X GET http://localhost:8082/foglamp/statistics
    """
    statistics = await statistics_db_services.read_statistics()

    return web.json_response(statistics)


async def get_statistics_history(request):
    """
    Args:
        request:

    Returns:
            a list of general set of statistics

    :Example:
            curl -X GET http://localhost:8082/foglamp/statistics/history?limit=1
    """

    try:
        limit = request.query.get('limit') if 'limit' in request.query else 0

        statistics = await statistics_db_services.read_statistics_history(int(limit))

        if not statistics:
            raise ValueError('No statistics available')

        # TODO: find out where from this "interval" will be picked and what will be its role in query?
        return web.json_response({"interval": 5, 'statistics': statistics})
    except ValueError as ex:
        raise web.HTTPNotFound(reason=str(ex))
