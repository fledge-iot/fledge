# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Template module for 'poll' type plugin """
import struct
from datetime import datetime, timezone
import random
import uuid
import pexpect
import sys
import time
import json
import select
import time
import requests
import warnings
import datetime
import traceback
import math
from foglamp.common import logger
from foglamp.services.south import exceptions

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

_LOGGER = logger.setup(__name__)


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

    handle = config

    return handle


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

    try:
        bluetooth_adr = handle['bluetooth_adr']
        object_temp_celsius = None
        ambient_temp_celsius = None
        lux_luminance = None
        rel_humidity = None
        bar_pressure = None

        # print(('{:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now()))  )
        print("INFO: [re]starting..")

        tag = SensorTag(bluetooth_adr)  # pass the Bluetooth Address
        # Get temperature
        tag.char_write_cmd(0x24, 0x01)  # Enable temperature sensor

        count = 0
        while count < SensorTag.reading_iterations:
            object_temp_celsius, ambient_temp_celsius = SensorTag.hexTemp2C(tag.char_read_hnd(0x21, "temperature"))
            time.sleep(0.5)  # wait for a while
            count = count + 1

        # Get luminance
        tag.char_write_cmd(0x44, 0x01)
        lux_luminance = SensorTag.hexLum2Lux(tag.char_read_hnd(0x41, "luminance"))

        # Get humidity
        tag.char_write_cmd(0x2C, 0x01)
        rel_humidity = SensorTag.hexHum2RelHum(tag.char_read_hnd(0x29, "humidity"))

        # Get pressure
        tag.char_write_cmd(0x34, 0x01)
        bar_pressure = SensorTag.hexPress2Press(tag.char_read_hnd(0x31, "barPressure"))

        data = {
                'asset':     'sensortag',
                'timestamp': time_stamp,
                'key':       str(uuid.uuid4()),
                'readings':  {
                    'objectTemperature': object_temp_celsius,
                    'ambientTemperature': ambient_temp_celsius,
                    'luminance': lux_luminance,
                    'humidity': rel_humidity,
                    'pressure': bar_pressure
                }
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

# TODO: Implement FOGL-701 (implement AuditLogger which logs to DB and can be used by all ) for this class
class SensorTag(object):
    """Handles polling of readings from SensorTag
        Cloned from https://github.com/OrestisEv/SensorTag-Pi3
    """
    flag_to_send = False  # Flag to send data to database
    reading_iterations = 1  # number of iterations to read data from the TAG

    # defining variable for sending data to DB
    API_BASE_URI = "http://tcstestbed.unige.ch/api/"
    ble_id = "SensTag004"
    resource_name = "temperature"
    location = "&pos_x=1&pos_y=5.5&pos_z=1"  # location of my desk

    def __init__(self, bluetooth_adr):
        self.con = pexpect.spawn('gatttool -b ' + bluetooth_adr + ' --interactive')
        self.con.expect('\[LE\]>', timeout=600)
        print("INFO: Preparing to connect. Hold on a second...If nothing happens please press the power button...")
        self.con.sendline('connect')
        # test for success of connect
        self.con.expect('.*Connection successful.*\[LE\]>')
        print("INFO: Connection Successful!")
        self.cb = {}

    def char_write_cmd(self, handle, value):
        # The 0%x for value is VERY naughty!  Fix this!
        cmd = 'char-write-cmd 0x%02x 0%x' % (handle, value)
        self.con.sendline(cmd)
        # delay for 1 second so that Tag can enable registers
        time.sleep(1)

    def char_read_hnd(self, handle, sensortype):
        self.con.sendline('char-read-hnd 0x%02x' % handle) #send the hex value to the Tag
        #print('DEBUGGING: char-read-hnd 0x%02x' % handle)
        self.con.expect('.*descriptor:.* \r')
        reading = self.con.after
        print("DEBUGGING: Reading from Tag... %s \n" % reading) #print(the outcome as it comes while reading the Tag
        rval = reading.split() #splitting the reading based on the spaces
        print("DEBUGGING: rval" + str(rval))

        if sensortype in ['temperature']:
            # The raw data value read from this sensor are two unsigned 16 bit values
            raw_measurement = rval[-4] + rval[-3] + rval[-2] + rval[-1]
        elif sensortype in ['movement']:
            # TODO:
            pass
        elif sensortype in ['humidity']:
            # The raw data value read from this sensor are two unsigned 16 bit values
            # raw_measurement = rval[-1] + rval[-2]
            raw_measurement = rval[-1]
        elif sensortype in ['barPressure']:
            # The data from the pressure sensor consists of two 24-bit unsigned integers
            # raw_measurement = rval[-1] + rval[-2] + rval[-3]
            raw_measurement = rval[-1]
        elif sensortype in ['luminance']:
            # The data from the optical sensor consists of a single 16-bit unsigned integer
            # raw_measurement = rval[-1] + rval[-2]
            raw_measurement = rval[-1]
        else:
            raw_measurement = 0

        print(raw_measurement)
        return raw_measurement

    # TODO: Work on Notifications
    # Notification handle = 0x0025 value: 9b ff 54 07
    def notification_loop(self):
        while True:
            try:
                pnum = self.con.expect('Notification handle = .*? \r', timeout=4)
            except pexpect.TIMEOUT:
                print("TIMEOUT exception!")  # was: print("TIMEOUT exception!")
                break
            if pnum == 0:
                after = self.con.after
                hxstr = after.split()[3:]
                print("****")
                handle = int(float.fromhex(hxstr[0]))
                self.cb[handle]([int(float.fromhex(n)) for n in hxstr[2:]])
            else:
                print("TIMEOUT!!")
        pass

    def register_cb(self, handle, fn):
        self.cb[handle] = fn;
        return

    @staticmethod
    def hexTemp2C(raw_tempr):
        """
        Conversion method at http://processors.wiki.ti.com/index.php/CC2650_SensorTag_User's_Guide#Gatt_Server
        The raw data value read from this sensor are two unsigned 16 bit values, one for die (ambience) temperature and
        one for object temperature. To convert to temperature in degrees (Celsius), use the algorithm below:
        void sensorTmp007Convert(uint16_t rawAmbTemp, uint16_t rawObjTemp, float *tAmb, float *tObj)
        {
          const float SCALE_LSB = 0.03125;
          float t;
          int it;

          it = (int)((rawObjTemp) >> 2);
          t = ((float)(it)) * SCALE_LSB;
          *tObj = t;

          it = (int)((rawAmbTemp) >> 2);
          t = (float)it;
          *tAmb = t * SCALE_LSB;
        }
        :param raw_tempr:
        :return:
        """
        raw_temperature = raw_tempr.decode()
        SCALE_LSB = 0.03125

        # Choose object temperature (reverse bytes for little endian)
        raw_IR_temp = int('0x' + raw_temperature[0:2] + raw_temperature[2:4], 16)
        IR_temp_int = raw_IR_temp >> 2
        IR_temp_celsius = float(IR_temp_int) * SCALE_LSB

        # Choose ambient temperature (reverse bytes for little endian)
        raw_ambient_temp = int('0x' + raw_temperature[4:6] + raw_temperature[6:8], 16)
        ambient_temp_int = raw_ambient_temp >> 2  # Shift right, based on from TI
        ambient_temp_celsius = float(ambient_temp_int) * SCALE_LSB  # Convert to Celsius based on info from TI
        ambient_temp_fahrenheit = (ambient_temp_celsius * 1.8) + 32  # Convert to Fahrenheit

        print("INFO: IR Celsius:    %f" % IR_temp_celsius)
        print("INFO: Ambient Celsius:    %f" % ambient_temp_celsius)
        print("Fahrenheit: %f" % ambient_temp_fahrenheit)
        return IR_temp_celsius, ambient_temp_celsius

    @staticmethod
    def hexMovement2Mov(raw_movement):
        """
        Conversion method at http://processors.wiki.ti.com/index.php/CC2650_SensorTag_User's_Guide#Gatt_Server

        Gyroscope raw data make up 0-5 of the data from the movement service, in the order X, Y, Z axis. Data from
        each axis consists of two bytes, encoded as a signed integer. For conversion from gyroscope raw data to
        degrees/second, use the algorithm below on each of the first three 16-bit values in the incoming data, one for
        each axis. Note that the axis data from a disabled axis will be 0, so the size of the incoming data is always
        18 bytes. When the WOM feature is enabled, the latest measured data will be continuously transmitted.
        float sensorMpu9250GyroConvert(int16_t data)
        {
          //-- calculate rotation, unit deg/s, range -250, +250
          return (data * 1.0) / (65536 / 500);
        }

        Accelerometer raw data make up bytes 6-11 of the data from the movement service, in the order X, Y, Z axis.
        Data from each axis consists of two bytes, encoded as a signed integer. For conversion from accelerometer raw
        data to Gravity (G), use the algorithm below on each the three 16-bit values in the incoming data, one for each
        axis.
        // Accelerometer ranges
        #define ACC_RANGE_2G      0
        #define ACC_RANGE_4G      1
        #define ACC_RANGE_8G      2
        #define ACC_RANGE_16G     3

        float sensorMpu9250AccConvert(int16_t rawData)
        {
          float v;

          switch (accRange)
          {
          case ACC_RANGE_2G:
            //-- calculate acceleration, unit G, range -2, +2
            v = (rawData * 1.0) / (32768/2);
            break;

          case ACC_RANGE_4G:
            //-- calculate acceleration, unit G, range -4, +4
            v = (rawData * 1.0) / (32768/4);
            break;

          case ACC_RANGE_8G:
            //-- calculate acceleration, unit G, range -8, +8
            v = (rawData * 1.0) / (32768/8);
            break;

          case ACC_RANGE_16G:
            //-- calculate acceleration, unit G, range -16, +16
            v = (rawData * 1.0) / (32768/16);
            break;
          }

          return v;
        }

        Magnetometer raw data make up bytes 12-17 of the data from the movement service, in the order X, Y, Z axis.
        Data from each axis consists of two bytes, encoded as a signed integer. The conversion is done in the
        SensorTag firmware so there is no calculation involved apart from changing the integer to a float if required.
        The measurement unit is uT (micro Tesla).
        float sensorMpu9250MagConvert(int16_t data)
        {
          //-- calculate magnetism, unit uT, range +-4900
          return 1.0 * data;
        }
        :param raw_movement:
        :return:
        """
        # To be implemented
        pass

    @staticmethod
    def hexHum2RelHum(raw_humd):
        """
        Conversion method at http://processors.wiki.ti.com/index.php/CC2650_SensorTag_User's_Guide#Gatt_Server

        The data from the humidity sensor consists of two 16-bit unsigned integers: the temperature in bytes 0 and 1,
        and the pressure in bytes 2 and 3. Conversion to temperature and relative humidity is done as shown below.
        The temperature unit is degrees Celsius (°C), the humidity unit is relative humidity (%RH).
        void sensorHdc1000Convert(uint16_t rawTemp, uint16_t rawHum,
                        float *temp, float *hum)
        {
          //-- calculate temperature [°C]
          *temp = ((double)(int16_t)rawTemp / 65536)*165 - 40;

          //-- calculate relative humidity [%RH]
          rawHum &= ~0x0003; // remove status bits
          *hum = ((double)rawHum / 65536)*100;
        }
        :param raw_humd:
        :return:
        """
        interim_value = raw_humd.decode()
        # raw_temperature = int('0x'+interim_value[0:2]+interim_value[2:4], 16)
        # temperature = ((raw_temperature / 65536) * 165) - 40
        raw_humidity = int('0x'+interim_value[0:2], 16)
        humidity = float((raw_humidity)) / 65536 * 100  # get the int value from hex and divide as per Dataset.
        # print("INFO: tempr:    %f" % temperature)
        print("INFO: humidity:    %f" % humidity)
        return humidity

    @staticmethod
    def hexPress2Press(raw_pr):
        """
        Conversion method at http://processors.wiki.ti.com/index.php/CC2650_SensorTag_User's_Guide#Gatt_Server

        The data from the pressure sensor consists of two 24-bit unsigned integers: the temperature in bytes 0-2,
        the pressure in bytes 3-5. The conversion and adjustment calculations is done in firmware, so the
        application in effect only has to divide the incoming values by 100. Conversion to temperature and
        pressure is done as shown below. The temperature unit is degrees Celsius, the pressure in hectopascal (hPa).
        float sensorBmp280Convert(uint32_t rawValue)
        {
          return rawValue / 100.0f;
        }
        :param raw_pr:
        :return:
        """
        interim_value = raw_pr.decode()
        raw_pressure = int('0x'+interim_value[0:2], 16)
        pressure = float(raw_pressure) / 100.0
        print("INFO: pressure:    %f" % pressure)
        return pressure

    @staticmethod
    def hexLum2Lux(raw_lumn):
        """
        Conversion method at http://processors.wiki.ti.com/index.php/CC2650_SensorTag_User's_Guide#Gatt_Server

        The data from the optical sensor consists of a single 16-bit unsigned integer. Conversion to l
        ight intensity (LUX) is shown below.
        float sensorOpt3001Convert(uint16_t rawData)
        {
            uint16_t e, m;

            m = rawData & 0x0FFF;
            e = (rawData & 0xF000) >> 12;

            /** e on 4 bits stored in a 16 bit unsigned => it can store 2 << (e - 1) with e < 16 */
            e = (e == 0) ? 1 : 2 << (e - 1);

            return m * (0.01 * e);
        }
        :param raw_lumn:
        :return:
        """
        interim_value = raw_lumn.decode()
        print(interim_value)
        raw_luminance = int('0x'+interim_value[0:2]+interim_value[2:4], 16)
        m = "0FFF"
        e = "F000"
        # raw_luminance = int(raw_luminance, 16)
        m = int(m, 16)  # Assign initial values as per the CC2650 Optical Sensor Dataset
        exp = int(e, 16)  # Assign initial values as per the CC2650 Optical Sensor Dataset
        m = (raw_luminance & m)  # as per the CC2650 Optical Sensor Dataset
        exp = (raw_luminance & exp) >> 12  # as per the CC2650 Optical Sensor Dataset
        exp = 1 if exp == 0 else 2
        exp = exp << (exp -1)
        luminance = (m * (0.01 * exp))  # as per the CC2650 Optical Sensor Dataset
        print("INFO: luminance:    %f" % luminance)
        return luminance  # returning luminance in lux

    @staticmethod
    def send_to_DB(data_to_send, type):
        SensorTag.data_to_send = str(int(data_to_send))  # getting rid of decimals
        timestamp = ('{:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now()))  # get the current date and time
        if type in ['Ambient']:
            SensorTag.resource_name = "Ambient Temperature"
            SensorTag.unit = "celsius"
        elif type in ['IR']:
            SensorTag.resource_name = "IR Temperature"
            SensorTag.unit = "celsius"
        elif type in ['luminance']:
            SensorTag.resource_name = "luminance"
            SensorTag.unit = "lux"
        elif type in ['humidity']:
            SensorTag.resource_name = "humidity"
            SensorTag.unit = "Rel.hum"
        elif type in ['barPressure']:
            SensorTag.resource_name = "barPressure"
            SensorTag.unit = "hPa"
        try:
            insert_value_DB = requests.get(SensorTag.API_BASE_URI + "insertValue.php?node_name=" + str(
                SensorTag.ble_id) + "&resource_name=" + SensorTag.resource_name + "&value=" + data_to_send + "&unit=" + SensorTag.unit + "&timestamp=" + timestamp + SensorTag.location)
            insert_value_DB.raise_for_status()
            print(
                "INFO: Send successfully value: " + str(data_to_send) + ' ' + SensorTag.unit + " to DB with node ID: " + str(
                    SensorTag.ble_id))
        # print(insert_value_DB #debugging: see the outcome of the request)

        except:
            print("Error")
            warnings.warn("Could not get values from sensor:" + str(SensorTag.ble_id))
            traceback.print_exc()

        return

if __name__ == "__main__":
    bluetooth_adr = sys.argv[1]
    plugin_poll({'bluetooth_adr': bluetooth_adr})
