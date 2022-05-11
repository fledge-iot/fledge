# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import json
import logging
import urllib.parse
import aiohttp

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


def setup(app):
    app.router.add_route('POST', '/fledge/proxy', add)
    app.router.add_route('DELETE', '/fledge/proxy/{service_name}', delete)


async def add(request):
    """ Add API proxy for a service

    :Example:
        curl -sX POST http://localhost:<SVC_MGT_PORT>/fledge/proxy -d '{"service_name": "SVC #1", "DELETE": {"/fledge/svc/([0-9][0-9]*)$": "/svc/([0-9][0-9]*)$"}, "GET": {"/fledge/svc/([0-9][0-9]*)$": "/svc/([0-9][0-9]*)$"}, "POST": {"/fledge/svc": "/svc"}, "PUT": {"/fledge/svc/([0-9][0-9]*)$": "/svc/([0-9][0-9]*)$", "/fledge/svc/match": "/svc/match"}}'
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
        try:
            for method, path in data.items():
                for admin_route, micro_svc_route in path.items():
                    prefix_url = '/{}/{}'.format(admin_route.split('/')[1], admin_route.split('/')[2])
                    break
                break
            widecast = '{}{{head:.*}}'.format(prefix_url)
            # Add dynamic public routes for configured Proxy
            server.Server.dynamic_route.add_any(widecast, handler=handler)
            # NOTE: There will be no same Public URL for different Proxies
            # Add service name KV pair in-memory structure
            server.Server._API_PROXIES.update({svc_name: {"endpoints": data, "prefix_url": prefix_url}})
        except Exception as ex:
            msg = str(ex)
            raise web.HTTPInternalServerError(reason=msg, body=json.dumps({'message': msg}))
        return web.json_response({"inserted": "Proxy has been configured for {} service.".format(svc_name)})


async def delete(request):
    """ Stop API proxy for a service

    :Example:
             curl -sX DELETE http://localhost:<SVC_MGT_PORT>/fledge/proxy/{service}
   """
    svc_name = request.match_info.get('service_name', None)
    svc_name = urllib.parse.unquote(svc_name) if svc_name is not None else None
    try:
        ServiceRegistry.get(name=svc_name)
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


async def handler(request):
    """ widecast handler """
    allow_methods = ["GET", "POST", "PUT", "DELETE"]
    if request.method not in allow_methods:
        raise web.HTTPMethodNotAllowed(method=request.method, allowed_methods=allow_methods)
    try:
        data = await request.json() if request.method != 'GET' else None
        # Find service name as per request.rel_url in proxy dict in-memory
        is_proxy_svc_found = False
        proxy_svc_name = None
        for svc_name, svc_info in server.Server._API_PROXIES.items():
            if svc_info['prefix_url'] in str(request.rel_url):
                is_proxy_svc_found = True
                proxy_svc_name = svc_name
        if is_proxy_svc_found and proxy_svc_name is not None:
            svc, token = await _get_service_record_info_along_with_bearer_token(proxy_svc_name)
            url = str(request.url).split('fledge/')[1]
            result = await _call_microservice_service_api(request.method, svc._protocol, svc._address,
                                                          svc._port, url, token, data)
        else:
            raise web.HTTPForbidden()
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({"info": result})


async def _get_service_record_info_along_with_bearer_token(svc_name):
    try:
        service = ServiceRegistry.get(name=svc_name)
        svc_name = service[0]._name
        token = ServiceRegistry.getBearerToken(svc_name)
    except service_registry_exceptions.DoesNotExist:
        msg = "No service available with {} name.".format(svc_name)
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
            _logger.warning("{} method is not implemented yet.".format(method))
    except Exception as ex:
        _logger.error(str(ex))
        raise Exception(response)
    else:
        return response
