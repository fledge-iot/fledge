import asyncio

from .device_api.coap import controller as coap_controller
from .admin_api import controller as admin_api_controller
import foglamp.env as env


def start():
    env.load_config()

    coap_controller.start()

    admin_api_controller.start()

    asyncio.get_event_loop().run_forever()

