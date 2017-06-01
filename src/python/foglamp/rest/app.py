"""
See
http://aiohttp.readthedocs.io/en/stable/deployment.html#start-gunicorn
for starting the 'app' module variable with gunicorn
"""

from aiohttp import web
from .model import User
from .login import auth_middleware
from .login import register as login_register
import logging

app = None

def _init():
    # Create a bogus user until users are moved to the database
    User.objects.create(name='username', password='password')

    global app
    app = web.Application(middlewares=[auth_middleware])

    router = app.router

    login_register(router)

    # Static content - It's a hack
    #router__.add_static('/', '/home/foglamp/foglamp/example/web/login')


#TODO log exceptions
try:
    _init()
except Exception as e:
    logging.error(e)

