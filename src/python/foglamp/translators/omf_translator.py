#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Pushes information stored in FogLAMP into PICROMF (PI Connector Relay OMF)
The information are sent in chunks,
the table foglamp.streams and block_size are used for this handling

.. todo::
   - # TODO: FOGL-251 - it should evolve using the DB layer
   - only part of the code is using async

"""

import json
import time
import requests

import psycopg2
import asyncio

from foglamp import logger, statistics, configuration_manager

# Module information
__author__ = "${FULL_NAME}"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# FIXME: it will be removed using the DB layer
_DB_URL = 'postgresql:///foglamp'
"""DB references"""

_module_name = "OMF Translator"

_message_list = {

    # Information messages
    "i000001": " ",
    "i000002": _module_name + " - Started.",
    "i000003": _module_name + " - Execution completed.",

    # Warning / Error messages
    "e000001": _module_name + " - cannot complete the operation.",
    "e000002": _module_name + " - cannot retrieve the starting point for sending operation.",
    "e000003": _module_name + " - cannot update the reached position.",
    "e000004": _module_name + " - cannot complete the sending operation.",
    "e000005": _module_name + " - cannot setup the logger - error details |{0}|",

    "e000006": _module_name + " - cannot initialize the plugin.",
    "e000007": _module_name + " - an error occurred during the OMF request - error details |{0}|",
    "e000008": _module_name + " - an error occurred during the OMF's objects creation.",
    "e000009": _module_name + " - cannot retrieve information about the sensor.",
    "e000010": _module_name + " - unable to extend the in memory structure with new data.",
    "e000011": _module_name + " - cannot create the OMF types.",
    "e000012": _module_name + " - unknown asset_code - asset |{0}| - error details |{1}|",
    "e000013": _module_name + " - cannot prepare sensor information for PICROMF - error details |{0}|",
    "e000014": _module_name + " - ",

    "e000015": _module_name + " - cannot update statistics.",
    "e000016": _module_name + " - ",
    "e000017": _module_name + " - cannot complete loading data into the memory.",
    "e000018": _module_name + " - cannot complete the initialization.",
    "e000019": _module_name + " - cannot complete the preparation of the in memory structure.",

}
"""Messages used for Information, Warning and Error notice"""

_logger = ""

_event_loop = ""

# Managed by initialize_plugin
_relay_url = ""
_producer_token = ""
_channel_id = 1
"""Channel Id for the OMF translator"""

_omf_max_retry = 5
_omf_retry_sleep_time = 1

_block_size = 1000
"""The size of a block of readings to send in each transmission"""


# OMF objects creation
_types = ""

# OMF object's static attributes
_sensor_location = "S.F."

# OMF types definitions - default vales
_type_id = "0"

_OMF_types_definition = []
_sensor_data_keys = []
_asset_code_type = {}
"""Associates the asset code to the corresponding type"""

_DEFAULT_OMF_CONFIG = {
    "URL": {
        "description": "The URL of the PI Connector to send data to",
        "type": "string",
        "default": "http://WIN-4M7ODKB0RH2:8118/ingress/messages"
    },
    "producerToken": {
        "description": "The producer token that represents this FogLAMP stream",
        "type": "string",
        "default": "omf_translator_404"

    },
    "channelID": {
        "description": "Channel ID for the OMF translator",
        "type": "integer",
        "default": "1"

    },
    "OMFMaxRetry": {
        "description": "Max number of retries for the communication with the OMF PI Connector Relay",
        "type": "integer",
        "default": "5"

    },
    "OMFRetrySleepTime": {
        "description": "Seconds between each retry for the communication with the OMF PI Connector Relay",
        "type": "integer",
        "default": "1"

    },
    "blockSize": {
        "description": "The size of a block of readings to send in each transmission.",
        "type": "integer",
        "default": "1000"

    },

}
_CONFIG_CATEGORY_NAME = 'OMF_TRANS'
_CONFIG_CATEGORY_DESCRIPTION = 'Configuration of OMF Translator plugin'

_config = ""
"""Configurations retrieved from the Configuration Manager"""

# DB operations
_pg_conn = ""
_pg_cur = ""

# statistics
_num_sent = 0

# internal statistic
_num_unsent = 0
"""rows that generate errors in the preparation process, before sending them to OMF"""


def initialize_plugin():
    """Initializes the OMF plugin for the sending of blocks of readings to the PI Connector.

    Retrieves the configuration for :
        relay_url      - URL           - The URL of the PI Connector to send data to.
        producer_token - producerToken - The producer token that represents this FogLAMP stream
        types          - OMFTypes      - A JSON object that contains the OMF type definitions for this stream

    Raises:
        Exception: Fails to initialize the plugin
    """

    global _event_loop
    global _config

    global _relay_url
    global _producer_token
    global _types

    global _type_id

    global _sensor_data_keys
    global _asset_code_type

    global _OMF_types_definition
    global _channel_id

    global _block_size

    global _omf_max_retry
    global _omf_retry_sleep_time

    try:
        _event_loop.run_until_complete(configuration_manager.create_category(_CONFIG_CATEGORY_NAME, _DEFAULT_OMF_CONFIG,
                                                                             _CONFIG_CATEGORY_DESCRIPTION))
        _config = _event_loop.run_until_complete(configuration_manager.get_category_all_items(_CONFIG_CATEGORY_NAME))

        _block_size = _omf_max_retry = int(_config['blockSize']['value'])

        # OMF parameters
        _omf_max_retry = int(_config['OMFMaxRetry']['value'])
        _omf_retry_sleep_time = int(_config['OMFRetrySleepTime']['value'])

        # Channel parameters
        _channel_id = int(_config['channelID']['value'])

        # URL
        _relay_url = _config['URL']['value']

        # OMF types definition - xxx
        _type_id = "150"

        # producerToken
        _producer_token = _config['producerToken']['value']

        # OMFTypes
        _sensor_data_keys = ["x", "y", "z", "pressure", "lux", "humidity", "temperature",
                             "object", "ambient", "left", "right", "magnet", "button"]
        """Available proprieties in the reading field"""

        _asset_code_type = {
            # asset_code                  OMF type
            "TI sensorTag/accelerometer": "TI_sensorTag_accelerometer",
            "TI sensorTag/gyroscope":     "TI_sensorTag_gyroscope",
            "TI sensorTag/magnetometer":  "TI_sensorTag_magnetometer",
            "TI sensorTag/humidity":      "TI_sensorTag_humidity",
            "TI sensorTag/luxometer":     "TI_sensorTag_luxometer",
            "TI sensorTag/pressure":      "TI_sensorTag_pressure",
            "TI sensorTag/temperature":   "TI_sensorTag_temperature",
            "TI sensorTag/keys":          "TI_sensorTag_keys",
            "mouse":                      "mouse"
        }

        _OMF_types_definition = {
            "TI_sensorTag_accelerometer": [
                {
                    "id": "xxx",
                    "type": "object",
                    "classification": "static",
                    "properties": {
                        "Name": {
                            "type": "string",
                            "isindex": True
                        },
                        "Location": {
                            "type": "string"
                        }
                    }
                },
                {
                    "id": "xxx",
                    "type": "object",
                    "classification": "dynamic",
                    "properties": {
                        "Time": {
                            "format": "date-time",
                            "type": "string",
                            "isindex": True
                        },
                        "x": {
                            "type": "number"
                        },
                        "y": {
                            "type": "number"
                        },
                        "z": {
                            "type": "number"
                        }
                    }
                }
            ],
            "TI_sensorTag_gyroscope": [
                {
                    "id": "xxx",
                    "type": "object",
                    "classification": "static",
                    "properties": {
                        "Name": {
                            "type": "string",
                            "isindex": True
                        },
                        "Location": {
                            "type": "string"
                        }
                    }
                },
                {
                    "id": "xxx",
                    "type": "object",
                    "classification": "dynamic",
                    "properties": {
                        "Time": {
                            "format": "date-time",
                            "type": "string",
                            "isindex": True
                        },
                        "x": {
                            "type": "number"
                        },
                        "y": {
                            "type": "number"
                        },
                        "z": {
                            "type": "number"
                        }
                    }
                }
            ],
            "TI_sensorTag_magnetometer": [
                {
                    "id": "xxx",
                    "type": "object",
                    "classification": "static",
                    "properties": {
                        "Name": {
                            "type": "string",
                            "isindex": True
                        },
                        "Location": {
                            "type": "string"
                        }
                    }
                },
                {
                    "id": "xxx",
                    "type": "object",
                    "classification": "dynamic",
                    "properties": {
                        "Time": {
                            "format": "date-time",
                            "type": "string",
                            "isindex": True
                        },
                        "x": {
                            "type": "number"
                        },
                        "y": {
                            "type": "number"
                        },
                        "z": {
                            "type": "number"
                        }
                    }
                }
            ],
            "TI_sensorTag_humidity": [
                {
                    "id":  "xxx",
                    "type": "object",
                    "classification": "static",
                    "properties": {
                        "Name": {
                            "type": "string",
                            "isindex": True
                        },
                        "Location": {
                            "type": "string"
                        }
                    }
                },
                {
                    "id":  "xxx",
                    "type": "object",
                    "classification": "dynamic",
                    "properties": {
                        "Time": {
                            "format": "date-time",
                            "type": "string",
                            "isindex": True
                        },
                        "humidity": {
                            "type": "number"
                        },
                        "temperature": {
                            "type": "number"
                        }
                    }
                }
            ],
            "TI_sensorTag_luxometer": [
                {
                    "id": "xxx",
                    "type": "object",
                    "classification": "static",
                    "properties": {
                        "Name": {
                            "type": "string",
                            "isindex": True
                        },
                        "Location": {
                            "type": "string"
                        }
                    }
                },
                {
                    "id": "xxx",
                    "type": "object",
                    "classification": "dynamic",
                    "properties": {
                        "Time": {
                            "format": "date-time",
                            "type": "string",
                            "isindex": True
                        },
                        "lux": {
                            "type": "integer"
                        }
                    }
                }
            ],
            "TI_sensorTag_pressure": [
                {
                    "id":  "xxx",
                    "type": "object",
                    "classification": "static",
                    "properties": {
                        "Name": {
                            "type": "string",
                            "isindex": True
                        },
                        "Location": {
                            "type": "string"
                        }
                    }
                },
                {
                    "id":  "xxx",
                    "type": "object",
                    "classification": "dynamic",
                    "properties": {
                        "Time": {
                            "format": "date-time",
                            "type": "string",
                            "isindex": True
                        },
                        "pressure": {
                            "type": "integer"
                        }
                    }
                }
            ],
            "TI_sensorTag_temperature": [
                {
                    "id": "xxx",
                    "type": "object",
                    "classification": "static",
                    "properties": {
                        "Name": {
                            "type": "string",
                            "isindex": True
                        },
                        "Location": {
                            "type": "string"
                        }
                    }
                },
                {
                    "id": "xxx",
                    "type": "object",
                    "classification": "dynamic",
                    "properties": {
                        "Time": {
                            "format": "date-time",
                            "type": "string",
                            "isindex": True
                        },
                        "object": {
                            "type": "number"
                        },
                        "ambient": {
                            "type": "number"
                        }
                    }
                }
            ],
            "TI_sensorTag_keys": [
                {
                    "id": "xxx",
                    "type": "object",
                    "classification": "static",
                    "properties": {
                        "Name": {
                            "type": "string",
                            "isindex": True
                        },
                        "Location": {
                            "type": "string"
                        }
                    }
                },
                {
                    "id": "xxx",
                    "type": "object",
                    "classification": "dynamic",
                    "properties": {
                        "Time": {
                            "format": "date-time",
                            "type": "string",
                            "isindex": True
                        },
                        "left": {
                            "type": "string"
                        },
                        "right": {
                            "type": "string"
                        },
                        "magnet": {
                            "type": "string"
                        }
                    }
                }
            ],
            "mouse": [
                {
                    "id": "xxx",
                    "type": "object",
                    "classification": "static",
                    "properties": {
                        "Name": {
                            "type": "string",
                            "isindex": True
                        },
                        "Location": {
                            "type": "string"
                        }
                    }
                },
                {
                    "id": "xxx",
                    "type": "object",
                    "classification": "dynamic",
                    "properties": {
                        "Time": {
                            "format": "date-time",
                            "type": "string",
                            "isindex": True
                        },
                        "button": {
                            "type": "string"
                        }
                    }
                }
            ]
        }

    except Exception:
        message = _message_list["e000006"]

        _logger.exception(message)
        raise


def send_in_memory_data_to_picromf(message_type, omf_data):
    """Sends data to PICROMF - it retries the operation using a sleep time increased *2 for every retry

    it logs a WARNING only at the end of the retry mechanism

    Args:
        message_type: possible values - Type | Container | Data
        omf_data:     message to send

    Raises:
        Exception: an error occurred during the OMF request

    """

    global _omf_max_retry

    sleep_time = _omf_retry_sleep_time

    message = ""
    status = 0
    num_retry = 1

    while num_retry < _omf_max_retry:
        try:
            status = 0
            msg_header = {'producertoken': _producer_token,
                          'messagetype': message_type,
                          'action': 'create',
                          'messageformat': 'JSON',
                          'omfversion': '1.0'}

            omf_data_json = json.dumps(omf_data)

            response = requests.post(_relay_url, headers=msg_header, data=omf_data_json, verify=False,
                                     timeout=30)

            # FIXME: temporary/testing code
            if response.status_code == 400:
                raise RuntimeError(response.text)

            _logger.debug("Response |{0}| message: |{1}| |{2}| ".format(message_type,
                                                                        response.status_code,
                                                                        response.text))

            break

        except Exception as e:
            message = _message_list["e000007"].format(e)
            status = 1

            time.sleep(sleep_time)
            num_retry += 1
            sleep_time *= 2

    if status != 0:
        _logger.warning(message)
        raise Exception(message)


def position_read():
    """Retrieves the starting point for the sent operation

    Returns:
        position: starting point for the send operation

    Raises:
        Exception: operations at db level failed

    Todo:
        it should evolve using the DB layer
    """

    global _pg_conn
    global _pg_cur

    position = 0

    try:
        sql_cmd = "SELECT last_object FROM foglamp.streams WHERE id={0}".format(_channel_id)

        _pg_cur.execute(sql_cmd)
        rows = _pg_cur.fetchall()
        for row in rows:
            position = row[0]
            _logger.debug("DB row position |{0}| : ". format(row[0]))

    except Exception:
        message = _message_list["e000002"]

        _logger.exception(message)
        raise

    return position


def position_update(new_position):
    """Updates reached position in the communication with PICROMF

    Args:
        new_position:  Last row already sent to the PICROMF

    Todo:
        it should evolve using the DB layer

    """

    global _pg_conn
    global _pg_cur

    try:
        _logger.debug("Last position, sent |{0}| ".format(str(new_position)))

        sql_cmd = "UPDATE foglamp.streams SET last_object={0}, ts=now()  WHERE id={1}".format(new_position, _channel_id)
        _pg_cur.execute(sql_cmd)

        _pg_conn.commit()

    except Exception:
        message = _message_list["e000003"]

        _logger.exception(message)
        raise


def omf_types_creation():
    """Creates the types into OMF

    """

    try:
        for asset_code in _asset_code_type:
            sensor_type = _asset_code_type[asset_code]

            tmp_type_sensor_id = "type_sensor_id_" + _type_id + "_" + sensor_type
            tmp_type_measurement_id = "type_measurement_" + _type_id + "_" + sensor_type

            omf_type = _OMF_types_definition[sensor_type]
            omf_type[0]["id"] = tmp_type_sensor_id
            omf_type[1]["id"] = tmp_type_measurement_id

            send_in_memory_data_to_picromf("Type", omf_type)

    except Exception:
        message = _message_list["e000011"]

        _logger.exception(message)
        raise


def omf_objects_creation():
    """Creates all the OMF objects

    Raises:
        Exception: an error occurred during the OMF's objects creation.

    """

    global _sensor_location

    try:
        for sensor_info in _asset_code_type:

            tmp_sensor_id = sensor_info
            tmp_measurement_id = "measurement_" + tmp_sensor_id

            tmp_type = _asset_code_type[tmp_sensor_id]

            tmp_type_sensor_id = "type_sensor_id_" + _type_id + "_" + tmp_type
            tmp_type_measurement_id = "type_measurement_" + _type_id + "_" + tmp_type

            _logger.debug("OMF_object_creation ")
            omf_object_creation(tmp_sensor_id, tmp_measurement_id, tmp_type_sensor_id, tmp_type_measurement_id)

    except Exception:
        message = _message_list["e000008"]

        _logger.exception(message)
        raise


def omf_object_creation(tmp_sensor_id, tmp_measurement_id, tmp_type_sensor_id, tmp_type_measurement_id):
    """Creates an object into PICROMF

    Raises:
        Exception: an error occurred during the OMF's objects creation.

    """

    global _sensor_location

    try:
        # PICROMF objects definition
        containers = [
            {
                "id": tmp_measurement_id,
                "typeid": tmp_type_measurement_id
            }
        ]

        static_data = [{
            "typeid": tmp_type_sensor_id,
            "values": [{
                "Name": tmp_sensor_id,
                "Location": _sensor_location
            }]
        }]

        link_data = [{
            "typeid": "__Link",
            "values": [{
                "source": {
                    "typeid": tmp_type_sensor_id,
                    "index": "_ROOT"
                },
                "target": {
                    "typeid": tmp_type_sensor_id,
                    "index": tmp_sensor_id
                }
            }, {
                "source": {
                    "typeid": tmp_type_sensor_id,
                    "index": tmp_sensor_id
                },
                "target": {
                    "containerid": tmp_measurement_id
                }

            }]
        }]

        send_in_memory_data_to_picromf("Container", containers)
        send_in_memory_data_to_picromf("Data", static_data)
        send_in_memory_data_to_picromf("Data", link_data)

    except Exception:
        message = _message_list["e000008"]

        _logger.exception(message)
        raise


async def send_data_to_picromf():
    """Reads data from the Storage Layer and sends them to the PICROMF

    Raises:
        Exception: cannot complete the sending operation

    Todo:
        it should evolve using the DB layer

    """

    global _pg_conn
    global _pg_cur

    data_to_send = []

    try:
        _pg_conn = psycopg2.connect(_DB_URL)
        _pg_cur = _pg_conn.cursor()

        position = position_read()
        _logger.debug("Last position, already sent |{0}| ".format(str(position)))

        _logger.debug("{0}".format("omf_translator_perf - load_data_into_memory START "))
        raw_data = load_data_into_memory(position)
        _logger.debug("{0}".format("omf_translator_perf - load_data_into_memory END "))

        _logger.debug("{0}".format("omf_translator_perf - transform_in_memory_data START "))
        data_available, new_position = transform_in_memory_data(data_to_send, raw_data)
        _logger.debug("{0}".format("omf_translator_perf - load_data_into_memory END "))

        if data_available:
            _logger.debug("{0}".format("omf_translator_perf - send_in_memory_data_to_picromf START "))
            send_in_memory_data_to_picromf("Data", data_to_send)
            _logger.debug("{0}".format("omf_translator_perf - send_in_memory_data_to_picromf END "))

            position_update(new_position)
            await update_statistics()

    except Exception:
        message = _message_list["e000004"]

        _logger.exception(message)
        raise


def load_data_into_memory(position):
    """Extracts data from the DB Layer loading into the memory

    Raises:
        Exception: cannot complete loading data in memory

    Todo:
        it should evolve using the DB layer

    """

    global _pg_conn
    global _pg_cur

    try:
        sql_cmd = "SELECT id, asset_code, user_ts, reading FROM foglamp.readings WHERE id> {0} ORDER BY id LIMIT {1}"\
                  .format(position, _block_size)

        _pg_cur.execute(sql_cmd)
        rows = _pg_cur.fetchall()

    except Exception:
        message = _message_list["e000017"]

        _logger.exception(message)
        raise

    return rows


def transform_in_memory_data(data_to_send, raw_data):
    """Transforms in memory data into a new structure that could be converted into JSON for PICROMF

    Raises:
        Exception: cannot complete the preparation of the in memory structure.

    """

    global _num_sent
    global _num_unsent

    new_position = 0
    data_available = False

    try:
        for row in raw_data:

            row_id = row[0]
            asset_code = row[1]

            # Identification of the object/sensor
            measurement_id = "measurement_" + asset_code

            tmp_type = ""
            try:
                # Evaluates if it is a known asset code
                tmp_type = _asset_code_type[asset_code]

            except Exception as e:
                message = _message_list["e000012"].format(tmp_type, e)

                _logger.warning(message)
            else:
                try:
                    transform_in_memory_row(data_to_send, row, measurement_id)

                    # Used for the statistics update
                    _num_sent += 1

                    # Latest position reached
                    new_position = row_id

                    data_available = True

                except Exception as e:
                    _num_unsent += 1

                    message = _message_list["e000013"].format(e)
                    _logger.warning(message)

    except Exception:
        message = _message_list["e000019"]

        _logger.exception(message)
        raise

    return data_available,  new_position


def transform_in_memory_row(data_to_send, row, target_stream_id):
    """Extends the in memory structure using data retrieved from the Storage Layer

    Args:
        data_to_send:      data to send - updated/used by reference
        row:               information retrieved from the Storage Layer that it is used to extend data_to_send
        target_stream_id:  OMF container ID

    Raises:
        Exception: unable to extend the in memory structure with new data.

    """

    data_available = False

    try:
        row_id = row[0]
        asset_code = row[1]
        timestamp = row[2].isoformat()
        sensor_data = row[3]

        _logger.debug("Stream ID : |{0}| Sensor ID : |{1}| Row ID : |{2}|  "
                      .format(target_stream_id, asset_code, str(row_id)))

        # Prepares new data for the PICROMF
        new_data = [
            {
                "containerid": target_stream_id,
                "values": [
                    {
                        "Time": timestamp
                    }
                ]
            }
        ]

        # Evaluates which data is available
        for data_key in sensor_data:
            try:
                new_data[0]["values"][0][data_key] = sensor_data[data_key]

                data_available = True
            except KeyError:
                pass

        if data_available:
            # note : append produces an not properly constructed OMF message
            data_to_send.extend(new_data)

            _logger.debug("in memory info |{0}| ".format(new_data))
        else:
            message = _message_list["e000009"]
            _logger.warning(message)

    except Exception:
        message = _message_list["e000010"]

        _logger.exception(message)
        raise


def send_init():
    """Setup the correct state to being able to send data to the PICROMF

    Raises :
        Exception - cannot complete the initialization
    """

    try:
        prg_text = ", for Linux (x86_64)"

        start_message = "" + _module_name + "" + prg_text + " " + __copyright__ + " "
        _logger.info("{0}".format(start_message))
        _logger.info(_message_list["i000002"])

        initialize_plugin()

        omf_types_creation()
        omf_objects_creation()

    except Exception:
        message = _message_list["e000018"]

        _logger.exception(message)
        raise


async def update_statistics():
    """Updates FogLAMP statistics

    Raises :
        Exception - cannot update statistics
    """

    try:
        await statistics.update_statistics_value('SENT', _num_sent)

    except Exception:
        message = _message_list["e000015"]

        _logger.exception(message)
        raise


if __name__ == "__main__":

    try:
        _logger = logger.setup(__name__)

    except Exception as ex:
        tmp_message = _message_list["e000005"].format(str(ex))

        print ("ERROR - ", tmp_message)

    try:
        _logger.debug("{0}".format("omf_translator_perf - START "))

        _event_loop = asyncio.get_event_loop()

        _logger.debug("{0}".format("omf_translator_perf - send_init START "))
        send_init()
        _logger.debug("{0}".format("omf_translator_perf - send_init END "))

        _event_loop.run_until_complete(send_data_to_picromf())

        _logger.info(_message_list["i000003"])

    except Exception as ex:
        tmp_message = _message_list["e000001"].format(str(ex))

        _logger.exception(tmp_message)

    _logger.debug("{0}".format("omf_translator_perf - END "))
