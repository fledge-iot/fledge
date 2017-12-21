# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""CoAP handler for sensor readings"""

import asyncio
import json

import aiocoap.resource
import cbor2
import logging

from foglamp.common import logger
from foglamp.services.south.ingest import Ingest

__author__ = "Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_LOGGER = logger.setup(__name__)

_DEFAULT_CONFIG = {
    'plugin': {
         'description': 'Python module name of the plugin to load',
         'type': 'string',
         'default': 'coap_listen'
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
    """ Returns information about the plugin.

    Args:
    Returns:
        dict: plugin information
    Raises:
    """

    return {'name': 'CoAP Server',
            'version': '1.0',
            'mode': 'async',
            'type': 'device',
            'interface': '1.0',
            'config': _DEFAULT_CONFIG
            }


def plugin_init(config):
    """ Registers CoAP handler to accept sensor readings

    Args:
        config: JSON configuration document for the device configuration category
    Returns:
        handle: JSON object to be used in future calls to the plugin
    Raises:
    """
    handle = config

    _LOGGER.setLevel(logging.INFO)
    """ We want to see informational output from this plugin """

    return handle


def plugin_start(handle):
    """ Starts the device ingress process.
        Used only for device plugins that support async IO.

    Args:
        handle: handle returned by the plugin initialisation call
    Returns:
    Raises:
    """

    uri = handle['uri']['value']
    port = handle['port']['value']

    _LOGGER.info('CoAP listener started on port {} with uri {}'.format(port, uri))

    root = aiocoap.resource.Site()

    root.add_resource(('.well-known', 'core'),
                      aiocoap.resource.WKCResource(root.get_resources_as_linkheader))

    root.add_resource(('other', uri), CoAPIngest())

    asyncio.ensure_future(aiocoap.Context.create_server_context(root, bind=('::', int(port))))


def plugin_reconfigure(handle, new_config):
    """ Reconfigures the plugin, it should be called when the configuration of the plugin is changed during the
        operation of the device service.
        The new configuration category should be passed.

    Args:
        handle: handle returned by the plugin initialisation call
        new_config: JSON object representing the new configuration category for the category
    Returns:
        new_handle: new handle to be used in the future calls
    Raises:
    """

    new_handle = {}

    return new_handle


def plugin_shutdown(handle):
    """ Shutdowns the plugin doing required cleanup, to be called prior to the device service being shut down.

    Args:
        handle: handle returned by the plugin initialisation call
    Returns:
    Raises:
    """

# TODO: Implement FOGL-701 (implement AuditLogger which logs to DB and can be used by all ) for this class
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

