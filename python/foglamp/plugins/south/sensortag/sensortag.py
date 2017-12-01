# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Template module for 'poll' type plugin """
import copy
from datetime import datetime, timezone
import uuid
import pexpect
import json
import time
import datetime
import sys
import asyncio
from aiohttp import web
from foglamp.services.south import exceptions
from foglamp.common import logger
from foglamp.plugins.south.sensortag.sensortag_poll import *
from foglamp.services.south.ingest import Ingest


__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_DEFAULT_CONFIG = {
    'plugin': {
         'description': 'Python module name of the plugin to load',
         'type': 'string',
         'default': 'sensortag'
    },
    'pollInterval': {
        'description': 'The interval between poll calls to the device poll routine expressed in milliseconds.',
        'type': 'integer',
        'default': '500'
    },
    'bluetoothAddr': {
        'description': 'Bluetooth Hexadecimal address of SensorTag device',
        'type': 'string',
        'default': 'B0:91:22:EA:79:04'
    }
}

# TODO: Implement logging
_LOGGER = logger.setup(__name__)

sensortag_characteristics = characteristics

def plugin_info():
    """ Returns information about the plugin.

    Args:
    Returns:
        dict: plugin information
    Raises:
    """

    return {
        'name': 'Poll plugin',
        'version': '1.0',
        'mode': 'poll', ''
        'type': 'device',
        'interface': '1.0',
        'config': _DEFAULT_CONFIG
    }


def plugin_init(config):
    """ Initialise the plugin.

    Args:
        config: JSON configuration document for the device configuration category
    Returns:
        handle: JSON object to be used in future calls to the plugin
    Raises:
    """
    global sensortag_characteristics

    bluetooth_adr = config['bluetooth_adr']
    tag = SensorTag(bluetooth_adr)

    # The GATT table can change for different firmware revisions, so it is important to do a proper characteristic
    # discovery rather than hard-coding the attribute handles.
    for char in sensortag_characteristics.keys():
        for type in ['data', 'configuration', 'period']:
            handle = tag.get_char_handle(sensortag_characteristics[char][type]['uuid'])
            sensortag_characteristics[char][type]['handle'] = handle

    data = copy.deepcopy(config)
    data['characteristics'] = sensortag_characteristics
    return data


def plugin_poll(handle):
    """ Extracts data from the sensor and returns it in a JSON document as a Python dict.

    Available for poll mode only.

    Args:
        handle: handle returned by the plugin initialisation call
    Returns:
        returns a sensor reading in a JSON document, as a Python dict, if it is available
        None - If no reading is available
    Raises:
        DataRetrievalError
    """

    time_stamp = str(datetime.datetime.now(tz=timezone.utc))
    data = {
        'asset': 'sensortag',
        'timestamp': time_stamp,
        'key': str(uuid.uuid4()),
        'readings': {}
    }

    try:
        bluetooth_adr = handle['bluetooth_adr']
        object_temp_celsius = None
        ambient_temp_celsius = None
        lux_luminance = None
        rel_humidity = None
        bar_pressure = None
        movement = None
        char_enable = '01'
        char_disable = '00'

        # print(('{:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now()))  )
        print("INFO: [re]starting..")

        tag = SensorTag(bluetooth_adr)  # pass the Bluetooth Address
        # print(json.dumps(handle['characteristics']))

        # Get temperature
        tag.char_write_cmd(handle['characteristics']['temperature']['configuration']['handle'], char_enable)
        count = 0
        while count < SensorTag.reading_iterations:
            object_temp_celsius, ambient_temp_celsius = SensorTag.hexTemp2C(tag.char_read_hnd(
                handle['characteristics']['temperature']['data']['handle'], "temperature"))
            time.sleep(0.5)  # wait for a while
            count = count + 1

        # Get luminance
        tag.char_write_cmd(handle['characteristics']['luminance']['configuration']['handle'], char_enable)
        lux_luminance = SensorTag.hexLum2Lux(tag.char_read_hnd(
            handle['characteristics']['luminance']['data']['handle'], "luminance"))

        # Get humidity
        tag.char_write_cmd(handle['characteristics']['humidity']['configuration']['handle'], char_enable)
        rel_humidity = SensorTag.hexHum2RelHum(tag.char_read_hnd(
            handle['characteristics']['humidity']['data']['handle'], "humidity"))

        # Get pressure
        tag.char_write_cmd(handle['characteristics']['pressure']['configuration']['handle'], char_enable)
        bar_pressure = SensorTag.hexPress2Press(tag.char_read_hnd(
            handle['characteristics']['pressure']['data']['handle'], "pressure"))

        # TODO: Implement movement data capture
        # Get movement
        # tag.char_write_cmd(handle['characteristics']['pressure']['configuration']['handle'], char_enable)

        # Disable sensors
        tag.char_write_cmd(handle['characteristics']['temperature']['configuration']['handle'], char_disable)
        tag.char_write_cmd(handle['characteristics']['luminance']['configuration']['handle'], char_disable)
        tag.char_write_cmd(handle['characteristics']['humidity']['configuration']['handle'], char_disable)
        tag.char_write_cmd(handle['characteristics']['pressure']['configuration']['handle'], char_disable)
        tag.char_write_cmd(handle['characteristics']['movement']['configuration']['handle'], char_disable)

        data['readings'] = {
                    'objectTemperature': object_temp_celsius,
                    'ambientTemperature': ambient_temp_celsius,
                    'luminance': lux_luminance,
                    'humidity': rel_humidity,
                    'pressure': bar_pressure,
                    'movement': movement
                }
    except Exception as ex:
        raise exceptions.DataRetrievalError(ex)

    return data


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
    pass


# Pending: complete below class implementation
# TODO: Implement FOGL-701 (implement AuditLogger which logs to DB and can be used by all ) for this class
class SensorTagIngest(object):
    """Handles incoming sensor readings from HTTP Listener"""

    @staticmethod
    async def render_post(request):
        """Store sensortag readings to FogLAMP
        """

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


if __name__ == "__main__":
    # To run: python3 python/foglamp/plugins/south/sensortag/sensortag.py B0:91:22:EA:79:04

    bluetooth_adr = sys.argv[1]
    # print(plugin_init({'bluetooth_adr': bluetooth_adr}))
    print(plugin_poll(plugin_init({'bluetooth_adr': bluetooth_adr})))

    # tag = SensorTag(bluetooth_adr)
    # handle = tag.get_char_handle(characteristics['temperature']['data']['uuid'])
    # print(handle)
