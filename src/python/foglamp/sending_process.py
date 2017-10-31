#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" The sending process is run according to a schedule in order to send reading data
to the historian, e.g. the PI system.
It’s role is to implement the rules as to what needs to be sent and when,
extract the data from the storage subsystem and stream it to the translator
for sending to the external system.
The sending process does not implement the protocol used to send the data,
that is devolved to the translation plugin in order to allow for flexibility
in the translation process.

"""

import resource

import asyncio
import sys
import time
import importlib
import logging
import datetime

from foglamp.parser import Parser
from foglamp.storage.storage import Storage, Readings
from foglamp import logger, statistics, configuration_manager

import foglamp.storage.payload_builder as payload_builder


__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"
""" Module information """

_MODULE_NAME = "sending_process"

_MESSAGES_LIST = {

    # Information messages
    "i000001": "Started.",
    "i000002": "Execution completed.",
    "i000003": _MODULE_NAME + " disabled.",
    "i000004": "no data will be sent, the stream id is disabled - stream id |{0}|",

    # Warning / Error messages
    "e000000": "general error",
    "e000001": "cannot start the logger - error details |{0}|",
    "e000002": "cannot complete the operation - error details |{0}|",
    "e000003": "cannot complete the retrieval of the configuration",
    "e000004": "cannot complete the initialization - error details |{0}|",
    "e000005": "cannot load the plugin |{0}|",
    "e000006": "cannot complete the sending operation of a block of data.",
    "e000007": "cannot complete the termination of the sending process.",
    "e000008": "unknown data source, it could be only: readings, statistics or audit.",
    "e000009": "cannot load data into memory - error details |{0}|",
    "e000010": "cannot update statistics.",
    "e000011": "invalid input parameters, the stream id is required and it should be a number "
               "- parameters |{0}|",
    "e000012": "cannot connect to the DB Layer - error details |{0}|",
    "e000013": "cannot validate the stream id - error details |{0}|",
    "e000014": "multiple streams having same id are defined - stream id |{0}|",
    "e000015": "the selected plugin is not a valid translator - plug in type/name |{0} / {1}|",
    "e000016": "invalid stream id, it is not defined - stream id |{0}|",
    "e000017": "cannot handle command line parameters - error details |{0}|",
    "e000018": "cannot initialize the plugin |{0}|",
    "e000019": "cannot retrieve the starting point for sending operation.",
    "e000020": "cannot update the reached position - error details |{0}|",
    "e000021": "cannot complete the sending operation - error details |{0}|",
    "e000022": "unable to convert in memory data structure related to the statistics data "
               "- error details |{0}|",
    "e000023": "cannot complete the initialization - error details |{0}|",

    "e000024": "unable to log the operation in the Storage Layer - error details |{0}|",

    "e000025": "Required argument '--name' is missing - command line |{0}|",
    "e000026": "Required argument '--port' is missing - command line |{0}|",
    "e000027": "Required argument '--address' is missing - command line |{0}|",


}
""" Messages used for Information, Warning and Error notice """

_logger = ""

_event_loop = ""

_log_debug_level = 0
""" Defines what and the level of details for logging """

_log_performance = False
""" Enable/Disable performance logging, enabled using a command line parameter"""


class PluginInitialiseFailed(RuntimeError):
    """ PluginInitializeFailed """
    pass


class UnknownDataSource(RuntimeError):
    """ the data source could be only one among: readings, statistics or audit """
    pass


class InvalidCommandLineParameters(RuntimeError):
    """ Invalid command line parameters, the stream id is the only required """
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
            process_memory = usage.ru_maxrss / 1000

            delta = datetime.datetime.now() - start
            delta_milliseconds = int(delta.total_seconds() * 1000)

            _logger.info("PERFORMANCE - {0} - milliseconds |{1:>8,}| - memory MB |{2:>8,}|"
                         .format(func.__name__,
                                 delta_milliseconds,
                                 process_memory))

        return res

    return wrapper


class LogStorage(object):
    """ Logs operations in the Storage layer """

    LOG_CODE = "STRMN"
    """ Process name for logging the operations """

    class Severity(object):
        """ Log severity level """

        SUCCESS = 0
        FAILURE = 1
        WARNING = 2
        INFO = 4

    def __init__(self, storage):

        self._storage = storage
        """ Reference to the Storage Layer """

    def write(self, level, log):
        """ Logs an operation in the Storage layer

        Args:
            level: {SUCCESS|FAILURE|WARNING|INFO}
            log: message to log as a dict
        Returns:
        Raises:
            Logs in the syslog in case of an error but the exception is not propagated
        """

        try:
            payload = payload_builder.PayloadBuilder() \
                .INSERT(code=LogStorage.LOG_CODE,
                        level=level,
                        log=log) \
                .payload()

            self._storage.insert_into_tbl("log", payload)

        except Exception as _ex:
            _message = _MESSAGES_LIST["e000024"].format(_ex)

            _logger.error(_message)


class SendingProcess:
    """ SendingProcess """

    # Filesystem path where the translators reside
    _TRANSLATOR_PATH = "foglamp.translators."

    # Define the type of the plugin managed by the Sending Process
    _PLUGIN_TYPE = "translator"

    # Types of sources for the data blocks
    _DATA_SOURCE_READINGS = "readings"
    _DATA_SOURCE_STATISTICS = "statistics"
    _DATA_SOURCE_AUDIT = "audit"

    # Configuration retrieved from the Configuration Manager
    _CONFIG_CATEGORY_NAME = 'SEND_PR'
    _CONFIG_CATEGORY_DESCRIPTION = 'Configuration of the Sending Process'

    _CONFIG_DEFAULT = {
        "enable": {
            "description": "A switch that can be used to enable or disable execution of "
                           "the sending process.",
            "type": "boolean",
            "default": "True"
        },
        "duration": {
            "description": "How long the sending process should run (in seconds) before stopping.",
            "type": "integer",
            "default": "60"
        },
        "source": {
            "description": "Defines the source of the data to be sent on the stream, "
                           "this may be one of either readings, statistics or audit.",
            "type": "string",
            "default": _DATA_SOURCE_READINGS
        },
        "blockSize": {
            "description": "The size of a block of readings to send in each transmission.",
            "type": "integer",
            "default": "5000"
        },
        "sleepInterval": {
            "description": "A period of time, expressed in seconds, "
                           "to wait between attempts to send readings when there are no "
                           "readings to be sent.",
            "type": "integer",
            "default": "5"
        },
        "translator": {
            "description": "The name of the translator to use to translate the readings "
                           "into the output format and send them",
            "type": "string",
            "default": "omf_translator"
        },

    }

    def __init__(self, _mgt_name, _mgt_port, _mgt_address):
        """

        Args:
            _mgt_name: Unique name that represents the microservice
            _mgt_port: Dynamic port of the management API - Used by the Storage layer
            _mgt_address: IP address of the server for the management API - Used by the Storage layer

        Returns:
        Raises:
        """

        # Configurations retrieved from the Configuration Manager
        self._config = {
            'enable': self._CONFIG_DEFAULT['enable']['default'],
            'duration': int(self._CONFIG_DEFAULT['duration']['default']),
            'source': self._CONFIG_DEFAULT['source']['default'],
            'blockSize': int(self._CONFIG_DEFAULT['blockSize']['default']),
            'sleepInterval': int(self._CONFIG_DEFAULT['sleepInterval']['default']),
            'translator': self._CONFIG_DEFAULT['translator']['default'],
        }
        self._config_from_manager = ""

        # Plugin handling - loading an empty plugin
        self._module_template = self._TRANSLATOR_PATH + "empty_translator"
        self._plugin = importlib.import_module(self._module_template)
        self._plugin_info = {
            'name': "",
            'version': "",
            'type': "",
            'interface': "",
            'config': ""
        }

        self._mgt_name = _mgt_name
        self._mgt_port = _mgt_port
        self._mgt_address = _mgt_address
        ''' Parameters for the Storage layer '''

        self._storage = Storage(_mgt_address, _mgt_port)
        self._readings = Readings(_mgt_address, _mgt_port)
        """" Interfaces to the FogLAMP Storage Layer """

        self._log_storage = LogStorage(self._storage)
        """" Used to log operations in the Storage Layer """

    def _retrieve_configuration(self, stream_id):
        """ Retrieves the configuration from the Configuration Manager

        Args:
            stream_id: managed stream id

        Returns:
        Raises:
        .. todo::
        """

        _logger.debug("{0} - ".format("_retrieve_configuration"))

        try:
            config_category_name = self._CONFIG_CATEGORY_NAME + "_" + str(stream_id)

            _event_loop.run_until_complete(configuration_manager.create_category(
                                                         config_category_name,
                                                         self._CONFIG_DEFAULT,
                                                         self._CONFIG_CATEGORY_DESCRIPTION))
            _config_from_manager = _event_loop.run_until_complete(
                                            configuration_manager.get_category_all_items
                                            (config_category_name))

            # Retrieves the configurations and apply the related conversions
            self._config['enable'] = True if _config_from_manager['enable']['value'].upper() == 'TRUE' else False
            self._config['duration'] = int(_config_from_manager['duration']['value'])
            self._config['source'] = _config_from_manager['source']['value']

            self._config['blockSize'] = int(_config_from_manager['blockSize']['value'])
            self._config['sleepInterval'] = int(_config_from_manager['sleepInterval']['value'])
            self._config['translator'] = _config_from_manager['translator']['value']

        except Exception:
            _message = _MESSAGES_LIST["e000003"]

            _logger.error(_message)
            raise

    def _plugin_load(self):
        """ Loads the plugin

        Args:
        Returns:
        Raises:
        Todo:
        """

        module_to_import = self._TRANSLATOR_PATH + self._config['translator']

        try:
            self._plugin = importlib.import_module(module_to_import)

        except ImportError:
            _message = _MESSAGES_LIST["e000005"].format(module_to_import)

            _logger.error(_message)
            raise

    def start(self, stream_id):
        """ Setup the correct state for the Sending Process

        Args:
            stream_id: managed stream id
        Returns:
            False = the sending process is disabled
        Raises:
            PluginInitialiseFailed
        Todo:
        """

        exec_sending_process = False

        _logger.debug("{0} - ".format("start"))

        try:
            prg_text = ", for Linux (x86_64)"

            start_message = "" + _MODULE_NAME + "" + prg_text + " " + __copyright__ + " "
            _logger.info("{0}".format(start_message))
            _logger.info(_MESSAGES_LIST["i000001"])

            if self._is_stream_id_valid(stream_id):

                self._retrieve_configuration(stream_id)

                exec_sending_process = self._config['enable']

                if self._config['enable']:

                    self._plugin_load()

                    self._plugin._log_debug_level = _log_debug_level
                    self._plugin._log_performance = _log_performance

                    self._plugin_info = self._plugin.plugin_retrieve_info(stream_id)

                    _logger.debug("{0} - {1} - {2} ".format("start",
                                                            self._plugin_info['name'],
                                                            self._plugin_info['version']))

                    if self._is_translator_valid():
                        try:
                            self._plugin._storage = self._storage

                            self._plugin.plugin_init()

                        except Exception as e:
                            _message = _MESSAGES_LIST["e000018"].format(self._plugin_info['name'])

                            _logger.error(_message)
                            raise PluginInitialiseFailed(e)
                    else:
                        exec_sending_process = False

                        _message = _MESSAGES_LIST["e000015"].format(self._plugin_info['type'],
                                                                    self._plugin_info['name'])
                        _logger.warning(_message)

                else:
                    _message = _MESSAGES_LIST["i000003"]

                    _logger.info(_message)

        except Exception as _ex:
            _message = _MESSAGES_LIST["e000004"].format(str(_ex))

            _logger.error(_message)

            self._log_storage.write(LogStorage.Severity.FAILURE, {"error - on start": _message})
            raise

        return exec_sending_process

    def stop(self):
        """ Terminates the sending process and the related plugin

        Args:
        Returns:
        Raises:
        Todo:
        """

        try:
            self._plugin.plugin_shutdown()

        except Exception:
            _message = _MESSAGES_LIST["e000007"]

            _logger.error(_message)

            self._log_storage.write(LogStorage.Severity.FAILURE, {"error - on stop": _message})
            raise

    def _load_data_into_memory(self, last_object_id):
        """ Identifies the data source requested and call the appropriate handler

        Args:
        Returns:
            data_to_send: a list of elements having each the structure :
                row id     - integer
                asset code - string
                timestamp  - timestamp
                value      - dictionary, like for example {"lux": 53570.172}

        Raises:
            UnknownDataSource
        Todo:
        """

        _logger.debug("{0} ".format("_load_data_into_memory"))

        try:
            if self._config['source'] == self._DATA_SOURCE_READINGS:
                data_to_send = self._load_data_into_memory_readings(last_object_id)

            elif self._config['source'] == self._DATA_SOURCE_STATISTICS:
                data_to_send = self._load_data_into_memory_statistics(last_object_id)

            elif self._config['source'] == self._DATA_SOURCE_AUDIT:
                data_to_send = self._load_data_into_memory_audit(last_object_id)

            else:
                _message = _MESSAGES_LIST["e000008"]

                _logger.error(_message)
                raise UnknownDataSource

        except Exception:
            _message = _MESSAGES_LIST["e000009"]

            _logger.error(_message)
            raise

        return data_to_send

    @_performance_log
    def _load_data_into_memory_readings(self, last_object_id):
        """ Extracts from the DB Layer data related to the readings loading into a memory structure

        Args:
            last_object_id: last value already handled
        Returns:
            raw_data: data extracted from the DB Layer
        Raises:
        Todo:
        """

        _logger.debug("{0} - position {1} ".format("_load_data_into_memory_readings", last_object_id))

        try:
            # Loads data
            payload = payload_builder.PayloadBuilder() \
                .WHERE(['id', '>', last_object_id]) \
                .LIMIT(self._config['blockSize']) \
                .ORDER_BY(['id', 'ASC']) \
                .payload()

            readings = self._readings.query(payload)

            raw_data = readings['rows']

        except Exception as _ex:
            _message = _MESSAGES_LIST["e000009"].format(str(_ex))

            _logger.error(_message)
            raise

        return raw_data

    @_performance_log
    def _load_data_into_memory_statistics(self, last_object_id):
        """ Extracts statistics data from the DB Layer, converts it into the proper format
            loading into a memory structure

        Args:
            last_object_id: last row_id already handled

        Returns:
            converted_data: data extracted from the DB Layer and converted in the proper format
        Raises:
        Todo:
        """

        _logger.debug("{0} - position |{1}| ".format("_load_data_into_memory_statistics", last_object_id))

        try:
            payload = payload_builder.PayloadBuilder() \
                .WHERE(['id', '>', last_object_id]) \
                .LIMIT(self._config['blockSize']) \
                .ORDER_BY(['id', 'ASC']) \
                .payload()

            statistics_history = self._storage.query_tbl_with_payload('statistics_history', payload)

            raw_data = statistics_history['rows']

            converted_data = self._transform_in_memory_data_statistics(raw_data)

        except Exception:
            _message = _MESSAGES_LIST["e000009"]

            _logger.error(_message)
            raise

        return converted_data

    @staticmethod
    def _transform_in_memory_data_statistics(raw_data):
        """ Transforms statistics data retrieved form the DB layer to the proper format

        Args:
            raw_data: list to convert having the structure
                row id     : int
                asset code : string
                timestamp  : timestamp
                value      : int

        Returns:
            converted_data: converted data
        Raises:
        Todo:
        """

        converted_data = []

        # Extracts only the asset_code column
        # and renames the columns to id, asset_code, user_ts, reading

        try:
            for row in raw_data:

                # Removes spaces
                asset_code = row['key'].strip()

                new_row = {
                    'id': row['id'],                    # Row id
                    'asset_code': asset_code,           # Asset code
                    'user_ts': row['ts'],               # Timestamp
                    'reading': {'value': row['value']}  # Converts raw data to a Dictionary
                }

                converted_data.append(new_row)

        except Exception as e:
            _message = _MESSAGES_LIST["e000022"].format(str(e))

            _logger.error(_message)
            raise e

        return converted_data

    def _load_data_into_memory_audit(self, last_object_id):
        """ Extracts from the DB Layer data related to the statistics audit into the memory
        #

        Args:
        Returns:
        Raises:
        Todo: TO BE IMPLEMENTED
        """

        _logger.debug("{0} - position {1} ".format("_load_data_into_memory_audit", last_object_id))

        try:
            # Temporary code
            if self._module_template != "":
                raw_data = ""
            else:
                raw_data = ""

        except Exception:
            _message = _MESSAGES_LIST["e000000"]

            _logger.error(_message)
            raise

        return raw_data

    def _last_object_id_read(self, stream_id):
        """ Retrieves the starting point for the send operation

        Args:
            stream_id: managed stream id

        Returns:
            last_object_id: starting point for the send operation

        Raises:
        Todo:
            it should evolve using the DB layer
        """

        try:
            where = 'id={0}'.format(stream_id)
            streams = self._storage.query_tbl('streams', where)
            rows = streams['rows']

            if len(rows) == 0:
                _message = _MESSAGES_LIST["e000016"].format(str(stream_id))
                raise ValueError(_message)

            elif len(rows) > 1:

                _message = _MESSAGES_LIST["e000014"].format(str(stream_id))
                raise ValueError(_message)

            else:
                last_object_id = rows[0]['last_object']
                _logger.debug("{0} - last_object id |{1}| ".format("_last_object_id_read", last_object_id))

        except Exception:
            _message = _MESSAGES_LIST["e000019"]

            _logger.error(_message)
            raise

        return last_object_id

    def _is_stream_id_valid(self, stream_id):
        """ Checks if the provided stream id  is valid

        Args:
            stream_id: managed stream id
        Returns:
            True/False
        Raises:
        Todo:
            it should evolve using the DB layer
        """

        try:
            streams = self._storage.query_tbl('streams', 'id={0}'.format(stream_id))
            rows = streams['rows']

            if len(rows) == 0:
                _message = _MESSAGES_LIST["e000016"].format(str(stream_id))
                raise ValueError(_message)

            elif len(rows) > 1:

                _message = _MESSAGES_LIST["e000014"].format(str(stream_id))
                raise ValueError(_message)
            else:
                if rows[0]['active'] == 't':
                    stream_id_valid = True
                else:
                    _message = _MESSAGES_LIST["i000004"].format(stream_id)
                    _logger.info(_message)

                    stream_id_valid = False

        except Exception as e:
            _message = _MESSAGES_LIST["e000013"].format(str(e))

            _logger.error(_message)
            raise e

        return stream_id_valid

    def _last_object_id_update(self, new_last_object_id, stream_id):
        """ Updates reached position

        Args:
            new_last_object_id: Last row id already sent
            stream_id:          Managed stream id

        Todo:
            it should evolve using the DB layer

        """

        try:
            _logger.debug("Last position, sent |{0}| ".format(str(new_last_object_id)))

            # TODO : FOGL-623 - avoid the update of the field ts when it will be managed by the DB itself
            #
            payload = payload_builder.PayloadBuilder() \
                .SET(last_object=new_last_object_id, ts='now()') \
                .WHERE(['id', '=', stream_id]) \
                .payload()

            self._storage.update_tbl("streams", payload)

        except Exception as _ex:
            _message = _MESSAGES_LIST["e000020"].format(_ex)

            _logger.error(_message)
            raise

    @_performance_log
    def _send_data_block(self, stream_id):
        """ Sends a block of data to the destination using the configured plugin

        Args:
        Returns:
        Raises:
        Todo:
        """

        data_sent = False

        _logger.debug("{0} - ".format("_send_data_block"))

        try:
            last_object_id = self._last_object_id_read(stream_id)

            data_to_send = self._load_data_into_memory(last_object_id)

            if data_to_send:

                data_sent, new_last_object_id, num_sent = self._plugin.plugin_send(data_to_send, stream_id)

                if data_sent:
                    # Updates reached position, statistics and logs the operation within the Storage Layer

                    self._last_object_id_update(new_last_object_id, stream_id)

                    self._update_statistics(num_sent, stream_id)

                    self._log_storage.write(LogStorage.Severity.INFO, {"sentRows": num_sent})

        except Exception:
            _message = _MESSAGES_LIST["e000006"]

            _logger.error(_message)
            raise

        return data_sent

    def send_data(self, stream_id):
        """ Handles the sending of the data to the destination using the configured plugin
            for a defined amount of time

        Args:
        Returns:
        Raises:
        Todo:
        """

        _logger.debug("{0} - ".format("send_data"))

        try:
            start_time = time.time()
            elapsed_seconds = 0

            while elapsed_seconds < self._config['duration']:

                try:
                    data_sent = self._send_data_block(stream_id)

                except Exception as e:
                    data_sent = False

                    _message = _MESSAGES_LIST["e000021"].format(e)
                    _logger.error(_message)

                if not data_sent:
                    _logger.debug("{0} - sleeping".format("send_data"))
                    time.sleep(self._config['sleepInterval'])

                elapsed_seconds = time.time() - start_time
                _logger.debug("{0} - elapsed_seconds {1}".format(
                                                            "send_data",
                                                            elapsed_seconds))

        except Exception:
            _message = _MESSAGES_LIST["e000021"].format("")

            _logger.error(_message)

            self._log_storage.write(LogStorage.Severity.FAILURE, {"error - on send_data": _message})
            raise

    def _is_translator_valid(self):
        """ Checks if the translator has adequate characteristics to be used for sending of the data

        Args:
        Returns:
            translator_ok: True if the translator is a proper one
        Raises:
        Todo:
        """

        translator_ok = False

        try:
            if self._plugin_info['type'] == self._PLUGIN_TYPE and \
               self._plugin_info['name'] != "Empty translator":

                translator_ok = True

        except Exception:
            _message = _MESSAGES_LIST["e000000"]

            _logger.error(_message)
            raise

        return translator_ok

    @staticmethod
    def _update_statistics(num_sent, stream_id):
        """ Updates FogLAMP statistics

        Raises :
        """

        try:
            stat = 'SENT_' + str(stream_id)
            _event_loop.run_until_complete(statistics.update_statistics_value(stat, num_sent))

        except Exception:
            _message = _MESSAGES_LIST["e000010"]

            _logger.error(_message)
            raise


def handling_input_parameters():
    """ Handles command line parameters

    Returns:
        param_mgt_name: Parameter generated by the scheduler, unique name that represents the microservice.
        param_mgt_port: Parameter generated by the scheduler, Dynamic port of the management API.
        param_mgt_address: Parameter generated by the scheduler, IP address of the server for the management API.
        stream_id: Define the stream id to be used.
        log_performance: Enable/Disable the logging of the performance.
        log_debug_level: Enable/define the level of logging for the debugging 0-3.

    Raises :
        InvalidCommandLineParameters

    """

    _logger.debug("{func} - argv {v0} ".format(
                func="handling_input_parameters",
                v0=str(sys.argv[1:])))

    # Retrieves parameters
    param_mgt_name = Parser.get('--name')
    param_mgt_port = Parser.get('--port')
    param_mgt_address = Parser.get('--address')

    param_stream_id = Parser.get('--stream_id')
    param_performance_log = Parser.get('--performance_log')
    param_debug_level = Parser.get('--debug_level')

    # Evaluates mandatory parameters
    if param_mgt_port is None:
        _message = _MESSAGES_LIST["e000026"].format(str(sys.argv))
        _logger.error(_message)

        raise InvalidCommandLineParameters(_message)


    if param_stream_id is None:
        _message = _MESSAGES_LIST["e000011"].format(str(sys.argv))
        _logger.error(_message)

        raise InvalidCommandLineParameters(_message)
    else:
        try:
            stream_id = int(param_stream_id)

        except Exception:
            _message = _MESSAGES_LIST["e000011"].format(str(sys.argv))
            _logger.error(_message)

            raise InvalidCommandLineParameters(_message)

    # Evaluates optional parameters
    if param_mgt_name is None:
        _message = _MESSAGES_LIST["e000025"].format(str(sys.argv))
        _logger.warning(_message)

    if param_mgt_address is None:
        _message = _MESSAGES_LIST["e000027"].format(str(sys.argv))
        _logger.warning(_message)

    if param_performance_log is not None:
        log_performance = True
    else:
        log_performance = False

    if param_debug_level is not None:
        log_debug_level = int(param_debug_level)
    else:
        log_debug_level = 0

    _logger.debug("{func} "
                  "- name |{name}| - port |{port}| - address |{address}| "
                  "- stream_id |{stream_id}| - log_performance |{perf}| "
                  "- log_debug_level |{debug_level}|".format(
                        func="handling_input_parameters",

                        name=param_mgt_name,
                        port=param_mgt_port,
                        address=param_mgt_address,

                        stream_id=stream_id,
                        perf=log_performance,
                        debug_level=log_debug_level))

    return param_mgt_name, param_mgt_port, param_mgt_address, stream_id, log_performance, log_debug_level


if __name__ == "__main__":

    # Logger start
    try:
        _logger = logger.setup(__name__)

    except Exception as ex:
        message = _MESSAGES_LIST["e000001"].format(str(ex))
        current_time = time.strftime("%Y-%m-%d %H:%M:%S:")

        print("{0} - ERROR - {1}".format(current_time, message))
        sys.exit(1)

    # Command line parameter handling
    try:
        mgt_name, mgt_port, mgt_address, \
            input_stream_id, _log_performance, _log_debug_level \
            = handling_input_parameters()

    except Exception as ex:
        message = _MESSAGES_LIST["e000017"].format(str(ex))

        _logger.exception(message)
        sys.exit(1)

    # Instance creation
    try:
        sending_process = SendingProcess(mgt_name, mgt_port, mgt_address)

    except Exception as ex:
        message = _MESSAGES_LIST["e000023"].format(str(ex))

        _logger.exception(message)
        sys.exit(1)

    else:
        #
        # Main code
        #

        # Reconfigures the logger using the Stream ID to differentiates
        # logging from different processes
        _logger.removeHandler(_logger.handle)
        logger_name = _MODULE_NAME + "_" + str(input_stream_id)
        _logger = logger.setup(logger_name)

        try:
            # Set the debug level
            if _log_debug_level == 1:
                _logger.setLevel(logging.INFO)

            elif _log_debug_level >= 2:
                _logger.setLevel(logging.DEBUG)

            _event_loop = asyncio.get_event_loop()

            if sending_process.start(input_stream_id):
                sending_process.send_data(input_stream_id)

            sending_process.stop()

            _logger.info(_MESSAGES_LIST["i000002"])

            sys.exit(0)

        except Exception as ex:
            message = _MESSAGES_LIST["e000002"].format(str(ex))

            _logger.exception(message)
            sys.exit(1)
