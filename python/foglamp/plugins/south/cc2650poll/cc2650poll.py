# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Module for Sensortag CC2650 'poll' type plugin """

import copy
import datetime
import uuid
import json
import asyncio
from foglamp.plugins.south.common.sensortag_cc2650 import *
from foglamp.services.south import exceptions
from foglamp.common import logger
from foglamp.services.south.ingest import Ingest

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_DEFAULT_CONFIG = {
    'plugin': {
         'description': 'Sensortag CC2650 poll type plugin',
         'type': 'string',
         'default': 'cc2650poll'
    },
    'pollInterval': {
        'description': 'The interval between poll calls to the device poll routine expressed in milliseconds.',
        'type': 'integer',
        'default': '500'
    },
    'bluetoothAddress': {
        'description': 'Bluetooth MAC address',
        'type': 'string',
        'default': 'B0:91:22:EA:79:04'
    },
    'connectionTimeout': {
        'description': 'BLE Device timeout value in seconds',
        'type': 'integer',
        'default': '10'
    },
    'shutdownThreshold': {
        'description': 'Time in seconds allowed for shutdown to complete the pending tasks',
        'type': 'integer',
        'default': '10'
    }
}

_LOGGER = logger.setup(__name__, level=20)

sensortag_characteristics = characteristics


def plugin_info():
    """ Returns information about the plugin.

    Args:
    Returns:
        dict: plugin information
    Raises:
    """

    return {
        'name': 'TI SensorTag CC2650 Poll plugin',
        'version': '1.0',
        'mode': 'poll',
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
    data = copy.deepcopy(config)

    bluetooth_adr = config['bluetoothAddress']['value']
    timeout = config['connectionTimeout']['value']
    tag = SensorTagCC2650(bluetooth_adr, timeout)

    data['is_connected'] = tag.is_connected
    if data['is_connected'] is True:
        # The GATT table can change for different firmware revisions, so it is important to do a proper characteristic
        # discovery rather than hard-coding the attribute handles.
        for char in sensortag_characteristics.keys():
            for _type in ['data', 'configuration', 'period']:
                handle = tag.get_char_handle(sensortag_characteristics[char][_type]['uuid'])
                sensortag_characteristics[char][_type]['handle'] = handle

        # Get Battery handle
        handle = tag.get_char_handle(battery['data']['uuid'])
        battery['data']['handle'] = handle
        sensortag_characteristics['battery'] = battery

        data['characteristics'] = sensortag_characteristics
        data['tag'] = tag
        _LOGGER.info('SensorTagCC2650 {} Polling initialized'.format(bluetooth_adr))

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
    if 'tag' not in handle:
        return {}

    time_stamp = str(datetime.datetime.now(tz=datetime.timezone.utc))
    data = {
        'asset': 'TI Sensortag CC2650',
        'timestamp': time_stamp,
        'key': str(uuid.uuid4()),
        'readings': {}
    }
    bluetooth_adr = handle['bluetoothAddress']['value']
    tag = handle['tag']
    object_temp_celsius = None
    ambient_temp_celsius = None
    lux_luminance = None
    rel_humidity = None
    rel_temperature = None
    bar_pressure = None
    movement = None
    battery_level = None
    keypress_state = None

    try:
        if not tag.is_connected:
            raise RuntimeError

        # Enable sensors
        tag.char_write_cmd(handle['characteristics']['temperature']['configuration']['handle'], char_enable)
        tag.char_write_cmd(handle['characteristics']['luminance']['configuration']['handle'], char_enable)
        tag.char_write_cmd(handle['characteristics']['humidity']['configuration']['handle'], char_enable)
        tag.char_write_cmd(handle['characteristics']['pressure']['configuration']['handle'], char_enable)
        tag.char_write_cmd(handle['characteristics']['movement']['configuration']['handle'], movement_enable)

        # Get temperature
        count = 0
        while count < SensorTagCC2650.reading_iterations:
            object_temp_celsius, ambient_temp_celsius = tag.hex_temp_to_celsius(
                tag.char_read_hnd(handle['characteristics']['temperature']['data']['handle'], "temperature"))
            time.sleep(0.5)  # wait for a while
            count = count + 1

        # Get luminance
        lux_luminance = tag.hex_lux_to_lux(
            tag.char_read_hnd(handle['characteristics']['luminance']['data']['handle'], "luminance"))

        # Get humidity
        rel_humidity, rel_temperature = tag.hex_humidity_to_rel_humidity(
            tag.char_read_hnd(handle['characteristics']['humidity']['data']['handle'], "humidity"))

        # Get pressure
        bar_pressure = tag.hex_pressure_to_pressure(
            tag.char_read_hnd(handle['characteristics']['pressure']['data']['handle'], "pressure"))

        # Get movement
        gyro_x, gyro_y, gyro_z, acc_x, acc_y, acc_z, mag_x, mag_y, mag_z, acc_range = tag.hex_movement_to_movement(
            tag.char_read_hnd(handle['characteristics']['movement']['data']['handle'], "movement"))
        movement = {
            'gyro': {
                'x': gyro_x,
                'y': gyro_y,
                'z': gyro_z,
            },
            'acc': {
                'x': acc_x,
                'y': acc_y,
                'z': acc_z,
            },
            'mag': {
                'x': mag_x,
                'y': mag_y,
                'z': mag_z,
            },
            'acc_range': acc_range
        }

        battery_level = tag.get_battery_level(
            tag.char_read_hnd(handle['characteristics']['battery']['data']['handle'], "battery"))

        # Disable sensors
        tag.char_write_cmd(handle['characteristics']['temperature']['configuration']['handle'], char_disable)
        tag.char_write_cmd(handle['characteristics']['luminance']['configuration']['handle'], char_disable)
        tag.char_write_cmd(handle['characteristics']['humidity']['configuration']['handle'], char_disable)
        tag.char_write_cmd(handle['characteristics']['pressure']['configuration']['handle'], char_disable)
        tag.char_write_cmd(handle['characteristics']['movement']['configuration']['handle'], movement_disable)

        # "values" (and not "readings") denotes that this reading needs to be further broken down to components.
        data['readings'] = {
            'temperature': {
                "object": object_temp_celsius,
                'ambient': ambient_temp_celsius
            },
            'luxometer': {"lux": lux_luminance},
            'humidity': {
                "humidity": rel_humidity,
                "temperature": rel_temperature
            },
            'pressure': {"pressure": bar_pressure},
            'gyroscope': {
                "x": gyro_x,
                "y": gyro_y,
                "z": gyro_z
            },
            'accelerometer': {
                "x": acc_x,
                "y": acc_y,
                "z": acc_z
            },
            'magnetometer': {
                "x": mag_x,
                "y": mag_y,
                "z": mag_z
            },
            'battery': {"percentage": battery_level},
        }
        for reading_key in data['readings']:
            asyncio.ensure_future(Ingest.add_readings(asset=data['asset'] + '/' + reading_key,
                                                                timestamp=data['timestamp'],
                                                                key=str(uuid.uuid4()),
                                                                readings=data['readings'][reading_key]))
    except (Exception, RuntimeError) as ex:
        _LOGGER.exception("SensorTagCC2650 {} exception: {}".format(bluetooth_adr, str(ex)))
        raise exceptions.DataRetrievalError(ex)

    _LOGGER.debug("SensorTagCC2650 {} reading: {}".format(bluetooth_adr, json.dumps(data)))
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
    # Find all running tasks:
    pending_tasks = asyncio.Task.all_tasks()

    # Wait until tasks done:
    asyncio.ensure_future(asyncio.wait(*pending_tasks, timeout=handle['shutdownThreshold']['value']))

    if 'tag' in handle:
        bluetooth_adr = handle['bluetoothAddress']['value']
        tag = handle['tag']
        tag.disconnect()
        _LOGGER.info('SensorTagCC2650 {} Disconnected.'.format(bluetooth_adr))
