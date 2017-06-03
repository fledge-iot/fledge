import asyncio

from .device_api.coap.starter import start as coap_start
from .admin_api.starter import start as admin_api_start
from .model.starter import start as model_start
from .basic_config.starter import start as config_start


def start():
    config_start()
    model_start()
    coap_start()
    admin_api_start()

    asyncio.get_event_loop().run_forever()

