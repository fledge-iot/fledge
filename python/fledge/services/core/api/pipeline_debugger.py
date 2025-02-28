# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import json
import aiohttp
from aiohttp import web

from fledge.common.logger import FLCoreLogger
from fledge.common.service_record import ServiceRecord
from fledge.services.core.service_registry.service_registry import ServiceRegistry
from fledge.services.core.service_registry import exceptions as service_registry_exceptions


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2025 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_logger = FLCoreLogger().get_logger(__name__)

_help = """
    -----------------------------------------------------------------------------------------------------------------
    | GET | PUT                      |        /fledge/service/{name}/debug?action=                                  |
    -----------------------------------------------------------------------------------------------------------------
"""

SUPPORTED_ACTIONS = ["attach", "detach", "buffer", "isolate", "suspend", "replay", "step"]
FORBIDDEN_MSG = 'Resource you were trying to reach is absolutely forbidden for some reason'


def setup(app):
    app.router.add_route('GET', '/fledge/service/{name}/debug', get_action)
    app.router.add_route('PUT', '/fledge/service/{name}/debug', put_action)


async def get_action(request: web.Request) -> web.Response:
    if request.is_auth_optional:
        _logger.warning(FORBIDDEN_MSG)
        raise web.HTTPForbidden
    try:
        action_items = ['buffer', 'state']
        svc_name = request.match_info.get('name', None)
        if 'action' in request.query and request.query['action'] != '' and request.query['action'] in action_items:
            svc, svc_type, bearer_token = await _check_service(svc_name)
            url = "fledge/{}/debug/{}".format(svc_type, request.query['action'])
            status_code, response = await _call_service_api(
                'GET', svc._protocol, svc._address, svc._port, url, bearer_token, {})
        else:
            raise ValueError('The action query parameter is either missing, empty, or contains an invalid value. '
                             'Valid values are: {}'.format(action_items))
    except service_registry_exceptions.DoesNotExist:
        msg = "No '{}' service available!.".format(svc_name)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except ValueError as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response(status=status_code, body=response)

async def put_action(request: web.Request) -> web.Response:
    if request.is_auth_optional:
        _logger.warning(FORBIDDEN_MSG)
        raise web.HTTPForbidden
    try:
        data = {}
        svc_name = request.match_info.get('name', None)
        if 'action' in request.query and request.query['action'] != '' and request.query['action'] in SUPPORTED_ACTIONS:
            if request.body_exists:
                data = await request.json()
            svc, svc_type, bearer_token = await _check_service(svc_name)
            action_name = request.query['action']
            url = "fledge/{}/debug/{}".format(svc_type, action_name)
            # For consistency, the buffer size should also be set with PUT from the C pipeline
            verb = 'PUT' if action_name != 'buffer' else 'POST'
            status_code, response = await _call_service_api(
                verb, svc._protocol, svc._address, svc._port, url, bearer_token, data)
        else:
            raise ValueError('The action query parameter is either missing, empty, or contains an invalid value. '
                             'Valid values are: {}'.format(SUPPORTED_ACTIONS))
    except service_registry_exceptions.DoesNotExist:
        msg = "No '{}' service available!.".format(svc_name)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except ValueError as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response(status=status_code, body=response)

async def _check_service(svc_name):
    service = ServiceRegistry.get(name=svc_name)
    token = ServiceRegistry.getBearerToken(svc_name)
    svc = service[0]
    if svc._type == 'Northbound':
        svc_type = "north"
    elif svc._type == 'Southbound':
        svc_type = "south"
    else:
        raise ValueError('This is currently valid only for services with a type of "South" or "North".')
    if svc._status != ServiceRecord.Status.Running:
        raise ValueError("The '{}' service is not in a Running state.".format(svc_name))
    return svc, svc_type, token


async def _call_service_api(verb: str, protocol: str, address: str, port: int, uri: str, token: str, payload: dict):
    # Custom Request header
    headers = {}
    if token is not None:
        headers['Authorization'] = "Bearer {}".format(token)
    url = "{}://{}:{}/{}".format(protocol, address, port, uri)
    try:
        if verb == 'GET':
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    status_code = resp.status
                    jdoc = await resp.text()
                    response = (resp.status, jdoc)
                    if status_code not in range(200, 209):
                        _logger.error("GET Request Error code: {}, reason: {}, details: {}, url: {}".format(
                            resp.status, resp.reason, jdoc, uri))
        elif verb == 'PUT':
            async with aiohttp.ClientSession() as session:
                async with session.put(url, headers=headers, data=json.dumps(payload) if payload else None) as resp:
                    jdoc = await resp.text()
                    response = (resp.status, jdoc)
                    if resp.status not in range(200, 209):
                        _logger.error("PUT Request Error code: {}, reason: {}, details: {}, url: {}".format(
                            resp.status, resp.reason, jdoc, uri))
        else:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=json.dumps(payload), headers=headers) as resp:
                    jdoc = await resp.text()
                    response = (resp.status, jdoc)
                    if resp.status not in range(200, 209):
                        _logger.error("POST Request Error code: {}, reason: {}, details: {}, url: {}".format(
                            resp.status, resp.reason, jdoc, uri))
    except Exception as ex:
        raise Exception(str(ex))
    else:
        # Return Tuple - (http statuscode, message)
        return response

