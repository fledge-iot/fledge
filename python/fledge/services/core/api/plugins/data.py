# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import json
import urllib.parse
from aiohttp import web

from fledge.plugins.common import utils as common_utils
from fledge.common.plugin_discovery import PluginDiscovery
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.services.core import connect

__author__ = "Mark Riddoch, Ashish Jabble"
__copyright__ = "Copyright (c) 2022 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    ---------------------------------------------------------------------------------------
    | GET                   | /fledge/service/{service_name}/persist                      |
    | GET POST DELETE       | /fledge/service/{service_name}/plugin/{plugin_name}/data    |
    ---------------------------------------------------------------------------------------
"""


async def get_persist_plugins(request: web.Request) -> web.Response:
    """
    Args:
        request:
    Returns:
        list of plugins that have SP_PERSIST_DATA flag set in plugin info
    :Example:
        curl -sX GET "http://localhost:8081/fledge/service/{service_name}/persist"
    """
    plugins = common_utils.get_persist_plugins()
    return web.json_response({'persistent': plugins})


async def get(request: web.Request) -> web.Response:
    """
    Args:
        request:
    Returns:
        plugin data
    :Example:
        curl -sX GET "http://localhost:8081/fledge/service/{service_name}/plugin/{plugin_name}/data"
    """
    service = request.match_info.get('service_name', None)
    service = urllib.parse.unquote(service) if service is not None else None
    plugin = request.match_info.get('plugin_name', None)
    key = "{}{}".format(service, plugin)
    payload = PayloadBuilder().SELECT("key", "data").WHERE(['key', '=', key])
    storage_client = connect.get_storage_async()
    try:
        response = await _get_key(storage_client, payload)
        if response:
            data = response[0]['data']
        else:
            raise ValueError('No matching record found for {} key.'.format(key))
    except KeyError as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except ValueError as err:
        msg = str(err)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({'data': data})


async def add(request: web.Request) -> web.Response:
    """
    Args:
        request:
    Returns:
        plugin data
    :Example:
        curl -sX POST http://localhost:8081/fledge/service/{service_name}/plugin/{plugin_name}/data -d '{"data": {}}'
    """
    try:
        service = request.match_info.get('service_name', None)
        plugin = request.match_info.get('plugin_name', None)
        storage_client = connect.get_storage_async()
        await _find_svc_and_plugin(storage_client, service, plugin)
        key = "{}{}".format(service, plugin)
        payload = PayloadBuilder().SELECT("key", "data").WHERE(['key', '=', key])
        response = await _get_key(storage_client, payload)
        if response:
            msg = "{} key already exist.".format(key)
            return web.HTTPConflict(reason=msg, body=json.dumps({"message": msg}))
        data = await request.json()
        data = data["data"]
        if data is not None:
            payload = PayloadBuilder().INSERT(key=key, data=data)
            await storage_client.insert_into_tbl('plugin_data', payload.payload())
        else:
            raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": "Malformed data in payload"}))
    except KeyError as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except ValueError as err:
        msg = str(err)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({'result': "{} key added successfully.".format(key)})


async def delete(request: web.Request) -> web.Response:
    """
    Args:
        request:
    Returns:
        remove the entry from plugin_data
    :Example:
        curl -sX DELETE "http://localhost:8081/fledge/service/{service_name}/plugin/{plugin_name}/data"
    """
    try:
        service = request.match_info.get('service_name', None)
        service = urllib.parse.unquote(service) if service is not None else None
        plugin = request.match_info.get('plugin_name', None)
        storage_client = connect.get_storage_async()
        key = "{}{}".format(service, plugin)
        payload = PayloadBuilder().WHERE(['key', '=', key])
        response = await _get_key(storage_client, payload)
        if not response:
            raise ValueError('No matching record found for {} key.'.format(key))
        await storage_client.delete_from_tbl('plugin_data', payload.payload())
    except KeyError as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except ValueError as err:
        msg = str(err)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({'result': "{} deleted successfully.".format(key)})


async def _find_svc_and_plugin(storage, sname, pname):
    payload = PayloadBuilder().SELECT(["id", "enabled"]).WHERE(['schedule_name', '=', sname]).payload()
    result = await storage.query_tbl_with_payload('schedules', payload)
    if result['count'] == 0:
        raise ValueError('{} service does not exist.'.format(sname))
    plugins = PluginDiscovery.get_plugins_installed()
    plugin_names = [name['name'] for name in plugins]
    if pname not in plugin_names:
        raise ValueError('{} plugin does not exist.'.format(pname))


async def _get_key(storage, payload):
    result = await storage.query_tbl_with_payload('plugin_data', payload.payload())
    response = result['rows']
    return response
