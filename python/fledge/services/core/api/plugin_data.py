# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

from aiohttp import web
import urllib.parse

from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.services.core import connect

__author__ = "Mark Riddoch"
__copyright__ = "Copyright (c) 2022 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -------------------------------------------------------------------------------
    | GET                   | /fledge/plugin/data                                      |
    -------------------------------------------------------------------------------
"""


async def get_plugin_data(request):
    """
    Args:
        request:

    Returns:
            plugin data

    :Example:
            curl -X GET http://localhost:8081/fledge/plugin/data/
    """
    plugin = request.match_info.get('plugin_name', None)
    payload = PayloadBuilder().SELECT("key", "data") \
        .WHERE(['key', '=', plugin])

    storage_client = connect.get_storage_async()
    payload = PayloadBuilder(payload.chain_payload())
    try:
        result = await storage_client.query_tbl_with_payload('plugin_data', payload.payload())
        response = result['rows']
    except KeyError:
        raise web.HTTPBadRequest(reason=result['message'])
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=ex)

    return web.json_response({'data': response})
