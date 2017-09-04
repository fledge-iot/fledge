#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" The OMF translator is a plugin output formatter for the FogLAMP appliance.
It is loaded by the send process (see The FogLAMP Sending Process) and runs in the context of the send process,
to send the reading data to a PI Server (or Connector) using the OSIsoft OMF format.

IMPORTANT NOTE : This current version is an empty skeleton.

.. _send_data::

"""

import copy
import ast
import resource
import datetime
import sys
import asyncio
import time
import json
import requests
import logging
import psycopg2

from foglamp import logger, configuration_manager

# Module information
__author__ = "${FULL_NAME}"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_MODULE_NAME = "OMF Translator"

# Defines what and the level of details for logging
_log_debug_level = 0
_log_performance = False

# DB references
_DB_CONNECTION_STRING = 'postgresql:///foglamp'
_pg_conn = ()
_pg_cur = ()

_MESSAGES_LIST = {

    # Information messages
    "i000001": " ",
    "i000002": "Started.",
    "i000003": "Execution completed.",

    # Warning / Error messages
    "e000001": "cannot complete the operation.",
    "e000002": "cannot retrieve the starting point for sending operation.",
    "e000003": "cannot update the reached position.",
    "e000004": "cannot complete the sending operation.",
    "e000005": "cannot setup the logger - error details |{0}|",

    "e000006": "cannot initialize the plugin.",
    "e000007": "an error occurred during the OMF request - error details |{0}|",
    "e000008": "an error occurred during the OMF's objects creation.",
    "e000009": "cannot retrieve information about the sensor.",
    "e000010": "unable to extend the in memory structure with new data.",
    "e000011": "cannot create the OMF types.",
    "e000012": "unknown asset_code - asset |{0}| - error details |{1}|",
    "e000013": "cannot prepare sensor information for PICROMF - error details |{0}|",
    "e000014": "",

    "e000015": "cannot update statistics.",
    "e000016": "",
    "e000017": "cannot complete loading data into the memory.",
    "e000018": "cannot complete the initialization.",
    "e000019": "cannot complete the preparation of the in memory structure.",
    "e000020": "cannot complete the retrieval of the plugin information.",
    "e000021": "cannot complete the termination of the OMF translator.",

}
"""Messages used for Information, Warning and Error notice"""

# Configuration related to the OMF Translator
_CONFIG_CATEGORY_NAME = 'OMF_TR'
_CONFIG_CATEGORY_DESCRIPTION = 'Configuration of OMF Translator plugin'

_DEFAULT_OMF_CONFIG = {
    "URL": {
        "description": "The URL of the PI Connector to send data to",
        "type": "string",
        "default": "http://WIN-4M7ODKB0RH2:8118/ingress/messages"
    },
    "producerToken": {
        "description": "The producer token that represents this FogLAMP stream",
        "type": "string",
        "default": "omf_translator_739"

    },
    "OMFMaxRetry": {
        "description": "Max number of retries for the communication with the OMF PI Connector Relay",
        "type": "integer",
        "default": "2"

    },
    "OMFRetrySleepTime": {
        "description": "Seconds between each retry for the communication with the OMF PI Connector Relay",
        "type": "integer",
        "default": "1"

    },
    "OMFHttpTimeout": {
        "description": "Timeout in seconds for the HTTP operations with the OMF PI Connector Relay",
        "type": "integer",
        "default": "30"

    },
    "StaticData": {
        "description": "Static data to include in each sensor reading sent to OMF.",
        # FIXME:
        # "type": "JSON",
        "type": "string",
        "default": json.dumps(
            {
                "Location": "Palo Alto",
                "Company": "Dianomic"

            }
        )
    }

}


# Configuration related to the OMF Types
_CONFIG_CATEGORY_OMF_TYPES_NAME = 'OMF_TYPES'
_CONFIG_CATEGORY_OMF_TYPES_DESCRIPTION = 'Configuration of OMF types'

_DEFAULT_OMF_TYPES_CONFIG = {
    "type-id": {
        "description": "TBD",
        "type": "integer",
        "default": "739"
    },

    "mouse": {
        "description": "TBD",
        # FIXME:
        # "type": "JSON",
        "type": "string",
        "default": json.dumps(
            {
                "typename": "mouse",
                "static": {
                    "Name": {
                        "type": "string",
                        "isindex": True
                    },
                    "Location": {
                        "type": "string"
                    },
                    "Company": {
                        "type": "string"
                    },
                },
                "dynamic": {
                    "Time": {
                        "type": "string",
                        "format": "date-time",
                        "isindex": True
                    },
                    "button": {
                        "type": "string"
                    }
                }
            }
        )
    },
    "TI sensorTag/accelerometer": {
        "description": "TBD",
        # FIXME:
        "type": "string",
        "default": json.dumps(
            {
                "typename": "position",
                "static": {
                    "Name": {
                        "type": "string",
                        "isindex": True
                    },
                    "Location": {
                        "type": "string"
                    },
                    "Company": {
                        "type": "string"
                    },
                },
                "dynamic": {
                    "Time": {
                        "type": "string",
                        "format": "date-time",
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
        )
    },
}

 
# FIXME:
_DEFAULT_OMF_TYPES_CONFIG2 = {
    "type-id": {
        "description": "TBD",
        "type": "integer",
        "default": "739"
    },

    "wall clock": {
        "description": "wall clock",
        # FIXME:
        # "type": "JSON",
        "type": "string",
        "default": json.dumps(
            {
                "typename": "wall_clock",
                "static": {
                    "Name": {
                        "type": "string",
                        "isindex": True
                    },
                    "Location": {
                        "type": "string"
                    },
                    "Company": {
                        "type": "string"
                    },
                },
                "dynamic": {
                    "Time": {
                        "type": "string",
                        "format": "date-time",
                        "isindex": True
                    },
                    "tick": {
                        "type": "string"
                    }
                }
            }
        )
    },

    "mouse": {
        "description": "TBD",
        # FIXME:
        # "type": "JSON",
        "type": "string",
        "default": json.dumps(
            {
                "typename": "mouse",
                "static": {
                    "Name": {
                        "type": "string",
                        "isindex": True
                    },
                    "Location": {
                        "type": "string"
                    },
                    "Company": {
                        "type": "string"
                    },
                },
                "dynamic": {
                    "Time": {
                        "type": "string",
                        "format": "date-time",
                        "isindex": True
                    },
                    "button": {
                        "type": "string"
                    }
                }
            }
        )
    },
    "TI sensorTag/accelerometer": {
        "description": "TBD",
        # FIXME:
        "type": "string",
        "default": json.dumps(
            {
                "typename": "position",
                "static": {
                    "Name": {
                        "type": "string",
                        "isindex": True
                    },
                    "Location": {
                        "type": "string"
                    },
                    "Company": {
                        "type": "string"
                    },
                },
                "dynamic": {
                    "Time": {
                        "type": "string",
                        "format": "date-time",
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
        )
    },
    "TI sensorTag/gyroscope": {
        "description": "TBD",
        # FIXME:
        "type": "string",
        "default": json.dumps(
            {
                "typename": "position",
                "static": {
                    "Name": {
                        "type": "string",
                        "isindex": True
                    },
                    "Location": {
                        "type": "string"
                    },
                    "Company": {
                        "type": "string"
                    },
                },
                "dynamic": {
                    "Time": {
                        "type": "string",
                        "format": "date-time",
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
        )
    },
    "TI sensorTag/luxometer": {
        "description": "TBD",
        # FIXME:
        "type": "string",
        "default": json.dumps(
            {
                "typename": "luminosity",
                "static": {
                    "Name": {
                        "type": "string",
                        "isindex": True
                    },
                    "Location": {
                        "type": "string"
                    },
                    "Company": {
                        "type": "string"
                    },
                },
                "dynamic": {
                    "Time": {
                        "type": "string",
                        "format": "date-time",
                        "isindex": True
                    },
                    "lux": {
                        "type": "number"
                    }
                }
            }
        )
    },
}


_logger = ""

_event_loop = ""

# Configurations retrieved from the Configuration Manager
_config_omf_types = {}
_config_omf_types_from_manager = {}
_config = {
    'URL': _DEFAULT_OMF_CONFIG['URL']['default'],
    'producerToken': _DEFAULT_OMF_CONFIG['producerToken']['default'],
    'OMFMaxRetry': int(_DEFAULT_OMF_CONFIG['OMFMaxRetry']['default']),
    'OMFRetrySleepTime': _DEFAULT_OMF_CONFIG['OMFRetrySleepTime']['default'],
    'OMFHttpTimeout': int(_DEFAULT_OMF_CONFIG['OMFHttpTimeout']['default']),
    'StaticData':  ast.literal_eval(_DEFAULT_OMF_CONFIG['StaticData']['default'])
}
_config_from_manager = ""


_OMF_PREFIX_MEASUREMENT = "measurement_"
_OMF_SUFFIX_TYPENAME = "_typename"


_OMF_TEMPLATE_TYPE = {
    "typename": [
        {
            "id": "static-type-id",
            "type": "object",
            "classification": "static",
            "properties": {
            }
        },
        {
            "id": "dynamic-type-id",
            "type": "object",
            "classification": "dynamic",
            "properties": {
            }
        }
    ]
}

_OMF_TEMPLATE_CONTAINER = [
    {
        "id":  "xxx",
        "typeid":  "xxx"
    }
]

_OMF_TEMPLATE_STATIC_DATA = [
    {
        "typeid": "xxx",
        "values": [{
            "Name": "xxx"
        }]
    }
]

_OMF_TEMPLATE_LINK_DATA = [
    {
        "typeid": "__Link",
        "values": [{
            "source": {
                "typeid": "xxx",
                "index": "_ROOT"
            },
            "target": {
                "typeid": "xxx",
                "index": "xxx"
            }
        }, {
            "source": {
                "typeid": "xxx",
                "index": "xxx"
            },
            "target": {
                "containerid": "xxx"
            }

        }]
    }
]


class URLFetchError(RuntimeError):
    """ URLFetchError """
    pass


class PluginInitializeFailed(RuntimeError):
    """ PluginInitializeFailed """
    pass


def _performance_log(func):
    """ Logs information for performance measurement """

    # noinspection PyProtectedMember
    def wrapper(*arg):
        """ wrapper """

        start = datetime.datetime.now()

        # Code execution
        res = func(*arg)

        if _log_performance:
            usage = resource.getrusage(resource.RUSAGE_SELF)
            memory_process = (usage[2])/1000

            delta = datetime.datetime.now() - start
            delta_milliseconds = int(delta.total_seconds() * 1000)

            _logger.info("PERFORMANCE - {0} - milliseconds |{1:>8,}| - memory MB |{2:>8,}|"
                         .format(sys._getframe().f_locals['func'],
                                 delta_milliseconds,
                                 memory_process))

        return res

    return wrapper


def _configuration_retrieve(_stream_id):
    """ Retrieves the configuration from the Configuration Manager

    Returns:
    Raises:
    Todo:
    """

    global _config_from_manager
    global _config
    global _config_omf_types
    global _config_omf_types_from_manager

    _logger.debug("{0} - _configuration_retrieve".format(_MODULE_NAME))

    # Configuration related to the OMF Translator
    try:
        config_category_name = _CONFIG_CATEGORY_NAME + "_" + str(_stream_id)

        _event_loop.run_until_complete(configuration_manager.create_category(config_category_name, _DEFAULT_OMF_CONFIG,
                                                                             _CONFIG_CATEGORY_DESCRIPTION))
        _config_from_manager = _event_loop.run_until_complete(configuration_manager.get_category_all_items
                                                              (config_category_name))

        # Retrieves the configurations and apply the related conversions
        _config['URL'] = _config_from_manager['URL']['value']
        _config['producerToken'] = _config_from_manager['producerToken']['value']
        _config['OMFMaxRetry'] = int(_config_from_manager['OMFMaxRetry']['value'])
        _config['OMFRetrySleepTime'] = int(_config_from_manager['OMFRetrySleepTime']['value'])
        _config['OMFHttpTimeout'] = int(_config_from_manager['OMFHttpTimeout']['value'])

        _config['StaticData'] = ast.literal_eval(_config_from_manager['StaticData']['value'])

    except Exception:
        _message = _MESSAGES_LIST["e000003"]

        _logger.error(_message)
        raise

    # Configuration related to the OMF Types
    try:
        _event_loop.run_until_complete(configuration_manager.create_category(_CONFIG_CATEGORY_OMF_TYPES_NAME,
                                                                             _DEFAULT_OMF_TYPES_CONFIG,
                                                                             _CONFIG_CATEGORY_OMF_TYPES_DESCRIPTION))
        _config_omf_types_from_manager = _event_loop.run_until_complete(configuration_manager.get_category_all_items
                                                                        (_CONFIG_CATEGORY_OMF_TYPES_NAME))

        _config_omf_types = copy.deepcopy(_config_omf_types_from_manager)

        # Converts the value field from str to a dict
        for item in _config_omf_types:

            if _config_omf_types[item]['type'] == 'string':

                # The conversion from a dict to str changes the case and it should be fixed before the conversion
                value = _config_omf_types[item]['value'].replace("true", "True")

                new_value = ast.literal_eval(value)
                _config_omf_types[item]['value'] = new_value

    except Exception:
        _message = _MESSAGES_LIST["e000003"]

        _logger.error(_message)
        raise


def retrieve_plugin_info(_stream_id):
    """ Allows the device service to retrieve information from the plugin

    Returns:
        plugin_info
    Raises:
    Todo:
    """

    global _logger
    global _event_loop

    try:
        # note : _module_name is used as __name__ refers to the Sending Process
        if _log_debug_level == 0:
            _logger = logger.setup(_MODULE_NAME)

        elif _log_debug_level == 1:
            _logger = logger.setup(_MODULE_NAME, level=logging.INFO)

        elif _log_debug_level >= 2:
            _logger = logger.setup(_MODULE_NAME, level=logging.DEBUG)

    except Exception as e:
        _message = _MESSAGES_LIST["e000005"].format(str(e))
        _current_time = time.strftime("%Y-%m-%d %H:%M:%S:")

        print ("{0} - ERROR - {1}".format(_current_time, _message))

    try:
        _event_loop = asyncio.get_event_loop()

        _configuration_retrieve(_stream_id)

        plugin_info = {
            'name': "OMF Translator",
            'version': "1.0.0",
            'type': "translator",
            'interface': "1.0",
            'config': _config
        }

    except Exception:
        _message = _MESSAGES_LIST["e000020"]

        _logger.error(_message)
        raise

    return plugin_info


def plugin_init():
    """ Initializes the OMF plugin for the sending of blocks of readings to the PI Connector.

    Returns:
    Raises:
        PluginInitializeFailed
    Todo:
    """

    global _pg_conn
    global _pg_cur

    try:
        _logger.debug("plugin_init - URL {0}".format(_config['URL']))

        _pg_conn = psycopg2.connect(_DB_CONNECTION_STRING)
        _pg_cur = _pg_conn.cursor()

    except Exception:
        _message = _MESSAGES_LIST["e000006"]

        _logger.error(_message)
        raise PluginInitializeFailed


def plugin_shutdown():
    """ Terminates the OMF plugin

    Returns:
    Raises:
    Todo:
    """

    global _pg_conn

    try:
        _logger.debug("{0} - plugin_shutdown".format(_MODULE_NAME))

        _pg_conn.close()

    except Exception:
        _message = _MESSAGES_LIST["e000021"]

        _logger.error(_message)
        raise PluginInitializeFailed


def _retrieve_omf_types_already_created(configuration_key, type_id):
    """
     # FIXME:
     Args:
     Returns:
     Raises:
     Todo:
     """

    global _pg_cur

    sql_cmd = "SELECT asset_code FROM foglamp.omf_created_objects " \
              "WHERE configuration_key='{0}' and type_id={1}".format(configuration_key, type_id)

    _pg_cur.execute(sql_cmd)
    rows = _pg_cur.fetchall()

    return rows


def _is_omf_object_already_created(configuration_key, asset_code, type_id):
    """
     # FIXME:
     Args:
     Returns:
     Raises:
     Todo:
     """

    global _pg_cur

    object_already_created = False

    sql_cmd = "SELECT asset_code FROM foglamp.omf_created_objects " \
              "WHERE configuration_key='{0}' and asset_code='{1}' and type_id={2}".format(configuration_key,
                                                                                          asset_code,
                                                                                          type_id)

    _pg_cur.execute(sql_cmd)
    rows = _pg_cur.fetchall()

    if len(rows) >= 1:
        object_already_created = True

    return object_already_created


def _flag_created_omf_type(configuration_key, asset_code, type_id):
    """
     # FIXME:
     Args:
     Returns:
     Raises:
     Todo:
     """

    global _pg_cur
    global _pg_conn

    sql_cmd = "INSERT INTO foglamp.omf_created_objects  " \
              "(configuration_key, asset_code, type_id) " \
              "VALUES ('{0}', '{1}', {2})".format(configuration_key,
                                                  asset_code,
                                                  type_id)

    _pg_cur.execute(sql_cmd)
    _pg_conn.commit()


def _generate_omf_asset_id(asset_code):
    """
     # FIXME:
     Args:
     Returns:
     Raises:
     Todo:
     """

    asset_id = asset_code.replace(" ", "")
    return asset_id


def _generate_omf_measurement(asset_code):
    """
     # FIXME:
     Args:
     Returns:
     Raises:
     Todo:
     """

    asset_id = asset_code.replace(" ", "")
    return _OMF_PREFIX_MEASUREMENT + asset_id

 
def _generate_omf_typename_automatic(asset_code):
    """
     # FIXME:
     Args:
     Returns:
     Raises:
     Todo:
     """

    asset_id = asset_code.replace(" ", "")

    return asset_id + _OMF_SUFFIX_TYPENAME


def _evaluate_property_type(value):
    """
     # FIXME:
     Args:
     Returns:
     Raises:
     Todo:
     """

    try:
        float(value)

        try:
            # Evaluates if it is a int or a number
            if int(float(value)) == value:

                # Checks the case having .0 as 967.0
                int_str = str(int(float(value)))
                value_str = str(value)

                if int_str == value_str:
                    property_type = "integer"
                else:
                    property_type = "number"

            else:
                property_type = "number"

        except ValueError:
            property_type = "string"

    except ValueError:
        property_type = "string"

    return property_type


def _create_omf_objects_automatic(asset_info):
    """
     # FIXME:
     Args:
     Returns:
     Raises:
     Todo:
     """

    typename, omf_type = _create_omf_type_automatic(asset_info)
    _create_omf_object_links(asset_info["asset_code"], typename, omf_type)


def _create_omf_type_automatic(asset_info):
    """
     # FIXME:
     Args:
     Returns:
     Raises:
     Todo:
     """

    type_id = _config_omf_types["type-id"]["value"]

    sensor_id = _generate_omf_asset_id(asset_info["asset_code"])
    asset_data = asset_info["asset_data"]

    typename = _generate_omf_typename_automatic(sensor_id)

    new_tmp_dict = copy.deepcopy(_OMF_TEMPLATE_TYPE)
    omf_type = {typename: new_tmp_dict["typename"]}

    # Handles Static section
    # Generates elements evaluating the StaticData retrieved form the Configuration Manager
    omf_type[typename][0]["properties"]["Name"] = {
            "type": "string",
            "isindex": True
        }

    omf_type[typename][0]["id"] = type_id + "_" + typename + "_sensor"

    for item in _config['StaticData']:
        omf_type[typename][0]["properties"][item] = {"type": "string"}

    # Handles Dynamic section
    omf_type[typename][1]["properties"]["Time"] = {
          "type": "string",
          "format": "date-time",
          "isindex": True
        }
    omf_type[typename][1]["id"] = type_id + "_" + typename + "_measurement"

    for item in asset_data:
        item_type = _evaluate_property_type(asset_data[item])
        omf_type[typename][1]["properties"][item] = {"type": item_type}

    if _log_debug_level == 3:
        _logger.debug("_create_omf_type_automatic - sensor_id |{0}| - omf_type |{1}| ".format(sensor_id, str(omf_type)))

    _send_in_memory_data_to_picromf("Type", omf_type[typename])

    return typename, omf_type


def _create_omf_objects_configuration_based(asset_code, asset_code_omf_type):
    """
     # FIXME:
     Args:
     Returns:
     Raises:
     Todo:
     """

    typename, omf_type = _create_omf_type_configuration_based(asset_code_omf_type)
    _create_omf_object_links(asset_code, typename, omf_type)


def _create_omf_type_configuration_based(asset_code_omf_type):
    """
     # FIXME:
     Args:
     Returns:
     Raises:
     Todo:
     """

    type_id = _config_omf_types["type-id"]["value"]
    typename = asset_code_omf_type["typename"]

    new_tmp_dict = copy.deepcopy(_OMF_TEMPLATE_TYPE)
    omf_type = {typename: new_tmp_dict["typename"]}

    # Handles Static section
    omf_type[typename][0]["properties"] = asset_code_omf_type["static"]
    omf_type[typename][0]["id"] = type_id + "_" + typename + "_sensor"

    # Handles Dynamic section
    omf_type[typename][1]["properties"] = asset_code_omf_type["dynamic"]
    omf_type[typename][1]["id"] = type_id + "_" + typename + "_measurement"

    if _log_debug_level == 3:
        _logger.debug("_create_omf_type_configuration_based - omf_type |{0}| ".format(str(omf_type)))

    _send_in_memory_data_to_picromf("Type", omf_type[typename])

    return typename, omf_type


def _create_omf_object_links(asset_code, typename, omf_type):
    """
     # FIXME:
     Args:
     Returns:
     Raises:
     Todo:
     """

    sensor_id = _generate_omf_asset_id(asset_code)
    measurement_id = _generate_omf_measurement(sensor_id)

    type_sensor_id = omf_type[typename][0]["id"]
    type_measurement_id = omf_type[typename][1]["id"]

    # Handles containers
    containers = copy.deepcopy(_OMF_TEMPLATE_CONTAINER)
    containers[0]["id"] = measurement_id
    containers[0]["typeid"] = type_measurement_id

    # Handles static_data
    static_data = copy.deepcopy(_OMF_TEMPLATE_STATIC_DATA)
    static_data[0]["typeid"] = type_sensor_id
    static_data[0]["values"][0] = copy.deepcopy(_config['StaticData'])
    static_data[0]["values"][0]['Name'] = sensor_id

    # Handles link_data
    link_data = copy.deepcopy(_OMF_TEMPLATE_LINK_DATA)
    link_data[0]["values"][0]['source']['typeid'] = type_sensor_id
    link_data[0]["values"][0]['target']['typeid'] = type_sensor_id
    link_data[0]["values"][0]['target']['index'] = sensor_id

    link_data[0]["values"][1]['source']['typeid'] = type_sensor_id
    link_data[0]["values"][1]['source']['index'] = sensor_id
    link_data[0]["values"][1]['target']['containerid'] = measurement_id

    if _log_debug_level == 3:
        _logger.debug("_create_omf_object_links - asset_code |{0}| - containers |{1}| ".format(asset_code,
                                                                                               str(containers)))
        _logger.debug("_create_omf_object_links - asset_code |{0}| - static_data |{1}| ".format(asset_code,
                                                                                                str(static_data)))
        _logger.debug("_create_omf_object_links - asset_code |{0}| - link_data |{1}| ".format(asset_code,
                                                                                              str(link_data)))

    _send_in_memory_data_to_picromf("Container", containers)
    _send_in_memory_data_to_picromf("Data", static_data)
    _send_in_memory_data_to_picromf("Data", link_data)


@_performance_log
def _identify_unique_asset_codes(raw_data):
    """
    # FIXME:
    Args:
    Returns:
    Raises:
    Todo:
    """

    asset_code_to_evaluate = []

    for row in raw_data:
        asset_code = row[1]
        asset_data = row[3]

        # Evaluates if the asset_code is already in the list
        if not any(item["asset_code"] == asset_code for item in asset_code_to_evaluate):

            asset_code_to_evaluate.append(
                {
                    "asset_code": asset_code,
                    "asset_data": asset_data
                }
            )

    return asset_code_to_evaluate


@_performance_log
def _create_omf_objects(raw_data, stream_id):
    """
    # FIXME:
    Args:
    Returns:
    Raises:
    Todo:
    """

    config_category_name = _CONFIG_CATEGORY_NAME + "_" + str(stream_id)
    type_id = _config_omf_types['type-id']['value']

    asset_codes_to_evaluate = _identify_unique_asset_codes(raw_data)

    asset_codes_already_created = _retrieve_omf_types_already_created(config_category_name, type_id)

    for item in asset_codes_to_evaluate:

        asset_code = item["asset_code"]

        # Evaluates if it is a new OMF type
        if not any(tmp_item[0] == asset_code for tmp_item in asset_codes_already_created):

            asset_code_omf_type = ""

            try:
                asset_code_omf_type = copy.deepcopy(_config_omf_types[asset_code]["value"])
            except KeyError:
                configuration_based = False
            else:
                configuration_based = True

            if configuration_based:
                _logger.debug("creates type - configuration based - asset |{0}| ".format(asset_code))

                _create_omf_objects_configuration_based(asset_code, asset_code_omf_type)
            else:
                # handling - Automatic OMF Type Mapping
                _logger.debug("creates type - automatic handling - asset |{0}| ".format(asset_code))

                _create_omf_objects_automatic(item)

            _flag_created_omf_type(config_category_name, asset_code, type_id)
        else:
            _logger.debug("asset already created - asset |{0}| ".format(asset_code))


@_performance_log
def plugin_send(raw_data, stream_id):
    """ Translates and sends to the destination system the data provided by the Sending Process

    Returns:
        data_to_send

    Raises:
    Todo:
    """

    data_to_send = []
    data_sent = False

    try:
        data_available, new_position, num_sent = _transform_in_memory_data(data_to_send, raw_data)

        if data_available:
            _create_omf_objects(raw_data, stream_id)

            _send_in_memory_data_to_picromf("Data", data_to_send)
            data_sent = True

    except Exception:
        _message = _MESSAGES_LIST["e000004"]

        _logger.error(_message)
        raise

    return data_sent, new_position, num_sent


@_performance_log
def _send_in_memory_data_to_picromf(message_type, omf_data):
    """Sends data to PICROMF - it retries the operation using a sleep time increased *2 for every retry

    it logs a WARNING only at the end of the retry mechanism

    Args:
        message_type: possible values - Type | Container | Data
        omf_data:     _message to send

    Raises:
        Exception: an error occurred during the OMF request

    """

    sleep_time = _config['OMFRetrySleepTime']

    _message = ""
    _error = False

    num_retry = 1

    msg_header = {'producertoken': _config['producerToken'],
                  'messagetype': message_type,
                  'action': 'create',
                  'messageformat': 'JSON',
                  'omfversion': '1.0'}

    omf_data_json = json.dumps(omf_data)

    while num_retry < _config['OMFMaxRetry']:
        _error = False

        try:
            response = requests.post(_config['URL'],
                                     headers=msg_header,
                                     data=omf_data_json,
                                     verify=False,
                                     timeout=_config['OMFHttpTimeout'])
        except Exception as e:
            _message = _MESSAGES_LIST["e000007"].format(e)
            _error = Exception(_message)

        else:
            # Evaluate the HTTP status codes
            if not str(response.status_code).startswith('2'):

                tmp_text = str(response.status_code) + " " + response.text
                _message = _MESSAGES_LIST["e000007"].format(tmp_text)
                _error = URLFetchError(_message)

            _logger.debug("Message type |{0}| response: |{1}| |{2}| ".format(message_type,
                                                                             response.status_code,
                                                                             response.text))

        if _error:
            time.sleep(sleep_time)
            num_retry += 1
            sleep_time *= 2
        else:
            break

    if _error:
        _logger.warning(_message)
        raise _error


@_performance_log
def _transform_in_memory_data(data_to_send, raw_data):
    """Transforms in memory data into a new structure that could be converted into JSON for PICROMF

    Raises:
        Exception: cannot complete the preparation of the in memory structure.

    """

    new_position = 0
    data_available = False

    # statistics
    num_sent = 0

    # internal statistic - rows that generate errors in the preparation process, before sending them to OMF
    num_unsent = 0

    try:
        for row in raw_data:

            row_id = row[0]
            asset_code = row[1]

            # Identification of the object/sensor
            measurement_id = _generate_omf_measurement(asset_code)
            
            try:
                _transform_in_memory_row(data_to_send, row, measurement_id)

                # Used for the statistics update
                num_sent += 1

                # Latest position reached
                new_position = row_id

                data_available = True

            except Exception as e:
                num_unsent += 1

                _message = _MESSAGES_LIST["e000013"].format(e)
                _logger.warning(_message)

    except Exception:
        _message = _MESSAGES_LIST["e000019"]

        _logger.error(_message)
        raise

    return data_available, new_position, num_sent


def _transform_in_memory_row(data_to_send, row, target_stream_id):
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

        if _log_debug_level == 3:
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

            if _log_debug_level == 3:
                _logger.debug("in memory info |{0}| ".format(new_data))

        else:
            _message = _MESSAGES_LIST["e000009"]
            _logger.warning(_message)

    except Exception:
        _message = _MESSAGES_LIST["e000010"]

        _logger.error(_message)
        raise


if __name__ == "__main__":
    try:
        # note : _module_name is used as __name__ refers to the Sending Process
        _logger = logger.setup(_MODULE_NAME)

    except Exception as ex:
        message = _MESSAGES_LIST["e000005"].format(str(ex))
        current_time = time.strftime("%Y-%m-%d %H:%M:%S:")

        print ("{0} - ERROR - {1}".format(current_time, message))

    try:
        _event_loop = asyncio.get_event_loop()

    except Exception as ex:
        message = _MESSAGES_LIST["e000006"].format(str(ex))

        _logger.error(message)
        raise
