# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import asyncio
from functools import wraps
import json
import traceback
from datetime import datetime

from aiohttp import web
import jwt

from fledge.common.logger import FLCoreLogger
from fledge.services.core.firewall import Firewall
from fledge.services.core.user_model import User


__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_logger = FLCoreLogger().get_logger(__name__)


async def error_middleware(app, handler):
    async def middleware_handler(request):
        if_trace = request.query.get('trace') if 'trace' in request.query and request.query.get('trace') == '1' else None

        try:
            response = await handler(request)
        except (web.HTTPException, asyncio.CancelledError):
            raise
        # Below Exception must come last as it is the super class of all exceptions
        except Exception as ex:
            return handle_api_exception(ex, ex.__class__.__name__, if_trace)
        else:
            return response

    return middleware_handler


async def optional_auth_middleware(app, handler):
    async def middleware(request):
        _logger.debug("Received %s request for %s", request.method, request.path)
        request.is_auth_optional = True
        request.user = None
        check_firewall(request)
        return await handler(request)
    return middleware


async def auth_middleware(app, handler):
    async def _disconnect_idle_logins(user_token):
        timeout, sessions = await User.Sessions.get()
        fmt = "%Y-%m-%d %H:%M:%S.%f"
        current_time = datetime.now().strftime(fmt)
        for session in sessions:
            if session['token'] == user_token:
                diff = datetime.strptime(current_time, fmt) - datetime.strptime(session['last_accessed_ts'], fmt)
                if diff.seconds > timeout:
                    raise User.SessionTimeout("Session has timed out or been disconnected. Log in again.")
                session['last_accessed_ts'] = current_time
                break

    async def middleware(request):
        # if `rest_api` config has `authentication` set to mandatory then:
        #   request must carry auth header,
        #   actual value will be checked too and if bad then 401: unauthorized will be returned
        _logger.debug("Received %s request for %s", request.method, request.path)
        request.is_auth_optional = False
        request.user = None
        check_firewall(request)
        if request.method == 'OPTIONS':
            return await handler(request)

        # make case insensitive `Authorization` should work
        try:
            token = request.headers.get('authorization', None)
        except:
            token = request.headers.get('Authorization', None)

        if token:
            try:
                # validate the token and get user id
                uid = await User.Objects.validate_token(token)
                if not str(handler).startswith("<function ping"):
                    # disconnect idle user logins
                    await _disconnect_idle_logins(token)
                # extend the token expiry, as token is valid
                # and no bad token exception raised
                await User.Objects.refresh_token_expiry(token)
                # set the user to request object
                request.user = await User.Objects.get(uid=uid)
                # set the token to request
                request.token = token
                # set if user is admin
                request.user_is_admin = True if int(request.user["role_id"]) == 1 else False
                # validate request path
                await validate_requests(request)
            except User.SessionTimeout as e:
                await User.Objects.delete_token(token)
                raise web.HTTPUnauthorized(reason=e)
            except (jwt.DecodeError, jwt.ExpiredSignatureError, User.InvalidToken, User.TokenExpired) as e:
                raise web.HTTPUnauthorized(reason=e)
            except jwt.exceptions.InvalidAlgorithmError:
                raise web.HTTPUnauthorized(reason="The token has expired, login again.")
        else:
            if str(handler).startswith("<function ping"):
                pass
            elif str(handler).startswith("<function login"):
                pass
            elif str(handler).startswith("<function update_password"):  # when pwd expiration
                pass
            else:
                raise web.HTTPUnauthorized()

        return await handler(request)
    return middleware


async def certificate_login_middleware(app, handler):
    async def middleware(request):
        if request.method == 'OPTIONS':
            return await handler(request)
        request.auth_method = 'certificate'
        return await handler(request)
    return middleware


async def password_login_middleware(app, handler):
    async def middleware(request):
        if request.method == 'OPTIONS':
            return await handler(request)
        request.auth_method = 'password'
        return await handler(request)
    return middleware


def has_permission(permission):
    """Decorator that restrict access only for authorized users with correct permissions (role_name)

    if user is authorized and does not have permission raises HTTPForbidden.
    """
    def wrapper(fn):
        @wraps(fn)
        async def wrapped(*args, **kwargs):
            request = args[-1]
            if not isinstance(request, web.BaseRequest):
                msg = ("Incorrect decorator usage. "
                       "Expecting `def handler(request)` "
                       "or `def handler(self, request)`.")
                raise RuntimeError(msg)

            if request.is_auth_optional is False:  # auth is mandatory
                roles_id = [int(r["id"]) for r in await User.Objects.get_role_id_by_name(permission)]
                if int(request.user["role_id"]) not in roles_id:
                    raise web.HTTPForbidden

            ret = await fn(*args, **kwargs)
            return ret

        return wrapped

    return wrapper


def handle_api_exception(ex, _class=None, if_trace=0):
    err_msg = {"message": "[{}] {}".format(_class,  str(ex))}

    if if_trace:
        err_msg.update({"exception": _class, "traceback": traceback.format_exc()})

    return web.Response(status=500, body=json.dumps({'error': err_msg}).encode('utf-8'),
                        content_type='application/json')


async def validate_requests(request):
    """
        a) With "normal" based user role id=2 only
           - restrict operations of Control scripts and pipelines except GET
        b) With "view" based user role id=3 only
           - read access operations (GET calls)
           - change profile (PUT call)
           - logout (PUT call)
           - extension API (PUT match call)
        c) With "data-view" based user role id=4 only
           - ping (GET call)
           - browser asset read operation (GET call)
           - service (GET call)
           - statistics, statistics history, statistics rate (GET call)
           - user profile (GET call)
           - user roles (GET call)
           - change profile (PUT call)
           - logout (PUT call)
        d) With "control" based user role id=5 only
           - same as normal user can do
           - All CRUD's privileges for control scripts
           - All CRUD's privileges for control pipelines
    """
    user_id = request.user['id']
    # Only URL's which are specific meant for Admin user
    if not request.user_is_admin and request.method == 'GET':
        # Special case: Allowed GET user for Control user
        if int(request.user["role_id"]) != 5 and str(request.rel_url) == '/fledge/user':
            raise web.HTTPForbidden
    # Normal/Editor user
    if int(request.user["role_id"]) == 2 and request.method != 'GET':
        # Special case: Allowed control entrypoint update request and handling of rejection in its handler
        if str(request.rel_url).startswith('/fledge/control') and not str(request.rel_url).startswith(
                '/fledge/control/request'):
            raise web.HTTPForbidden
    # Viewer user
    elif int(request.user["role_id"]) == 3:
        if request.method != 'GET':
            supported_endpoints = ['/fledge/user', '/fledge/user/{}/password'.format(user_id), '/logout',
                                   '/fledge/extension/bucket/match']
            if not str(request.rel_url).endswith(tuple(supported_endpoints)):
                raise web.HTTPForbidden
        else:
            if '/debug?action=' in str(request.rel_url):
                raise web.HTTPForbidden
    # Data Viewer user
    elif int(request.user["role_id"]) == 4:
        if request.method == 'GET':
            supported_endpoints = ['/fledge/asset', '/fledge/ping', '/fledge/statistics',
                                   '/fledge/user?', '/fledge/user/role']
            if not (str(request.rel_url).startswith(tuple(supported_endpoints)
                                                    ) or str(request.rel_url).endswith('/fledge/service')):
                raise web.HTTPForbidden
        elif request.method == 'PUT':
            supported_endpoints = ['/fledge/user', '/fledge/user/{}/password'.format(user_id), '/logout']
            if not str(request.rel_url).endswith(tuple(supported_endpoints)):
                raise web.HTTPForbidden
        else:
            raise web.HTTPForbidden


def check_firewall(req: web.Request) -> None:
    # FIXME: Need to check on other environments like AWS, docker; May be ideal with socket
    # import socket
    # hostname = socket.gethostname()
    # IPAddr = socket.gethostbyname(hostname)

    source_ip_address = req.transport.get_extra_info('peername')[0]
    if source_ip_address not in ['localhost', '127.0.0.1']:
        firewall_ip_addresses = Firewall.IPAddresses.get()
        if 'allowedIP' in firewall_ip_addresses:
            allowed = firewall_ip_addresses['allowedIP']
            if allowed:
                if source_ip_address not in allowed:
                    raise web.HTTPForbidden
            else:
                if 'deniedIP' in firewall_ip_addresses:
                    if source_ip_address in firewall_ip_addresses['deniedIP']:
                        raise web.HTTPForbidden

