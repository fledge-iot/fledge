#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2017

""" Backups the entire FogLAMP repository into a file in the local filesystem, it executes a full warm backup.

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

from foglamp import logger, configuration_manager

import foglamp.backup_restore.lib as lib

__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_MODULE_NAME = "foglamp_backup"

_MESSAGES_LIST = {

    # Information messages
    "i000001": "Execution started.",
    "i000002": "Execution completed.",

    # Warning / Error messages
    "e000001": "cannot initialize the logger - error details |{0}|",
    "e000002": "an error occurred during the backup operation - error details |{0}|",
}
""" Messages used for Information, Warning and Error notice """

_logger = ""


class ConfigRetrievalError(RuntimeError):
    """ Unable to retrieve the parameters from the configuration manager """
    pass


class BackupError(RuntimeError):
    """ An error occurred during the backup operation """
    pass


class Backup:
    """ Backups the entire FogLAMP repository into a file in the local filesystem, it executes a full warm backup """

    _MODULE_NAME = "foglamp_backup_Backup"

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

    _config_from_manager = {}
    _config = {}
    
    _logger = ""
    _event_loop = ""
    _job = ""
    
    def __init__(self):
        self._config_from_manager = {}
        self._config = {}

        self._job = lib.Job()
        self._event_loop = asyncio.get_event_loop()

        try:
            self._logger = logger.setup(self._MODULE_NAME)

            # Sets the logger for the library
            lib._logger = self._logger
    
        except Exception as _ex:
            _message = self._MESSAGES_LIST["e000001"].format(str(_ex))
            _current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    
            print("[FOGLAMP] {0} - ERROR - {1}".format(_current_time, _message), file=sys.stderr)
            sys.exit(1)            

    def _exec_backup(self, _backup_file):
        """ Backups the entire FogLAMP repository into a file in the local file system

        Args:
            _backup_file: backup file to create
        Returns:
            _status: exit status of the operation, 0=Successful
        Raises:
        Todo:
        """

        self._logger.debug("{0} - ".format(sys._getframe().f_code.co_name))

        # Executes the backup
        cmd = "pg_dump"
        cmd += " --serializable-deferrable -Fc  "
        cmd += " -h {host} -p {port} {db} > {file}".format(
            host=self._config['host'],
            port=self._config['port'],
            db=self._config['database'],
            file=_backup_file)

        _status, output = lib.exec_wait_retry(cmd, True, timeout=self._config['timeout'])

        self._logger.debug("{func} - status |{status}| - cmd |{cmd}|  output |{output}| ".format(
                    func=sys._getframe().f_code.co_name,
                    status=_status,
                    cmd=cmd,
                    output=output))

        return _status

    def _generate_file_name(self):
        """ Generates the file name for the backup operation, it uses hours/minutes/seconds for the file name generation

        Args:
        Returns:
            _backup_file: generated file name
        Raises:
        Todo:
        """

        self._logger.debug("{0} - ".format(sys._getframe().f_code.co_name))

        # Evaluates the parameters
        execution_time = time.strftime("%Y_%m_%d_%H_%M_%S")

        full_file_name = self._config['backup_dir'] + "/" + "foglamp" + "_" + execution_time
        ext = "dump"

        _backup_file = "{file}.{ext}".format(file=full_file_name, ext=ext)

        return _backup_file

    def _retrieve_configuration_from_manager(self):
        """" Retrieves the configuration from the configuration manager

        Args:
        Returns:
        Raises:
        Todo:
        """

        self._event_loop.run_until_complete(configuration_manager.create_category(
                                                                            self._CONFIG_CATEGORY_NAME,
                                                                            self._CONFIG_DEFAULT,
                                                                            self._CONFIG_CATEGORY_DESCRIPTION))
        self._config_from_manager = self._event_loop.run_until_complete(
                                                    configuration_manager.get_category_all_items
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
        Todo:
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
        Todo:
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
        Todo:
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

                raise ConfigRetrievalError(ex)
        else:
            self._update_configuration_file()

    def _purge_old_backups(self):
        """  Deletes old backups in relation at the retention parameter

        Args:
        Returns:
        Raises:
        Todo:
        """

        # -1 so at the end of the execution will remain _config['retention'] backups
        backup_to_delete = self._config['retention'] - 1

        cmd = """
        
            SELECT  id,file_name FROM foglamp.backups WHERE id NOT in (
                SELECT id FROM foglamp.backups ORDER BY ts DESC LIMIT {0}
            )            
        """.format(backup_to_delete)

        data = lib.storage_retrieve(cmd)

        for row in data:
            file_name = row['file_name']

            if os.path.exists(file_name):
                try:
                    os.remove(file_name)

                except Exception as _ex:
                    _message = self._MESSAGES_LIST["e000004"].format(file_name, _ex)
                    self._logger.warning(_message)

            try:
                cmd = """
                    DELETE FROM foglamp.backups WHERE file_name='{0}'
                 """.format(file_name)

                lib.storage_update(cmd)

            except Exception as _ex:
                _message = self._MESSAGES_LIST["e000005"].format(file_name, _ex)
                self._logger.warning(_message)

    def start(self):
        """  Setups the correct state for the execution of the backup

        Args:
        Returns:
            proceed_execution: True= the backup operation could be executed
        Raises:
        Todo:
        """

        self._logger.debug("{func}".format(func=sys._getframe().f_code.co_name))

        proceed_execution = False

        self._retrieve_configuration()

        pid = self._job.is_running()
        if pid == 0:

            # no job is running
            pid = os.getpid()
            self._job.set_as_running(lib._JOB_SEM_FILE_BACKUP, pid)
            proceed_execution = True

        else:
            _message = self._MESSAGES_LIST["e000008"].format(pid)
            self._logger.warning("{0}".format(_message))

        return proceed_execution

    def stop(self):
        """ Sets the correct state to terminate the execution

        Args:
        Returns:
        Raises:
        Todo:
        """

        self._logger.debug("{func}".format(func=sys._getframe().f_code.co_name))

        self._job.set_as_completed(lib._JOB_SEM_FILE_BACKUP)

    def execute(self):
        """ Main - Executes the backup functionality

        Args:
        Returns:
            _exit_value: 0=Backup successfully executed

        Raises:
        Todo:
        """

        self._purge_old_backups()

        backup_file = self._generate_file_name()

        lib.backup_status_create(backup_file, lib._BACKUP_STATUS_RUNNING)
        status = self._exec_backup(backup_file)
        lib.backup_status_update(backup_file, status)

        if status == lib._BACKUP_STATUS_SUCCESSFUL:
            _exit_value = 0

        else:
            self._logger.error(self._MESSAGES_LIST["e000007"])
            _exit_value = 1

        return _exit_value


if __name__ == "__main__":

    try:
        _logger = logger.setup(_MODULE_NAME)
        _logger.info(_MESSAGES_LIST["i000001"])

    except Exception as ex:
        message = _MESSAGES_LIST["e000001"].format(str(ex))
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")

        print("[FOGLAMP] {0} - ERROR - {1}".format(current_time, message), file=sys.stderr)
        sys.exit(1)
    else:
        backup = Backup()

        try:
            exit_value = 1

            if backup.start():
                exit_value = backup.execute()

                backup.stop()

            _logger.info(_MESSAGES_LIST["i000002"])
            sys.exit(exit_value)

        except Exception as ex:
            message = _MESSAGES_LIST["e000002"].format(ex)
            _logger.exception(message)

            backup.stop()
            _logger.info(_MESSAGES_LIST["i000002"])
            sys.exit(1)
