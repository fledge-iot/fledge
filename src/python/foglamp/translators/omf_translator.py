#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" The OMF translator is a plugin output formatter for the FogLAMP appliance.
It is loaded by the send process (see The FogLAMP Sending Process) and runs in the context of the send process,
to send the reading data to a PI Server (or Connector) using the OSIsoft OMF format.

PICROMF = PI Connector Relay OMF

"""

import copy
import ast
import resource
import datetime
import asyncio
import time
import json
import requests
import logging

from foglamp import logger, configuration_manager
from foglamp.storage.storage import Storage

import foglamp.storage.payload_builder as payload_builder

# Module information
__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_MODULE_NAME = "omf_translator"

_storage = ()

# Messages used for Information, Warning and Error notice
_MESSAGES_LIST = {

    # Information messages
    "i000001": " ",

    # Warning / Error messages
    "e000001": "cannot initialize the plugin - error details |{0}|",
    "e000002": "cannot complete the preparation of the in memory structure.",
    "e000003": "cannot update the reached position.",
    "e000004": "cannot complete the sending operation - error details |{0}|",
    "e000005": "cannot start the logger - error details |{0}|",
    "e000006": "cannot prepare sensor information for PICROMF - error details |{0}|",
    "e000007": "an error occurred during the OMF request - error details |{0}|",
    "e000008": "cannot complete the retrieval of the plugin information - error details |{0}|",
    "e000009": "cannot retrieve information about the sensor.",
    "e000010": "unable to extend the memory structure with new data.",
    "e000011": "cannot complete the termination of the OMF translator - error details |{0}|",

}

# Configuration related to the OMF Translator
_CONFIG_CATEGORY_NAME = 'OMF_TR'
_CONFIG_CATEGORY_DESCRIPTION = 'Configuration of OMF Translator plugin'

_CONFIG_DEFAULT_OMF = {
    "URL": {
        "description": "The URL of the PI Connector to send data to",
        "type": "string",
        "default": "http://WIN-4M7ODKB0RH2:8118/ingress/messages"
    },
    "producerToken": {
        "description": "The producer token that represents this FogLAMP stream",
        "type": "string",
        "default": "omf_translator_0001"

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
    "OMFHttpTimeout": {
        "description": "Timeout in seconds for the HTTP operations with the OMF PI Connector Relay",
        "type": "integer",
        "default": "30"

    },
    "StaticData": {
        "description": "Static data to include in each sensor reading sent to OMF.",
        "type": "JSON",
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

_CONFIG_DEFAULT_OMF_TYPES = {
    "type-id": {
        "description": "Identify sensor and measurement types",
        "type": "integer",
        "default": "0001"
    },
}

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

# Defines what and the level of details for logging
_log_debug_level = 0
_log_performance = False

_logger = ""

_event_loop = ""

# Configurations retrieved from the Configuration Manager
_config_omf_types = {}
_config_omf_types_from_manager = {}
_config = {}
_config_from_manager = {}

# Forces the recreation of PIServer objects when the first error occurs
_recreate_omf_objects = True


class URLFetchError(RuntimeError):
    """ URLFetchError """
    pass


class PluginInitializeFailed(RuntimeError):
    """ PluginInitializeFailed """
    pass


def _performance_log(func):
    """ Logs information for performance measurement """

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
                         .format(func.__name__,
                                 delta_milliseconds,
                                 memory_process))

        return res

    return wrapper


def _retrieve_configuration(stream_id):
    """ Retrieves the configuration from the Configuration Manager

    Returns:
    Raises:
    Todo:
    """

    global _config_from_manager
    global _config
    global _config_omf_types
    global _config_omf_types_from_manager

    _logger.debug("{0} - ".format("_retrieve_configuration"))

    # Configuration related to the OMF Translator
    try:
        config_category_name = _CONFIG_CATEGORY_NAME + "_" + str(stream_id)

        _event_loop.run_until_complete(configuration_manager.create_category(config_category_name, _CONFIG_DEFAULT_OMF,
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
                                                                             _CONFIG_DEFAULT_OMF_TYPES,
                                                                             _CONFIG_CATEGORY_OMF_TYPES_DESCRIPTION))
        _config_omf_types_from_manager = _event_loop.run_until_complete(configuration_manager.get_category_all_items
                                                                        (_CONFIG_CATEGORY_OMF_TYPES_NAME))

        _config_omf_types = copy.deepcopy(_config_omf_types_from_manager)

        # Converts the value field from str to a dict
        for item in _config_omf_types:

            if _config_omf_types[item]['type'] == 'JSON':

                # The conversion from a dict to str changes the case and it should be fixed before the conversion
                value = _config_omf_types[item]['value'].replace("true", "True")

                new_value = ast.literal_eval(value)
                _config_omf_types[item]['value'] = new_value

    except Exception:
        _message = _MESSAGES_LIST["e000003"]

        _logger.error(_message)
        raise


def plugin_retrieve_info(stream_id):
    """ Allows the device service to retrieve information from the plugin

    Args:
        stream_id
    Returns:
        plugin_info: information that described the plugin
    Raises:
    Todo:
    """

    global _logger
    global _event_loop

    try:
        # note : _module_name is used as __name__ refers to the Sending Process
        logger_name = _MODULE_NAME + "_" + str(stream_id)

        if _log_debug_level == 0:
            _logger = logger.setup(logger_name)

        elif _log_debug_level == 1:
            _logger = logger.setup(logger_name, level=logging.INFO)

        elif _log_debug_level >= 2:
            # noinspection PyArgumentEqualDefault
            _logger = logger.setup(logger_name, level=logging.DEBUG)

    except Exception as ex:
        _message = _MESSAGES_LIST["e000005"].format(str(ex))
        _current_time = time.strftime("%Y-%m-%d %H:%M:%S:")

        print ("{0} - ERROR - {1}".format(_current_time, _message))

        raise ex

    _logger.debug("{0} - ".format("plugin_retrieve_info"))

    try:
        _event_loop = asyncio.get_event_loop()

        _retrieve_configuration(stream_id)

        plugin_info = {
            'name': "OMF Translator",
            'version': "1.0.0",
            'type': "translator",
            'interface': "1.0",
            'config': _config
        }

    except Exception as ex:
        _message = _MESSAGES_LIST["e000008"].format(ex)

        _logger.error(_message)
        raise

    return plugin_info


def plugin_init():
    """ Initializes the OMF plugin for the sending of blocks of readings to the PI Connector.

    Args:
    Returns:
    Raises:
        PluginInitializeFailed
    Todo:
    """

    global _recreate_omf_objects

    _logger.debug("{0} - URL {1}".format("plugin_init", _config['URL']))

    try:

        _recreate_omf_objects = True

    except Exception as ex:
        _message = _MESSAGES_LIST["e000001"].format(ex)

        _logger.error(_message)
        raise PluginInitializeFailed(ex)


@_performance_log
def plugin_send(raw_data, stream_id):
    """ Translates and sends to the destination system the data provided by the Sending Process

    Args:
        raw_data  : Data to send as retrieved from the storage layer
        stream_id

    Returns:
        data_to_send : True, data successfully sent to the destination system
        new_position : Last row_id already sent
        num_sent     : Number of rows sent, used for the update of the statistics
    Raises:
    Todo:
    """

    global _recreate_omf_objects

    data_to_send = []
    data_sent = False

    config_category_name = _CONFIG_CATEGORY_NAME + "_" + str(stream_id)
    type_id = _config_omf_types['type-id']['value']

    try:
        data_available, new_position, num_sent = _transform_in_memory_data(data_to_send, raw_data)

        if data_available:
            _create_omf_objects(raw_data, config_category_name, type_id)

            try:
                _send_in_memory_data_to_picromf("Data", data_to_send)

            except Exception as ex:
                # Forces the recreation of PIServer's objects on the first error occurred
                if _recreate_omf_objects:

                    _logger.debug("{0} - Forces objects recreation ".format("plugin_send"))

                    _deleted_omf_types_already_created(config_category_name, type_id)
                    _recreate_omf_objects = False

                raise ex
            else:
                data_sent = True

    except Exception as ex:
        _message = _MESSAGES_LIST["e000004"].format(ex)

        _logger.exception(_message)
        raise

    return data_sent, new_position, num_sent


def plugin_shutdown():
    """ Terminates the plugin

    Returns:
    Raises:
    Todo:
    """

    try:
        _logger.debug("{0} - plugin_shutdown".format(_MODULE_NAME))

    except Exception as ex:
        _message = _MESSAGES_LIST["e000011"].format(ex)

        _logger.error(_message)
        raise


def _deleted_omf_types_already_created(config_category_name, type_id):
    """ Deletes OMF types/objects tracked as already created, it is used to force the recreation of the types

     Args:
        config_category_name: used to identify OMF objects already created
        type_id:              used to identify OMF objects already created

     Returns:
     Raises:
     Todo:
     """

    payload = payload_builder.PayloadBuilder() \
        .WHERE(['configuration_key', '=', config_category_name]) \
        .AND_WHERE(['type_id', '=', type_id]) \
        .payload()

    _storage.delete_from_tbl("omf_created_objects", payload)


def _retrieve_omf_types_already_created(configuration_key, type_id):
    """ Retrieves the list of OMF types already defined/sent to the PICROMF

     Args:
         configuration_key - part of the key to identify the type
         type_id           - part of the key to identify the type
     Returns:
        List of Asset code already defined into the PI Server
     Raises:
     Todo:
     """

    payload = payload_builder.PayloadBuilder() \
        .WHERE(['configuration_key', '=', configuration_key]) \
        .AND_WHERE(['type_id', '=', type_id]) \
        .payload()

    omf_created_objects = _storage.query_tbl_with_payload('omf_created_objects', payload)

    _logger.debug("{func} - omf_created_objects {item} ".format(
                                                                func="_retrieve_omf_types_already_created",
                                                                item=omf_created_objects))

    # Extracts only the asset_code column
    rows = []
    for row in omf_created_objects['rows']:
        rows.append(row['asset_code'])

    return rows


def _flag_created_omf_type(configuration_key, type_id, asset_code):
    """ Stores into the Storage layer the successfully creation of the type into PICROMF.
     Args:
         configuration_key - part of the key to identify the type
         type_id           - part of the key to identify the type
         asset_code        - asset code defined into PICROMF
     Returns:
     Raises:
     Todo:
     """

    payload = payload_builder.PayloadBuilder()\
        .INSERT(configuration_key=configuration_key,
                asset_code=asset_code,
                type_id=type_id)\
        .payload()

    _storage.insert_into_tbl("omf_created_objects", payload)


def _generate_omf_asset_id(asset_code):
    """ Generates an asset id usable by AF/PI Server from an asset code stored into the Storage layer

     Args:
         asset_code : Asset code stored into the Storage layer
     Returns:
        Asset id usable by AF/PI Server
     Raises:
     Todo:
     """

    asset_id = asset_code.replace(" ", "")
    return asset_id


def _generate_omf_measurement(asset_code):
    """ Generates the measurement id associated to an asset code

     Args:
         asset_code :  Asset code retrieved from the Storage layer
     Returns:
        Measurement id associated to the specific asset code
     Raises:
     Todo:
     """

    asset_id = asset_code.replace(" ", "")
    return _OMF_PREFIX_MEASUREMENT + asset_id

 
def _generate_omf_typename_automatic(asset_code):
    """ Generates the typename associated to an asset code for the automated generation of the OMF types

     Args:
         asset_code :  Asset code retrieved from the Storage layer
     Returns:
        typename associated to the specific asset code

     Raises:
     Todo:
     """

    asset_id = asset_code.replace(" ", "")

    return asset_id + _OMF_SUFFIX_TYPENAME


def _evaluate_property_type(value):
    """ Evaluates the type of the property in relation to its value

     Args:
        value : value of the property
     Returns:
         Evaluated type {integer,number,string}
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
    """ Handles the Automatic OMF Type Mapping

     Args:
         asset_info : Asset's information as retrieved from the Storage layer,
                      having also a sample value for the asset
     Returns:
         response_status_code: http response code related to the PICROMF request
     Raises:
     Todo:
     """

    typename, omf_type = _create_omf_type_automatic(asset_info)
    _create_omf_object_links(asset_info["asset_code"], typename, omf_type)


def _create_omf_type_automatic(asset_info):
    """ Automatic OMF Type Mapping - Handles the OMF type creation

     Args:
         asset_info : Asset's information as retrieved from the Storage layer,
                      having also a sample value for the asset

     Returns:
         typename : typename associate to the asset
         omf_type : describe the OMF type as a python dict
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
    """ Handles the Configuration Based OMF Type Mapping

     Args:
        asset_code
        asset_code_omf_type : describe the OMF type as a python dict
     Returns:
     Raises:
     Todo:
     """

    typename, omf_type = _create_omf_type_configuration_based(asset_code_omf_type)
    _create_omf_object_links(asset_code, typename, omf_type)


def _create_omf_type_configuration_based(asset_code_omf_type):
    """ Configuration Based OMF Type Mapping - Handles the OMF type creation

     Args:
        asset_code_omf_type : describe the OMF type as a python dict

     Returns:
         typename : typename associate to the asset
         omf_type : describe the OMF type as a python dict
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
    """ Handles the creation of the links between the OMF objects :
        sensor, its measurement, sensor type and measurement type

     Args:
        asset_code
        typename : name/id of the type
        omf_type : describe the OMF type as a python dict
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

    return


@_performance_log
def _identify_unique_asset_codes(raw_data):
    """ Identify unique asset codes in the data block

    Args:
        raw_data : data block retrieved from the Storage layer that should be handled/sent
    Returns:
        asset_code_to_evaluate : list of unique codes

    Raises:
    Todo:
    """

    asset_code_to_evaluate = []

    for row in raw_data:
        asset_code = row['asset_code']
        asset_data = row['reading']

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
def _create_omf_objects(raw_data, config_category_name, type_id):
    """ Handles the creation of the OMF types related to the asset codes using one of the 2 possible ways :
            Automatic OMF Type Mapping
            Configuration Based OMF Type Mapping

    Args:
        raw_data :            data block to manage as retrieved from the Storage layer
        config_category_name: used to identify OMF objects already created
        type_id:              used to identify OMF objects already created
    Returns:
    Raises:
    Todo:
    """

    asset_codes_to_evaluate = _identify_unique_asset_codes(raw_data)

    asset_codes_already_created = _retrieve_omf_types_already_created(config_category_name, type_id)

    for item in asset_codes_to_evaluate:

        asset_code = item["asset_code"]

        # Evaluates if it is a new OMF type
        if not any(tmp_item == asset_code for tmp_item in asset_codes_already_created):

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

            _flag_created_omf_type(config_category_name, type_id, asset_code)

        else:
            _logger.debug("asset already created - asset |{0}| ".format(asset_code))


@_performance_log
def _send_in_memory_data_to_picromf(message_type, omf_data):
    """ Sends data to PICROMF - it retries the operation using a sleep time increased *2 for every retry
        it logs a WARNING only at the end of the retry mechanism in case of a communication error

    Args:
        message_type: possible values {Type, Container, Data}
        omf_data:     OMF message to send

    Returns:
    Raises:
        Exception: an error occurred during the OMF request
        URLFetchError: in case of http response code different from 2xx

    Todo:
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

    if _log_debug_level == 3:
        _logger.debug("OMF message : |{0}| |{1}| " .format(message_type, omf_data_json))

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

            _logger.debug("message type |{0}| response: |{1}| |{2}| ".format(message_type,
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
    """ Transforms the in memory data into a new structure that could be converted into JSON for the PICROMF

    Args:
    Returns:
    Raises:
    Todo:

    """

    new_position = 0
    data_available = False

    # statistics
    num_sent = 0

    # internal statistic - rows that generate errors in the preparation process, before sending them to OMF
    num_unsent = 0

    try:
        for row in raw_data:

            row_id = row['id']
            asset_code = row['asset_code']

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

                _message = _MESSAGES_LIST["e000006"].format(e)
                _logger.warning(_message)

    except Exception:
        _message = _MESSAGES_LIST["e000002"]

        _logger.error(_message)
        raise

    return data_available, new_position, num_sent


def _transform_in_memory_row(data_to_send, row, target_stream_id):
    """ Extends the in memory structure using data retrieved from the Storage Layer

    Args:
        data_to_send:      data block to send - updated/used by reference
        row:               information retrieved from the Storage Layer that it is used to extend data_to_send
        target_stream_id:  OMF container ID

    Returns:
    Raises:
    Todo:

    """

    data_available = False

    try:
        row_id = row['id']
        asset_code = row['asset_code']
        timestamp = row['user_ts']
        sensor_data = row['reading']

        if _log_debug_level == 3:
            _logger.debug("stream ID : |{0}| sensor ID : |{1}| row ID : |{2}|  "
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
            # note : append produces a not properly constructed OMF message
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

    # Used to assign the proper objects type without actually executing them
    _storage = Storage()
    _logger = logger.setup(_MODULE_NAME)
    _event_loop = asyncio.get_event_loop()
