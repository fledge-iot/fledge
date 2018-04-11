# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" The OMF North is a plugin output formatter for the FogLAMP appliance.
It is loaded by the send process (see The FogLAMP Sending Process) and runs in the context of the send process,
to send the reading data to a PI Server (or Connector) using the OSIsoft OMF format.
PICROMF = PI Connector Relay OMF"""

from datetime import datetime
import sys
import copy
import ast
import resource
import datetime
import time
import json
import requests
import logging
import urllib3
import foglamp.plugins.north.common.common as plugin_common
import foglamp.plugins.north.common.exceptions as plugin_exceptions
from foglamp.common import logger
from foglamp.common.storage_client import payload_builder

# Module information
__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# LOG configuration
_LOG_LEVEL_DEBUG = 10
_LOG_LEVEL_INFO = 20
_LOG_LEVEL_WARNING = 30

_LOGGER_LEVEL = _LOG_LEVEL_WARNING
_LOGGER_DESTINATION = logger.SYSLOG
_logger = None

_MODULE_NAME = "omf_north"

# Defines what and the level of details for logging
_log_debug_level = 0
_log_performance = False

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
_CONFIG_CATEGORY_DESCRIPTION = 'Configuration of OMF North plugin'
_CONFIG_DEFAULT_OMF = {
    'plugin': {
        'description': 'OMF North Plugin',
        'type': 'string',
        'default': 'omf'
    },
    "URL": {
        "description": "The URL of the PI Connector to send data to",
        "type": "string",
        "default": "https://pi-server:5460/ingress/messages"
    },
    "producerToken": {
        "description": "The producer token that represents this FogLAMP stream",
        "type": "string",
        "default": "omf_north_0001"
    },
    "OMFMaxRetry": {
        "description": "Max number of retries for the communication with the OMF PI Connector Relay",
        "type": "integer",
        "default": "3"
    },
    "OMFRetrySleepTime": {
        "description": "Seconds between each retry for the communication with the OMF PI Connector Relay, "
                       "NOTE : the time is doubled at each attempt.",
        "type": "integer",
        "default": "1"
    },
    "OMFHttpTimeout": {
        "description": "Timeout in seconds for the HTTP operations with the OMF PI Connector Relay",
        "type": "integer",
        "default": "10"
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
    },
    "applyFilter": {
        "description": "Whether to apply filter before processing the data",
        "type": "boolean",
        "default": "False"
    },
    "filterRule": {
        "description": "JQ formatted filter to apply (applicable if applyFilter is True)",
        "type": "string",
        "default": ".[]"
    }
}

# Configuration related to the OMF Types
_CONFIG_CATEGORY_OMF_TYPES_NAME = 'OMF_TYPES'
_CONFIG_CATEGORY_OMF_TYPES_DESCRIPTION = 'Configuration of OMF types'

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
        'name': "OMF North",
        'version': "1.0.0",
        'type': "north",
        'interface': "1.0",
        'config': _CONFIG_DEFAULT_OMF
    }

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

    try:
        # note : _module_name is used as __name__ refers to the Sending Proces
        logger_name = _MODULE_NAME + "_" + str(data['stream_id']['value'])

        _logger = \
            logger.setup(logger_name, destination=_LOGGER_DESTINATION) if _log_debug_level == 0 else\
            logger.setup(logger_name, destination=_LOGGER_DESTINATION, level=logging.INFO if _log_debug_level == 1 else logging.DEBUG)

    except Exception as ex:
        _logger.error("{0} - ERROR - {1}".format(time.strftime("%Y-%m-%d %H:%M:%S:"), plugin_common.MESSAGES_LIST["e000012"].format(str(ex))))
        raise ex
    _logger.debug("{0} - ".format("plugin_info"))

    # Retrieves the configurations and apply the related conversions
    _config['_CONFIG_CATEGORY_NAME'] = data['_CONFIG_CATEGORY_NAME']
    _config['URL'] = data['URL']['value']
    _config['producerToken'] = data['producerToken']['value']
    _config['OMFMaxRetry'] = int(data['OMFMaxRetry']['value'])
    _config['OMFRetrySleepTime'] = int(data['OMFRetrySleepTime']['value'])
    _config['OMFHttpTimeout'] = int(data['OMFHttpTimeout']['value'])
    _config['StaticData'] = ast.literal_eval(data['StaticData']['value'])
    # TODO: compare instance fetching via inspect vs as param passing
    # import inspect
    # _config['sending_process_instance'] = inspect.currentframe().f_back.f_locals['self']
    _config['sending_process_instance'] = data['sending_process_instance']

    # _config_omf_types = json.loads(data['omf_types']['value'])
    _config_omf_types = _config['sending_process_instance']._fetch_configuration(cat_name=_CONFIG_CATEGORY_OMF_TYPES_NAME,
                                                                                 cat_desc=_CONFIG_CATEGORY_OMF_TYPES_DESCRIPTION,
                                                                                 cat_config=CONFIG_DEFAULT_OMF_TYPES,
                                                                                 cat_keep_original=True)

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

    # Avoids the warning message - InsecureRequestWarning
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    return _config

@_performance_log
def plugin_send(data, raw_data, stream_id):
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
    data_to_send = []
    type_id = _config_omf_types['type-id']['value']

    omf_north = OmfNorthPlugin(data['sending_process_instance'], data, _config_omf_types, _logger)

    try:
        is_data_available, new_position, num_sent = omf_north.transform_in_memory_data(data_to_send, raw_data)
        if is_data_available:
            omf_north.create_omf_objects(raw_data, config_category_name, type_id)
            try:
                omf_north.send_in_memory_data_to_picromf("Data", data_to_send)
            except Exception as ex:
                # Forces the recreation of PIServer's objects on the first error occurred
                if _recreate_omf_objects:
                    omf_north.deleted_omf_types_already_created(config_category_name, type_id)
                    _recreate_omf_objects = False
                    _logger.debug("{0} - Forces objects recreation ".format("plugin_send"))
                raise ex
            else:
                is_data_sent = True
    except Exception as ex:
        _logger.exception(plugin_common.MESSAGES_LIST["e000031"].format(ex))
        raise
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


class OmfNorthPlugin(object):
    """ North OMF North Plugin """

    def __init__(self, sending_process_instance, config, config_omf_types, _logger):

        self._sending_process_instance = sending_process_instance

        self._config = config
        self._config_omf_types = config_omf_types
        self._logger = _logger

    def deleted_omf_types_already_created(self, config_category_name, type_id):
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

        self._sending_process_instance._storage.delete_from_tbl("omf_created_objects", payload)
    
    def _retrieve_omf_types_already_created(self, configuration_key, type_id):
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

        omf_created_objects = self._sending_process_instance._storage.query_tbl_with_payload('omf_created_objects', payload)
        self._logger.debug("{func} - omf_created_objects {item} ".format(
                                                                    func="_retrieve_omf_types_already_created",
                                                                    item=omf_created_objects))
        # Extracts only the asset_code column
        rows = []
        for row in omf_created_objects['rows']:
            rows.append(row['asset_code'])
        return rows
    
    def _flag_created_omf_type(self, configuration_key, type_id, asset_code):
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
        self._sending_process_instance._storage.insert_into_tbl("omf_created_objects", payload)
    
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
        return _OMF_PREFIX_MEASUREMENT + asset_id
     
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
    
    def _create_omf_objects_automatic(self, asset_info):
        """ Handles the Automatic OMF Type Mapping
         Args:
             asset_info : Asset's information as retrieved from the Storage layer,
                          having also a sample value for the asset
         Returns:
             response_status_code: http response code related to the PICROMF request
         Raises:
         """
        typename, omf_type = self._create_omf_type_automatic(asset_info)
        self._create_omf_object_links(asset_info["asset_code"], typename, omf_type)
    
    def _create_omf_type_automatic(self, asset_info):
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
        for item in asset_data:
            item_type = plugin_common.evaluate_type(asset_data[item])
            omf_type[typename][1]["properties"][item] = {"type": item_type}
        if _log_debug_level == 3:
            self._logger.debug("_create_omf_type_automatic - sensor_id |{0}| - omf_type |{1}| ".format(sensor_id, str(omf_type)))
        self.send_in_memory_data_to_picromf("Type", omf_type[typename])
        return typename, omf_type
    
    def _create_omf_objects_configuration_based(self, asset_code, asset_code_omf_type):
        """ Handles the Configuration Based OMF Type Mapping
         Args:
            asset_code
            asset_code_omf_type : describe the OMF type as a python dict
         Returns:
         Raises:
         """
        typename, omf_type = self._create_omf_type_configuration_based(asset_code_omf_type)
        self._create_omf_object_links(asset_code, typename, omf_type)
    
    def _create_omf_type_configuration_based(self, asset_code_omf_type):
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
        self.send_in_memory_data_to_picromf("Type", omf_type[typename])
        return typename, omf_type
    
    def _create_omf_object_links(self, asset_code, typename, omf_type):
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
        self.send_in_memory_data_to_picromf("Container", containers)
        self.send_in_memory_data_to_picromf("Data", static_data)
        self.send_in_memory_data_to_picromf("Data", link_data)
        return
    
    @_performance_log
    def create_omf_objects(self, raw_data, config_category_name, type_id):
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
        asset_codes_already_created = self._retrieve_omf_types_already_created(config_category_name, type_id)
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
                    self._create_omf_objects_configuration_based(asset_code, asset_code_omf_type)
                else:
                    # handling - Automatic OMF Type Mapping
                    self._logger.debug("creates type - automatic handling - asset |{0}| ".format(asset_code))
                    self._create_omf_objects_automatic(item)
                self._flag_created_omf_type(config_category_name, type_id, asset_code)
            else:
                self._logger.debug("asset already created - asset |{0}| ".format(asset_code))
    
    @_performance_log
    def send_in_memory_data_to_picromf(self, message_type, omf_data):
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
                response = requests.post(self._config['URL'],
                                         headers=msg_header,
                                         data=omf_data_json,
                                         verify=False,
                                         timeout=self._config['OMFHttpTimeout'])
            except Exception as e:
                _error = Exception(plugin_common.MESSAGES_LIST["e000024"].format(e))
                _message = plugin_common.MESSAGES_LIST["e000024"].format(e)
            else:
                # Evaluate the HTTP status codes
                if not str(response.status_code).startswith('2'):
                    tmp_text = str(response.status_code) + " " + response.text
                    _message = plugin_common.MESSAGES_LIST["e000024"].format(tmp_text)
                    _error = plugin_exceptions.URLFetchError(_message)
                self._logger.debug("message type |{0}| response: |{1}| |{2}| ".format(message_type,
                                                                                 response.status_code,
                                                                                 response.text))
            if _error:
                time.sleep(sleep_time)
                num_retry += 1
                sleep_time *= 2
            else:
                break
        if _error:
            self._logger.warning(_message)
            raise _error
    
    @_performance_log
    def transform_in_memory_data(self, data_to_send, raw_data):
        """ Transforms the in memory data into a new structure that could be converted into JSON for the PICROMF
        Args:
        Returns:
        Raises:
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
                measurement_id = self._generate_omf_measurement(asset_code)
                
                try:
                    self._transform_in_memory_row(data_to_send, row, measurement_id)
                    # Used for the statistics update
                    num_sent += 1
                    # Latest position reached
                    new_position = row_id
                    data_available = True
                except Exception as e:
                    num_unsent += 1
                    self._logger.warning(plugin_common.MESSAGES_LIST["e000023"].format(e))
        except Exception:
            self._logger.error(plugin_common.MESSAGES_LIST["e000021"])
            raise
        return data_available, new_position, num_sent
    
    def _transform_in_memory_row(self, data_to_send, row, target_stream_id):
        """ Extends the in memory structure using data retrieved from the Storage Layer
        Args:
            data_to_send:      data block to send - updated/used by reference
            row:               information retrieved from the Storage Layer that it is used to extend data_to_send
            target_stream_id:  OMF container ID
        Returns:
        Raises:
        """
        data_available = False
        try:
            row_id = row['id']
            asset_code = row['asset_code']
            timestamp_raw = row['user_ts']

            # Converts Date/time to a proper ISO format - Z is the zone designator for the zero UTC offset
            step1 = datetime.datetime.strptime(timestamp_raw, '%Y-%m-%d %H:%M:%S.%f+00')
            timestamp = step1.isoformat() + 'Z'

            sensor_data = row['reading']
            if _log_debug_level == 3:
                self._logger.debug("stream ID : |{0}| sensor ID : |{1}| row ID : |{2}|  "
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
                    self._logger.debug("in memory info |{0}| ".format(new_data))
            else:
                self._logger.warning(plugin_common.MESSAGES_LIST["e000020"])
        except Exception:
            self._logger.error(plugin_common.MESSAGES_LIST["e000022"])
            raise
