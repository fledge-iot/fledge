# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Module for Sensortag CC2650 'async' type plugin """

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
         'description': 'Sensortag CC2650 async type plugin',
         'type': 'string',
         'default': 'cc2650async'
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
        'name': 'TI SensorTag CC2650 Async plugin',
        'version': '1.0',
        'mode': 'async',
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

        data['notification_handles'] = tag.get_notification_handles()
        data['characteristics'] = sensortag_characteristics
        data['tag'] = tag
        _LOGGER.info('SensorTagCC2650 {} Async fetching initialized'.format(bluetooth_adr))

    return data


def plugin_start(handle):
    """ Extracts data from the sensor and returns it in a JSON document as a Python dict.

    Available for async mode only.

    Args:
        handle: handle returned by the plugin initialisation call
    Returns:
        returns a sensor reading in a JSON document, as a Python dict, if it is available
        None - If no reading is available
    Raises:
        TimeoutError
    """
    async def save_data():
        if 'tag' not in handle:
            return
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

            # Enable notification
            for notification_handle in handle['notification_handles']:
                tag.char_write_cmd(notification_handle, notification_enable)

            # Enable sensors
            tag.char_write_cmd(handle['characteristics']['temperature']['configuration']['handle'], char_enable)
            tag.char_write_cmd(handle['characteristics']['luminance']['configuration']['handle'], char_enable)
            tag.char_write_cmd(handle['characteristics']['humidity']['configuration']['handle'], char_enable)
            tag.char_write_cmd(handle['characteristics']['pressure']['configuration']['handle'], char_enable)
            tag.char_write_cmd(handle['characteristics']['movement']['configuration']['handle'], movement_enable)

            # TODO: How to implement CTRL-C or terminate process?
            debug_cnt = 0  # Used only for debugging. debug_cnt should be set to 0 in production.
            cnt = 0
            while True:
                time_stamp = str(datetime.datetime.now(tz=datetime.timezone.utc))
                try:
                    pattern_index = tag.con.expect('Notification handle = .*? \r', timeout=4)
                except pexpect.TIMEOUT:
                    _LOGGER.error("SensorTagCC2650 {} async timeout")
                    print("TIMEOUT exception!")
                    break

                # expect, if succesfull, will return the index of the pattern "Notification handle = " which ideally
                # should appear at col 0. If not, then pexpect.TIMEOUT will be raised. Also, this choice of pattern
                # will help in splitting at line#176.
                if pattern_index == 0:
                    after = tag.con.after
                    hex_string = after.split()[3:]

                    cnt += 1
                    # Used only for debugging. debug_cnt should be set to 0 in production
                    if debug_cnt > 0:
                        if cnt >= debug_cnt:
                            break
                        print(cnt, "****", hex_string)

                    # Allow some breathing time for event loop to finish the background tasks.
                    if cnt % 50 == 0:
                        await asyncio.sleep(.5)

                    # Get temperature
                    if int(handle['characteristics']['temperature']['data']['handle'], 16) == \
                            int(hex_string[0].decode(), 16):
                        object_temp_celsius, ambient_temp_celsius = tag.hex_temp_to_celsius(
                                                                    tag.get_raw_measurement("temperature", hex_string))
                        data = {
                            'asset': 'temperature',
                            'timestamp': time_stamp,
                            'key': str(uuid.uuid4()),
                            'readings': {
                                'temperature': {
                                    "object": object_temp_celsius,
                                    'ambient': ambient_temp_celsius
                                },
                            }
                        }

                    # Get luminance
                    if int(handle['characteristics']['luminance']['data']['handle'], 16) == \
                            int(hex_string[0].decode(), 16):
                        lux_luminance = tag.hex_lux_to_lux(tag.get_raw_measurement("luminance", hex_string))
                        data = {
                            'asset': 'luxometer',
                            'timestamp': time_stamp,
                            'key': str(uuid.uuid4()),
                            'readings': {
                                'luxometer': {"lux": lux_luminance},
                            }
                        }

                    # Get humidity
                    if int(handle['characteristics']['humidity']['data']['handle'], 16) == \
                            int(hex_string[0].decode(), 16):
                        rel_humidity, rel_temperature = tag.hex_humidity_to_rel_humidity(
                                                        tag.get_raw_measurement("humidity", hex_string))
                        data = {
                            'asset': 'humidity',
                            'timestamp': time_stamp,
                            'key': str(uuid.uuid4()),
                            'readings': {
                                'humidity': {
                                    "humidity": rel_humidity,
                                    "temperature": rel_temperature
                                },
                            }
                        }

                    # Get pressure
                    if int(handle['characteristics']['pressure']['data']['handle'], 16) == \
                            int(hex_string[0].decode(), 16):
                        bar_pressure = tag.hex_pressure_to_pressure(tag.get_raw_measurement("pressure", hex_string))
                        data = {
                            'asset': 'pressure',
                            'timestamp': time_stamp,
                            'key': str(uuid.uuid4()),
                            'readings': {
                                'pressure': {"pressure": bar_pressure},
                            }
                        }

                    # Get movement
                    if int(handle['characteristics']['movement']['data']['handle'], 16) == \
                            int(hex_string[0].decode(), 16):
                        gyro_x, gyro_y, gyro_z, acc_x, acc_y, acc_z, mag_x, mag_y, mag_z, acc_range = \
                            tag.hex_movement_to_movement(tag.char_read_hnd(
                                                handle['characteristics']['movement']['data']['handle'], "movement"))
                        movement = {
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
                        }
                        # Dedicated add_readings for movement
                        for reading_key in movement:
                            data = {
                                'asset': reading_key,
                                'timestamp': time_stamp,
                                'key': str(uuid.uuid4()),
                                'readings': {
                                    reading_key: movement[reading_key],
                                }
                            }
                            await Ingest.add_readings(asset='TI Sensortag CC2650/{}'.format(data['asset']),
                                                                timestamp=data['timestamp'],
                                                                key=data['key'],
                                                                readings=data['readings'])

                    # Get battery
                    # FIXME: Investigate why no battery input in async mode?
                    if int(battery['data']['handle'], 16) == int(hex_string[0].decode(), 16):
                        battery_level = tag.get_battery_level(
                            tag.char_read_hnd(battery['data']['handle'], "battery"))
                        data = {
                            'asset': 'battery',
                            'timestamp': time_stamp,
                            'key': str(uuid.uuid4()),
                            'readings': {
                                'battery': {"percentage": battery_level},
                            }
                        }

                    # Get keypress
                    # FIXME: Investigate why no keypress input?
                    if int(keypress['data']['handle'], 16) == int(hex_string[0].decode(), 16):
                        keypress_state = tag.get_keypress_state(
                            tag.char_read_hnd(keypress['data']['handle'], "keypress"))
                        data = {
                            'asset': 'keypress',
                            'timestamp': time_stamp,
                            'key': str(uuid.uuid4()),
                            'readings': {
                                'keypress': {"state": keypress_state},
                            }
                        }

                    # Common add_readings for all keys other than movement
                    if int(handle['characteristics']['movement']['data']['handle'], 16) != \
                            int(hex_string[0].decode(), 16):
                        await Ingest.add_readings(asset='TI Sensortag CC2650/{}'.format(data['asset']),
                                                            timestamp=data['timestamp'],
                                                            key=data['key'],
                                                            readings=data['readings'])
                else:
                    _LOGGER.error("SensorTagCC2650 {} async timeout")
                    print("TIMEOUT!!")
        except (Exception, RuntimeError) as ex:
            _LOGGER.exception("SensorTagCC2650 {} exception: {}".format(bluetooth_adr, str(ex)))
            raise exceptions.DataRetrievalError(ex)

        _LOGGER.debug("SensorTagCC2650 {} reading: {}".format(bluetooth_adr, json.dumps(data)))

    asyncio.ensure_future(save_data())


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

        # Disable sensors
        tag.char_write_cmd(handle['characteristics']['temperature']['configuration']['handle'], char_disable)
        tag.char_write_cmd(handle['characteristics']['luminance']['configuration']['handle'], char_disable)
        tag.char_write_cmd(handle['characteristics']['humidity']['configuration']['handle'], char_disable)
        tag.char_write_cmd(handle['characteristics']['pressure']['configuration']['handle'], char_disable)
        tag.char_write_cmd(handle['characteristics']['movement']['configuration']['handle'], movement_disable)

        # Disable notification
        for notification_handle in handle['notification_handles']:
            tag.char_write_cmd(notification_handle, notification_disable)

        tag.disconnect()
        _LOGGER.info('SensorTagCC2650 {} Disconnected.'.format(bluetooth_adr))
