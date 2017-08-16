# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""SenseHat for sensor readings"""

import asyncio

from foglamp import logger
from foglamp.device.ingest import Ingest
from sense_hat import SenseHat
from datetime import datetime, timezone

__author__ = "Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_LOGGER = logger.setup(__name__)

# pylint: disable=line-too-long
# Configuration: https://docs.google.com/document/d/1wPg-XzkdLPgFlC3JjpSaMivVH3VyjKvGa4TVJJukvdg/edit#heading=h.ru11tt2gnb6g
# pylint: enable=line-too-long
_CONFIG_CATEGORY_NAME = 'HAT_CONF'
_CONFIG_CATEGORY_DESCRIPTION = 'Sense Hat Configuration'
_READINGS_WRITE_FREQUENCY_SECONDS = .001

async def start():
    sense = SenseHat()
    sense.set_imu_config(True, True, True)
    while True:
        await asyncio.sleep(_READINGS_WRITE_FREQUENCY_SECONDS)

        # "TI sensorTag/pressure"
        try:
            sensor_value_object = {'sensor_values': {'pressure': sense.get_pressure()}}
        except Exception:
            _LOGGER.exception("Unable to read pressure")
            continue
        sensor_value_object["asset"] = "TI sensorTag/pressure"
        sensor_value_object["timestamp"] = "{!s}".format(datetime.now(tz=timezone.utc))
        try:
            await Ingest.add_readings(sensor_value_object)
        except Exception:
            _LOGGER.exception("Error saving sensor readings: %s", sensor_value_object)

        # "TI sensorTag/humidity"
        try:
            sensor_value_object = {'sensor_values': {'humidity': sense.get_humidity(),'temperature': sense.get_temperature()}}
        except Exception:
            _LOGGER.exception("Unable to read humdity/temperature")
            continue
        sensor_value_object["asset"] = "TI sensorTag/humidity"
        sensor_value_object["timestamp"] = "{!s}".format(datetime.now(tz=timezone.utc))
        try:
            await Ingest.add_readings(sensor_value_object)
        except Exception:
            _LOGGER.exception("Error saving sensor readings: %s", sensor_value_object)

        # "TI sensorTag/gyroscope"
        try:
            sensor_value_object = {
                'sensor_values': sense.get_gyroscope_raw()}
        except Exception:
            _LOGGER.exception("Unable to read gyroscope ")
            continue
        sensor_value_object["asset"] = "TI sensorTag/gyroscope"
        sensor_value_object["timestamp"] = "{!s}".format(datetime.now(tz=timezone.utc))
        try:
            await Ingest.add_readings(sensor_value_object)
        except Exception:
            _LOGGER.exception("Error saving sensor readings: %s", sensor_value_object)

        # "TI sensorTag/magnetometer"
        try:
            sensor_value_object = {
                'sensor_values': sense.get_compass_raw()}
        except Exception:
            _LOGGER.exception("Unable to read magnetometer ")
            continue
        sensor_value_object["asset"] = "TI sensorTag/magnetometer"
        sensor_value_object["timestamp"] = "{!s}".format(datetime.now(tz=timezone.utc))
        try:
            await Ingest.add_readings(sensor_value_object)
        except Exception:
            _LOGGER.exception("Error saving sensor readings: %s", sensor_value_object)

        # "TI sensorTag/accelerometer"
        try:
            sensor_value_object = {
                'sensor_values': sense.get_accelerometer_raw()}
        except Exception:
            _LOGGER.exception("Unable to read accelerometer ")
            continue
        sensor_value_object["asset"] = "TI sensorTag/accelerometer"
        sensor_value_object["timestamp"] = "{!s}".format(datetime.now(tz=timezone.utc))
        try:
            await Ingest.add_readings(sensor_value_object)
        except Exception:
            _LOGGER.exception("Error saving sensor readings: %s", sensor_value_object)

