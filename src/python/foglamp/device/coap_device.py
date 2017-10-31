# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""CoAP handler for sensor readings"""

import asyncio
import json

import aiocoap.resource
import cbor2

from foglamp import logger
from foglamp.device.ingest import Ingest


__author__ = "Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_LOGGER = logger.setup(__name__)

_DEFAULT_CONFIG = {
    'plugin': {
         'description': 'Python module name of the plugin to load',
         'type': 'string',
         'default': 'coap'
    },
    'port': {
        'description': 'Port to listen on',
        'type': 'integer',
        'default': '5683',
    },
    'uri': {
        'description': 'URI to accept data on',
        'type': 'string',
        'default': 'sensor-values',
    }
}


def plugin_info():
    return {'name': 'CoAP Server', 'version': '1.0', 'mode': 'async', 'type': 'device',
            'interface': '1.0', 'config': _DEFAULT_CONFIG}


def plugin_init(config):
    """Registers CoAP handler to accept sensor readings"""

    uri = config['uri']['value']
    port = config['port']['value']

    root = aiocoap.resource.Site()

    root.add_resource(('.well-known', 'core'),
                      aiocoap.resource.WKCResource(root.get_resources_as_linkheader))

    root.add_resource(('other', uri), CoAPIngest())

    asyncio.ensure_future(aiocoap.Context.create_server_context(root, bind=('::', int(port))))

    return {}


def plugin_run(data):
    pass


def plugin_reconfigure(config):
    pass


def plugin_shutdown(data):
    pass


class CoAPIngest(aiocoap.resource.Resource):
    """Handles incoming sensor readings from CoAP"""

    @staticmethod
    async def render_post(request):
        """Store sensor readings from CoAP to FogLAMP

        Args:
            request:
                The payload is a cbor-encoded array that decodes to JSON
                similar to the following:

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
        # aiocoap handlers must be defensive about exceptions. If an exception
        # is raised out of a handler, it is permanently disabled by aiocoap.
        # Therefore, Exception is caught instead of specific exceptions.

        # TODO: The payload is documented at
        # https://docs.google.com/document/d/1rJXlOqCGomPKEKx2ReoofZTXQt9dtDiW_BHU7FYsj-k/edit#
        # and will be moved to a .rst file

        code = aiocoap.numbers.codes.Code.INTERNAL_SERVER_ERROR
        increment_discarded_counter = True
        message = ''

        try:
            if not Ingest.is_available():
                message = '{"busy": true}'
            else:
                payload = cbor2.loads(request.payload)

                if not isinstance(payload, dict):
                    raise ValueError('Payload must be a dictionary')

                asset = payload.get('asset')
                timestamp = payload.get('timestamp')

                key = payload.get('key')

                # readings and sensor_readings are optional
                try:
                    readings = payload['readings']
                except KeyError:
                    readings = payload.get('sensor_values')  # sensor_values is deprecated

                increment_discarded_counter = False

                await Ingest.add_readings(asset=asset, timestamp=timestamp, key=key,
                                          readings=readings)

                # Success
                code = aiocoap.numbers.codes.Code.VALID
        except (ValueError, TypeError) as e:
            code = aiocoap.numbers.codes.Code.BAD_REQUEST
            message = json.dumps({message: str(e)})
        except Exception:
            _LOGGER.exception('Add readings failed')

        if increment_discarded_counter:
            Ingest.increment_discarded_readings()

        return aiocoap.Message(payload=message.encode('utf-8'), code=code)

