#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2017

""" Backups the entire FogLAMP repository into a file in the local filesystem,
it executes a full warm backup.

The information about executed backups are stored into the Storage Layer.

The parameters for the execution are retrieved from the configuration manager.
It could work also without the configuration manager,
retrieving the parameters for the execution from the local file 'configuration.ini'.

"""

import time
import sys
import asyncio
import configparser
import os

from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.common.process import FoglampProcess
from foglamp.common import logger
import logging

import foglamp.tasks.backup_restore.lib as lib
import foglamp.tasks.backup_restore.exceptions as exceptions

__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_MODULE_NAME = "foglamp_backup_module"

_MESSAGES_LIST = {

    # Information messages
    "i000001": "Execution started.",
    "i000002": "Execution completed.",

    # Warning / Error messages
    "e000001": "cannot initialize the logger - error details |{0}|",
    "e000002": "an error occurred during the backup operation - error details |{0}|",
}
""" Messages used for Information, Warning and Error notice """

_logger = {}


class Backup(FoglampProcess):
    """ Backups the entire FogLAMP repository into a file in the local filesystem,
        it executes a full warm backup
    """

    _MODULE_NAME = "foglamp_backup"

    _MESSAGES_LIST = {

        # Information messages
        "i000001": "Execution started.",
        "i000002": "Execution completed.",

        # Warning / Error messages
        "e000000": "general error",
        "e000001": "cannot initialize the logger - error details |{0}|",
        "e000002": "cannot retrieve the configuration from the manager, trying retrieving from file "
                   "- error details |{0}|",
        "e000003": "cannot retrieve the configuration from file - error details |{0}|",
        "e000004": "cannot delete/purge old backup file on file system - file name |{0}| error details |{1}|",
        "e000005": "cannot delete/purge old backup information on the storage layer "
                   "- file name |{0}| error details |{1}|",
        "e000007": "Backup failed.",
        "e000008": "cannot execute the backup, either a backup or a restore is already running - pid |{0}|",
    }
    """ Messages used for Information, Warning and Error notice """

    _CONFIG_FILE = "configuration.ini"

    # Configuration retrieved from the Configuration Manager
    _CONFIG_CATEGORY_NAME = 'BACK_REST'
    _CONFIG_CATEGORY_DESCRIPTION = 'Configuration for backup and restore operations'

    _CONFIG_DEFAULT = {
        "host": {
            "description": "Host server for backup and restore operations.",
            "type": "string",
            "default": "localhost"
        },
        "port": {
            "description": "PostgreSQL port for backup and restore operations.",
            "type": "integer",
            "default": "5432"
        },
        "database": {
            "description": "Database to manage for backup and restore operations.",
            "type": "string",
            "default": "foglamp"
        },
        # FIXME:
        "backup_dir": {
            "description": "Directory where the backups will be created.",
            "type": "string",
            "default": "/tmp"
        },
        "retention": {
            "description": "Number of backups to maintain, old ones will be deleted.",
            "type": "integer",
            "default": "5"
        },
        "max_retry": {
            "description": "Number of retries for FogLAMP stop/start operations.",
            "type": "integer",
            "default": "5"
        },
        "timeout": {
            "description": "Timeout in seconds for the execution of the external commands.",
            "type": "integer",
            "default": "1200"
        },
    }

    def __init__(self):
        super().__init__()

        try:
            self._logger = logger.setup(self._MODULE_NAME)

            # FIXME:
            # Sets the logger for the library
            lib._logger = self._logger
    
        except Exception as _ex:
            _message = self._MESSAGES_LIST["e000001"].format(str(_ex))
            _current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    
            print("[FOGLAMP] {0} - ERROR - {1}".format(_current_time, _message), file=sys.stderr)
            sys.exit(1)            

        self._config_from_manager = {}
        self._config = {}

        self._job = lib.Job()
        self._event_loop = asyncio.get_event_loop()

    def init(self):
        """  Setups the correct state for the execution of the backup

        Args:
        Returns:
        Raises:
        """

        self._logger.debug("{func}".format(func="init"))

        self._retrieve_configuration()

        pid = self._job.is_running()
        if pid == 0:

            # no job is running
            pid = os.getpid()
            self._job.set_as_running(lib.JOB_SEM_FILE_BACKUP, pid)

        else:
            _message = self._MESSAGES_LIST["e000008"].format(pid)
            self._logger.warning("{0}".format(_message))

            raise exceptions.BackupOrRestoreAlreadyRunning

    def run(self):
        """ Executes the backup functionality

        Args:
        Returns:

        Raises:
        """

        self._logger.debug("{func}".format(func="run"))

    def shutdown(self):
        """ Sets the correct state to terminate the execution

        Args:
        Returns:
        Raises:
        """

        self._logger.debug("{func}".format(func="shutdown"))

    def _retrieve_configuration_from_manager(self):
        """" Retrieves the configuration from the configuration manager

        Args:
        Returns:
        Raises:
        """

        cfg_manager = ConfigurationManager(self._storage)

        self._event_loop.run_until_complete(cfg_manager.create_category(
                                                                        self._CONFIG_CATEGORY_NAME,
                                                                        self._CONFIG_DEFAULT,
                                                                        self._CONFIG_CATEGORY_DESCRIPTION))
        self._config_from_manager = self._event_loop.run_until_complete(cfg_manager.get_category_all_items
                                                                        (self._CONFIG_CATEGORY_NAME))

        self._config['host'] = self._config_from_manager['host']['value']

        self._config['port'] = int(self._config_from_manager['port']['value'])
        self._config['database'] = self._config_from_manager['database']['value']
        self._config['backup_dir'] = self._config_from_manager['backup_dir']['value']
        self._config['retention'] = int(self._config_from_manager['retention']['value'])
        self._config['timeout'] = int(self._config_from_manager['timeout']['value'])

    def _retrieve_configuration_from_file(self):
        """" Retrieves the configuration from the local file

        Args:
        Returns:
        Raises:
        """

        config_file = configparser.ConfigParser()
        config_file.read(self._CONFIG_FILE)

        self._config['host'] = config_file['DEFAULT']['host']
        self._config['port'] = int(config_file['DEFAULT']['port'])
        self._config['database'] = config_file['DEFAULT']['database']
        self._config['backup_dir'] = config_file['DEFAULT']['backup_dir']
        self._config['retention'] = int(config_file['DEFAULT']['retention'])
        self._config['timeout'] = int(config_file['DEFAULT']['timeout'])

    def _update_configuration_file(self):
        """ Updates the configuration file with the values retrieved from tha manager.

        Args:
        Returns:
        Raises:
        """

        config_file = configparser.ConfigParser()

        config_file['DEFAULT']['host'] = self._config['host']
        config_file['DEFAULT']['port'] = str(self._config['port'])
        config_file['DEFAULT']['database'] = self._config['database']
        config_file['DEFAULT']['backup_dir'] = self._config['backup_dir']
        config_file['DEFAULT']['retention'] = str(self._config['retention'])
        config_file['DEFAULT']['timeout'] = str(self._config['timeout'])

        with open(self._CONFIG_FILE, 'w') as file:
            config_file.write(file)

    def _retrieve_configuration(self):
        """  Retrieves the configuration either from the manager or from a local file.
        the local configuration file is used if the configuration manager is not available
        and updated with the values retrieved from the manager when feasible.

        Args:
        Returns:
        Raises:
            exceptions.ConfigRetrievalError
        """

        try:
            self._retrieve_configuration_from_manager()

        except Exception as _ex:
            _message = self._MESSAGES_LIST["e000002"].format(_ex)
            self._logger.warning(_message)

            try:
                self._retrieve_configuration_from_file()

            except Exception as _ex:
                _message = self._MESSAGES_LIST["e000003"].format(_ex)
                self._logger.error(_message)

                raise exceptions.ConfigRetrievalError(ex)
        else:
            self._update_configuration_file()


if __name__ == "__main__":

    # Initializes the logger
    try:
        # FIXME: for debug purpose
        # _logger = logger.setup(_MODULE_NAME)
        _logger = logger.setup(_MODULE_NAME,
                               destination=logger.CONSOLE,
                               level=logging.DEBUG)

        _logger.info(_MESSAGES_LIST["i000001"])

    except Exception as ex:
        message = _MESSAGES_LIST["e000001"].format(str(ex))
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")

        print("[FOGLAMP] {0} - ERROR - {1}".format(current_time, message), file=sys.stderr)
        sys.exit(1)

    # Initializes FoglampProcess and Backup classes - handling the command line parameters
    try:
        backup = Backup()

    except Exception as ex:
        message = _MESSAGES_LIST["e000002"].format(ex)
        _logger.exception(message)

        _logger.info(_MESSAGES_LIST["i000002"])
        sys.exit(1)

    # Executes the backup
    try:
        # FIXME: To be removed
        # noinspection PyProtectedMember
        _logger.debug("{module} - name |{name}| - address |{addr}| - port |{port}|".format(
            module=_MODULE_NAME,
            name=backup._name,
            addr=backup._core_management_host,
            port=backup._core_management_port))

        exit_value = 1

        backup.init()
        backup.run()
        exit_value = 0
        backup.shutdown()

        _logger.info(_MESSAGES_LIST["i000002"])
        sys.exit(exit_value)

    except Exception as ex:
        message = _MESSAGES_LIST["e000002"].format(ex)
        _logger.exception(message)

        backup.shutdown()
        _logger.info(_MESSAGES_LIST["i000002"])
        sys.exit(1)
