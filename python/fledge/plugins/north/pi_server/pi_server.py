# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" The OMF North is a plugin output formatter for the Fledge appliance.
It is loaded by the send process (see The Fledge Sending Process) and runs in the context of the send process,
to send the reading data to a PI Server (or Connector) using the OSIsoft OMF format.
PICROMF = PI Connector Relay OMF"""

import aiohttp
import asyncio
import gzip
import sys
import copy
import ast
import resource
import datetime
import time
import json
import logging
import fledge.plugins.north.common.common as plugin_common
import fledge.plugins.north.common.exceptions as plugin_exceptions
from fledge.common import logger
from fledge.common.storage_client import payload_builder

# Module information
__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


# LOG configuration
_LOG_LEVEL_DEBUG = 10
_LOG_LEVEL_INFO = 20
_LOG_LEVEL_WARNING = 30

_LOGGER_LEVEL = _LOG_LEVEL_WARNING
_LOGGER_DESTINATION = logger.SYSLOG
_logger = None

_MODULE_NAME = "pi_server_north"

# Messages used for Information, Warning and Error notice
MESSAGES_LIST = {

    # Information messages
    "i000000": "information.",

    # Warning / Error messages
    "e000000": "general error.",

    "e000001": "the producerToken must be defined, use the Fledge API to set a proper value.",
    "e000002": "the producerToken cannot be an empty string, use the Fledge API to set a proper value.",

    "e000010": "the type-id must be defined, use the Fledge API to set a proper value.",
    "e000011": "the type-id cannot be an empty string, use the Fledge API to set a proper value.",

}


# Defines what and the level of details for logging
_log_debug_level = 0
_log_performance = False
_stream_id = None

# Configurations retrieved from the Configuration Manager
_config_omf_types = {}
_config = {}

# Forces the recreation of PIServer objects when the first error occurs
_recreate_omf_objects = True

# Messages used for Information, Warning and Error notice
_MESSAGES_LIST = {
    # Information messages
    "i000000": "information.",
    # Warning / Error messages
    "e000000": "general error.",
}
# Configuration related to the OMF North
_CONFIG_CATEGORY_DESCRIPTION = 'PI Server North Plugin'
_CONFIG_DEFAULT_OMF = {
    'plugin': {
        'description': 'PI Server North Plugin',
        'type': 'string',
        'default': 'pi_server',
        'readonly': 'true'
    },
    "URL": {
        "description": "URL of PI Connector to send data to",
        "type": "string",
        "default": "https://pi-server:5460/ingress/messages",
        "order": "1",
        "displayName": "URL"
    },
    "producerToken": {
        "description": "Producer token for this Fledge stream",
        "type": "string",
        "default": "pi_server_north_0001",
        "order": "2",
        "displayName": "Producer Token"
    },
    "source": {
        "description": "Source of data to be sent on the stream. May be either readings or statistics.",
        "type": "enumeration",
        "default": "readings",
        "options": ["readings", "statistics"],
        "order": "3",
        "displayName": "Data Source"
    },
    "compression": {
        "description": "Compress message body",
        "type": "boolean",
        "default": "true",
        "displayName": "Compression"
    },
    "StaticData": {
        "description": "Static data to include in each sensor reading sent via OMF",
        "type": "JSON",
        "default": json.dumps(
            {
                "Location": "Palo Alto",
                "Company": "Dianomic"
            }
        ),
        "order": "4",
        "displayName": "Static Data"
    },
    "applyFilter": {
        "description": "Should filter be applied before processing the data?",
        "type": "boolean",
        "default": "False",
        "order": "5",
        "displayName": "Apply Filter"
    },
    "filterRule": {
        "description": "JQ formatted filter to apply (only applicable if applyFilter is True)",
        "type": "string",
        "default": ".[]",
        "order": "6",
        "displayName": "Filter Rule",
        "validity": "applyFilter == \"true\""
    },
    "OMFRetrySleepTime": {
        "description": "Seconds between each retry for communication with the OMF PI Connector Relay. "
                       "This time is doubled at each attempt.",
        "type": "integer",
        "default": "1",
        "order": "9",
        "displayName": "Sleep Time Retry"
    },
    "OMFMaxRetry": {
        "description": "Max number of retries for communication with the OMF PI Connector Relay",
        "type": "integer",
        "default": "3",
        "order": "10",
        "displayName": "Maximum Retry"
    },
    "OMFHttpTimeout": {
        "description": "Timeout in seconds for HTTP operations with the OMF PI Connector Relay",
        "type": "integer",
        "default": "10",
        "order": "13",
        "displayName": "HTTP Timeout"
    },
    "formatInteger": {
        "description": "OMF format property to apply to the type Integer",
        "type": "string",
        "default": "int64",
        "order": "14",
        "displayName": "Integer Format"
    },
    "formatNumber": {
        "description": "OMF format property to apply to the type Number",
        "type": "string",
        "default": "float64",
        "order": "15",
        "displayName": "Number Format"
    },
    "notBlockingErrors": {
        "description": "These errors are considered not blocking in the communication with the PI Server,"
                       " the sending operation will proceed with the next block of data if one of these is encountered",
        "type": "JSON",
        "default": json.dumps(
            [
                {'id': 400, 'message': 'Invalid value type for the property'},
                {'id': 400, 'message': 'Redefinition of the type with the same ID is not allowed'}
            ]
        ),
        "readonly": "true"
    },

}

# Configuration related to the OMF Types
_CONFIG_CATEGORY_OMF_TYPES_NAME = 'OMF_TYPES'
_CONFIG_CATEGORY_OMF_TYPES_DESCRIPTION = 'OMF Types'

CONFIG_DEFAULT_OMF_TYPES = {
    "type-id": {
        "description": "Identify sensor and measurement types",
        "type": "integer",
        "default": "0001"
    },
}

_OMF_PREFIX_MEASUREMENT = "measurement_"
_OMF_SUFFIX_TYPENAME = "_typename"

OMF_TEMPLATE_TYPE = {
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
        "id": "xxx",
        "typeid": "xxx"
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


def _performance_log(_function):
    """ Logs information for performance measurement """

    def wrapper(*arg):
        """ wrapper """

        # Avoids any exceptions related to the performance measurement
        try:

            start = datetime.datetime.now()

            # Code execution
            result = _function(*arg)

            if _log_performance:
                usage = resource.getrusage(resource.RUSAGE_SELF)
                memory_process = (usage[2]) / 1000
                delta = datetime.datetime.now() - start
                delta_milliseconds = int(delta.total_seconds() * 1000)

                _logger.info("PERFORMANCE - {0} - milliseconds |{1:>8,}| - memory MB |{2:>8,}|".format(
                    _function.__name__,
                    delta_milliseconds,
                    memory_process))

            return result

        except Exception as ex:
            print("ERROR - {func} - error details |{error}|".format(
                                                                        func="_performance_log",
                                                                        error=ex), file=sys.stderr)
            raise

    return wrapper


def plugin_info():
    return {
        'name': "PI Server North",
        'version': "1.0.0",
        'type': "north",
        'interface': "1.0",
        'config': _CONFIG_DEFAULT_OMF
    }


def _validate_configuration(data):
    """ Validates the configuration retrieved from the Configuration Manager
    Args:
        data: configuration retrieved from the Configuration Manager
    Returns:
    Raises:
        ValueError
    """

    _message = ""

    if 'producerToken' not in data:
        _message = MESSAGES_LIST["e000001"]

    else:
        if data['producerToken']['value'] == "":

            _message = MESSAGES_LIST["e000002"]

    if _message != "":
        _logger.error(_message)
        raise ValueError(_message)


def _validate_configuration_omf_type(data):
    """ Validates the configuration retrieved from the Configuration Manager related to the OMF types
    Args:
        data: configuration retrieved from the Configuration Manager
    Returns:
    Raises:
        ValueError
    """

    _message = ""

    if 'type-id' not in data:
        _message = MESSAGES_LIST["e000010"]
    else:
        if data['type-id']['value'] == "":

            _message = MESSAGES_LIST["e000011"]

    if _message != "":
        _logger.error(_message)
        raise ValueError(_message)


def plugin_init(data):
    """ Initializes the OMF plugin for the sending of blocks of readings to the PI Connector.
    Args:
    Returns:
    Raises:
        PluginInitializeFailed
    """
    global _config
    global _config_omf_types
    global _logger
    global _recreate_omf_objects
    global _log_debug_level, _log_performance, _stream_id

    _log_debug_level = data['debug_level']
    _log_performance = data['log_performance']
    _stream_id = data['stream_id']

    try:
        # note : _module_name is used as __name__ refers to the Sending Proces
        logger_name = _MODULE_NAME + "_" + str(_stream_id)

        _logger = \
            logger.setup(logger_name, destination=_LOGGER_DESTINATION) if _log_debug_level == 0 else\
            logger.setup(logger_name, destination=_LOGGER_DESTINATION, level=logging.INFO if _log_debug_level == 1 else logging.DEBUG)

    except Exception as ex:
        _logger.error("{0} - ERROR - {1}".format(time.strftime("%Y-%m-%d %H:%M:%S:"), plugin_common.MESSAGES_LIST["e000012"].format(str(ex))))
        raise ex
    _logger.debug("{0} - ".format("plugin_info"))

    _validate_configuration(data)

    # Retrieves the configurations and apply the related conversions
    _config['_CONFIG_CATEGORY_NAME'] = data['_CONFIG_CATEGORY_NAME']
    _config['URL'] = data['URL']['value']
    _config['producerToken'] = data['producerToken']['value']
    _config['OMFMaxRetry'] = int(data['OMFMaxRetry']['value'])
    _config['OMFRetrySleepTime'] = int(data['OMFRetrySleepTime']['value'])
    _config['OMFHttpTimeout'] = int(data['OMFHttpTimeout']['value'])

    _config['StaticData'] = ast.literal_eval(data['StaticData']['value'])
    _config['notBlockingErrors'] = ast.literal_eval(data['notBlockingErrors']['value'])

    _config['formatNumber'] = data['formatNumber']['value']
    _config['formatInteger'] = data['formatInteger']['value']

    _config['compression'] = data['compression']['value']

    # TODO: compare instance fetching via inspect vs as param passing
    # import inspect
    # _config['sending_process_instance'] = inspect.currentframe().f_back.f_locals['self']
    _config['sending_process_instance'] = data['sending_process_instance']

    # _config_omf_types = json.loads(data['omf_types']['value'])
    _config_omf_types = _config['sending_process_instance']._fetch_configuration(cat_name=_CONFIG_CATEGORY_OMF_TYPES_NAME,
                                                                                 cat_desc=_CONFIG_CATEGORY_OMF_TYPES_DESCRIPTION,
                                                                                 cat_config=CONFIG_DEFAULT_OMF_TYPES,
                                                                                 cat_keep_original=True)

    _validate_configuration_omf_type(_config_omf_types)

    # Converts the value field from str to a dict
    for item in _config_omf_types:
        if _config_omf_types[item]['type'] == 'JSON':
            # The conversion from a dict to str changes the case and it should be fixed before the conversion
            value = _config_omf_types[item]['value'].replace("true", "True")
            new_value = ast.literal_eval(value)
            _config_omf_types[item]['value'] = new_value

    _logger.debug("{0} - URL {1}".format("plugin_init", _config['URL']))
    try:
        _recreate_omf_objects = True
    except Exception as ex:
        _logger.error(plugin_common.MESSAGES_LIST["e000011"].format(ex))
        raise plugin_exceptions.PluginInitializeFailed(ex)

    return _config


async def plugin_send(data, raw_data, stream_id):
    """ Translates and sends to the destination system the data provided by the Sending Process
    Args:
        data: plugin_handle from sending_process
        raw_data  : Data to send as retrieved from the storage layer
        stream_id
    Returns:
        data_to_send : True, data successfully sent to the destination system
        new_position : Last row_id already sent
        num_sent     : Number of rows sent, used for the update of the statistics
    Raises:
    """

    global _recreate_omf_objects

    is_data_sent = False
    config_category_name = data['_CONFIG_CATEGORY_NAME']
    type_id = _config_omf_types['type-id']['value']

    omf_north = PIServerNorthPlugin(data['sending_process_instance'], data, _config_omf_types, _logger)

    # Alloc the in memory buffer
    buffer_size = len(raw_data)
    data_to_send = [None for _ in range(buffer_size)]

    is_data_available, new_position, num_sent = omf_north.transform_in_memory_data(data_to_send, raw_data)

    if is_data_available:

        await omf_north.create_omf_objects(raw_data, config_category_name, type_id)

        try:
            await omf_north.send_in_memory_data_to_picromf("Data", data_to_send)

        except Exception as ex:
            # Forces the recreation of PIServer's objects on the first error occurred
            if _recreate_omf_objects:
                await omf_north.deleted_omf_types_already_created(config_category_name, type_id)
                _recreate_omf_objects = False
                _logger.debug("{0} - Forces objects recreation ".format("plugin_send"))
            raise ex
        else:
            is_data_sent = True

    return is_data_sent, new_position, num_sent


def plugin_shutdown(data):
    """ Terminates the plugin
    Returns:
    Raises:
    """
    try:
        _logger.debug("{0} - plugin_shutdown".format(_MODULE_NAME))
    except Exception as ex:
        _logger.error(plugin_common.MESSAGES_LIST["e000013"].format(ex))
        raise


def plugin_reconfigure():
    """ plugin_reconfigure """

    pass


class PIServerNorthPlugin(object):
    """ North OMF North Plugin """

    def __init__(self, sending_process_instance, config, config_omf_types, _logger):

        self._sending_process_instance = sending_process_instance

        self._config = config
        self._config_omf_types = config_omf_types
        self._logger = _logger

    async def deleted_omf_types_already_created(self, config_category_name, type_id):
        """ Deletes OMF types/objects tracked as already created, it is used to force the recreation of the types
         Args:
            config_category_name: used to identify OMF objects already created
            type_id:              used to identify OMF objects already created
         Returns:
         Raises:
         """
        payload = payload_builder.PayloadBuilder() \
            .WHERE(['configuration_key', '=', config_category_name]) \
            .AND_WHERE(['type_id', '=', type_id]) \
            .payload()

        await self._sending_process_instance._storage_async.delete_from_tbl("omf_created_objects", payload)

    async def _retrieve_omf_types_already_created(self, configuration_key, type_id):
        """ Retrieves the list of OMF types already defined/sent to the PICROMF
         Args:
             configuration_key - part of the key to identify the type
             type_id           - part of the key to identify the type
         Returns:
            List of Asset code already defined into the PI Server
         Raises:
         """
        payload = payload_builder.PayloadBuilder() \
            .WHERE(['configuration_key', '=', configuration_key]) \
            .AND_WHERE(['type_id', '=', type_id]) \
            .payload()

        omf_created_objects = await self._sending_process_instance._storage_async.query_tbl_with_payload('omf_created_objects', payload)
        self._logger.debug("{func} - omf_created_objects {item} ".format(
                                                                    func="_retrieve_omf_types_already_created",
                                                                    item=omf_created_objects))
        # Extracts only the asset_code column
        rows = []
        for row in omf_created_objects['rows']:
            rows.append(row['asset_code'])

        return rows

    async def _flag_created_omf_type(self, configuration_key, type_id, asset_code):
        """ Stores into the Storage layer the successfully creation of the type into PICROMF.
         Args:
             configuration_key - part of the key to identify the type
             type_id           - part of the key to identify the type
             asset_code        - asset code defined into PICROMF
         Returns:
         Raises:
         """
        payload = payload_builder.PayloadBuilder()\
            .INSERT(configuration_key=configuration_key,
                    asset_code=asset_code,
                    type_id=type_id)\
            .payload()
        await self._sending_process_instance._storage_async.insert_into_tbl("omf_created_objects", payload)

    def _generate_omf_asset_id(self, asset_code):
        """ Generates an asset id usable by AF/PI Server from an asset code stored into the Storage layer
         Args:
             asset_code : Asset code stored into the Storage layer
         Returns:
            Asset id usable by AF/PI Server
         Raises:
         """
        asset_id = asset_code.replace(" ", "")
        return asset_id

    def _generate_omf_measurement(self, asset_code):
        """ Generates the measurement id associated to an asset code
         Args:
             asset_code :  Asset code retrieved from the Storage layer
         Returns:
            Measurement id associated to the specific asset code
         Raises:
         """
        asset_id = asset_code.replace(" ", "")
        type_id = self._config_omf_types['type-id']['value']
        return type_id + _OMF_PREFIX_MEASUREMENT + asset_id

    def _generate_omf_typename_automatic(self, asset_code):
        """ Generates the typename associated to an asset code for the automated generation of the OMF types
         Args:
             asset_code :  Asset code retrieved from the Storage layer
         Returns:
            typename associated to the specific asset code
         Raises:
         """
        asset_id = asset_code.replace(" ", "")
        return asset_id + _OMF_SUFFIX_TYPENAME

    async def _create_omf_objects_automatic(self, asset_info):
        """ Handles the Automatic OMF Type Mapping
         Args:
             asset_info : Asset's information as retrieved from the Storage layer,
                          having also a sample value for the asset
         Returns:
             response_status_code: http response code related to the PICROMF request
         Raises:
         """
        typename, omf_type = await self._create_omf_type_automatic(asset_info)
        await self._create_omf_object_links(asset_info["asset_code"], typename, omf_type)

    async def _create_omf_type_automatic(self, asset_info):
        """ Automatic OMF Type Mapping - Handles the OMF type creation
         Args:
             asset_info : Asset's information as retrieved from the Storage layer,
                          having also a sample value for the asset
         Returns:
             typename : typename associate to the asset
             omf_type : describe the OMF type as a python dict
         Raises:
         """
        type_id = self._config_omf_types["type-id"]["value"]
        sensor_id = self._generate_omf_asset_id(asset_info["asset_code"])
        asset_data = asset_info["asset_data"]
        typename = self._generate_omf_typename_automatic(sensor_id)
        new_tmp_dict = copy.deepcopy(OMF_TEMPLATE_TYPE)
        omf_type = {typename: new_tmp_dict["typename"]}
        # Handles Static section
        # Generates elements evaluating the StaticData retrieved form the Configuration Manager
        omf_type[typename][0]["properties"]["Name"] = {
            "type": "string",
            "isindex": True
        }
        omf_type[typename][0]["id"] = type_id + "_" + typename + "_sensor"
        for item in self._config['StaticData']:
            omf_type[typename][0]["properties"][item] = {"type": "string"}
        # Handles Dynamic section
        omf_type[typename][1]["properties"]["Time"] = {
            "type": "string",
            "format": "date-time",
            "isindex": True
        }
        omf_type[typename][1]["id"] = type_id + "_" + typename + "_measurement"

        # Applies configured format property for the specific type
        for item in asset_data:
            item_type = plugin_common.evaluate_type(asset_data[item])

            self._logger.debug(
                "func |{func}| - item_type |{type}| - formatInteger |{int}| - formatNumber |{float}| ".format(
                            func="_create_omf_type_automatic",
                            type=item_type,
                            int=self._config['formatInteger'],
                            float=self._config['formatNumber']))

            # Handles OMF format property to force the proper OCS type, especially for handling decimal numbers
            if item_type == "integer":

                # Forces the creation of integer as number
                omf_type[typename][1]["properties"][item] = {"type":  "number",
                                                             "format": self._config['formatNumber']}

                #
                # omf_type[typename][1]["properties"][item] = {"type": item_type,
                #                                              "format": self._config['formatInteger']}
            elif item_type == "number":
                omf_type[typename][1]["properties"][item] = {"type": item_type,
                                                             "format": self._config['formatNumber']}

            elif item_type == "array":
                omf_type[typename][1]["properties"][item] = {
                                                                "type": item_type,
                                                                "items": {
                                                                    "type": "number",
                                                                    "format": self._config['formatNumber']
                                                                }
                                                             }
            else:
                omf_type[typename][1]["properties"][item] = {"type": item_type}


        if _log_debug_level == 3:
            self._logger.debug("_create_omf_type_automatic - sensor_id |{0}| - omf_type |{1}| ".format(sensor_id, str(omf_type)))

        await self.send_in_memory_data_to_picromf("Type", omf_type[typename])

        return typename, omf_type

    async def _create_omf_objects_configuration_based(self, asset_code, asset_code_omf_type):
        """ Handles the Configuration Based OMF Type Mapping
         Args:
            asset_code
            asset_code_omf_type : describe the OMF type as a python dict
         Returns:
         Raises:
         """
        typename, omf_type = await self._create_omf_type_configuration_based(asset_code_omf_type)
        await self._create_omf_object_links(asset_code, typename, omf_type)

    async def _create_omf_type_configuration_based(self, asset_code_omf_type):
        """ Configuration Based OMF Type Mapping - Handles the OMF type creation
         Args:
            asset_code_omf_type : describe the OMF type as a python dict
         Returns:
             typename : typename associate to the asset
             omf_type : describe the OMF type as a python dict
         Raises:
         """
        type_id = self._config_omf_types["type-id"]["value"]
        typename = asset_code_omf_type["typename"]
        new_tmp_dict = copy.deepcopy(OMF_TEMPLATE_TYPE)
        omf_type = {typename: new_tmp_dict["typename"]}
        # Handles Static section
        omf_type[typename][0]["properties"] = asset_code_omf_type["static"]
        omf_type[typename][0]["id"] = type_id + "_" + typename + "_sensor"
        # Handles Dynamic section
        omf_type[typename][1]["properties"] = asset_code_omf_type["dynamic"]
        omf_type[typename][1]["id"] = type_id + "_" + typename + "_measurement"
        if _log_debug_level == 3:
            self._logger.debug("_create_omf_type_configuration_based - omf_type |{0}| ".format(str(omf_type)))

        await self.send_in_memory_data_to_picromf("Type", omf_type[typename])

        return typename, omf_type

    async def _create_omf_object_links(self, asset_code, typename, omf_type):
        """ Handles the creation of the links between the OMF objects :
            sensor, its measurement, sensor type and measurement type
         Args:
            asset_code
            typename : name/id of the type
            omf_type : describe the OMF type as a python dict
         Returns:
         Raises:
         """
        sensor_id = self._generate_omf_asset_id(asset_code)
        measurement_id = self._generate_omf_measurement(sensor_id)
        type_sensor_id = omf_type[typename][0]["id"]
        type_measurement_id = omf_type[typename][1]["id"]
        # Handles containers
        containers = copy.deepcopy(_OMF_TEMPLATE_CONTAINER)
        containers[0]["id"] = measurement_id
        containers[0]["typeid"] = type_measurement_id
        # Handles static_data
        static_data = copy.deepcopy(_OMF_TEMPLATE_STATIC_DATA)
        static_data[0]["typeid"] = type_sensor_id
        static_data[0]["values"][0] = copy.deepcopy(self._config['StaticData'])
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
            self._logger.debug("_create_omf_object_links - asset_code |{0}| - containers |{1}| ".format(asset_code,
                                                                                                   str(containers)))
            self._logger.debug("_create_omf_object_links - asset_code |{0}| - static_data |{1}| ".format(asset_code,
                                                                                                    str(static_data)))
            self._logger.debug("_create_omf_object_links - asset_code |{0}| - link_data |{1}| ".format(asset_code,
                                                                                                  str(link_data)))
        await self.send_in_memory_data_to_picromf("Container", containers)
        await self.send_in_memory_data_to_picromf("Data", static_data)
        await self.send_in_memory_data_to_picromf("Data", link_data)

        return

    async def create_omf_objects(self, raw_data, config_category_name, type_id):
        """ Handles the creation of the OMF types related to the asset codes using one of the 2 possible ways :
                Automatic OMF Type Mapping
                Configuration Based OMF Type Mapping
        Args:
            raw_data :            data block to manage as retrieved from the Storage layer
            config_category_name: used to identify OMF objects already created
            type_id:              used to identify OMF objects already created
        Returns:
        Raises:
        """
        asset_codes_to_evaluate = plugin_common.identify_unique_asset_codes(raw_data)
        asset_codes_already_created = await self._retrieve_omf_types_already_created(config_category_name, type_id)

        for item in asset_codes_to_evaluate:
            asset_code = item["asset_code"]

            # Evaluates if it is a new OMF type
            if not any(tmp_item == asset_code for tmp_item in asset_codes_already_created):

                asset_code_omf_type = ""
                try:
                    asset_code_omf_type = copy.deepcopy(self._config_omf_types[asset_code]["value"])
                except KeyError:
                    configuration_based = False
                else:
                    configuration_based = True

                if configuration_based:
                    self._logger.debug("creates type - configuration based - asset |{0}| ".format(asset_code))
                    await self._create_omf_objects_configuration_based(asset_code, asset_code_omf_type)
                else:

                    # handling - Automatic OMF Type Mapping
                    self._logger.debug("creates type - automatic handling - asset |{0}| ".format(asset_code))
                    await self._create_omf_objects_automatic(item)

                await self._flag_created_omf_type(config_category_name, type_id, asset_code)
            else:
                self._logger.debug("asset already created - asset |{0}| ".format(asset_code))

    async def send_in_memory_data_to_picromf(self, message_type, omf_data):
        """ Sends data to PICROMF - it retries the operation using a sleep time increased *2 for every retry
            it logs a WARNING only at the end of the retry mechanism in case of a communication error
        Args:
            message_type: possible values {Type, Container, Data}
            omf_data:     OMF message to send
        Returns:
        Raises:
            Exception: an error occurred during the OMF request
            URLFetchError: in case of http response code different from 2xx
        """
        sleep_time = self._config['OMFRetrySleepTime']
        _message = ""
        _error = False
        num_retry = 1
        msg_header = {'producertoken': self._config['producerToken'],
                      'messagetype': message_type,
                      'action': 'create',
                      'messageformat': 'JSON',
                      'omfversion': '1.0'}
        omf_data_json = json.dumps(omf_data)

        self._logger.debug("OMF message length |{0}| ".format(len(omf_data_json)))

        if _log_debug_level == 3:
            self._logger.debug("OMF message : |{0}| |{1}| " .format(message_type, omf_data_json))

        while num_retry <= self._config['OMFMaxRetry']:
            _error = False
            try:
                use_compression = True if self._config['compression'].upper() == 'TRUE' else False
                if use_compression:
                    msg_body = gzip.compress(bytes(omf_data_json, 'utf-8'))
                    msg_header.update({'compression': 'gzip'})
                    # https://docs.aiohttp.org/en/stable/client_advanced.html#uploading-pre-compressed-data
                    msg_header.update({'Content-Encoding': 'gzip'})
                else:
                    msg_body = omf_data_json

                self._logger.info("SEND requested with compression: %s started at: %s", str(use_compression), datetime.datetime.now().isoformat())
                async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
                    async with session.post(
                                            url=self._config['URL'],
                                            headers=msg_header,
                                            data=msg_body,
                                            timeout=self._config['OMFHttpTimeout']
                                            ) as resp:

                        status_code = resp.status
                        text = await resp.text()
            except (TimeoutError, asyncio.TimeoutError) as ex:
                _message = plugin_common.MESSAGES_LIST["e000024"].format(self._config['URL'], "connection Timeout")
                _error = plugin_exceptions.URLConnectionError(_message)

            except Exception as ex:
                details = str(ex)
                _message = plugin_common.MESSAGES_LIST["e000024"].format(self._config['URL'], details)
                _error = plugin_exceptions.URLConnectionError(_message)

            else:
                self._logger.info("PI Server responded with status: %s received at: %s", str(status_code),
                                     datetime.datetime.now().isoformat())
                # Evaluate the HTTP status codes
                if not str(status_code).startswith('2'):
                    if any(_['id'] == status_code and _['message'] in text for _ in self._config['notBlockingErrors']):

                        # The error encountered is in the list of not blocking
                        # the sending operation will proceed with the next block of data
                        self._logger.warning(plugin_common.MESSAGES_LIST["e000032"].format(status_code, text))
                        _error = ""
                    else:
                        _tmp_text = "status code " + str(status_code) + " - " + text
                        _message = plugin_common.MESSAGES_LIST["e000024"].format(self._config['URL'], _tmp_text)
                        _error = plugin_exceptions.URLConnectionError(_message)

                self._logger.debug("message type |{0}| response: |{1}| |{2}| ".format(
                    message_type,
                    status_code,
                    text))

            if _error:
                await asyncio.sleep(sleep_time)
                num_retry += 1
                sleep_time *= 2
            else:
                break

        if _error:
            raise _error

    @_performance_log
    def transform_in_memory_data(self, data_to_send, raw_data):
        """ Transforms the in memory data into a new structure that could be converted into JSON for the PICROMF
        Args:
            data_to_send - Transformed/generated data
            raw_data - Input data
        Returns:
            data_available - True, there are new data
            _new_position - It corresponds to the row_id of the last element
            _num_sent - Number of elements handled, used to update the statistics
        Raises:
        """

        _new_position = 0
        data_available = False

        # statistics
        _num_sent = 0

        idx = 0

        try:

            for row in raw_data:

                # Identification of the object/sensor
                measurement_id = self._generate_omf_measurement(row['asset_code'])

                try:
                    # The expression **row['reading'] - joins the 2 dictionaries
                    #
                    # The code formats the date to the format OMF/the PI Server expects directly
                    # without using python date library for performance reason and
                    # because it is expected to receive the date in a precise/fixed format :
                    #   2018-05-28 16:56:55.000000+00
                    data_to_send[idx] = {
                            "containerid": measurement_id,
                            "values": [
                                {
                                    "Time": row['user_ts'][0:10] + "T" + row['user_ts'][11:23] + "Z",
                                    **row['reading']
                                }
                            ]
                        }

                    if _log_debug_level == 3:
                        self._logger.debug("stream ID : |{0}| sensor ID : |{1}| row ID : |{2}|  "
                                           .format(measurement_id, row['asset_code'], str(row['id'])))

                        self._logger.debug("in memory info |{0}| ".format(data_to_send[idx]))

                    idx += 1

                    # Used for the statistics update
                    _num_sent += 1

                    # Latest position reached
                    _new_position = row['id']

                    data_available = True

                except Exception as e:
                    self._logger.warning(plugin_common.MESSAGES_LIST["e000023"].format(e))

        except Exception:
            self._logger.error(plugin_common.MESSAGES_LIST["e000021"])
            raise

        return data_available, _new_position, _num_sent