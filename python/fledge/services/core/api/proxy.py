# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END
import json
import logging
import aiohttp

from aiohttp import web
from fledge.common import logger
from fledge.services.core import server
from fledge.services.core.service_registry import exceptions as service_registry_exceptions
from fledge.services.core.service_registry.service_registry import ServiceRegistry


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2022 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_logger = logger.setup(__name__, level=logging.INFO)
SVC_TYPE = "BucketStorage"


def setup(app):
    app.router.add_route('*', '/fledge/bucket{head:.*}', handler)


async def handler(request):
    """ For example: For a bucket service
        POST -   /bucket
        GET -    /bucket/([0-9][0-9]*)$
        DELETE - /bucket/([0-9][0-9]*)$
        PUT -    /bucket/([0-9][0-9]*)$
        PUT -    /bucket/match
    """
    allow_methods = ["GET", "POST", "PUT", "DELETE"]
    if request.method not in allow_methods:
        raise web.HTTPMethodNotAllowed(method=request.method, allowed_methods=allow_methods)
    try:
        data = await request.json() if request.method != 'GET' else None
        svc, token = await _get_service_record_info_along_with_bearer_token()
        if svc._name not in server.Server._API_PROXIES.keys():
            raise web.HTTPForbidden()
        url = str(request.url).split('fledge/')[1]
        result = await _call_microservice_service_api(request.method, svc._protocol, svc._address, 
                                                      svc._port, url, token, data)
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({"info": result})


async def _get_service_record_info_along_with_bearer_token():
    try:
        service = ServiceRegistry.get(s_type=SVC_TYPE)
        svc_name = service[0]._name
        token = ServiceRegistry.getBearerToken(svc_name)
    except service_registry_exceptions.DoesNotExist:
        msg = "No service available with {} type.".format(SVC_TYPE)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    else:
        return service[0], token


async def _call_microservice_service_api(method: str, protocol: str, address: str, port: int, uri: str, token: str,
                                         data: dict):
    headers = {'Content-type': 'application/json'}
    if token is not None:
        headers['Authorization'] = "Bearer {}".format(token)
    url = "{}://{}:{}/{}".format(protocol, address, port, uri)
    try:
        if method == 'GET':
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    response = await resp.text()
                    if resp.status not in range(200, 209):
                        raise Exception("Error: Http status code: {}, reason: {}, response: {}".format(
                            resp.status, resp.reason, response))
        elif method == 'POST':
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=json.dumps(data), headers=headers) as resp:
                    response = await resp.text()
                    if resp.status not in range(200, 209):
                        raise Exception("Error: Http status code: {}, reason: {}, response: {}".format(
                            resp.status, resp.reason, response))
        elif method == 'PUT':
            async with aiohttp.ClientSession() as session:
                async with session.put(url, data=json.dumps(data), headers=headers) as resp:
                    response = await resp.text()
                    if resp.status not in range(200, 209):
                        raise Exception("Error: Http status code: {}, reason: {}, response: {}".format(
                            resp.status, resp.reason, response))
        elif method == 'DELETE':
            async with aiohttp.ClientSession() as session:
                async with session.delete(url, data=json.dumps(data), headers=headers) as resp:
                    response = await resp.text()
                    if resp.status not in range(200, 209):
                        raise Exception("Error: Http status code: {}, reason: {}, response: {}".format(
                            resp.status, resp.reason, response))
        else:
            _logger.warning("Not implemented yet for {} method.".format(method))
    except Exception as ex:
        _logger.error(str(ex))
        raise Exception(response)
    else:
        return response
