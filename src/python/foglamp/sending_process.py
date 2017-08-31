#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" The sending process is run according to a schedule in order to send reading data to the historian,
e.g. the PI system.
It’s role is to implement the rules as to what needs to be sent and when,
extract the data from the storage subsystem and stream it to the translator for sending to the external system.
The sending process does not implement the protocol used to send the data,
that is devolved to the translation plugin in order to allow for flexibility in the translation process.

"""

import resource
import argparse

import asyncio
import sys
import time
import psycopg2
import importlib
import logging
import datetime

from foglamp import logger, statistics, configuration_manager

# Module information
__author__ = "${FULL_NAME}"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# Defines what and the level of details for logging
_log_debug_level = 0
_log_performance = False

_MODULE_NAME = "Sending Process"

# Messages used for Information, Warning and Error notice
_MESSAGES_LIST = {

    # Information messages
    "i000001": "Started.",
    "i000002": "Execution completed.",
    "i000003": _MODULE_NAME + " disabled.",

    # Warning / Error messages
    "e000000": "general error",
    "e000001": "cannot setup the logger - error details |{0}|",
    "e000002": "cannot complete the operation - error details |{0}|",
    "e000003": "cannot complete the retrieval of the configuration",
    "e000004": "cannot complete the initialization",
    "e000005": "cannot load the plugin |{0}|",
    "e000006": "cannot complete the sending operation of a block of data.",
    "e000007": "cannot complete the termination of the sending process.",
    "e000008": "unknown data source, it could be only: readings, statistics or audit.",
    "e000009": "cannot complete loading data into the memory.",
    "e000010": "cannot update statistics.",
    "e000011": "invalid input parameters, the stream id is required and it should be a number - parameters |{0}|",
    "e000012": "cannot connect to the DB Layer - error details |{0}|",
    "e000013": "cannot validate the stream id - error details |{0}|",
    "e000014": "multiple streams having same id are defined - stream id |{0}|",
    "e000015": "the selected plugin is not a valid translator - plug in |{0} / {1}|",
    "e000016": "invalid stream id, it is not defined - stream id |{0}|",
    "e000017": "cannot handle command line parameters - error details |{0}|",
    "e000018": "cannot initialize the plugin |{0}|",
    "e000019": "cannot retrieve the starting point for sending operation.",
    "e000020": "cannot update the reached position.",
    "e000021": "cannot complete the sending operation - error details |{0}|",
    "e000022": "",
}

_TRANSLATOR_PATH = "foglamp.translators."
# Define the type of the plugin managed by the Sending Process
_PLUGIN_TYPE = "translator"

_DATA_SOURCE_READINGS = "readings"
_DATA_SOURCE_STATISTICS = "statistics"
_DATA_SOURCE_AUDIT = "audit"

# FIXME: set proper values
_CONFIG_DEFAULT = {
    "enable": {
        "description": "A switch that can be used to enable or disable execution of the sending process.",
        "type": "boolean",
        "default": "True"
    },
    "duration": {
        "description": "How long the sending process should run before stopping.",
        "type": "integer",
        "default": "1"
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
                       "to wait between attempts to send readings when there are no readings to be sent.",
        "type": "integer",
        "default": "1"
    },
    "translator": {
        "description": "The name of the translator to use to translate the readings "
                       "into the output format and send them",
        "type": "string",
        "default": "omf_translator_new"
        # FIXME:
        # "default": "omf_translator"
    },

}
_CONFIG_CATEGORY_NAME = 'SEND_PR'
_CONFIG_CATEGORY_DESCRIPTION = 'Configuration of the Sending Process'

# Configurations retrieved from the Configuration Manager
_config_from_manager = ""

# Configurations used in the Sending Process
_config = {
    'enable': _CONFIG_DEFAULT['enable']['default'],
    'duration': int(_CONFIG_DEFAULT['duration']['default']),
    'source': _CONFIG_DEFAULT['source']['default'],
    'blockSize': int(_CONFIG_DEFAULT['blockSize']['default']),
    'sleepInterval': int(_CONFIG_DEFAULT['sleepInterval']['default']),
    'translator': _CONFIG_DEFAULT['translator']['default'],
}

# Plugin handling - loading an empty plugin
_module_template = _TRANSLATOR_PATH + "empty_translator"
_plugin = importlib.import_module(_module_template)
_plugin_info = {
    'name': "",
    'version': "",
    'type': "",
    'interface': "",
    'config': ""
}

# DB references
_DB_CONNECTION_STRING = 'postgresql:///foglamp'
_pg_conn = ()
_pg_cur = ()

_logger = ""
_event_loop = ""
_stream_id = 0


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

    # noinspection PyProtectedMember
    def wrapper(*arg):
        """ wrapper """

        start = datetime.datetime.now()

        # Code execution
        res = func(*arg)

        if _log_performance:
            usage = resource.getrusage(resource.RUSAGE_SELF)
            process_memory = usage.ru_maxrss/1000

            delta = datetime.datetime.now() - start
            delta_milliseconds = int(delta.total_seconds() * 1000)

            _logger.info("PERFORMANCE - {0} - milliseconds |{1:>8,}| - memory MB |{2:>8,}|"
                         .format(sys._getframe().f_locals['func'],
                                 delta_milliseconds,
                                 process_memory))

        return res

    return wrapper


def _retrieve_configuration(stream_id):
    """ Retrieves the configuration from the Configuration Manager

    Args:
        stream_id - managed stream id

    Returns:
    Raises:
    Todo:
    """

    global _config_from_manager
    global _config

    try:
        _logger.debug("function _retrieve_configuration")

        config_category_name = _CONFIG_CATEGORY_NAME + "_" + str(stream_id)

        _event_loop.run_until_complete(configuration_manager.create_category(config_category_name, _CONFIG_DEFAULT,
                                                                             _CONFIG_CATEGORY_DESCRIPTION))
        _config_from_manager = _event_loop.run_until_complete(configuration_manager.get_category_all_items
                                                              (config_category_name))

        # Retrieves the configurations and apply the related conversions
        _config['enable'] = True if _config_from_manager['enable']['value'].upper() == 'TRUE' else False
        _config['duration'] = int(_config_from_manager['duration']['value'])
        _config['source'] = _config_from_manager['source']['value']

        _config['blockSize'] = int(_config_from_manager['blockSize']['value'])
        _config['sleepInterval'] = int(_config_from_manager['sleepInterval']['value'])
        _config['translator'] = _config_from_manager['translator']['value']

    except Exception:
        _message = _MESSAGES_LIST["e000003"]

        _logger.error(_message)
        raise


def _plugin_load():
    """ Loads the plugin

    Args:
    Returns:
    Raises:
    Todo:
    """

    global _plugin

    module_to_import = _TRANSLATOR_PATH + _config['translator']

    try:
        _plugin = importlib.import_module(module_to_import)

    except ImportError:
        _message = _MESSAGES_LIST["e000005"].format(module_to_import)

        _logger.error(_message)
        raise


def _sending_process_init():
    """ Setup the correct state for the Sending Process

    Args:
    Returns:
        False = the sending process is disabled
    Raises:
        PluginInitialiseFailed
    Todo:
    """

    global _plugin
    global _plugin_info

    global _pg_conn
    global _pg_cur

    try:
        prg_text = ", for Linux (x86_64)"

        start_message = "" + _MODULE_NAME + "" + prg_text + " " + __copyright__ + " "
        _logger.info("{0}".format(start_message))
        _logger.info(_MESSAGES_LIST["i000001"])

        try:
            _pg_conn = psycopg2.connect(_DB_CONNECTION_STRING)
            _pg_cur = _pg_conn.cursor()

            # FIXME:
            debug_code()

        except Exception as e:
            _message = _MESSAGES_LIST["e000012"].format(str(e))

            _logger.error(_message)
            raise
        else:
            if is_stream_id_valid(_stream_id):

                _retrieve_configuration(_stream_id)

                if _config['enable']:

                    _plugin_load()

                    _plugin._log_debug_level = _log_debug_level
                    _plugin._log_performance = _log_performance

                    _plugin_info = _plugin.retrieve_plugin_info(_stream_id)

                    _logger.debug("_sending_process_init - {0} - {1} ".format(_plugin_info['name'],
                                                                              _plugin_info['version']))

                    if _is_translator_valid():
                        try:
                            _plugin.plugin_init()

                        except Exception:
                            _message = _MESSAGES_LIST["e000018"].format(_plugin_info['name'])

                            _logger.error(_message)
                            raise PluginInitialiseFailed

                else:
                    _message = _MESSAGES_LIST["i000003"]

                    _logger.info(_message)

    except Exception:
        _message = _MESSAGES_LIST["e000004"]

        _logger.error(_message)
        raise

    return _config['enable']


def _sending_process_shutdown():
    """ Terminates the sending process and the related plugin

    Args:
    Returns:
    Raises:
    Todo:
    """

    global _plugin
    global _pg_conn

    try:
        _plugin.plugin_shutdown()

        _pg_conn.close()

    except Exception:
        _message = _MESSAGES_LIST["e000007"]

        _logger.error(_message)
        raise


@_performance_log
def _load_data_into_memory_readings(last_object_id):
    """ Extracts from the DB Layer data related to the readings loading into the memory

    Args:
    Returns:
        raw_data: data extracted from the DB Layer
    Raises:
    Todo:
    """

    global _pg_cur

    try:
        _logger.debug("_load_data_into_memory_readings")

        sql_cmd = "SELECT id, asset_code, user_ts, reading " \
                  "FROM foglamp.readings " \
                  "WHERE id> {0} " \
                  "ORDER BY id LIMIT {1}" \
            .format(last_object_id, _config['blockSize'])

        _pg_cur.execute(sql_cmd)
        raw_data = _pg_cur.fetchall()

    except Exception:
        _message = _MESSAGES_LIST["e000009"]

        _logger.error(_message)
        raise

    return raw_data


def _load_data_into_memory_statistics(last_object_id):
    """ Extracts from the DB Layer data related to the statistics loading into the memory
    #

    Args:
    Returns:
    Raises:
    Todo: TO BE IMPLEMENTED
    """

    try:
        _logger.debug("_load_data_into_memory_statistics {0}".format(last_object_id))

        raw_data = ""

    except Exception:
        _message = _MESSAGES_LIST["e000000"]

        _logger.error(_message)
        raise

    return raw_data


def _load_data_into_memory_audit(last_object_id):
    """ Extracts from the DB Layer data related to the statistics audit into the memory
    #

    Args:
    Returns:
    Raises:
    Todo: TO BE IMPLEMENTED
    """

    try:
        _logger.debug("_load_data_into_memory_audit {0} ".format(last_object_id))

        raw_data = ""

    except Exception:
        _message = _MESSAGES_LIST["e000000"]

        _logger.error(_message)
        raise

    return raw_data


def _load_data_into_memory(last_object_id):
    """ Identifies the data source requested and call the appropriate handler

    Args:
    Returns:
    Raises:
        UnknownDataSource
    Todo:
    """

    try:
        _logger.debug("_load_data_into_memory")

        if _config['source'] == _DATA_SOURCE_READINGS:
            data_to_send = _load_data_into_memory_readings(last_object_id)

        elif _config['source'] == _DATA_SOURCE_STATISTICS:
            data_to_send = _load_data_into_memory_statistics(last_object_id)

        elif _config['source'] == _DATA_SOURCE_AUDIT:
            data_to_send = _load_data_into_memory_audit(last_object_id)

        else:
            _message = _MESSAGES_LIST["e000008"]

            _logger.error(_message)
            raise UnknownDataSource

    except Exception:
        _message = _MESSAGES_LIST["e000009"]

        _logger.error(_message)
        raise

    return data_to_send


# FIXME:
def debug_code():
    """ debug_code """
    global _pg_cur
    global _pg_conn

    list_sql_cmd = (
        "DELETE FROM foglamp.omf_created_objects;",
        "UPDATE foglamp.streams SET last_object=0, ts=now() WHERE id=1",
        "UPDATE foglamp.statistics SET value=0;",
        "DELETE FROM foglamp.configuration WHERE \"key\"='OMF_TRANS';",
        "DELETE FROM foglamp.configuration WHERE \"key\"='OMF_TR_1';",
        "DELETE FROM foglamp.configuration WHERE \"key\"='SEND_PR_1';",
        "DELETE FROM foglamp.configuration WHERE \"key\"='OMF_TYPES';",


    )

    for cmd in list_sql_cmd:

        _pg_cur.execute(cmd)
        _pg_conn.commit()


def last_object_id_read():
    """ Retrieves the starting point for the send operation

    Returns:
        last_object_id: starting point for the send operation

    Raises:
    Todo:
        it should evolve using the DB layer
    """

    global _pg_cur

    try:
        sql_cmd = "SELECT last_object FROM foglamp.streams WHERE id={0}".format(_stream_id)

        _pg_cur.execute(sql_cmd)
        rows = _pg_cur.fetchall()

        if len(rows) == 0:
            _message = _MESSAGES_LIST["e000016"].format(str(_stream_id))
            raise ValueError(_message)

        elif len(rows) > 1:

            _message = _MESSAGES_LIST["e000014"].format(str(_stream_id))
            raise ValueError(_message)

        else:
            last_object_id = rows[0][0]
            _logger.debug("DB row last_object_id |{0}| : ".format(last_object_id))

    except Exception:
        _message = _MESSAGES_LIST["e000019"]

        _logger.error(_message)
        raise

    return last_object_id


def is_stream_id_valid(stream_id):
    """ Checks if the provided stream id  is valid

    Returns:
        True/False
    Raises:
    Todo:
        it should evolve using the DB layer
    """

    global _pg_cur

    try:
        sql_cmd = "SELECT id FROM foglamp.streams WHERE id={0}".format(stream_id)

        _pg_cur.execute(sql_cmd)
        rows = _pg_cur.fetchall()

        if len(rows) == 0:
            _message = _MESSAGES_LIST["e000016"].format(str(stream_id))
            raise ValueError(_message)

        elif len(rows) > 1:

            _message = _MESSAGES_LIST["e000014"].format(str(stream_id))
            raise ValueError(_message)
        else:
            stream_id_valid = True

    except Exception as e:
        _message = _MESSAGES_LIST["e000013"].format(str(e))

        _logger.error(_message)
        raise e

    return stream_id_valid


def last_object_id_update(new_last_object_id):
    """ Updates reached position

    Args:
        new_last_object_id: Last row id already sent

    Todo:
        it should evolve using the DB layer

    """
    global _pg_cur
    global _pg_conn

    try:
        _logger.debug("Last position, sent |{0}| ".format(str(new_last_object_id)))

        sql_cmd = "UPDATE foglamp.streams SET last_object={0}, ts=now()  WHERE id={1}" \
            .format(new_last_object_id, _stream_id)

        _pg_cur.execute(sql_cmd)

        _pg_conn.commit()

    except Exception:
        _message = _MESSAGES_LIST["e000020"]

        _logger.error(_message)
        raise


@_performance_log
def _send_data_block():
    """ Sends a block of data to the destination using the configured plugin

    Args:
    Returns:
    Raises:
    Todo:
    """

    data_sent = False
    try:
        _logger.debug("_send_data_block")

        last_object_id = last_object_id_read()

        data_to_send = _load_data_into_memory(last_object_id)

        if data_to_send:

            data_sent, new_last_object_id, num_sent = _plugin.plugin_send(data_to_send, _stream_id)

            if data_sent:
                last_object_id_update(new_last_object_id)

                update_statistics(num_sent)

    except Exception:
        _message = _MESSAGES_LIST["e000006"]

        _logger.error(_message)
        raise

    return data_sent


def _send_data():
    """ Handles the sending of the data to the destination using the configured plugin for a defined amount of time

    Args:
    Returns:
    Raises:
    Todo:
    """

    try:
        _logger.debug("_send_data")

        start_time = time.time()
        elapsed_seconds = 0

        while elapsed_seconds < _config['duration']:

            try:
                data_sent = _send_data_block()

            except Exception as e:
                data_sent = False

                _message = _MESSAGES_LIST["e000021"].format(e)
                _logger.error(_message)

            if not data_sent:
                _logger.debug("_send_data - SLEEPING ")
                time.sleep(_config['sleepInterval'])

            elapsed_seconds = time.time() - start_time
            _logger.debug("_send_data - elapsed_seconds {0} ".format(elapsed_seconds))

    except Exception:
        _message = _MESSAGES_LIST["e000021"].format("")

        _logger.error(_message)
        raise


def _is_translator_valid():
    """ Checks if the translator has adequate characteristics to be used for sending of the data

    Args:
    Returns:
        translator_ok: True if the translator is a proper one
    Raises:
    Todo:
    """

    translator_ok = False

    try:
        if _plugin_info['type'] == _PLUGIN_TYPE and \
           _plugin_info['name'] != "Empty translator":

            translator_ok = True

    except Exception:
        _message = _MESSAGES_LIST["e000000"]

        _logger.error(_message)
        raise

    return translator_ok


def update_statistics(num_sent):
    """ Updates FogLAMP statistics

    Raises :
    """

    try:
        _event_loop.run_until_complete(statistics.update_statistics_value('SENT', num_sent))

    except Exception:
        _message = _MESSAGES_LIST["e000010"]

        _logger.error(_message)
        raise


def handling_input_parameters():
    """ Handles command line parameters

    Raises :
        InvalidCommandLineParameters
    """

    global _log_performance
    global _log_debug_level
    global _stream_id

    parser = argparse.ArgumentParser(prog=_MODULE_NAME)
    parser.description = '%(prog)s -- extract the data from the storage subsystem ' \
                         'and stream it to the translator for sending to the external system.'
    parser.epilog = ' '

    parser.add_argument('-s', '--stream_id',
                        required=True,
                        default=0,
                        help='Define the stream id, it should be a number.')

    parser.add_argument('-p', '--performance_log',
                        default=False,
                        choices=['y', 'yes', 'n', 'no'],
                        help='Enable the logging of the performance.')

    parser.add_argument('-d', '--debug_level',
                        default='0',
                        choices=['0', '1', '2', '3'],
                        help='Enable/define the level of logging for debugging '
                             '- level 0 only warning '
                             '- level 1 info '
                             '- level 2 debug '
                             '- level 3 detailed debug - impacts performance')

    namespace = parser.parse_args(sys.argv[1:])

    _log_performance = True if namespace.performance_log in ['y', 'yes'] else False
    _log_debug_level = int(namespace.debug_level)

    try:
        _stream_id = int(namespace.stream_id) if namespace.stream_id else 1

    except Exception as e:
        _message = _MESSAGES_LIST["e000011"].format(str(sys.argv))

        _logger.error(_message)
        raise e


if __name__ == "__main__":

    try:
        _logger = logger.setup(__name__)

    except Exception as ex:
        message = _MESSAGES_LIST["e000001"].format(str(ex))
        current_time = time.strftime("%Y-%m-%d %H:%M:%S:")

        print("{0} - ERROR - {1}".format(current_time, message))
        sys.exit(1)

    try:
        handling_input_parameters()

    except Exception as ex:
        message = _MESSAGES_LIST["e000017"].format(str(ex))

        _logger.exception(message)
        sys.exit(1)

    else:
        try:
            # Set the debug level
            if _log_debug_level == 1:
                _logger.setLevel(logging.INFO)

            elif _log_debug_level >= 2:
                _logger.setLevel(logging.DEBUG)

            _event_loop = asyncio.get_event_loop()

            if _sending_process_init():

                if _is_translator_valid():
                    _send_data()
                else:
                    message = _MESSAGES_LIST["e000015"].format(_plugin_info['name'], _plugin_info['type'])
                    _logger.warning(message)

                _sending_process_shutdown()

                _logger.info(_MESSAGES_LIST["i000002"])

            sys.exit(0)

        except Exception as ex:
            message = _MESSAGES_LIST["e000002"].format(str(ex))

            _logger.exception(message)
            sys.exit(1)
