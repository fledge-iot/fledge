# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from aiohttp import web
from foglamp.common.storage_client.payload_builder import PayloadBuilder
from foglamp.services.core import connect

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -------------------------------------------------------------------------------
    | GET                   | /foglamp/track                                      |
    -------------------------------------------------------------------------------
"""


#################################
#  Asset tracker
#################################


async def get_asset_tracker(request):
    """
    Args:
        request:

    Returns:
            asset track records

    :Example:
            curl -X GET http://localhost:8081/foglamp/track
            curl -X GET http://localhost:8081/foglamp/track?asset=XXX
            curl -X GET http://localhost:8081/foglamp/track?event=XXX
            curl -X GET http://localhost:8081/foglamp/track?service=XXX
    """
    # TODO: limit, offset?
    payload = PayloadBuilder().SELECT("asset", "event", "service", "foglamp", "plugin", "ts") \
        .ALIAS("return", ("ts", 'timestamp')).FORMAT("return", ("ts", "YYYY-MM-DD HH24:MI:SS.MS")) \
        .WHERE(['1', '=', 1])
    if 'asset' in request.query and request.query['asset'] != '':
        asset = request.query['asset']
        payload.AND_WHERE(['asset', '=', asset])
    if 'event' in request.query and request.query['event'] != '':
        event = request.query['event']
        payload.AND_WHERE(['event', '=', event])
    if 'service' in request.query and request.query['service'] != '':
        service = request.query['service']
        payload.AND_WHERE(['service', '=', service])

    _and_where_payload = payload.chain_payload()
    storage_client = connect.get_storage_async()
    payload = PayloadBuilder(_and_where_payload)
    try:
        result = await storage_client.query_tbl_with_payload('asset_tracker', payload.payload())
    except Exception as ex:
        raise web.HTTPException(reason=ex)

    return web.json_response({'track': result['rows']})
