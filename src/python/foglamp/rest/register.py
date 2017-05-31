import foglamp.rest.app as app
import asyncio


def register():
    # TODO Read port from config (but might use nginx or gunicorn in production)
    """Create a http server for REST listening on port 8080"""

    loop = asyncio.get_event_loop()
    f = loop.create_server(app.make_handler(), '0.0.0.0', 8080)
    loop.create_task(f)

