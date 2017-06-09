import asyncio

from foglamp.device_api.coap import controller as coap_controller
from foglamp.admin_api import controller as admin_api_controller
import foglamp.env as env


def start():
    """Starts FogLAMP services"""
    env.load_config()
    coap_controller.start()
    admin_api_controller.start()
    asyncio.get_event_loop().run_forever()

