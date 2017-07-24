# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from aiohttp import web
import json

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


def json_error(message):
    return web.Response(
        body=json.dumps({'error': message}).encode('utf-8'),
        content_type='application/json')

async def error_middleware(app, handler):
    async def middleware_handler(request):
        try:
            response = await handler(request)
            if response.status == 404:
                return json_error(response.message)
            return response
        except web.HTTPNotFound as ex:
            return json_error(ex.reason)
        except web.HTTPInternalServerError as ex:
            return json_error(ex.reason + '[' + ex.text + ']')
        except web.HTTPException as ex:
            if ex.status == 404:
                return json_error(ex.reason)
            raise
    return middleware_handler
