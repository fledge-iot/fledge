#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" The sending process is run according to a schedule in order to send reading data
    to the historian, e.g. the PI system.
    It’s role is to implement the rules as to what needs to be sent and when,
    extract the data from the storage subsystem and stream it to the north
    for sending to the external system.
    The sending process does not implement the protocol used to send the data,
    that is devolved to the translation plugin in order to allow for flexibility
    in the translation process.
"""

import importlib
import aiohttp
import resource
import asyncio
import sys
import time
import logging
import datetime
import signal
import json
import uuid
import copy

import foglamp.plugins.north.common.common as plugin_common
from foglamp.common.parser import Parser
from foglamp.common.storage_client.storage_client import StorageClientAsync, ReadingsStorageClientAsync
from foglamp.common.storage_client import payload_builder
from foglamp.common import statistics
from foglamp.common.jqfilter import JQFilter
from foglamp.common.audit_logger import AuditLogger
from foglamp.common.process import FoglampProcess
from foglamp.common import logger

__author__ = "Stefano Simonelli, Massimiliano Pinto, Mark Riddoch, Amarendra K Sinha"
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
    "e000008": "unknown data source, it could be only: readings or statistics.",
    "e000009": "cannot load data into memory - error details |{0}|",
    "e000010": "cannot update statistics.",
    "e000011": "invalid input parameters, the stream id is required and it should be a number "
               "- parameters |{0}|",
    "e000012": "cannot connect to the DB Layer - error details |{0}|",
    "e000013": "cannot validate the stream id - error details |{0}|",
    "e000014": "multiple streams having same id are defined - stream id |{0}|",
    "e000015": "the selected plugin is not a valid north plug in type/name |{0} / {1}|",
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
    "e000028": "cannot complete the fetch operation - error details |{0}|",
    "e000029": "an error occurred  during the teardown operation - error details |{0}|",
    "e000030": "unable to create parent configurtion category",
}
""" Messages used for Information, Warning and Error notice """

_LOGGER = logger.setup(__name__)
_event_loop = ""
_log_performance = False
""" Enable/Disable performance logging, enabled using a command line parameter"""


class PluginInitialiseFailed(RuntimeError):
    """ PluginInitializeFailed """
    pass


class UnknownDataSource(RuntimeError):
    """ the data source could be only one among: readings or statistics"""
    pass


class InvalidCommandLineParameters(RuntimeError):
    """ Invalid command line parameters, the stream id is the only required """
    pass


def apply_date_format(in_data):
    """ This routine adds the default UTC zone format to the input date time string
    If a timezone (strting with + or -) is found, all the following chars
    are replaced by +00, otherwise +00 is added.
    Note: if the input zone is +02:00 no date conversion is done,
          at the time being this routine expects UTC date time values.
    Examples:
        2018-05-28 16:56:55              ==> 2018-05-28 16:56:55.000000+00
        2018-05-28 13:42:28.84           ==> 2018-05-28 13:42:28.840000+00
        2018-03-22 17:17:17.166347       ==> 2018-03-22 17:17:17.166347+00
        2018-03-22 17:17:17.166347+00:00 ==> 2018-03-22 17:17:17.166347+00
        2018-03-22 17:17:17.166347+00    ==> 2018-03-22 17:17:17.166347+00
        2018-03-22 17:17:17.166347+02:00 ==> 2018-03-22 17:17:17.166347+00
    Args:
        the date time string to format
    Returns:
        the newly formatted datetime string
    """
    # Look for timezone start with '-' a the end of the date (-XY:WZ)
    zone_index = in_data.rfind("-")
    # If index is less than 10 we don't have the trailing zone with -
    if (zone_index < 10):
        #  Look for timezone start with '+' (+XY:ZW)
        zone_index = in_data.rfind("+")
    if zone_index == -1:
        if in_data.rfind(".") == -1:
            # there are no milliseconds in the date
            in_data += ".000000"
        # Pads with 0 if needed
        in_data = in_data.ljust(26, '0')
        # Just add +00
        timestamp = in_data + "+00"
    else:
        # Remove everything after - or + and add +00
        timestamp = in_data[:zone_index] + "+00"
    return timestamp


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
            _LOGGER.info("PERFORMANCE - {0} - milliseconds |{1:>8,}| - memory MB |{2:>8,}|"
                         .format(func.__name__,
                                 delta_milliseconds,
                                 process_memory))
        return res

    return wrapper


def handling_input_parameters():
    """ Handles command line parameters"""
    param_performance_log = Parser.get('--performance_log')
    param_debug_level = Parser.get('--debug_level')
    if param_performance_log is not None:
        log_performance = True
    else:
        log_performance = False
    if param_debug_level is not None:
        log_debug_level = int(param_debug_level)
    else:
        log_debug_level = 0

    return log_performance, log_debug_level


class SendingProcess(FoglampProcess):
    """ SendingProcess """
    _logger = None  # type: logging.Logger
    _stop_execution = False
    """ sets to True when a signal is captured and a termination is needed """
    TASK_FETCH_SLEEP = 0.5
    """ The amount of time the fetch operation will sleep if there are no more data to load or in case of an error """
    TASK_SEND_SLEEP = 0.5
    """ The amount of time the sending operation will sleep in case of an error """
    TASK_SLEEP_MAX_INCREMENTS = 4
    """ Maximum number of increments for the sleep handling, the amount of time is doubled at every sleep """
    TASK_SEND_UPDATE_POSITION_MAX = 10
    """ the position is updated after the specified numbers of interactions of the sending task """
    _NORTH_PATH = "foglamp.plugins.north."
    """Filesystem path where the norths reside"""
    _PLUGIN_TYPE = "north"
    """Define the type of the plugin managed by the Sending Process"""

    _AUDIT_CODE = "STRMN"
    """Audit code to use"""

    _CONFIG_CATEGORY_NAME = 'SEND_PR'
    _CONFIG_CATEGORY_DESCRIPTION = 'Sending Process'
    _CONFIG_DEFAULT = {
        "enable": {
            "description": "Enable execution of the sending process",
            "type": "boolean",
            "default": "True"
        },
        "duration": {
            "description": "Time in seconds the sending process should run",
            "type": "integer",
            "default": "60"
        },
        "source": {
            "description": "Source of data to be sent on the stream. May be either readings or statistics.",
            "type": "string",
            "default": "readings"
        },
        "blockSize": {
            "description": "Bytes to send in each transmission",
            "type": "integer",
            "default": "500"
        },
        "sleepInterval": {
            "description": "Time in seconds to wait between duration checks",
            "type": "integer",
            "default": "1"
        },
        'plugin': {
            'description': 'The name of the translator to use to translate the readings into the output format and send them.',
            'type': 'string',
            'default': 'omf'
        },
        "memory_buffer_size": {
            "description": "Number of elements of blockSize size to be buffered in memory",
            "type": "integer",
            "default": "10"
        },
        "destination_id": {
            "description": "Destination ID",
            "type": "integer",
            "default": "1"
        },
        "stream_id": {
            "description": "Stream ID",
            "type": "integer",
            "default": "0"
        }
    }

    def __init__(self, loop=None):
        super().__init__()

        if not SendingProcess._logger:
            SendingProcess._logger = _LOGGER
        self._config = {
            'enable': self._CONFIG_DEFAULT['enable']['default'],
            'duration': int(self._CONFIG_DEFAULT['duration']['default']),
            'source': self._CONFIG_DEFAULT['source']['default'],
            'blockSize': int(self._CONFIG_DEFAULT['blockSize']['default']),
            'sleepInterval': float(self._CONFIG_DEFAULT['sleepInterval']['default']),
            'memory_buffer_size': int(self._CONFIG_DEFAULT['memory_buffer_size']['default']),
        }
        self._config_from_manager = ""
        self._module_template = self._NORTH_PATH + "empty." + "empty"
        self._plugin = importlib.import_module(self._module_template)
        self._plugin_info = {
            'name': "",
            'version': "",
            'type': "",
            'interface': "",
            'config': ""
        }
        self._plugin_handle = None
        self.statistics_key = None
        self._readings = None
        """" Interfaces to the FogLAMP Storage Layer """
        self._audit = None
        """" Used to log operations in the Storage Layer """
        self._log_performance = None
        """ Enable/Disable performance logging, enabled using a command line parameter"""
        self._debug_level = None
        """ Defines what and the level of details for logging """
        self._task_fetch_data_run = True
        self._task_send_data_run = True
        """" The specific task will run until the value is True """
        self._task_fetch_data_task_id = None
        self._task_send_data_task_id = None
        """" Used to to managed the fetch/send operations """
        self._task_fetch_data_sem = None
        self._task_send_data_sem = None
        """" Semaphores used for the synchronization of the fetch/send operations """
        self._memory_buffer = [None]
        """" In memory buffer where the data is loaded from the storage layer before to send it to the plugin """
        self._memory_buffer_fetch_idx = 0
        self._memory_buffer_send_idx = 0
        """" Used to to managed the in memory buffer for the fetch/send operations """
        self._event_loop = asyncio.get_event_loop() if loop is None else loop

    @staticmethod
    def _signal_handler(_signal_num, _stack_frame):
        """ Handles signals to properly terminate the execution"""
        SendingProcess._stop_execution = True
        SendingProcess._logger.info(
            "{func} - signal captured |{signal_num}| ".format(func="_signal_handler", signal_num=_signal_num))

    @staticmethod
    def performance_track(message):
        """ Tracks information for performance measurement"""
        if _log_performance:
            usage = resource.getrusage(resource.RUSAGE_SELF)
            process_memory = usage.ru_maxrss / 1000

    async def _update_statistics(self, num_sent):
        """ Updates FogLAMP statistics"""
        try:
            key = self.statistics_key
            _stats = await statistics.create_statistics(self._storage_async)
            await _stats.update(key, num_sent)
        except Exception:
            _message = _MESSAGES_LIST["e000010"]
            SendingProcess._logger.error(_message)
            raise

    async def _last_object_id_update(self, new_last_object_id):
        """ Updates reached position"""
        try:
            payload = payload_builder.PayloadBuilder() \
                .SET(last_object=new_last_object_id, ts='now()') \
                .WHERE(['id', '=', self._stream_id]) \
                .payload()
            await self._storage_async.update_tbl("streams", payload)
        except Exception as _ex:
            SendingProcess._logger.error(_MESSAGES_LIST["e000020"].format(_ex))
            raise

    async def _update_position_reached(self, update_last_object_id, tot_num_sent):
        """ Updates last_object_id, statistics and audit"""
        await self._last_object_id_update(update_last_object_id)
        await self._update_statistics(tot_num_sent)
        await self._audit.information(self._AUDIT_CODE, {"sentRows": tot_num_sent})

    async def _task_send_data(self):
        """ Sends the data from the in memory structure to the destination using the loaded plugin"""
        data_sent = False
        db_update = False
        update_last_object_id = 0
        tot_num_sent = 0
        update_position_idx = 0

        try:
            self._memory_buffer_send_idx = 0
            sleep_time = self.TASK_SEND_SLEEP
            sleep_num_increments = 1

            while self._task_send_data_run:
                slept = False
                if self._memory_buffer_send_idx < self._config['memory_buffer_size']:
                    new_last_object_id = None
                    num_sent = 0
                    if self._memory_buffer[self._memory_buffer_send_idx] is not None:  # if there are data to send
                        try:
                            data_sent, new_last_object_id, num_sent = \
                                await self._plugin.plugin_send(self._plugin_handle,
                                                               self._memory_buffer[self._memory_buffer_send_idx], self._stream_id)
                        except Exception as ex:
                            _message = _MESSAGES_LIST["e000021"].format(ex)
                            SendingProcess._logger.error(_message)
                            await self._audit.failure(self._AUDIT_CODE, {"error - on _task_send_data": _message})
                            data_sent = False
                            slept = True
                            await asyncio.sleep(sleep_time)

                        if data_sent:
                            db_update = True
                            update_last_object_id = new_last_object_id
                            tot_num_sent = tot_num_sent + num_sent
                            self._memory_buffer[self._memory_buffer_send_idx] = None
                            self._memory_buffer_send_idx += 1
                            self._task_send_data_sem.release()
                            self.performance_track("task _task_send_data")
                    else:
                        # Updates the position before going to wait for the semaphore
                        if db_update:
                            await self._update_position_reached(update_last_object_id, tot_num_sent)
                            update_position_idx = 0
                            tot_num_sent = 0
                            db_update = False
                        await self._task_fetch_data_sem.acquire()

                    # Updates the Storage layer every 'self.UPDATE_POSITION_MAX' interactions
                    if db_update:
                        if update_position_idx >= self.TASK_SEND_UPDATE_POSITION_MAX:
                            await self._update_position_reached(update_last_object_id, tot_num_sent)
                            update_position_idx = 0
                            tot_num_sent = 0
                            db_update = False
                        else:
                            update_position_idx += 1
                else:
                    self._memory_buffer_send_idx = 0

                # Handles the sleep time, it is doubled every time up to a limit
                if slept:
                    sleep_num_increments += 1
                    sleep_time *= 2
                    if sleep_num_increments > self.TASK_SLEEP_MAX_INCREMENTS:
                        sleep_time = self.TASK_SEND_SLEEP
                        sleep_num_increments = 1

            # Checks if the information on the Storage layer needs to be updates
            if db_update:
                await self._update_position_reached(update_last_object_id, tot_num_sent)
        except Exception as ex:
            SendingProcess._logger.error(_MESSAGES_LIST["e000021"].format(ex))
            if db_update:
                await self._update_position_reached(update_last_object_id, tot_num_sent)
            await self._audit.failure(self._AUDIT_CODE, {"error - on _task_send_data": _message})
            raise

    @staticmethod
    def _transform_in_memory_data_statistics(raw_data):
        converted_data = []
        try:
            for row in raw_data:
                timestamp = apply_date_format(row['ts'])  # Adds timezone UTC
                asset_code = row['key'].strip()
                new_row = {
                    'id': row['id'],
                    'asset_code': asset_code,
                    'read_key': str(uuid.uuid4()),
                    'reading': {'value': row['value']},
                    'user_ts': timestamp,
                }
                converted_data.append(new_row)
        except Exception as e:
            SendingProcess._logger.error(_MESSAGES_LIST["e000022"].format(str(e)))
            raise e
        return converted_data

    async def _load_data_into_memory_statistics(self, last_object_id):
        """ Extracts statistics data from the DB Layer, converts it into the proper format"""
        raw_data = None
        try:
            payload = payload_builder.PayloadBuilder() \
                .SELECT("id", "key", '{"column": "ts", "timezone": "UTC"}', "value", "history_ts") \
                .WHERE(['id', '>', last_object_id]) \
                .LIMIT(self._config['blockSize']) \
                .ORDER_BY(['id', 'ASC']) \
                .payload()
            statistics_history = await self._storage_async.query_tbl_with_payload('statistics_history', payload)
            raw_data = statistics_history['rows']
            converted_data = self._transform_in_memory_data_statistics(raw_data)
        except Exception:
            SendingProcess._logger.error(_MESSAGES_LIST["e000009"])
            raise
        return converted_data

    @staticmethod
    def _transform_in_memory_data_readings(raw_data):
        converted_data = []
        try:
            for row in raw_data:
                # Converts values to the proper types, for example "180.2" to float 180.2
                payload = row['reading']
                for key in list(payload.keys()):
                    value = payload[key]
                    payload[key] = plugin_common.convert_to_type(value)
                timestamp = apply_date_format(row['user_ts'])  # Adds timezone UTC
                new_row = {
                    'id': row['id'],
                    'asset_code': row['asset_code'],
                    'read_key': row['read_key'],
                    'reading': payload,
                    'user_ts': timestamp
                }
                converted_data.append(new_row)
        except Exception as e:
            SendingProcess._logger.error(_MESSAGES_LIST["e000022"].format(str(e)))
            raise e
        return converted_data

    async def _load_data_into_memory_readings(self, last_object_id):
        """ Extracts from the DB Layer data related to the readings loading into a memory structure"""
        raw_data = None
        converted_data = []
        try:
            # Loads data, +1 as > is needed
            readings = await self._readings.fetch(last_object_id + 1, self._config['blockSize'])
            raw_data = readings['rows']
            converted_data = self._transform_in_memory_data_readings(raw_data)
        except aiohttp.client_exceptions.ClientPayloadError as _ex:
            SendingProcess._logger.warning(_MESSAGES_LIST["e000009"].format(str(_ex)))
        except Exception as _ex:
            SendingProcess._logger.error(_MESSAGES_LIST["e000009"].format(str(_ex)))
            raise
        return converted_data

    async def _load_data_into_memory(self, last_object_id):
        """ Identifies the data source requested and call the appropriate handler"""
        try:
            if self._config['source'] == 'readings':
                data_to_send = await self._load_data_into_memory_readings(last_object_id)
            elif self._config['source'] == 'statistics':
                data_to_send = await self._load_data_into_memory_statistics(last_object_id)
            else:
                SendingProcess._logger.error(_MESSAGES_LIST["e000008"])
                raise UnknownDataSource
        except Exception:
            SendingProcess._logger.error(_MESSAGES_LIST["e000009"])
            raise
        return data_to_send

    async def _last_object_id_read(self):
        """ Retrieves the starting point for the send operation"""
        try:
            where = 'id={0}'.format(self._stream_id)
            streams = await self._storage_async.query_tbl('streams', where)
            rows = streams['rows']
            if len(rows) == 0:
                raise ValueError(_MESSAGES_LIST["e000016"].format(str(self._stream_id)))
            elif len(rows) > 1:
                raise ValueError(_MESSAGES_LIST["e000014"].format(str(self._stream_id)))
            else:
                last_object_id = rows[0]['last_object']
        except Exception:
            SendingProcess._logger.error(_MESSAGES_LIST["e000019"])
            raise
        return last_object_id

    async def _task_fetch_data(self):
        """ Read data from the Storage Layer into a memory structure"""
        try:
            last_object_id = await self._last_object_id_read()
            self._memory_buffer_fetch_idx = 0
            sleep_time = self.TASK_FETCH_SLEEP
            sleep_num_increments = 1
            while self._task_fetch_data_run:
                slept = False
                if self._memory_buffer_fetch_idx < self._config['memory_buffer_size']:
                    # Checks if there is enough space to load a new block of data
                    if self._memory_buffer[self._memory_buffer_fetch_idx] is None:
                        try:
                            data_to_send = await self._load_data_into_memory(last_object_id)
                        except Exception as ex:
                            _message = _MESSAGES_LIST["e000028"].format(ex)
                            SendingProcess._logger.error(_message)
                            await self._audit.failure(self._AUDIT_CODE, {"error - on _task_fetch_data": _message})
                            data_to_send = False
                            slept = True
                            await asyncio.sleep(sleep_time)
                        if data_to_send:
                            # Handles the JQFilter functionality
                            if self._config_from_manager['applyFilter']["value"].upper() == "TRUE":
                                jqfilter = JQFilter()
                                # Steps needed to proper format the data generated by the JQFilter
                                # to the one expected by the SP
                                data_to_send_2 = jqfilter.transform(data_to_send,
                                                                    self._config_from_manager['filterRule']["value"])
                                data_to_send_3 = json.dumps(data_to_send_2)
                                del data_to_send_2
                                data_to_send_4 = eval(data_to_send_3)
                                del data_to_send_3
                                data_to_send = data_to_send_4[0]
                                del data_to_send_4
                            # Loads the block of data into the in memory buffer
                            self._memory_buffer[self._memory_buffer_fetch_idx] = data_to_send
                            last_position = len(data_to_send) - 1
                            last_object_id = data_to_send[last_position]['id']
                            self._memory_buffer_fetch_idx += 1
                            self._task_fetch_data_sem.release()
                            self.performance_track("task _task_fetch_data")
                        else:
                            # There is no more data to load
                            slept = True
                            await asyncio.sleep(sleep_time)
                    else:
                        # There is no more space in the in memory buffer
                        await self._task_send_data_sem.acquire()
                else:
                    self._memory_buffer_fetch_idx = 0
                # Handles the sleep time, it is doubled every time up to a limit
                if slept:
                    sleep_num_increments += 1
                    sleep_time *= 2
                    if sleep_num_increments > self.TASK_SLEEP_MAX_INCREMENTS:
                        sleep_time = self.TASK_FETCH_SLEEP
                        sleep_num_increments = 1
        except Exception as ex:
            _message = _MESSAGES_LIST["e000028"].format(ex)
            SendingProcess._logger.error(_message)
            await self._audit.failure(self._AUDIT_CODE, {"error - on _task_fetch_data": _message})
            raise

    async def send_data(self):
        """ Handles the sending of the data to the destination using the configured plugin for a defined amount of time"""

        # Prepares the in memory buffer for the fetch/send operations
        self._memory_buffer = [None for _ in range(self._config['memory_buffer_size'])]
        self._task_fetch_data_sem = asyncio.Semaphore(0)
        self._task_send_data_sem = asyncio.Semaphore(0)
        self._task_fetch_data_task_id = asyncio.ensure_future(self._task_fetch_data())
        self._task_send_data_task_id = asyncio.ensure_future(self._task_send_data())
        self._task_fetch_data_run = True
        self._task_send_data_run = True

        try:
            start_time = time.time()
            elapsed_seconds = 0
            while elapsed_seconds < self._config['duration']:
                # Terminates the execution in case a signal has been received
                if SendingProcess._stop_execution:
                    SendingProcess._logger.info("{func} - signal received, stops the execution".format(
                        func="send_data"))
                    break
                # Context switch to either the fetch or the send operation
                await asyncio.sleep(self._config['sleepInterval'])
                elapsed_seconds = time.time() - start_time
                SendingProcess._logger.debug("{0} - elapsed_seconds {1}".format("send_data", elapsed_seconds))
        except Exception as ex:
            _message = _MESSAGES_LIST["e000021"].format(ex)
            SendingProcess._logger.error(_message)
            await self._audit.failure(self._AUDIT_CODE, {"error - on send_data": _message})

        try:
            # Graceful termination of the tasks
            self._task_fetch_data_run = False
            self._task_send_data_run = False
            # Unblocks the task if it is waiting
            self._task_fetch_data_sem.release()
            self._task_send_data_sem.release()
            await self._task_fetch_data_task_id
            await self._task_send_data_task_id
        except Exception as ex:
            SendingProcess._logger.error(_MESSAGES_LIST["e000029"].format(ex))

    async def _get_stream_id(self, config_stream_id, destination_id):
        async def get_rows_from_stream_id(stream_id):
            payload = payload_builder.PayloadBuilder() \
                .SELECT("id", "description", "active") \
                .WHERE(['id', '=', stream_id]) \
                .payload()
            streams = await self._storage_async.query_tbl_with_payload("streams", payload)
            return streams['rows']

        async def get_rows_from_name(description):
            payload = payload_builder.PayloadBuilder() \
                .SELECT("id", "description", "active") \
                .WHERE(['description', '=', description]) \
                .payload()
            streams = await self._storage_async.query_tbl_with_payload("streams", payload)
            return streams['rows']

        async def add_stream(config_stream_id, destination_id, description):
            if config_stream_id:
                payload = payload_builder.PayloadBuilder() \
                    .INSERT(id=config_stream_id,
                            destination_id=destination_id,
                            description=description) \
                    .payload()
                await self._storage_async.insert_into_tbl("streams", payload)
                rows = await get_rows_from_stream_id(stream_id=config_stream_id)
            else:
                # If an user is upgrading FogLamp, then it has got existing data in streams and destinations table but
                # no entry in configuration for streams_id and destinations_id for this process_name. Hence it must
                # check if an entry is already there for this process_name in streams table.
                rows = await get_rows_from_name(description=self._name)
                if len(rows) == 0:
                    payload = payload_builder.PayloadBuilder() \
                        .INSERT(destination_id=destination_id,
                                description=description) \
                        .payload()
                    await self._storage_async.insert_into_tbl("streams", payload)
                    rows = await get_rows_from_name(description=self._name)
            return rows[0]['id'], rows[0]['active']

        stream_id = None
        try:
            rows = await get_rows_from_stream_id(config_stream_id)
            if len(rows) == 0:
                stream_id, stream_id_valid = await add_stream(config_stream_id, destination_id, self._name)
            elif len(rows) > 1:
                raise ValueError(_MESSAGES_LIST["e000013"].format(stream_id))
            else:
                stream_id = rows[0]['id']
                if rows[0]['active'] == 't':
                    stream_id_valid = True
                else:
                    SendingProcess._logger.info(_MESSAGES_LIST["i000004"].format(stream_id))
                    stream_id_valid = False
        except Exception as e:
            SendingProcess._logger.error(_MESSAGES_LIST["e000013"].format(str(e)))
            raise e
        return stream_id, stream_id_valid

    async def _get_statistics_key(self):
        async def get_rows(key):
            payload = payload_builder.PayloadBuilder() \
                .SELECT("key", "description") \
                .WHERE(['key', '=', key]) \
                .LIMIT(1) \
                .payload()
            statistics = await self._storage_async.query_tbl_with_payload("statistics", payload)
            return statistics['rows']

        async def add_statistics(key, description):
            payload = payload_builder.PayloadBuilder() \
                .INSERT(key=key, description=description) \
                .payload()
            await self._storage_async.insert_into_tbl("statistics", payload)
            rows = await get_rows(key=key)
            return rows[0]['key']

        try:
            rows = await get_rows(key=self._name)
            statistics_key = await add_statistics(key=self._name, description=self._name) if len(rows) == 0 else rows[0]['key']
        except Exception as e:
            SendingProcess._logger.error("Unable to fetch statistics key for {} | {}".format(self._name, str(e)))
            raise e
        return statistics_key

    def _is_north_valid(self):
        """ Checks if the north has adequate characteristics to be used for sending of the data"""
        north_ok = False
        try:
            if self._plugin_info['type'] == self._PLUGIN_TYPE and \
                            self._plugin_info['name'] != "Empty North Plugin":
                north_ok = True
        except Exception:
            SendingProcess._logger.error(_MESSAGES_LIST["e000000"])
            raise
        return north_ok

    def _plugin_load(self):
        module_to_import = "{path_to}{foldername}.{filename}".format(path_to=self._NORTH_PATH,foldername=self._config['plugin'],filename=self._config['plugin'])
        try:
            self._plugin = __import__(module_to_import, fromlist=[''])
        except ImportError:
            SendingProcess._logger.error(_MESSAGES_LIST["e000005"].format(module_to_import))
            raise

    def _fetch_configuration(self, cat_name=None, cat_desc=None, cat_config=None, cat_keep_original=False):
        """ Retrieves the configuration from the Configuration Manager"""
        try:
            config_payload = json.dumps({
                "key": cat_name,
                "description": cat_desc,
                "value": cat_config,
                "keep_original_items": cat_keep_original
            })
            self._core_microservice_management_client.create_configuration_category(config_payload)
            _config_from_manager = self._core_microservice_management_client.get_configuration_category(category_name=cat_name)

            # Create the parent category for all north services
            try:
                parent_payload = json.dumps({"key": "North", "description": "North tasks", "value": {},
                                             "children": [cat_name], "keep_original_items": True})
                self._core_microservice_management_client.create_configuration_category(parent_payload)
            except KeyError:
                _LOGGER.error("Failed to create North parent configuration category for sending process")
                raise
            return _config_from_manager
        except Exception:
            SendingProcess._logger.error(_MESSAGES_LIST["e000003"])
            raise

    def _retrieve_configuration(self, cat_name=None, cat_desc=None, cat_config=None, cat_keep_original=False):
        """ Retrieves the configuration from the Configuration Manager"""
        try:
            _config_from_manager = self._fetch_configuration(cat_name,
                                                             cat_desc,
                                                             cat_config,
                                                             cat_keep_original)
            # Retrieves the configurations and apply the related conversions
            self._config['enable'] = True if _config_from_manager['enable']['value'].upper() == 'TRUE' else False
            self._config['duration'] = int(_config_from_manager['duration']['value'])
            self._config['source'] = _config_from_manager['source']['value']
            self._config['blockSize'] = int(_config_from_manager['blockSize']['value'])
            self._config['sleepInterval'] = float(_config_from_manager['sleepInterval']['value'])
            self._config['plugin'] = _config_from_manager['plugin']['value']
            self._config['memory_buffer_size'] = int(_config_from_manager['memory_buffer_size']['value'])
            _config_from_manager['_CONFIG_CATEGORY_NAME'] = cat_name
            self._config["stream_id"] = int(_config_from_manager['stream_id']['value'])
            self._config["destination_id"] = int(_config_from_manager['destination_id']['value'])
            self._config_from_manager = _config_from_manager
        except Exception:
            SendingProcess._logger.error(_MESSAGES_LIST["e000003"])
            raise

    async def _start(self):
        """ Setup the correct state for the Sending Process"""
        exec_sending_process = False
        try:
            SendingProcess._logger.debug("{}, for  Linux (x86_64) {}".format(_MODULE_NAME, __copyright__))
            SendingProcess._logger.info("Started")

            # config from sending process
            self._retrieve_configuration(cat_name=self._name,
                                         cat_desc=self._CONFIG_CATEGORY_DESCRIPTION,
                                         cat_config=self._CONFIG_DEFAULT,
                                         cat_keep_original=True)

            # Fetch destination_id and stream_id
            self._destination_id = self._config["destination_id"]  # always 1 for now
            self._stream_id, is_stream_valid = await self._get_stream_id(self._config["stream_id"], self._destination_id)
            if is_stream_valid is False:
                raise ValueError("Error in Stream Id for Sending Process {}".format(self._name))
            self.statistics_key = await self._get_statistics_key()

            # update configuration with the new destination_id and stream_id
            self._core_microservice_management_client.update_configuration_item(
                                                category_name=self._name,
                                                config_item="destination_id",
                                                category_data=json.dumps({"value": str(self._destination_id)}))
            self._core_microservice_management_client.update_configuration_item(
                                                category_name=self._name,
                                                config_item="stream_id",
                                                category_data=json.dumps({"value": str(self._stream_id)}))

            exec_sending_process = self._config['enable']

            if self._config['enable']:
                self._plugin_load()
                self._plugin_info = self._plugin.plugin_info()
                if self._is_north_valid():
                    try:
                        # Fetch plugin configuration
                        self._retrieve_configuration(cat_name=self._name,
                                                     cat_desc=self._CONFIG_CATEGORY_DESCRIPTION,
                                                     cat_config=self._plugin_info['config'],
                                                     cat_keep_original=True)
                        data = self._config_from_manager

                        # Append stream_id, destination_id etc to payload to be send to the plugin init
                        data['stream_id'] = self._stream_id
                        data['destination_id'] = self._destination_id
                        data['debug_level'] = self._debug_level
                        data['log_performance'] = self._log_performance
                        data.update({'sending_process_instance': self})
                        self._plugin_handle = self._plugin.plugin_init(data)
                    except Exception as e:
                        _message = _MESSAGES_LIST["e000018"].format(self._config['plugin'])
                        SendingProcess._logger.error(_message)
                        raise PluginInitialiseFailed(e)
                else:
                    exec_sending_process = False
                    _message = _MESSAGES_LIST["e000015"].format(self._plugin_info['type'],
                                                                self._plugin_info['name'])
                    SendingProcess._logger.warning(_message)
            else:
                SendingProcess._logger.info(_MESSAGES_LIST["i000003"])
        except (ValueError, Exception) as _ex:
            _message = _MESSAGES_LIST["e000004"].format(str(_ex))
            SendingProcess._logger.error(_message)
            await self._audit.failure(self._AUDIT_CODE, {"error - on start": _message})
            raise
        return exec_sending_process

    async def run(self):
        global _log_performance
        global _LOGGER

        # Setups signals handlers, to properly handle the termination
        # a) SIGTERM - 15 : kill or system shutdown
        signal.signal(signal.SIGTERM, SendingProcess._signal_handler)

        # Command line parameter handling
        self._log_performance, self._debug_level = handling_input_parameters()
        _log_performance = self._log_performance

        try:
            self._storage_async = StorageClientAsync(self._core_management_host, self._core_management_port)
            self._readings = ReadingsStorageClientAsync(self._core_management_host, self._core_management_port)
            self._audit = AuditLogger(self._storage_async)
        except Exception as ex:
            SendingProcess._logger.exception(_MESSAGES_LIST["e000023"].format(str(ex)))
            sys.exit(1)
        else:
            SendingProcess._logger.removeHandler(SendingProcess._logger.handle)
            logger_name = _MODULE_NAME + "_" + self._name
            SendingProcess._logger = logger.setup(logger_name, level=logging.INFO if self._debug_level in [None, 0,
                                                                                                           1] else logging.DEBUG)
            _LOGGER = SendingProcess._logger

            try:
                is_started = await self._start()
                if is_started:
                    await self.send_data()
                self.stop()
                SendingProcess._logger.info("Execution completed.")
                sys.exit(0)
            except (ValueError, Exception) as ex:
                SendingProcess._logger.exception(_MESSAGES_LIST["e000002"].format(str(ex)))
                sys.exit(1)

    def stop(self):
        """ Terminates the sending process and the related plugin"""
        try:
            self._plugin.plugin_shutdown(self._plugin_handle)
        except Exception:
            SendingProcess._logger.error(_MESSAGES_LIST["e000007"])
            self._event_loop.run_until_complete(
                self._audit.failure(self._AUDIT_CODE, {"error - on stop": _MESSAGES_LIST["e000007"]}))
            raise
        SendingProcess._logger.info("Stopped")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    sp = SendingProcess(loop)
    loop.run_until_complete(sp.run())
