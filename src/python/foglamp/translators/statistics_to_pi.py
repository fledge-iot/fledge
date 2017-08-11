#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Pushes FogLAMP statistics into PI through the PICROMF (PI Connector Relay OMF)

Note :

.. todo::
   - # TODO: FOGL-251 - it should evolve using the DB layer
   - only part of the code is using async
"""

import json
import time
import requests

from foglamp import logger

# Import packages - DB operations
import psycopg2
import asyncio
import aiopg
import aiopg.sa
import sqlalchemy as sa
from foglamp import configuration_manager

# Module information
__author__ = "${FULL_NAME}"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# FIXME: it will be removed using the DB layer
_DB_URL = 'postgresql:///foglamp'
"""DB references"""

_module_name = "statistics_to_pi"

_message_list = {

    # Information messages
    "i000001": "operation successfully completed",
    "i000002": _module_name + " - Started",
    "i000003": _module_name + " - Execution completed.",

    # Warning / Error messages
    "e000001": _module_name + " - generic error.",
    "e000002": _module_name + " - cannot retrieve the starting point for sending operation.",
    "e000003": _module_name + " - cannot update the reached position.",
    "e000004": _module_name + " - cannot complete the sending operation.",
    "e000005": _module_name + " - cannot configure the logging mechanism.",
    "e000006": _module_name + " - cannot initialize the plugin.",
    "e000007": _module_name + " - an error occurred during the OMF request - error details ",
    "e000008": _module_name + " - an error occurred during the OMF's objects creation.",
    "e000009": _module_name + " - cannot retrieve information about the sensor.",
    "e000010": _module_name + " - unable to extend the in memory structure with the data.",
    "e000011": _module_name + " - cannot create the OMF types.",
    "e000012": _module_name + " - unknown asset_code - asset - error details |{1}|.",
    "e000013": _module_name + " - cannot prepare sensor information for PICROMF.",
    "e000014": _module_name + " - cannot start the sending process.",
    "e000015": _module_name + " - cannot update statistics.",
    "e000016": _module_name + " - cannot update reached position/statistics during a previous error.",
    "e000017": _module_name + " - cannot complete loading data in memory.",
    "e000018": _module_name + " - cannot complete the initialization."

}
"""Messages used for Information, Warning and Error notice"""

_logger = ""

_statistics_history_tbl = sa.Table(
    'statistics_history',
    sa.MetaData(),
    sa.Column('key', sa.BigInteger, primary_key=True),
    sa.Column('value', sa.types.INTEGER),
    sa.Column('id', sa.types.INTEGER),
    sa.Column('ts', sa.types.TIMESTAMP))


_event_loop = ""

# Managed by initialize_plugin
_relay_url = ""
_producer_token = ""
_channel_id = 2

"""Channel Id for the OMF translator"""

_omf_max_retry = 5
_omf_retry_sleep_time = 1

_block_size = 1000
"""The size of a block of readings to send in each transmission"""


# OMF objects creation
_types = ""

# OMF object's attributes
_sensor_location = "S.F."

# OMF types definitions - default vales
_type_id = "0"

_OMF_types_definition = []
_sensor_data_keys = []
_sensor_types = []
_sensor_name_type = {}
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
        "default": "statistics_301"

    },
    "channelID": {
        "description": "Channel ID for the FogLAMP statistics into PI",
        "type": "integer",
        "default": "2"

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
_CONFIG_CATEGORY_NAME = 'STAT_PI'
_CONFIG_CATEGORY_DESCRIPTION = 'Configuration of FogLAMP statistics into PI'

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


class PICROMFNotReadyError(RuntimeError):
    """Impossible to reach the PICROMF."""
    pass


class HTTPError400(RuntimeError):
    """Raised in relation to the HTTP status_code during the communication with the PICROMF."""
    pass


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
    global _sensor_types
    global _sensor_name_type

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
        _type_id = "200"

        # producerToken
        _producer_token = _config['producerToken']['value']

        # OMFTypes
        _sensor_data_keys = [
            "buffered",
            "purged",
            "unsnpurged",
            "sent",
            "readings",
            "discarded",
            "unsent"
        ]

        """Available proprieties"""

        _sensor_types = [
            "buffered",
            "purged",
            "unsnpurged",
            "sent",
            "readings",
            "discarded",
            "unsent"
        ]

        _sensor_name_type = {
            # asset_code     OMF type
            "buffered": "buffered",
            "purged": "purged",
            "unsnpurged": "unsnpurged",
            "sent": "sent",
            "readings": "readings",
            "discarded": "discarded",
            "unsent": "unsent"
        }

        _OMF_types_definition = {
            "buffered": [
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
                        "value": {
                            "type": "number"
                        }
                    }
                }
            ],
            "purged": [
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
                        "value": {
                            "type": "number"
                        }
                    }
                }
            ],

            "unsnpurged": [
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
                        "value": {
                            "type": "number"
                        }
                    }
                }
            ],
            "sent": [
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
                        "value": {
                            "type": "number"
                        }
                    }
                }
            ],
            "readings": [
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
                        "value": {
                            "type": "number"
                        }
                    }
                }
            ],
            "discarded": [
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
                        "value": {
                            "type": "number"
                        }
                    }
                }
            ],
            "unsent": [
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
                        "value": {
                            "type": "number"
                        }
                    }
                }
            ]
        }

    except Exception:
        message = _message_list["e000006"]

        _logger.exception(message)
        raise


def _in_memory_load_new_data(data_values, target_stream_id, information_to_send):
    """Extends in memory data structure reading data from the Storage Layer

    Args:
        data_values:          data to send - updated/used by reference
        target_stream_id:     OMF container ID
        information_to_send:  information retrieved from the Storage Layer that should be prepared for the PICROMF

    Raises:
        Exception: unable to extend the in memory structure with the data

    """

    try:
        row_id = information_to_send.id
        asset_code = information_to_send.key.strip().lower()
        timestamp = information_to_send.ts.isoformat()
        sensor_data = information_to_send.value

        _logger.debug("Stream ID : |{0}| Sensor ID : |{1}| Row ID : |{2}|  "
                      .format(target_stream_id, asset_code, str(row_id)))

        # Prepares the data for PICROMF
        new_data_values = [
            {
                "containerid": target_stream_id,
                "values": [
                    {
                        "Time": timestamp
                    }
                ]
            }
        ]

        new_data_values[0]["values"][0]["value"] = sensor_data

        # note : append produces an not properly constructed OMF message
        data_values.extend(new_data_values)

        _logger.debug("in memory info |{0}| ".format(new_data_values))

    except Exception:
        message = _message_list["e000010"]

        _logger.exception(message)
        raise


def _send_in_memory_data_to_picromf(message_type, omf_data):
    """Sends data to PICROMF - it retries the operation using a sleep time increased *2 for every retry

    it logs a WARNING only at the end of the retry mechanism

    Args:
        message_type: possible values - Type | Container | Data
        omf_data:     message to send

    Raises:
        PICROMFNotReadyError

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
                raise HTTPError400(response.text)

            _logger.debug("Response |{0}| message: |{1}| |{2}| ".format(message_type,
                                                                        response.status_code,
                                                                        response.text))

            break

        except Exception as ex:
            message = _message_list["e000007"], str(ex)
            status = 1

            time.sleep(sleep_time)
            num_retry += 1
            sleep_time *= 2

    if status != 0:
        _logger.error(message)
        raise PICROMFNotReadyError(message)


def _position_read():
    """Retrieves the starting point for the send operation

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


def _position_update(new_position):
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


def _omf_types_creation():
    """Creates the types into OMF

    """

    global _sensor_types

    try:
        for sensor_type in _sensor_types:
            tmp_type_sensor_id = "type_sensor_id_" + _type_id + "_" + sensor_type
            tmp_type_measurement_id = "type_measurement_" + _type_id + "_" + sensor_type

            omf_type = _OMF_types_definition[sensor_type]
            omf_type[0]["id"] = tmp_type_sensor_id
            omf_type[1]["id"] = tmp_type_measurement_id

            _send_in_memory_data_to_picromf("Type", omf_type)

    except Exception:
        message = _message_list["e000011"]

        _logger.exception(message)
        raise


def _omf_objects_creation():
    """Sends to PICROMF the request for the creation of all the objects

    Raises:
        Exception: an error occurred during the OMF's objects creation.

    """

    global _sensor_location

    try:
        for sensor_info in _sensor_name_type:

            tmp_sensor_id = sensor_info
            tmp_measurement_id = "measurement_" + tmp_sensor_id

            tmp_type = _sensor_name_type[tmp_sensor_id]

            tmp_type_sensor_id = "type_sensor_id_" + _type_id + "_" + tmp_type
            tmp_type_measurement_id = "type_measurement_" + _type_id + "_" + tmp_type

            _logger.debug("OMF_object_creation ")
            _omf_object_creation(tmp_sensor_id, tmp_measurement_id, tmp_type_sensor_id, tmp_type_measurement_id)

    except Exception:
        message = _message_list["e000008"]

        _logger.exception(message)
        raise


def _omf_object_creation(tmp_sensor_id, tmp_measurement_id, tmp_type_sensor_id, tmp_type_measurement_id):
    """Sends to PICROMF the request for the creation of an object

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

        _send_in_memory_data_to_picromf("Container", containers)
        _send_in_memory_data_to_picromf("Data", static_data)
        _send_in_memory_data_to_picromf("Data", link_data)

    except Exception:
        message = _message_list["e000008"]

        _logger.exception(message)
        raise


async def _send_data_to_picromf():
    """Reads data from the Storage Layer sends them PICROMF

    Raises:
        Exception: cannot complete the sending operation

    Todo:
        it should evolve using the DB layer

    """

    global _pg_conn
    global _pg_cur

    data_to_send = []

    try:
        # Reads the position from which the data should be send
        _pg_conn = psycopg2.connect(_DB_URL)
        _pg_cur = _pg_conn.cursor()
        position = _position_read()
        _logger.debug("Last position, already sent |{0}| ".format(str(position)))

        data_available, new_position = await _in_memory_data_load(position, data_to_send)

        if data_available:
            _logger.debug("{0}".format("omf_translator_perf - OMF START "))
            _send_in_memory_data_to_picromf("Data", data_to_send)
            _logger.debug("{0}".format("omf_translator_perf - OMF END "))

            _position_update(new_position)

    except Exception:
        message = _message_list["e000004"]

        _logger.exception(message)
        raise


async def _in_memory_data_load(position, values):
    """Extracts data from the DB Layer loading in memory

    Raises:
        Exception: cannot complete loading data in memory

    Todo:
        it should evolve using the DB layer

    """

    global _num_sent
    global _num_unsent

    new_position = 0
    data_available = False

    try:
        async with aiopg.sa.create_engine(_DB_URL) as engine:
            async with engine.acquire() as conn:

                    _logger.debug("{0}".format("omf_translator_perf - DB read START "))

                    # Reads rows from the Storage layer and sends them to the PICROMF
                    async for db_row in conn.execute(_statistics_history_tbl.select()
                                                     .where(_statistics_history_tbl.c.id > position)
                                                     .order_by(_statistics_history_tbl.c.id).limit(_block_size)):

                        message = "### sensor information ##################################################"
                        _logger.debug("{0}".format(message))

                        # Identification of the object/sensor
                        sensor_id = db_row.key
                        sensor_id = sensor_id.strip().lower()
                        measurement_id = "measurement_" + sensor_id

                        tmp_type = ""
                        try:
                            # Evaluates if it is a known types
                            tmp_type = _sensor_name_type[sensor_id]

                        except Exception as ex:
                            message = _message_list["e000012"].format(tmp_type, ex)

                            _logger.warning(message)
                        else:
                            _logger.debug("db row |{0}| |{1}| |{2}| ".format(db_row.key,
                                                                             db_row.value,
                                                                             db_row.ts))

                            try:
                                _in_memory_load_new_data(values, measurement_id, db_row)

                                # Used for the statistics update
                                _num_sent += 1

                                # Latest position reached
                                new_position = db_row.id

                                data_available = True

                            except Exception as ex:
                                _num_unsent += 1

                                message = _message_list["e000013"], str(ex)
                                _logger.warning(message)

                    message = "### completed ##################################################"
                    _logger.debug("{0}".format(message))

                    _logger.debug("{0}".format("omf_translator_perf - DB read END "))

    except Exception:
        message = _message_list["e000017"]

        _logger.exception(message)
        raise

    return data_available,  new_position


def _send_init():
    """Setup the correct state to being able to send data to the PICROMF

    Raises :
        Exception - cannot complete the initialization
    """

    try:
        _logger.debug("{0}".format("statistics_to_pi_perf - INIT START "))

        prg_text = ", for Linux (x86_64)"

        start_message = "" + _module_name + "" + prg_text + " " + __copyright__ + " "
        _logger.info("{0}".format(start_message))
        _logger.info(_message_list["i000002"])

        initialize_plugin()

        _omf_types_creation()
        _omf_objects_creation()

        _logger.debug("{0}".format("statistics_to_pi_perf - INIT END "))

    except Exception:
        message = _message_list["e000018"]

        _logger.exception(message)
        raise


if __name__ == "__main__":

    try:

        _logger = logger.setup(__name__)
        _event_loop = asyncio.get_event_loop()

        _logger.debug("{0}".format("statistics_to_pi_perf - START "))

        _send_init()

        _event_loop.run_until_complete(_send_data_to_picromf())

        _logger.info(_message_list["i000003"])

    except Exception as e:
        tmp_message = _message_list["e000004"], str(e)

        _logger.exception(tmp_message)

    _logger.debug("{0}".format("statistics_to_pi_perf - END "))
