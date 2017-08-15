# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""CoAP handler for sensor readings"""

import asyncio
import dateutil.parser

import aiocoap.resource
from cbor2 import loads
from cbor2.decoder import CBORDecodeError

from foglamp import configuration_manager
from foglamp import logger
from foglamp.device.ingest import Ingest


__author__ = "Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_LOGGER = logger.setup(__name__)

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
    """Registers CoAP handler to accept sensor readings"""

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

    root.add_resource(('other', uri), IngestReadings())

    asyncio.Task(aiocoap.Context.create_server_context(root, bind=('::', int(port))))


class IngestReadings(aiocoap.resource.Resource):
    """Handles incoming sensor readings from CoAP"""

    @staticmethod
    async def render_post(request):
        """Store sensor readings from CoAP to FogLAMP

        Args:
            request:
                The payload is a cbor-encoded array that is supposed to decode to JSON
                conforming to the following:

                .. code-block:: python

                    {
                        "timestamp": "2017-01-02T01:02:03.23232Z-05:00",
                        "asset": "pump1",
                        "key": "80a43623-ebe5-40d6-8d80-3f892da9b3b4",
                        "readings": {
                            "velocity": "500",
                            "temperature": {
                                "value": "32",
                                "unit": "kelvin"
                            }
                        }
                    }
        """

        # TODO: The payload is documented at
        # https://docs.google.com/document/d/1rJXlOqCGomPKEKx2ReoofZTXQt9dtDiW_BHU7FYsj-k/edit#
        # and will be moved to a .rst file

        # TODO For aiocoap.Message, is payload required?
        try:
            payload = loads(request.payload)

            # Required inputs
            asset = payload['asset']
            timestamp = dateutil.parser.parse(payload['timestamp'])
        except (KeyError, TypeError, CBORDecodeError, ValueError):
            Ingest.increment_discarded_messages()
            _LOGGER.exception("Failed parsing readings payload")
            return aiocoap.Message(payload=''.encode("utf-8"),
                                   code=aiocoap.numbers.codes.Code.BAD_REQUEST)

        # Optional keys in the data
        key = payload.get('key')
        readings = payload.get('sensor_values', {})

        # Comment out to test IntegrityError
        # key = '123e4567-e89b-12d3-a456-426655440000'

        try:
            await Ingest.add_readings(asset=asset, timestamp=timestamp, key=key,
                                      readings=readings)

            # Success
            # TODO what should this return?
            return aiocoap.Message(payload=''.encode("utf-8"),
                                   code=aiocoap.numbers.codes.Code.VALID)
        # TODO catch real exception
        except Exception:
            _LOGGER.exception("Error saving sensor readings: %s", payload)
            return aiocoap.Message(payload=''.encode("utf-8"),
                                   code=aiocoap.numbers.codes.Code.INTERNAL_SERVER_ERROR)
