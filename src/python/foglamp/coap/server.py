import asyncio
import aiocoap
import aiocoap.resource as resource

from foglamp.coap.uri_handlers.sensor_values import SensorValues


class CoAPServer:
    @staticmethod
    def start():
        root = resource.Site()

        # Register CoAP methods
        root.add_resource(('.well-known', 'core'), resource.WKCResource(root.get_resources_as_linkheader))

        SensorValues().register(root)

        asyncio.Task(aiocoap.Context.create_server_context(root))
        asyncio.get_event_loop().run_forever()

