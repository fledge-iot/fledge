import asyncio
import aiocoap
import aiocoap.resource as resource

from foglamp.coap.sensor_values import SensorValues


def register():
    root = resource.Site()

    # Register CoAP methods
    root.add_resource(('.well-known', 'core'), resource.WKCResource(root.get_resources_as_linkheader))

    SensorValues().register(root)

    asyncio.Task(aiocoap.Context.create_server_context(root))
