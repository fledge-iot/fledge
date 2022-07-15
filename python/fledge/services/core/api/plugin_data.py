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
    ---------------------------------------------------------------------------------------
    | GET                   | /fledge/service/{service_name}/plugin/{plugin_name}/data    |
    | POST                  | /fledge/service/{service_name}/plugin/{plugin_name}/data    |
    | DELETE                | /fledge/service/{service_name}/plugin/{plugin_name}/data    |
    ---------------------------------------------------------------------------------------
"""


async def get_plugin_data(request):
    """
    Args:
        request:

    Returns:
            plugin data

    :Example:
            curl -X GET http://localhost:8081/fledge/service/{service_name}/plugin/{plugin_name}/data/
    """
    service = request.match_info.get('service_name', None)
    plugin = request.match_info.get('plugin_name', None)
    payload = PayloadBuilder().SELECT("key", "data") \
        .WHERE(['key', '=', service + plugin])

    storage_client = connect.get_storage_async()
    payload = PayloadBuilder(payload.chain_payload())
    try:
        result = await storage_client.query_tbl_with_payload('plugin_data', payload.payload())
        response = result['rows']
        if response:
            data = response[0]['data']
        else:
            raise web.HTTPBadRequest(reason='No matching key')
    except KeyError:
        raise web.HTTPBadRequest(reason=result['message'])
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=ex)

    return web.json_response({'data': data})

async def add_plugin_data(request):
    """
    Args:
        request:

    Returns:
            plugin data

    :Example:
            curl -X POST http://localhost:8081/fledge/service/{service_name}/plugin/{plugin_name}/data/
    """
    service = request.match_info.get('service_name', None)
    plugin = request.match_info.get('plugin_name', None)
    key = service + plugin
    data = await request.json()
    payload = PayloadBuilder().INSERT(key=key, data=data)

    storage_client = connect.get_storage_async()
    payload = PayloadBuilder(payload.chain_payload())
    try:
        result = await storage_client.insert_into_tbl('plugin_data', payload.payload())
    except KeyError:
        raise web.HTTPBadRequest(reason=result['message'])
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=ex)

    return web.json_response({'key': key})

async def delete_plugin_data(request):
    """
    Args:
        request:

    Returns:
            plugin data

    :Example:
            curl -X DELETE http://localhost:8081/fledge/service/{service_name}/plugin/{plugin_name}/data/
    """
    service = request.match_info.get('service_name', None)
    plugin = request.match_info.get('plugin_name', None)
    payload = PayloadBuilder().WHERE(['key', '=', service + plugin])

    storage_client = connect.get_storage_async()
    try:
        result = await storage_client.delete_from_tbl('plugin_data', payload.payload())
    except KeyError:
        raise web.HTTPBadRequest(reason=result['message'])
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=ex)

    return web.json_response({'deleted': 1})
