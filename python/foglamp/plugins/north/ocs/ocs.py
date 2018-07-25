# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" The OCS North is a plugin output formatter for the FogLAMP appliance.
    It is loaded by the send process (see The FogLAMP Sending Process) and runs in the context of the send process,
    to send the reading data to OSIsoft OCS (OSIsoft Cloud Services) using the OSIsoft OMF format.
    PICROMF = PI Connector Relay OMF
"""

from datetime import datetime
import sys
import copy
import ast
import resource
import datetime
import time
import json
import logging
# noinspection PyPackageRequirements
import foglamp.plugins.north.common.common as plugin_common
import foglamp.plugins.north.common.exceptions as plugin_exceptions
from foglamp.common import logger

import foglamp.plugins.north.omf.omf as omf

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

# Defines what and the level of details for logging
_log_debug_level = 0
_log_performance = False
_stream_id = None
_destination_id = None

_MODULE_NAME = "ocs_north"

# Messages used for Information, Warning and Error notice
MESSAGES_LIST = {

    # Information messages
    "i000000": "information.",

    # Warning / Error messages
    "e000000": "general error.",

    "e000001": "the producerToken must be defined, use the FogLAMP API to set a proper value.",
    "e000002": "the producerToken cannot be an empty string, use the FogLAMP API to set a proper value.",

    "e000010": "the type-id must be defined, use the FogLAMP API to set a proper value.",
    "e000011": "the type-id cannot be an empty string, use the FogLAMP API to set a proper value.",

}


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
_CONFIG_CATEGORY_DESCRIPTION = 'Configuration of OCS North plugin'


# The parameters used for the interaction with OCS are :
#    producerToken                      - It allows to ingest data into OCS using OMF.
#    tenant_id / client_id / client_id  - They are used for the authentication and interaction with the OCS API,
#                                         they are associated to the specific OCS account.
#    namespace                          - Specifies the OCS namespace where the information are stored,
#                                         it is used for the interaction with the OCS API.
#
_CONFIG_DEFAULT_OMF = {
    'plugin': {
        'description': 'OCS North Plugin',
        'type': 'string',
        'default': 'ocs'
    },
    "URL": {
        "description": "The URL of OCS (OSIsoft Cloud Services) ",
        "type": "string",
        "default": "https://dat-a.osisoft.com/api/omf"
    },
    "producerToken": {
        "description": "The producer token used to authenticate as a valid publisher and "
                       "required to ingest data into OCS using OMF.",
        "type": "string",
        "default": "ocs_north_0001"
    },
    "namespace": {
        "description": "Specifies the OCS namespace where the information are stored and "
                       "it is used for the interaction with the OCS API.",
        "type": "string",
        "default": "ocs_namespace_0001"
    },
    "tenant_id": {
      "description": "Tenant id associated to the specific OCS account.",
      "type": "string",
      "default": "ocs_tenant_id"
    },
    "client_id": {
      "description": "Client id associated to the specific OCS account, "
                     "it is used to authenticate the source for using the OCS API.",
      "type": "string",
      "default": "ocs_client_id"
    },
    "client_secret": {
      "description": "Client secret associated to the specific OCS account, "
                     "it is used to authenticate the source for using the OCS API.",
      "type": "string",
      "default": "ocs_client_secret"
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
    },
    "formatNumber": {
        "description": "OMF format property to apply to the type Number",
        "type": "string",
        "default": "float64"
    },
    "formatInteger": {
        "description": "OMF format property to apply to the type Integer",
        "type": "string",
        "default": "int32"
    }
}

# Configuration related to the OMF Types
_CONFIG_CATEGORY_OMF_TYPES_NAME = 'OCS_TYPES'
_CONFIG_CATEGORY_OMF_TYPES_DESCRIPTION = 'Configuration of OCS types'

_CONFIG_DEFAULT_OMF_TYPES = omf.CONFIG_DEFAULT_OMF_TYPES

_OMF_TEMPLATE_TYPE = omf.OMF_TEMPLATE_TYPE


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
                memory_process = (usage[2])/1000
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
    """ Returns information about the plugin.

    Args:
    Returns:
        dict: plugin information
    Raises:
    """

    return {
        'name': "OCS North",
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
    global _log_debug_level, _log_performance, _stream_id, _destination_id

    _log_debug_level = data['debug_level']
    _log_performance = data['log_performance']
    _stream_id = data['stream_id']
    _destination_id = data['destination_id']

    try:
        # note : _module_name is used as __name__ refers to the Sending Process
        logger_name = _MODULE_NAME + "_" + str(_stream_id)

        _logger = \
            logger.setup(logger_name, destination=_LOGGER_DESTINATION) if _log_debug_level == 0 else\
            logger.setup(
                            logger_name,
                            destination=_LOGGER_DESTINATION,
                            level=logging.INFO if _log_debug_level == 1 else logging.DEBUG)

    except Exception as ex:
        _logger.error("{0} - ERROR - {1}".format(
                                                time.strftime("%Y-%m-%d %H:%M:%S:"),
                                                plugin_common.MESSAGES_LIST["e000012"].format(str(ex))))
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

    _config['formatNumber'] = data['formatNumber']['value']
    _config['formatInteger'] = data['formatInteger']['value']

    # TODO: compare instance fetching via inspect vs as param passing
    # import inspect
    # _config['sending_process_instance'] = inspect.currentframe().f_back.f_locals['self']
    _config['sending_process_instance'] = data['sending_process_instance']

    # _config_omf_types = json.loads(data['omf_types']['value'])
    # noinspection PyProtectedMember
    _config_omf_types = _config['sending_process_instance']._fetch_configuration(
                                  cat_name=_CONFIG_CATEGORY_OMF_TYPES_NAME,
                                  cat_desc=_CONFIG_CATEGORY_OMF_TYPES_DESCRIPTION,
                                  cat_config=_CONFIG_DEFAULT_OMF_TYPES,
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


# noinspection PyUnusedLocal
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

    # Sets globals for the OMF module
    omf._logger = _logger
    omf._log_debug_level = _log_debug_level
    omf._log_performance = _log_performance

    ocs_north = OCSNorthPlugin(data['sending_process_instance'], data, _config_omf_types, _logger)

    try:
        # Alloc the in memory buffer
        buffer_size = len(raw_data)
        data_to_send = [None for x in range(buffer_size)]

        is_data_available, new_position, num_sent = ocs_north.transform_in_memory_data(data_to_send, raw_data)

        if is_data_available:

            await ocs_north.create_omf_objects(raw_data, config_category_name, type_id)

            try:
                await ocs_north.send_in_memory_data_to_picromf("Data", data_to_send)

            except Exception as ex:
                # Forces the recreation of PIServer's objects on the first error occurred
                if _recreate_omf_objects:
                    await ocs_north.deleted_omf_types_already_created(config_category_name, type_id)
                    _recreate_omf_objects = False
                    _logger.debug("{0} - Forces objects recreation ".format("plugin_send"))
                raise ex
            else:
                is_data_sent = True

    except Exception as ex:
        _logger.exception(plugin_common.MESSAGES_LIST["e000031"].format(ex))
        raise

    return is_data_sent, new_position, num_sent


# noinspection PyUnusedLocal
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
    """ Reconfigures the plugin, it should be called when the configuration of the plugin is changed during the
        operation of the South service.
        The new configuration category should be passed.

    Args:
    Returns:
    Raises:
    """

    pass


class OCSNorthPlugin(omf.OmfNorthPlugin):
    """ North OCS North Plugin """

    def __init__(self, sending_process_instance, config, config_omf_types,  _logger):

        super().__init__(sending_process_instance, config, config_omf_types, _logger)

    async def _create_omf_type_automatic(self, asset_info):
        """ Automatic OMF Type Mapping - Handles the OMF type creation

            Overwrite omf._create_omf_type_automatic function
            OCS needs the setting of the 'format' property to handle decimal numbers properly

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
        new_tmp_dict = copy.deepcopy(_OMF_TEMPLATE_TYPE)
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

            self._logger.debug(
                "func |{func}| - item_type |{type}| - formatInteger |{int}| - formatNumber |{float}| ".format(
                            func="_create_omf_type_automatic",
                            type=item_type,
                            int=self._config['formatInteger'],
                            float=self._config['formatNumber']))

            # Handles OMF format property to force the proper OCS type, especially for handling decimal numbers
            if item_type == "integer":

                omf_type[typename][1]["properties"][item] = {"type": item_type,
                                                             "format": self._config['formatInteger']}
            elif item_type == "number":
                omf_type[typename][1]["properties"][item] = {"type": item_type,
                                                             "format": self._config['formatNumber']}
            else:
                omf_type[typename][1]["properties"][item] = {"type": item_type}

        if _log_debug_level == 3:
            self._logger.debug("_create_omf_type_automatic - sensor_id |{0}| - omf_type |{1}| "
                               .format(sensor_id, str(omf_type)))

        await self.send_in_memory_data_to_picromf("Type", omf_type[typename])

        return typename, omf_type
