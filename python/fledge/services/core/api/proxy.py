# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END
import json
import logging

from aiohttp import web
from fledge.common import logger
from fledge.common.service_record import ServiceRecord
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
    allow_methods = ["GET", "POST", "PUT", "DELETE"]
    try:
        if request.method not in allow_methods:
            raise RuntimeError
        bucket_storage = await _get_address_and_mgt_port()
        # POST - /bucket
        # POST - /bucket/uid
        # GET - /bucket/uid
        # DELETE - /bucket/uid
        # PUT - /bucket/uid
        # PUT - /bucket/match

        url = str(request.url).split('fledge/')[1]
        message = "{} - {}://{}:{}/{}".format(request.method, bucket_storage._protocol, bucket_storage._address,
                                              bucket_storage._port, url)
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

