"""Intended for use with a WSGI compliant server such as Nginx or Gunicorn
|
See
http://aiohttp.readthedocs.io/en/stable/deployment.html#start-gunicorn
for starting the 'app' module variable with gunicorn
|
Example:|
gunicorn foglamp.admin_api.wsgi:app --bind localhost:8080 --worker-class aiohttp.GunicornWebWorker --reload
"""

import logging
from .app_builder import build as build_app


try:
    # The name 'app' is used by WSGI server. Don't change it.
    app = build_app()
except Exception as e:
    logging.exception("Unable to start web application")

