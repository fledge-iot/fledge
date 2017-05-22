import json
from datetime import datetime, timedelta

from aiohttp import web
import jwt

from user import User

User.objects.create(name='username', password='password')

JWT_SECRET = 'secret'
JWT_ALGORITHM = 'HS256'
JWT_EXP_DAYS = 7 
JWT_REFRESH_MINUTES = 15

def json_response(body='', **kwargs):
    kwargs['body'] = json.dumps(body or kwargs['body']).encode('utf-8')
    kwargs['content_type'] = 'text/json'
    return web.Response(**kwargs)

async def login(request):
    '''Given a user name and a password as query string, a 
    token in JWT format is returned. The token
    should be provided in the 'authorization' header. The token
    expires after 15 minutes. Post to /refresh_token to reset 
    the expiration time. The token can be refreshed for up to
    7 days.'''

    post_data = await request.post()

    try:
        user = User.objects.get(name=post_data['user'])
        user.match_password(post_data['password'])
    except (User.DoesNotExist, User.PasswordDoesNotMatch):
        return json_response({'message': 'Wrong credentials'}, status=400)

    payload = {
        'user_id': user.id
        , 'exp': datetime.utcnow() + timedelta(days=JWT_EXP_DAYS)
        , 'refresh_exp': (datetime.utcnow() + timedelta(minutes=JWT_REFRESH_MINUTES)).timestamp()
    }
    jwt_token = jwt.encode(payload, JWT_SECRET, JWT_ALGORITHM)
    return json_response({'token': jwt_token.decode('utf-8')})

async def refresh_token(request):
    '''Returns a new token that expires after 15 minutes'''
    if not request.user:
        return json_response({'message': 'Auth required'}, status=401)

    payload = {
        'user_id': request.payload['user_id']
        , 'exp': request.payload['exp']
        , 'refresh_exp': (datetime.utcnow() + timedelta(minutes=JWT_REFRESH_MINUTES)).timestamp()
    }
    jwt_token = jwt.encode(payload, JWT_SECRET, JWT_ALGORITHM)
    return json_response({'token': jwt_token.decode('utf-8')})

def authentication_required(func):
    '''Defines a decorator @authentication_required that should be added to all
    URI handlers that require authentication.'''
    def wrapper(request):
        if not request.user:
            return json_response({'message': 'Auth required'}, status=401)
        if datetime.utcnow().timestamp() > request.payload['refresh_exp']:
            return json_response({'message': 'Token expired'}
                                , status=400)
        return func(request)
    return wrapper

@authentication_required
async def get_user(request):
    '''An example method that responds with the currently logged in user's details in JSON format'''
    return json_response({'user': str(request.user)})

async def auth_middleware(app, handler):
    '''This method is called for every REST request. It inspects
        the token if there is one for validity and checks whether
        it has expired.'''

    async def middleware(request):
        request.user = None
        jwt_token = request.headers.get('authorization', None)
        if jwt_token:
            try:
                request.payload = jwt.decode(jwt_token, JWT_SECRET,
                                     algorithms=[JWT_ALGORITHM])
            except (jwt.DecodeError):
                return json_response({'message': 'Token is invalid'},
                                     status=400)
            except (jwt.ExpiredSignatureError):
                return json_response({'message': 'Token expired'},
                                     status=400)
            request.user = User.objects.get(id=request.payload['user_id'])
        return await handler(request)
    return middleware

app = web.Application(middlewares=[auth_middleware])
app.router.add_route('GET', '/whoami', get_user)
app.router.add_route('POST', '/login', login)
app.router.add_route('POST', '/refresh-token', refresh_token)
