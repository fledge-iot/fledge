from aiohttp import web
from .model import User
from .login import register_handlers as login_register_handlers, auth_middleware


def build():
    """
    :return: An application
    """

    # Create a bogus user until users are moved to the database
    User.objects.create(name='username', password='password')

    app = web.Application(middlewares=[auth_middleware])
    router = app.router

    # Register URI handlers
    login_register_handlers(router)

    # Static content - It's a hack
    #router__.add_static('/', '/home/foglamp/foglamp/example/web/login')

    return app

