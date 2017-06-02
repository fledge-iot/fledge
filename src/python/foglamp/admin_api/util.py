"""Defines utility function used
by all uri handlers
"""

from datetime import datetime
from aiohttp import web

def authentication_required(func):
    """Defines a decorator @authentication_required that should be added to all
    URI handlers that require authentication."""
    def wrapper(request):
        """Verify user is logged in and short-duration token has not expired"""
        if not request.user:
            return web.json_response({'message': 'Auth required'}, status=401)
        if datetime.utcnow().timestamp() > request.jwt_payload['refresh_exp']:
            return web.json_response({'message': 'Token expired'},
                                 status=400)
        return func(request)
    return wrapper
