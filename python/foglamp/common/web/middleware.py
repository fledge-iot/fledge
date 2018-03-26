# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from functools import wraps
import json
import traceback

from aiohttp import web
import jwt

from foglamp.services.core.user_model import User
from foglamp.common import logger

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_logger = logger.setup(__name__, level=20)


async def error_middleware(app, handler):
    async def middleware_handler(request):
        if_trace = request.query.get('trace') if 'trace' in request.query and request.query.get('trace') == '1' else None

        try:
            response = await handler(request)
            return response
        except web.HTTPException:
            raise
        # Below Exception must come last as it is the super class of all exceptions
        except Exception as ex:
            return handle_api_exception(ex, ex.__class__.__name__, if_trace)

    return middleware_handler


async def optional_auth_middleware(app, handler):
    async def middleware(request):
        _logger.info("Received %s request for %s", request.method, request.path)
        request.is_auth_optional = True
        request.user = None
        return await handler(request)
    return middleware


async def auth_middleware(app, handler):
    async def middleware(request):
        # if `rest_api` config has `authentication` set to mandatory then:
        #   request must carry auth header or should reuturn 403: Forbidden,
        #   actual header will be checked too and if bad then 401: unauthorized will be returned
        _logger.info("Received %s request for %s", request.method, request.path)

        request.is_auth_optional = False
        request.user = None

        if request.method == 'OPTIONS':
            return await handler(request)

        token = request.headers.get('authorization', None)
        if token:
            try:
                # validate the token and get user id
                uid = User.Objects.validate_token(token)
                # extend the token expiry, as token is valid
                # and no bad token exception raised
                User.Objects.refresh_token_expiry(token)
                # set the user to request object
                request.user = User.Objects.get(uid=uid)
                # set the token to request
                request.token = token
            except(User.InvalidToken, User.TokenExpired) as e:
                raise web.HTTPUnauthorized(reason=e)
            except (jwt.DecodeError, jwt.ExpiredSignatureError) as e:
                raise web.HTTPUnauthorized(reason=e)
        else:
            if str(handler).startswith("<function ping"):
                pass
            elif str(handler).startswith("<function login"):
                pass
            else:
                raise web.HTTPForbidden()

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
                roles_id = [int(r["id"]) for r in User.Objects.get_role_id_by_name(permission)]
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
