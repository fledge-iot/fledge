"""
Authentication-related URI handlers
"""

from datetime import datetime, timedelta

import jwt
from .model import User
from .util import authentication_required
from aiohttp.web import json_response

__JWT_SECRET = 'secret'
__JWT_ALGORITHM = 'HS256'
__JWT_EXP_DAYS = 7
__JWT_REFRESH_MINUTES = 15

async def login(request):
    """Given a user name and a password as query string, a
    token in JWT format is returned. The token
    should be provided in the 'authorization' header. The token
    expires after 15 minutes. Post to /refresh_token to reset
    the expiration time. The token can be refreshed for up to
    7 days.

    The response is a JSON document like:
    {
        "token": "eyJ0eXAiOiJKV1..."
    }
    """

    post_data = await request.post()

    try:
        user = User.objects.get(name=post_data['user'])
        user.match_password(post_data['password'])
    except (User.DoesNotExist, User.PasswordDoesNotMatch):
        return json_response({'message': 'Authentication failed'}, status=400)

    payload = {'user_id': user.id,
               'exp': datetime.utcnow() + timedelta(days=__JWT_EXP_DAYS),
               'refresh_exp': (datetime.utcnow()
                               + timedelta(minutes=__JWT_REFRESH_MINUTES)).timestamp()}

    jwt_token = jwt.encode(payload, __JWT_SECRET, __JWT_ALGORITHM)
    return json_response({'token': jwt_token.decode('utf-8')})

async def refresh_token(request):
    """Returns a new token that expires after 15 minutes"""
    if not request.user:
        return json_response({'message': 'Authentication required'}, status=400)

    payload = {'user_id': request.jwt_payload['user_id'],
               'exp': request.jwt_payload['exp'],
               'refresh_exp': (datetime.utcnow()
                               + timedelta(minutes=__JWT_REFRESH_MINUTES)).timestamp()}
    jwt_token = jwt.encode(payload, __JWT_SECRET, __JWT_ALGORITHM)
    return json_response({'token': jwt_token.decode('utf-8')})

@authentication_required
async def get_user(request):
    """An example method that responds with the currently logged in user's details in JSON format"""
    return json_response({'user': str(request.user)})

async def auth_middleware(app, handler):
    #pylint: disable=unused-argument
    """
    This method is called for every REST request. It inspects
    the token (if there is one) for validity and checks whether
    it has expired."""

    async def middleware(request):
        """
        If there is an authorization header, this function confirms the
        validity of it and checks whether the token's long duration
        has expired."""
        request.user = None
        jwt_token = request.headers.get('authorization', None)
        if jwt_token:
            try:
                request.jwt_payload = jwt.decode(
                    jwt_token
                    , __JWT_SECRET
                    , algorithms=[__JWT_ALGORITHM])
            except jwt.DecodeError:
                return json_response({'message': 'Token is invalid'},
                                     status=400)
            except jwt.ExpiredSignatureError:
                return json_response({'message': 'Token expired'},
                                     status=400)
            request.user = User.objects.get(id=request.jwt_payload['user_id'])
        return await handler(request)
    return middleware

def register_handlers(router):
    """Registers URI handlers"""
    router.add_route('POST', '/api/auth/login', login)
    router.add_route('POST', '/api/auth/refresh-token', refresh_token)
    router.add_route('GET', '/api/example/whoami', get_user)

