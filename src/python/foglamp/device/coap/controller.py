import asyncio
import aiocoap

from foglamp import configuration_manager
from foglamp.device.coap.sensor_values import SensorValues

"""Configuration for the CoAP are based on https://docs.google.com/document/d/1wPg-XzkdLPgFlC3JjpSaMivVH3VyjKvGa4TVJJukvdg/edit#heading=h.ru11tt2gnb6g"""


_CONFIG_CATEGORY_NAME = 'COAP_CONF'

_CONFIG_CATEGORY_DESCRIPTION = 'CoAP Configuration'

_DEFAULT_COAP_CONFIG = {
    "port": {
        "description": "Port to listen on",
        "type": "integer", 
        "default": "5683",
    },
    "uri": {
        "description" : "URI to accept data on",
        "type": "string",
        "default" : "sensor-values",
    },
    # certificate is not currently utilized 
    "certificate": {
        "description" : "X509 certificate used to identify ingress interface",
        "type" : "X509 certificate",
        "default": ""
    }
}

def configure_coap() -> (str, str): 
    """
    Configure the CoAP server 
    Return:
        Per CoAP configuration return corresponding values 
    """
    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(configuration_manager.create_category(_CONFIG_CATEGORY_NAME, _DEFAULT_COAP_CONFIG, _CONFIG_CATEGORY_DESCRIPTION))
    config = event_loop.run_until_complete(configuration_manager.get_category_all_items(_CONFIG_CATEGORY_NAME))

    uri = config["uri"]["value"]
    port = config["port"]["value"]

    return uri, int(port)
    
def start():
    """Registers all CoAP URI handlers"""
    # Retrive CoAP configs
    uri, port = configure_coap()

    root = aiocoap.resource.Site()

    # Register CoAP methods
    root.add_resource(('.well-known', 'core'),
                      aiocoap.resource.WKCResource(root.get_resources_as_linkheader))

    SensorValues().register_handlers(root, uri)

    asyncio.Task(aiocoap.Context.create_server_context(root, bind=('::', port)))
    # asyncio.Task(aiocoap.Context.create_server_context(root))



