import asyncio
import aiocoap
import aiocoap.resource as resource

from .methods.ingest import Ingest

class Server:
    @staticmethod
    def start():
        root = resource.Site()
        root.add_resource(('.well-known', 'core'), resource.WKCResource(root.get_resources_as_linkheader))

        # Register methods
        Ingest().register(root)

        asyncio.Task(aiocoap.Context.create_server_context(root))

