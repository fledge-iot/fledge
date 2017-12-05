# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Common class for TI Sensortag CC2650 for both 'async' type and 'poll' type plugins """


import pexpect
import sys
import json
import time
from foglamp.common import logger


__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_LOGGER = logger.setup(__name__)

# TODO: Out of 14 services, only below 5 services have been attended to. Next tasks will take care of at least up/down +
#       tick and battery level indicator services.
characteristics = {
    'temperature': {
        'data': {
            'uuid': 'f000aa01-0451-4000-b000-000000000000',
            'handle': '0x0000'
        },
        'notification': {
            'uuid': '2902',
            'handle': '0x0000'
        },
        'configuration': {
            'uuid': 'f000aa02-0451-4000-b000-000000000000',
            'handle': '0x0000'
        },
        'period': {
            'uuid': 'f000aa03-0451-4000-b000-000000000000',
            'handle': '0x0000'
        }
    },
    'movement': {
        'data': {
            'uuid': 'f000aa81-0451-4000-b000-000000000000',
            'handle': '0x0000'
        },
        'notification': {
            'uuid': '2902',
            'handle': '0x0000'
        },
        'configuration': {
            'uuid': 'f000aa82-0451-4000-b000-000000000000',
            'handle': '0x0000'
        },
        'period': {
            'uuid': 'f000aa83-0451-4000-b000-000000000000',
            'handle': '0x0000'
        }
    },
    'humidity': {
        'data': {
            'uuid': 'f000aa21-0451-4000-b000-000000000000',
            'handle': '0x0000'
        },
        'notification': {
            'uuid': '2902',
            'handle': '0x0000'
        },
        'configuration': {
            'uuid': 'f000aa22-0451-4000-b000-000000000000',
            'handle': '0x0000'
        },
        'period': {
            'uuid': 'f000aa23-0451-4000-b000-000000000000',
            'handle': '0x0000'
        }
    },
    'pressure': {
        'data': {
            'uuid': 'f000aa41-0451-4000-b000-000000000000',
            'handle': '0x0000'
        },
        'notification': {
            'uuid': '2902',
            'handle': '0x0000'
        },
        'configuration': {
            'uuid': 'f000aa42-0451-4000-b000-000000000000',
            'handle': '0x0000'
        },
        'period': {
            'uuid': 'f000aa43-0451-4000-b000-000000000000',
            'handle': '0x0000'
        }
    },
    'luminance': {
        'data': {
            'uuid': 'f000aa71-0451-4000-b000-000000000000',
            'handle': '0x0000'
        },
        'notification': {
            'uuid': '2902',
            'handle': '0x0000'
        },
        'configuration': {
            'uuid': 'f000aa72-0451-4000-b000-000000000000',
            'handle': '0x0000'
        },
        'period': {
            'uuid': 'f000aa73-0451-4000-b000-000000000000',
            'handle': '0x0000'
        }
    }
}

char_enable = '01'
char_disable = '00'
"""
movement_enable setting
Bits	Usage
0	Gyroscope z axis enable
1	Gyroscope y axis enable
2	Gyroscope x axis enable
3	Accelerometer z axis enable
4	Accelerometer y axis enable
5	Accelerometer x axis enable
6	Magnetometer enable (all axes)
7	Wake-On-Motion Enable
8:9	Accelerometer range (0=2G, 1=4G, 2=8G, 3=16G)
10:15	Not used
"""
movement_enable = 'FFFF'
movement_disable = '0000'


class SensorTagCC2650(object):
    """Handles readings from SensorTagCC2650
    """
    reading_iterations = 1  # number of iterations to read data from the TAG

    def __init__(self, bluetooth_adr):
        try:
            self.bluetooth_adr = bluetooth_adr
            self.con = pexpect.spawn('gatttool -b ' + bluetooth_adr + ' --interactive')
            self.con.expect('\[LE\]>', timeout=600)
            print('SensorTagCC2650 {} Preparing to connect. Hold on a second...If nothing happens please press the power button...'.format(bluetooth_adr))
            _LOGGER.info('SensorTagCC2650 {} Preparing to connect. Hold on a second...If nothing happens please press the power button...'.format(bluetooth_adr))
            self.con.sendline('connect')
            # test for success of connect
            self.con.expect('.*Connection successful.*\[LE\]>')
            print('SensorTagCC2650 {} connected successfully'.format(bluetooth_adr))
            _LOGGER.info('SensorTagCC2650 {} connected successfully'.format(bluetooth_adr))
        except Exception as ex:
            # TODO: Investigate why SensorTag goes to sleep often and find a suitable software solution to awake it.
            print('SensorTagCC2650 {} connection failure. ()'.format(bluetooth_adr, str(ex)))
            _LOGGER.exception('SensorTagCC2650 {} connection failure. ()'.format(bluetooth_adr, str(ex)))

    def get_char_handle(self, uuid):
        timeout = 3
        max_time = time.time() + timeout
        rval = '0x0000'
        while time.time() < max_time:
            try:
                cmd = 'char-read-uuid %s' % uuid
                self.con.sendline(cmd)
                # TODO: Devise a better method for all below
                self.con.expect('.*handle:.* \r', timeout=3)
                reading = self.con.after
                line = reading.decode().split('handle: ')[1]
                rval = line.split()[0]
            except Exception as ex:
                time.sleep(.5)
            else:
                break
        return rval

    def get_notification_handle(self, data_handle):
        # TODO: Confirm with product sources that notification handle will always be data_handle + 1
        return hex(int(data_handle, 16) + 1)

    def char_write_cmd(self, handle, value):
        self.con.sendline('char-write-cmd %s %s' % (handle, value))
        # delay for 1 second so that Tag can enable registers
        time.sleep(1)

    def char_read_hnd(self, handle, sensortype):
        self.con.sendline('char-read-hnd %s' % handle)
        self.con.expect('.*descriptor:.* \r')
        reading = self.con.after
        rval = reading.split()
        _LOGGER.info('SensorTagCC2650 {} DEBUGGING: Reading from Tag... {} \n'.format(self.bluetooth_adr, reading))
        # _LOGGER.info('SensorTagCC2650 {} DEBUGGING: rval {}'.format(self.bluetooth_adr, str(rval)))
        return self.get_raw_measurement(sensortype, rval)

    def get_raw_measurement(self, sensortype, rval):
        if sensortype in ['temperature']:
            # The raw data value read from this sensor are two unsigned 16 bit values
            raw_bytes = rval[-4] + rval[-3] + rval[-2] + rval[-1]
        elif sensortype in ['movement']:
            # The raw data value read from this sensor are 18 bytes
            raw_bytes = rval[-18] + rval[-17] + rval[-16] + rval[-15] + \
                              rval[-14] + rval[-13] + rval[-12] + rval[-11] + \
                              rval[-10] + rval[-9] + rval[-8] + rval[-7] + \
                              rval[-6] + rval[-5] + rval[-4] + rval[-3] + \
                              rval[-2] + rval[-1]
        elif sensortype in ['humidity']:
            # The raw data value read from this sensor are two unsigned 16 bit values
            raw_bytes = rval[-4] + rval[-3] + rval[-2] + rval[-1]
        elif sensortype in ['pressure']:
            # The data from the pressure sensor consists of two 24-bit unsigned integers
            raw_bytes = rval[-6] + rval[-5] + rval[-4] + rval[-3] + rval[-2] + rval[-1]
        elif sensortype in ['luminance']:
            # The data from the optical sensor consists of a single 16-bit unsigned integer
            raw_bytes = rval[-2] + rval[-1]
        else:
            raw_bytes = 0
        _LOGGER.info('SensorTagCC2650 {} sensortype: {} raw_bytes: {}'.format(self.bluetooth_adr, sensortype, raw_bytes))
        return raw_bytes


    def hex_temp_to_celsius(self, raw_tempr):
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
        raw_object_temp = int('0x' + raw_temperature[2:4] + raw_temperature[0:2], 16)
        object_temp_int = raw_object_temp >> 2
        object_temp_celsius = float(object_temp_int) * SCALE_LSB

        # Choose ambient temperature (reverse bytes for little endian)
        raw_ambient_temp = int('0x' + raw_temperature[6:8] + raw_temperature[4:6], 16)
        ambient_temp_int = raw_ambient_temp >> 2
        ambient_temp_celsius = float(ambient_temp_int) * SCALE_LSB
        ambient_temp_fahrenheit = (ambient_temp_celsius * 1.8) + 32

        _LOGGER.info('SensorTagCC2650 {} object Celsius: {} Ambient Celsius: {} Fahrenheit: {}'.format(self.bluetooth_adr, object_temp_celsius, ambient_temp_celsius, ambient_temp_fahrenheit))

        return object_temp_celsius, ambient_temp_celsius


    def hex_movement_to_movement(self, raw_movement):
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
        SensorTagCC2650 firmware so there is no calculation involved apart from changing the integer to a float if required.
        The measurement unit is uT (micro Tesla).
        float sensorMpu9250MagConvert(int16_t data)
        {
          //-- calculate magnetism, unit uT, range +-4900
          return 1.0 * data;
        }
        :param raw_movement:
        :return:
        """
        # TODO: Double confirm the formulae, calculations
        gyro_convert = lambda data: (data * 1.0) / (65536 / 500)
        acc_convert = lambda raw_data, ginfo: (raw_data * 1.0) / (32768/ginfo)
        mag_convert = lambda data: 1.0 * data
        get_signed_int = lambda x: -(x & 0x8000) | (x & 0x7fff)

        interim_value = raw_movement.decode()
        raw_gyro_x = get_signed_int(int('0x'+interim_value[1:2]+interim_value[0:1], 16))
        raw_gyro_y = get_signed_int(int('0x'+interim_value[3:4]+interim_value[2:3], 16))
        raw_gyro_z = get_signed_int(int('0x'+interim_value[5:6]+interim_value[4:5], 16))
        raw_acc_x = get_signed_int(int('0x'+interim_value[7:8]+interim_value[6:7], 16))
        raw_acc_y = get_signed_int(int('0x'+interim_value[9:10]+interim_value[8:9], 16))
        raw_acc_z = get_signed_int(int('0x'+interim_value[11:12]+interim_value[10:11], 16))
        raw_mag_x = get_signed_int(int('0x'+interim_value[13:14]+interim_value[12:13], 16))
        raw_mag_y = get_signed_int(int('0x'+interim_value[15:16]+interim_value[14:15], 16))
        raw_mag_z = get_signed_int(int('0x'+interim_value[17:18]+interim_value[16:17], 16))

        gyro_x = gyro_convert(raw_gyro_x)
        gyro_y = gyro_convert(raw_gyro_y)
        gyro_z = gyro_convert(raw_gyro_z)

        acc_range = int('0x'+movement_enable, 16) | int('0x00c0', 16) >> 6
        gdata = 16 if acc_range == 3 else 8 if acc_range == 2 else 4 if acc_range == 1 else 2
        acc_x = acc_convert(raw_acc_x, gdata)
        acc_y = acc_convert(raw_acc_y, gdata)
        acc_z = acc_convert(raw_acc_z, gdata)

        mag_x = mag_convert(raw_mag_x)
        mag_y = mag_convert(raw_mag_y)
        mag_z = mag_convert(raw_mag_z)

        return gyro_x, gyro_y, gyro_z, acc_x, acc_y, acc_z, mag_x, mag_y, mag_z, acc_range


    def hex_humidity_to_rel_humidity(self, raw_humd):
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
        raw_temperature = int('0x'+interim_value[2:4]+interim_value[0:2], 16)
        temperature = ((raw_temperature / 65536) * 165) - 40
        raw_humidity = int('0x'+interim_value[6:8]+interim_value[4:6], 16)
        raw_humidity &= -0x0003
        humidity = float((raw_humidity)) / 65536 * 100
        _LOGGER.info('SensorTagCC2650 {} tempr: {} humidity: {}'.format(self.bluetooth_adr, temperature, humidity))
        return humidity, temperature


    def hex_pressure_to_pressure(self, raw_pr):
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
        raw_pressure = int('0x'+interim_value[10:12]+interim_value[8:10]+interim_value[6:8], 16)
        pressure = float(raw_pressure) / 100.0
        _LOGGER.info('SensorTagCC2650 {} pressure: {}'.format(self.bluetooth_adr, pressure))
        return pressure


    def hex_lux_to_lux(self, raw_lumn):
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
        # Reverse LSB and MSB
        raw_luminance = int('0x'+interim_value[2:4]+interim_value[0:2], 16)
        m = "0FFF"
        e = "F000"
        m = int(m, 16)
        exp = int(e, 16)
        m = (raw_luminance & m)
        exp = (raw_luminance & exp) >> 12
        exp = 1 if exp == 0 else 2
        exp = exp << (exp -1)
        luminance = (m * (0.01 * exp))
        _LOGGER.info('SensorTagCC2650 {} luminance: {}'.format(self.bluetooth_adr, luminance))
        return luminance
