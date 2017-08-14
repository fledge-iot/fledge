# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""CoAP handler for coap://other/sensor_readings URI"""

import asyncio
import logging

import aiocoap.resource
from cbor2 import loads
from cbor2.decoder import CBORDecodeError

from foglamp import configuration_manager
from foglamp import logger
from foglamp.device.ingest import Ingest


_LOGGER = logger.setup(__name__)  # type: logging.Logger

# pylint: disable=line-too-long
# Configuration: https://docs.google.com/document/d/1wPg-XzkdLPgFlC3JjpSaMivVH3VyjKvGa4TVJJukvdg/edit#heading=h.ru11tt2gnb6g
# pylint: enable=line-too-long
_CONFIG_CATEGORY_NAME = 'COAP_CONF'
_CONFIG_CATEGORY_DESCRIPTION = 'CoAP Configuration'

_DEFAULT_CONFIG = {
    "port": {
        "description": "Port to listen on",
        "type": "integer",
        "default": "5683",
    },
    "uri": {
        "description": "URI to accept data on",
        "type": "string",
        "default": "sensor-values",
    }
}


async def start():
    """Registers CoAP URI handler"""

    # Retrieve CoAP configuration
    await configuration_manager.create_category(
        _CONFIG_CATEGORY_NAME,
        _DEFAULT_CONFIG,
        _CONFIG_CATEGORY_DESCRIPTION)

    config = await configuration_manager.get_category_all_items(_CONFIG_CATEGORY_NAME)

    uri = config["uri"]["value"]
    port = config["port"]["value"]

    root = aiocoap.resource.Site()

    root.add_resource(('.well-known', 'core'),
                      aiocoap.resource.WKCResource(root.get_resources_as_linkheader))

    root.add_resource(('other', uri), SensorValues())

    asyncio.Task(aiocoap.Context.create_server_context(root, bind=('::', int(port))))


class SensorValues(aiocoap.resource.Resource):
    """CoAP handler for coap://readings URI"""

    @staticmethod
    async def render_post(request):
        # Required keys in the payload
        try:
            payload = loads(request.payload)

            try:
                await Ingest.add_readings(payload)
                # Success
                # TODO what should this return?
                return aiocoap.Message(payload=''.encode("utf-8"),
                                       code=aiocoap.numbers.codes.Code.VALID)
            except (KeyError, IOError):
                _LOGGER.exception("Failed processing payload: %s", payload)
        except CBORDecodeError:
            Ingest.increment_discarded_messages()
            _LOGGER.exception("Failed parsing input message")

        # failure
        return aiocoap.Message(payload=''.encode("utf-8"),
                               code=aiocoap.numbers.codes.Code.BAD_REQUEST)
