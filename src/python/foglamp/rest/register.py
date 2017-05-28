from foglamp.rest.app import app
import asyncio


def register():
    loop = asyncio.get_event_loop()
    f = loop.create_server(app.make_handler(), '0.0.0.0', 8080)
    loop.create_task(f)

