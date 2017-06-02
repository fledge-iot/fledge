import asyncio

from .coap_api.coap_api import start as coap_start
from .admin_api.admin_api import start as admin_api_start
from .model.model import start as model_start
from .config import start as config_start


def start():
    config_start()
    model_start()
    coap_start()
    admin_api_start()

    asyncio.get_event_loop().run_forever()

