# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Module for Sensortag CC2650 'poll' type plugin """

import copy
import datetime
import json
import uuid

from foglamp.common import logger
from foglamp.plugins.common import utils
from foglamp.plugins.south.common.sensortag_cc2650 import *
from foglamp.services.south import exceptions

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_DEFAULT_CONFIG = {
    'plugin': {
         'description': 'TI SensorTag Polling South Plugin',
         'type': 'string',
         'default': 'cc2650poll'
    },
    'pollInterval': {
        'description': 'The interval between poll calls to the South device poll routine expressed in milliseconds.',
        'type': 'integer',
        'default': '500'
    },
    'bluetoothAddress': {
        'description': 'Bluetooth MAC address',
        'type': 'string',
        'default': 'B0:91:22:EA:79:04'
    },
    'connectionTimeout': {
        'description': 'BLE South Device timeout value in seconds',
        'type': 'integer',
        'default': '10'
    },
    'shutdownThreshold': {
        'description': 'Time in seconds allowed for shutdown to complete the pending tasks',
        'type': 'integer',
        'default': '10'
    },
    'management_host': {
        'description': 'Management host',
        'type': 'string',
        'default': '127.0.0.1',
    }
}

_LOGGER = logger.setup(__name__, level=20)


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
        'type': 'south',
        'interface': '1.0',
        'config': _DEFAULT_CONFIG
    }


def plugin_init(config):
    """ Initialise the plugin.

    Args:
        config: JSON configuration document for the South device configuration category
    Returns:
        handle: JSON object to be used in future calls to the plugin
    Raises:
    """
    sensortag_characteristics = copy.deepcopy(characteristics)
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
        raise RuntimeError

    time_stamp = utils.local_timestamp()
    data = list()
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
        readings = {
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

        for reading_key in readings.keys():
            data.append({
                'asset': 'TI Sensortag CC2650/' + reading_key,
                'timestamp': time_stamp,
                'key': str(uuid.uuid4()),
                'readings': readings[reading_key]
            })

    except (Exception, RuntimeError, pexpect.exceptions.TIMEOUT) as ex:
        _LOGGER.exception("SensorTagCC2650 {} exception: {}".format(bluetooth_adr, str(ex)))
        raise exceptions.DataRetrievalError(ex)

    _LOGGER.debug("SensorTagCC2650 {} reading: {}".format(bluetooth_adr, json.dumps(data)))
    return data


def plugin_reconfigure(handle, new_config):
    """  Reconfigures the plugin

    it should be called when the configuration of the plugin is changed during the operation of the South device service;
    The new configuration category should be passed.

    Args:
        handle: handle returned by the plugin initialisation call
        new_config: JSON object representing the new configuration category for the category
    Returns:
        new_handle: new handle to be used in the future calls
    Raises:
    """
    _LOGGER.info("Old config for CC2650POLL plugin {} \n new config {}".format(handle, new_config))

    # Find diff between old config and new config
    diff = utils.get_diff(handle, new_config)

    # Plugin should re-initialize and restart if key configuration is changed
    if 'bluetoothAddress' in diff or 'management_host' in diff:
        _plugin_stop(handle)
        new_handle = plugin_init(new_config)
        new_handle['restart'] = 'yes'
        _LOGGER.info("Restarting CC2650POLL plugin due to change in configuration keys [{}]".format(', '.join(diff)))
    elif 'pollInterval' in diff or 'connectionTimeout' in diff or 'shutdownThreshold' in diff:
        new_handle = copy.deepcopy(new_config)
        new_handle['restart'] = 'no'
    else:
        new_handle = copy.deepcopy(handle)
        new_handle['restart'] = 'no'
    return new_handle


def _plugin_stop(handle):
    """ Stops the plugin doing required cleanup, to be called prior to the South device service being shut down.

    Args:
        handle: handle returned by the plugin initialisation call
    Returns:
    Raises:
    """
    if 'tag' in handle:
        bluetooth_adr = handle['bluetoothAddress']['value']
        tag = handle['tag']
        tag.disconnect()
        _LOGGER.info('SensorTagCC2650 {} Disconnected.'.format(bluetooth_adr))


def plugin_shutdown(handle):
    """ Shutdowns the plugin doing required cleanup, to be called prior to the South device service being shut down.

    Args:
        handle: handle returned by the plugin initialisation call
    Returns:
    Raises:
    """
    _plugin_stop(handle)
    _LOGGER.info('CC2650 poll plugin shut down.')
