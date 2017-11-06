# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from aiohttp import web
import json
import sys, traceback

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


def json_error(message):
    return web.Response(body=json.dumps({'error': message}).encode('utf-8'), content_type='application/json')

async def error_middleware(app, handler):
    async def middleware_handler(request):
        if_trace = request.query.get('trace') if 'trace' in request.query and request.query.get('trace') == '1' else None

        try:
            response = await handler(request)
            if response.status == 404:
                return handle_api_exception({"code": response.status, "message": response.message}, ex.__class__.__name__, if_trace)
            return response
        except (web.HTTPNotFound, web.HTTPBadRequest) as ex:
            return handle_api_exception({"code": ex.status_code, "message": ex.reason}, ex.__class__.__name__, if_trace)
        except web.HTTPException as ex:
            raise
        # Below Exception must come last as it is the super class of all exceptions
        except Exception as ex:
            return handle_api_exception(ex, ex.__class__.__name__, if_trace)

    return middleware_handler


def handle_api_exception(ex, _class=None, if_trace=0):
    if not isinstance(ex, Exception):
        err_msg = ex
    else:
        _msg = str(ex)

        scode = 500
        err_msg = {"code": scode, "message": '['+_class+']'+_msg}

    if if_trace:
        err_msg.update({"exception": _class, "traceback": traceback.format_exc()})

    return json_error(err_msg)
