import asyncio
import aiocoap
import aiocoap.resource as resource

from .methods.ingest import Ingest

class CoAPServer:
    @staticmethod
    def start():
        root = resource.Site()

        # Register CoAP methods
        root.add_resource(('.well-known', 'core'), resource.WKCResource(root.get_resources_as_linkheader))

        Ingest().register(root)

        asyncio.Task(aiocoap.Context.create_server_context(root))

