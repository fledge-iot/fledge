'''
URI handlers accept a request object. This object has two
additional properties:
user
jwt_payload: the decrypted JWT payload
'''

from aiohttp import web
from foglamp.rest.login import login
from foglamp.rest.login import refresh_token
from foglamp.rest.login import auth_middleware
from foglamp.rest.login import get_user
from foglamp.rest.model import User

import asyncio

app = None
'''app is referenced by gunicorn - do not rename it'''

def _init():
    User.objects.create(name='username', password='password')

    global app
    app = web.Application(middlewares=[auth_middleware])

    router = app.router

    router.add_route('POST', '/api/auth/login', login)
    router.add_route('POST', '/api/auth/refresh-token', refresh_token)
    router.add_route('GET', '/api/example/whoami', get_user)

    # Static content - It's a hack
    #router__.add_static('/', '/home/foglamp/foglamp/example/web/login')


def register():
    loop = asyncio.get_event_loop()
    f = loop.create_server(app.make_handler(), '0.0.0.0', 8080)
    loop.create_task(f)

# Register URI handlers
# must do it now to support Unicorn
_init()

