"""
URI handlers accept a request object. This object has two
additional properties:
user
jwt_payload: the decrypted JWT payload
"""

from aiohttp import web
from foglamp.rest.login import login
from foglamp.rest.login import refresh_token
from foglamp.rest.login import auth_middleware
from foglamp.rest.login import get_user
from foglamp.rest.model import User

app = None

def _init():
    # Create a bogus user until users are moved to the database
    User.objects.create(name='username', password='password')

    global app
    app = web.Application(middlewares=[auth_middleware])

    router = app.router

    router.add_route('POST', '/api/auth/login', login)
    router.add_route('POST', '/api/auth/refresh-token', refresh_token)
    router.add_route('GET', '/api/example/whoami', get_user)

    # Static content - It's a hack
    #router__.add_static('/', '/home/foglamp/foglamp/example/web/login')


_init()

