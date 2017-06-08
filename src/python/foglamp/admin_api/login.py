"""
Authentication-related URI handlers
"""

from datetime import datetime, timedelta
from foglamp.admin_api.model import User
from foglamp.admin_api.auth import authentication_required
import jwt
from aiohttp import web
from foglamp.admin_api.auth import JWT_ALGORITHM, JWT_REFRESH_MINUTES, JWT_EXP_DAYS, JWT_SECRET

async def login(request):
    """Given a user name and a password as query string, tokens
    in JWT format are returned.
    |
    The response is a JSON document like:
    {
        "access_token": "eyJ0eXAiOiJKV1..."
        "refresh_token": "eyJ0eXAiOiJKV1..."
    }
    |
    access_token should be provided in the 'authorization' header
    for methods that require authentication.
    |
    The access token expires after 15 minutes. Post to /api/refresh_token with
    the 'authorization' header set to refresh_token to get a new
    access token. The refresh token expires after 7 days.
    """

    try:
        post_data = await request.json()
        user = User.objects.get(name=post_data['username'])
        user.match_password(post_data['password'])
    except (User.DoesNotExist, User.PasswordDoesNotMatch):
        return web.json_response({'message': 'Authentication failed'}, status=400)
    except Exception:
        return web.json_response({'message': 'Invalid request'}, status=400)

    access_payload = {'user_id': user.id,
                      'exp': (datetime.utcnow()
                            + timedelta(minutes=JWT_REFRESH_MINUTES)),
                      'access': 1
                    }

    refresh_payload = {'user_id': user.id,
                       'exp': datetime.utcnow() + timedelta(days=JWT_EXP_DAYS),
                       'access': 0
                      }

    access_t = jwt.encode(access_payload, JWT_SECRET, JWT_ALGORITHM)
    refresh_t = jwt.encode(refresh_payload, JWT_SECRET, JWT_ALGORITHM)

    return web.json_response({'access_token': access_t.decode('utf-8'),
                          'refresh_token': refresh_t.decode('utf-8'),
                         })


async def refresh_token(request):
    """Returns a new token that expires after 15 minutes"""
    if not request.user:
        return web.json_response({'message': 'Authentication required'}, status=400)

    try:
        if request.jwt_payload['access']:
            return web.json_response({'message': 'Refresh token not provided'},
                                     status=400)
    except Exception:
        return web.json_response({'message': 'Invalid token'},
                                 status=400)

    # TODO: Verify user exists
    payload = {'user_id': request.jwt_payload['user_id'],
               'exp': (datetime.utcnow()
                       + timedelta(minutes=JWT_REFRESH_MINUTES)),
               'access': 1
              }
    jwt_token = jwt.encode(payload, JWT_SECRET, JWT_ALGORITHM)
    return web.json_response({'access_token': jwt_token.decode('utf-8')})


@authentication_required
async def whoami(request):
    """An example method that responds with the currently logged in user's details in JSON format"""
    return web.json_response({'username': request.user.name})


def register_handlers(router):
    """Registers URI handlers"""
    router.add_route('POST', '/api/auth/login', login)
    router.add_route('POST', '/api/auth/refresh-token', refresh_token)
    router.add_route('GET', '/api/example/whoami', whoami)

