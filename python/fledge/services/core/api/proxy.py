# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END
import json
import logging
import aiohttp

from aiohttp import web
from fledge.common import logger
from fledge.common.service_record import ServiceRecord
from fledge.services.core import server
from fledge.services.core.service_registry import exceptions as service_registry_exceptions
from fledge.services.core.service_registry.service_registry import ServiceRegistry


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2022 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_logger = logger.setup(__name__, level=logging.INFO)

# TODO: dynamic service name or configurable
SVC_NAME = "Bucket Storage"
SVC_TYPE = "BucketStorage"


def setup(app):
    app.router.add_route('*', '/fledge/bucket{head:.*}', handler)


async def handler(request):
    """For example: For a bucketstorage service
        POST -   /bucket
        POST -   /bucket/uid
        GET -    /bucket/uid
        DELETE - /bucket/uid
        PUT -    /bucket/uid
        PUT -    /bucket/match
    """
    allow_methods = ["GET", "POST", "PUT", "DELETE"]
    if request.method not in allow_methods:
        raise web.HTTPMethodNotAllowed(method=request.method, allowed_methods=allow_methods)
    if SVC_NAME not in server.Server._API_PROXIES.keys():
        raise web.HTTPForbidden()
    # TODO: Match request.url with server.Server._PROXY_API_INFO KV pair and forward
    try:
        data = await request.json() if request.method != 'GET' else None
        svc, token = await _get_service_record_info_along_with_bearer_token()
        url = str(request.url).split('fledge/')[1]
        result = await _call_microservice_service_api(request.method, svc._protocol, svc._address,
                                                      svc._port, url, token, data)
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({"message": result})


async def _get_service_record_info_along_with_bearer_token():
    try:
        service = ServiceRegistry.filter_by_name_and_type(name=SVC_NAME, s_type=SVC_TYPE)
        token = ServiceRegistry.getBearerToken(SVC_NAME)
    except service_registry_exceptions.DoesNotExist:
        raise web.HTTPNotFound(reason="No {} service available.".format(SVC_NAME))
    else:
        return service[0], token


async def _call_microservice_service_api(method: str, protocol: str, address: str, port: int, uri: str, token: str,
                                         data: dict):
    headers = {'Content-type': 'application/json'}
    if token is not None:
        headers['Authorization'] = "Bearer {}".format(token)
    url = "{}://{}:{}/{}".format(protocol, address, port, uri)
    response = {}
    try:
        if method == 'GET':
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    status_code = resp.status
                    response = await resp.text()
                    if status_code not in range(200, 209):
                        raise Exception
        elif method == 'POST':
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=json.dumps(data), headers=headers) as resp:
                    status_code = resp.status
                    response = await resp.text()
                    if status_code not in range(200, 209):
                        raise Exception
        elif method == 'PUT':
            async with aiohttp.ClientSession() as session:
                async with session.put(url, data=json.dumps(data), headers=headers) as resp:
                    status_code = resp.status
                    response = await resp.text()
                    if status_code not in range(200, 209):
                        raise Exception
        elif method == 'DELETE':
            async with aiohttp.ClientSession() as session:
                async with session.delete(url, data=json.dumps(data), headers=headers) as resp:
                    status_code = resp.status
                    response = await resp.text()
                    if status_code not in range(200, 209):
                        raise Exception
        else:
            _logger.warning("Not implemented yet for {} method.".format(method))
    except Exception:
        _logger.error("Error code: {}, reason: {}, details: {}, url: {}".format(
            int(resp.status), resp.reason, response, url))
        raise
    else:
        return response
