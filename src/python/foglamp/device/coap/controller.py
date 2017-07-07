import asyncio
import aiocoap

from foglamp.device.coap.sensor_values import SensorValues


def start():
    """Registers all CoAP URI handlers"""
    root = aiocoap.resource.Site()

    # Register CoAP methods
    root.add_resource(('.well-known', 'core'),
                      aiocoap.resource.WKCResource(root.get_resources_as_linkheader))

    SensorValues().register_handlers(root)

    asyncio.Task(aiocoap.Context.create_server_context(root))
