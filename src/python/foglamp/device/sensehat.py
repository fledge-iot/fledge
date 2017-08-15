# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""CoAP handler for sensor readings"""

import asyncio

from cbor2 import loads
from cbor2.decoder import CBORDecodeError

from foglamp import configuration_manager
from foglamp import logger
from foglamp.device.ingest import Ingest
from sense_hat import SenseHat

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
_READINGS_WRITE_FREQUENCY_SECONDS = 5

async def start():
    while True:
        await asyncio.sleep(_READINGS_WRITE_FREQUENCY_SECONDS)
        payload=\
        {
          "timestamp"     : "2017-08-04T06:59:57.503Z",
          "asset"         : "TI sensorTag/luxometer",
          "sensor_values" : { "lux" : 49 }
        }
        try:
            await Ingest.add_readings(payload)
        except (KeyError, TypeError):
            _LOGGER.exception("Invalid payload: %s", payload)
        except Exception:
            _LOGGER.exception("Error saving sensor readings: %s", payload)