# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END
import json
import logging
import urllib.parse

from aiohttp import web
from fledge.common import logger
from fledge.services.core import server
from fledge.services.core.service_registry.service_registry import ServiceRegistry
from fledge.services.core.service_registry import exceptions as service_registry_exceptions

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2022 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_logger = logger.setup(__name__, level=logging.INFO)
SVC_TYPE = "BucketStorage"


def setup(app):
    app.router.add_route('POST', '/fledge/proxy', add)
    app.router.add_route('DELETE', '/fledge/proxy/{service_name}', delete)


async def add(request):
    """ Add API proxy for a service

    :Example:
             curl -sX POST http://localhost:<SVC_MGT_PORT>/fledge/proxy -d '{"service_name": "BucketStorage", "POST": {"/fledge/bucket": "/bucket"}}'
             curl -sX POST http://localhost:<SVC_MGT_PORT>/fledge/proxy -d '{"service_name": "BucketStorage", "GET": {"/fledge/bucket/{uniqueID}": "/bucket/{uniqueID}"}}'
             curl -sX POST http://localhost:<SVC_MGT_PORT>/fledge/proxy -d '{"service_name": "BucketStorage", "GET": {"/fledge/bucket/{uniqueID}": "/bucket/{uniqueID}"}, "PUT": {"/fledge/bucket/{uniqueID}": "/bucket/{uniqueID}"}, "DELETE": {"/fledge/bucket/{uniqueID}": "/bucket/{uniqueID}"}}'
            curl -sX POST http://localhost:<SVC_MGT_PORT>/fledge/proxy -d '{"service_name": "Bucket #1", "DELETE": {"/fledge/bucket/([0-9][0-9]*)$": "/bucket/([0-9][0-9]*)$"}, "GET": {"/fledge/bucket/([0-9][0-9]*)$": "/bucket/([0-9][0-9]*)$"}, "POST": {"/fledge/bucket": "/bucket"}, "PUT": {"/fledge/bucket/([0-9][0-9]*)$": "/bucket/([0-9][0-9]*)$", "/fledge/bucket/match": "/bucket/match"}}'
   """
    data = await request.json()
    svc_name = data.get('service_name', None)
    try:
        if svc_name is None:
            raise ValueError("service_name KV pair is required.")
        if svc_name is not None:
            if not isinstance(svc_name, str):
                raise TypeError("service_name must be in string.")
            svc_name = svc_name.strip()
            if not len(svc_name):
                raise ValueError("service_name cannot be empty.")
            del data['service_name']
            valid_verbs = ["GET", "POST", "PUT", "DELETE"]
            intersection = [i for i in valid_verbs if i in data]
            if not intersection:
                raise ValueError("Nothing to add in proxy for {} service. "
                                 "Pass atleast one {} verb in the given payload.".format(svc_name, valid_verbs))
            if not all(data.values()):
                raise ValueError("Value cannot be empty for a verb in the given payload.")
            for k, v in data.items():
                if not isinstance(v, dict):
                    raise TypeError("Value should be a dictionary object for {} key.".format(k))
                for k1, v1 in v.items():
                    if '/fledge/' not in k1:
                        raise ValueError("Public URL must start with /fledge prefix for {} key.".format(k))

            if svc_name in server.Server._API_PROXIES:
                raise ValueError("Proxy is already configured for {} service. "
                                 "Delete it first and then re-create.".format(svc_name))
    except (TypeError, ValueError, KeyError) as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({'message': msg}))
    else:
        # Add service name KV pair in-memory structure
        server.Server._API_PROXIES.update({svc_name: data})
        return web.json_response({"inserted": "Proxy has been configured for {} service.".format(svc_name)})


async def delete(request):
    """ Stop API proxy for a service

    :Example:
             curl -sX DELETE http://localhost:<SVC_MGT_PORT>/fledge/proxy/{service}
   """
    svc_name = request.match_info.get('service_name', None)
    svc_name = urllib.parse.unquote(svc_name) if svc_name is not None else None
    try:
        ServiceRegistry.filter_by_name_and_type(name=svc_name, s_type=SVC_TYPE)
        if svc_name not in server.Server._API_PROXIES:
            raise ValueError("For {} service, no proxy operation is configured.".format(svc_name))
    except service_registry_exceptions.DoesNotExist:
        msg = "{} service not found.".format(svc_name)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except (TypeError, ValueError, KeyError) as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({'message': msg}))
    else:
        # Remove service name KV pair from in-memory structure
        del server.Server._API_PROXIES[svc_name]
        return web.json_response({"deleted": "Proxy operations have been stopped for {} service.".format(svc_name)})
