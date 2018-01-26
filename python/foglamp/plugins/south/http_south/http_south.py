# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""HTTP Listener handler for sensor readings"""
import sys
from aiohttp import web
import asyncio
from foglamp.common import logger
from foglamp.common.web import middleware
from foglamp.services.south.ingest import Ingest

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_LOGGER = logger.setup(__name__, level=20)

_CONFIG_CATEGORY_NAME = 'HTTP_SOUTH'
_CONFIG_CATEGORY_DESCRIPTION = 'South Plugin HTTP Listener'
_DEFAULT_CONFIG = {
    'plugin': {
         'description': 'South Plugin HTTP Listener',
         'type': 'string',
         'default': 'http_south'
    },
    'port': {
        'description': 'Port to listen on',
        'type': 'integer',
        'default': '6683',
    },
    'host': {
        'description': 'Address to accept data on',
        'type': 'string',
        'default': '0.0.0.0',
    },
    'uri': {
        'description': 'URI to accept data on',
        'type': 'string',
        'default': 'sensor-reading',
    }
}


def plugin_info():
    return {
            'name': 'http_south',
            'version': '1.0',
            'mode': 'async',
            'type': 'south',
            'interface': '1.0',
            'config': _DEFAULT_CONFIG
    }


def plugin_init(config):
    """Registers HTTP Listener handler to accept sensor readings"""

    _LOGGER.info("Retrieve HTTP Listener Configuration %s", config)

    host = config['host']['value']
    port = config['port']['value']
    uri = config['uri']['value']

    return {'host': host, 'port': port, 'uri': uri}


def plugin_start(data):
    try:
        host = data['host']
        port = data['port']
        uri = data['uri']

        loop = asyncio.get_event_loop()

        app = web.Application(middlewares=[middleware.error_middleware])
        app.router.add_route('POST', '/{}'.format(uri), HttpSouthIngest.render_post)
        handler = app.make_handler()
        server_coro = loop.create_server(handler, host, port)
        future = asyncio.ensure_future(server_coro)

        def f_callback(f):
            # _LOGGER.info(repr(f.result()))
            """ <Server sockets=
            [<socket.socket fd=17, family=AddressFamily.AF_INET, type=2049,proto=6, laddr=('0.0.0.0', 6683)>]>"""
            data['server'] = f.result()

        future.add_done_callback(f_callback)

        data['app'] = app
        data['handler'] = handler
    except Exception as e:
        _LOGGER.exception(str(e))
        sys.exit(1)


def plugin_reconfigure(handle, new_config):
    """ Reconfigures the plugin

    it should be called when the configuration of the plugin is changed during the operation of the South device service;
    The new configuration category should be passed.

    Args:
        handle: handle returned by the plugin initialisation call
        new_config: JSON object representing the new configuration category for the category
    Returns:
        new_handle: new handle to be used in the future calls
    Raises:
    """

    _LOGGER.info("Old config for HTTP_SOUTH plugin {} \n new config {}".format(handle, new_config))

    new_handle = plugin_init(new_config)
    plugin_start(new_handle)
    return new_handle


def plugin_shutdown(data):
    try:
        app = data['app']
        handler = data['handler']
        server = data['server']

        server.close()
        asyncio.ensure_future(server.wait_closed())
        asyncio.ensure_future(app.shutdown())
        asyncio.ensure_future(handler.shutdown(60.0))
        asyncio.ensure_future(app.cleanup())
        _LOGGER.info('South HTTP plugin shut down.')
    except Exception as e:
        _LOGGER.exception(str(e))
        raise


# TODO: Implement FOGL-701 (implement AuditLogger which logs to DB and can be used by all ) for this class
class HttpSouthIngest(object):
    """Handles incoming sensor readings from HTTP Listener"""

    @staticmethod
    async def render_post(request):
        """Store sensor readings from CoAP to FogLAMP

        Args:
            request:
                The payload decodes to JSON similar to the following:

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
        Example:
            curl -X POST http://localhost:6683/sensor-reading -d '{"timestamp": "2017-01-02T01:02:03.23232Z-05:00", "asset": "pump1", "key": "80a43623-ebe5-40d6-8d80-3f892da9b3b4", "readings": {"velocity": "500", "temperature": {"value": "32", "unit": "kelvin"}}}'
        """
        # TODO: The payload is documented at
        # https://docs.google.com/document/d/1rJXlOqCGomPKEKx2ReoofZTXQt9dtDiW_BHU7FYsj-k/edit#
        # and will be moved to a .rst file

        increment_discarded_counter = False

        # TODO: Decide upon the correct format of message
        message = {'result': 'success'}
        code = web.HTTPOk.status_code

        try:
            if not Ingest.is_available():
                increment_discarded_counter = True
                message = {'busy': True}
            else:
                payload = await request.json()

                if not isinstance(payload, dict):
                    raise ValueError('Payload must be a dictionary')

                asset = payload.get('asset')
                timestamp = payload.get('timestamp')
                key = payload.get('key')

                # readings and sensor_readings are optional
                try:
                    readings = payload.get('readings')
                except KeyError:
                    readings = payload.get('sensor_values')  # sensor_values is deprecated

                if not isinstance(readings, dict):
                    raise ValueError('readings must be a dictionary')

                await Ingest.add_readings(asset=asset, timestamp=timestamp, key=key, readings=readings)
        except (ValueError, TypeError) as e:
            increment_discarded_counter = True
            code = web.HTTPBadRequest.status_code
            message = {'error': str(e)}
            _LOGGER.exception(str(e))
        except Exception as e:
            increment_discarded_counter = True
            code = web.HTTPInternalServerError.status_code
            message = {'error': str(e)}
            _LOGGER.exception(str(e))

        if increment_discarded_counter:
            Ingest.increment_discarded_readings()

        # expect keys in response:
        # (code = 2xx) result Or busy
        # (code = 4xx, 5xx) error
        message['status'] = code

        return web.json_response(message)
