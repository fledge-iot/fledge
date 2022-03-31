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
from fledge.common.storage_client.exceptions import StorageServerError
from fledge.services.core.service_registry import exceptions as service_registry_exceptions
from fledge.services.core.service_registry.service_registry import ServiceRegistry


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2022 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_logger = logger.setup(__name__, level=logging.INFO)


def setup(app):
    app.router.add_route('*', '/fledge/bucket{head:.*}', bucket_handler)


async def bucket_handler(request):
    """
        POST -   /bucket
        POST -   /bucket/uid
        GET -    /bucket/uid
        DELETE - /bucket/uid
        PUT -    /bucket/uid
        PUT -    /bucket/match
    """
    allow_methods = ["GET", "POST", "PUT", "DELETE"]
    data = None
    try:
        if request.method not in allow_methods:
            raise RuntimeError
        # TODO: any payload parameter handling required?
        if request.method != 'GET':
            data = await request.json()
        bucket_storage = await _get_address_and_mgt_port()
        url = str(request.url).split('fledge/')[1]
        message = "{} - {}://{}:{}/{} -- with data: {}".format(request.method, bucket_storage._protocol, bucket_storage._address,
                                              bucket_storage._port, url, data)
        # TODO:
        # Bearer token?
        #  Enable below line to call bucket API
        # _call_bucket_api(request.method, bucket_storage._protocol, bucket_storage._address, bucket_storage._port, url,
                         #token, data)
    except RuntimeError:
        raise web.HTTPMethodNotAllowed(method=request.method, allowed_methods=allow_methods)
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({"message": message})


async def _get_address_and_mgt_port():
    try:
        # FIXME: replace Storage service with BucketStorage
        bucket_service = ServiceRegistry.get(s_type=ServiceRecord.Type.Storage.name)
        _logger.info(bucket_service)
    except service_registry_exceptions.DoesNotExist:
        raise web.HTTPNotFound(reason="No Bucket Storage service available.")
    else:
        return bucket_service[0]


async def _call_bucket_api(method: str, protocol: str, address: str, port: int, uri: str, token: str, data: dict):
    headers = {'Content-type': 'application/json', 'Authorization': "Bearer {}".format(token)}
    url = "{}://{}:{}/{}".format(protocol, address, port, uri)
    response = {}
    try:
        if method == 'GET':
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    status_code = resp.status
                    response = await resp.text()
                    if status_code not in range(200, 209):
                        raise StorageServerError(code=resp.status, reason=resp.reason, error=response)
        elif method == 'POST':
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data, headers=headers) as resp:
                    status_code = resp.status
                    response = await resp.text()
                    if status_code not in range(200, 209):
                        raise StorageServerError(code=resp.status, reason=resp.reason, error=response)
        elif method == 'PUT':
            async with aiohttp.ClientSession() as session:
                async with session.put(url, data=data, headers=headers) as resp:
                    status_code = resp.status
                    response = await resp.text()
                    if status_code not in range(200, 209):
                        raise StorageServerError(code=resp.status, reason=resp.reason, error=response)
        elif method == 'DELETE':
            async with aiohttp.ClientSession() as session:
                async with session.delete(url, data=data, headers=headers) as resp:
                    status_code = resp.status
                    response = await resp.text()
                    if status_code not in range(200, 209):
                        raise StorageServerError(code=resp.status, reason=resp.reason, error=response)
        else:
            _logger.warning("Not implemented yet for {} method.".format(method))
    except Exception:
        _logger.error("Error code: %d, reason: %s, details: %s, url: %s",
                      resp.status, resp.reason, response, url)
        raise
    else:
        return response
