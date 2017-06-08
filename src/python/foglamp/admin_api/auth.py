"""
Authentication-related utilities
"""

from datetime import datetime
from aiohttp import web
import jwt
from foglamp.admin_api.model import User

# This will be moved to something that interacts with the configuration service
JWT_SECRET = 'secret'
JWT_ALGORITHM = 'HS256'
JWT_EXP_DAYS = 7
JWT_REFRESH_MINUTES = 15


def authentication_required(func):
    """Defines a decorator @authentication_required that should be added to all
    URI handlers that require authentication."""
    def wrapper(request):
        """Verify user is logged in and short-duration token has not expired"""
        if not request.user:
            return web.json_response({'message': 'Authentication required'}, status=403)

        try:
            if not request.jwt_payload['access']:
                return web.json_response({'message': 'Not an access token'},
                                         status=400)
        except Exception:
            return web.json_response({'message': 'Not an access token'},
                                     status=400)

        return func(request)
    return wrapper


async def auth_middleware(app, handler):
    #pylint: disable=unused-argument
    """This method is called for every REST request. It inspects
    the token (if there is one) for validity and checks whether
    it has expired.
    """

    async def middleware(request):
        """If there is an authorization header, this function confirms the
        validity of it and checks whether the token's long duration
        has expired.
        """
        request.user = None
        jwt_token = request.headers.get('authorization', None)
        if jwt_token:
            try:
                request.jwt_payload = jwt.decode(
                    jwt_token
                    , JWT_SECRET
                    , algorithms=[JWT_ALGORITHM])
            except jwt.DecodeError:
                return web.json_response({'message': 'Token is invalid'},
                                         status=400)
            except jwt.ExpiredSignatureError:
                return web.json_response({'message': 'Token expired'},
                                         status=401)
            request.user = User.objects.get(id=request.jwt_payload['user_id'])
        return await handler(request)
    return middleware

