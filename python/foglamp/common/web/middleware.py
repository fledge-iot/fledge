# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from aiohttp import web
import json
import traceback

import jwt
from foglamp.services.core.user_model import User

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


JWT_SECRET = 'f0gl@mp'
JWT_ALGORITHM = 'HS256'

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


async def auth_middleware(app, handler):
    async def middleware(request):
        # if `rest_api` config has `authentication` set to mandatory then:
        #   request must carry auth header or should reuturn 403: Forbidden,
        #   actual header will be checked too and if bad then 401: unauthorized will be returned
        # else
        #   no action required here

        request.user = None

        # need to check, how to

        jwt_token = request.headers.get('authorization', None)
        if jwt_token:
            try:
                payload = jwt.decode(jwt_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            except (jwt.DecodeError, jwt.ExpiredSignatureError):
                raise web.HTTPUnauthorized()

            request.user = User.Objects.get(uid=payload['uid'])
        else:
            # TODO: bypass ping route based on allowPing=>True

            if str(handler).startswith("<function ping"):
                pass
            elif str(handler).startswith("<function login"):
                pass
            else:
                raise web.HTTPForbidden()

        return await handler(request)
    return middleware


def handle_api_exception(ex, _class=None, if_trace=0):
    err_msg = {"message": "[{}] {}".format(_class,  str(ex))}

    if if_trace:
        err_msg.update({"exception": _class, "traceback": traceback.format_exc()})

    return web.Response(status=500, body=json.dumps({'error': err_msg}).encode('utf-8'),
                        content_type='application/json')
