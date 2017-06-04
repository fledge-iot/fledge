import asyncio

from .device_api.coap.controller import start as coap_start
from .admin_api.controller import start as admin_api_start
from .model.controller import start as model_start
from .env import read as env_read


def start():
    env_read()
    model_start()
    coap_start()
    admin_api_start()

    asyncio.get_event_loop().run_forever()

