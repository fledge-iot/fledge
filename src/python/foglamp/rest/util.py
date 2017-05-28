'''Defines utility function used
by all uri handlers'''

from datetime import datetime
from aiohttp import web
import json

def json_response(body='', **kwargs):
    '''Creates http response (body)'''
    kwargs['body'] = json.dumps(body or kwargs['body']).encode('utf-8')
    kwargs['content_type'] = 'text/json'
    return web.Response(**kwargs)

def authentication_required(func):
    '''Defines a decorator @authentication_required that should be added to all
    URI handlers that require authentication.'''
    def wrapper(request):
        '''Verify user is logged in and short-duration token has not expired'''
        if not request.user:
            return json_response({'message': 'Auth required'}, status=401)
        if datetime.utcnow().timestamp() > request.jwt_payload['refresh_exp']:
            return json_response({'message': 'Token expired'},
                                 status=400)
        return func(request)
    return wrapper
