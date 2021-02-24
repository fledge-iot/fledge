# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

from aiohttp import web
import urllib.parse

from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.services.core import connect

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -------------------------------------------------------------------------------
    | GET                   | /fledge/track                                      |
    -------------------------------------------------------------------------------
"""


async def get_asset_tracker_events(request):
    """
    Args:
        request:

    Returns:
            asset track records

    :Example:
            curl -X GET http://localhost:8081/fledge/track
            curl -X GET http://localhost:8081/fledge/track?asset=XXX
            curl -X GET http://localhost:8081/fledge/track?event=XXX
            curl -X GET http://localhost:8081/fledge/track?service=XXX
    """
    payload = PayloadBuilder().SELECT("asset", "event", "service", "fledge", "plugin", "ts") \
        .ALIAS("return", ("ts", 'timestamp')).FORMAT("return", ("ts", "YYYY-MM-DD HH24:MI:SS.MS")) \
        .WHERE(['1', '=', 1])
    if 'asset' in request.query and request.query['asset'] != '':
        asset = urllib.parse.unquote(request.query['asset'])
        payload.AND_WHERE(['asset', '=', asset])
    if 'event' in request.query and request.query['event'] != '':
        event = request.query['event']
        payload.AND_WHERE(['event', '=', event])
    if 'service' in request.query and request.query['service'] != '':
        service = urllib.parse.unquote(request.query['service'])
        payload.AND_WHERE(['service', '=', service])

    storage_client = connect.get_storage_async()
    payload = PayloadBuilder(payload.chain_payload())
    try:
        result = await storage_client.query_tbl_with_payload('asset_tracker', payload.payload())
        response = result['rows']
    except KeyError:
        raise web.HTTPBadRequest(reason=result['message'])
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=ex)

    return web.json_response({'track': response})
