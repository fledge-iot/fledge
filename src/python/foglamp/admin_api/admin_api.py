from aiohttp import web
from .model import User
from .login import register, auth_middleware
import asyncio


def create_app():
    """"""

    # Create a bogus user until users are moved to the database
    User.objects.create(name='username', password='password')

    app = web.Application(middlewares=[auth_middleware])
    router = app.router

    # Register URI handlers
    register(router)

    # Static content - It's a hack
    #router__.add_static('/', '/home/foglamp/foglamp/example/web/login')

    return app


def start():
    """Create a http server for REST listening on port 8080"""
    # TODO Read port from config (but might use nginx or gunicorn in production)

    loop = asyncio.get_event_loop()
    f = loop.create_server(create_app().make_handler(), '0.0.0.0', 8080)
    loop.create_task(f)

