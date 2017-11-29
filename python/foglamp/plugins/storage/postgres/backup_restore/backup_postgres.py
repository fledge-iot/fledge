#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2017

""" Backups the entire FogLAMP repository into a file in the local filesystem,
it executes a full warm backup.

The information about executed backups are stored into the Storage Layer.

The parameters for the execution are retrieved from the configuration manager.
It could work also without the configuration manager,
retrieving the parameters for the execution from the local file 'backup_configuration_cache.json'.

"""

import time
import sys
import asyncio
import os
import json

from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.common.storage_client import payload_builder
from foglamp.common.process import FoglampProcess
from foglamp.common import logger
import logging

import foglamp.plugins.storage.postgres.backup_restore.lib as lib
import foglamp.plugins.storage.postgres.backup_restore.exceptions as exceptions

__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_MODULE_NAME = "foglamp_backup_postgres_module"

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


class Backup(object):
    """ Backup API integration

    # CURRENTLY NOT IMPLEMENTED !!
    """

    # noinspection PyUnusedLocal
    def get_backup_list(self, limit, skip, status):
        """  Retrieves backups information

        Args:
            limit: maximum number of backups information to retrieve
            skip: TBD - # FIXME:
            status: BACKUP_STATUS_UNDEFINED= retrieves the information for all the backups state
                    or for a specific state only
        Returns:
        Raises:
        """

        pass


class BackupProcess(FoglampProcess):
    """ Backups the entire FogLAMP repository into a file in the local filesystem,
        it executes a full warm backup
    """

    _MODULE_NAME = "foglamp_backup_postgres"

    _DEFAULT_FOGLAMP_ROOT = "/usr/local/foglamp"
    """ Default value to use for the FOGLAMP_ROOT if the environment $FOGLAMP_ROOT is not defined """

    _BACKUP_FILE_NAME_PREFIX = "foglamp_backup_"
    """ Prefix used to generate a backup file name """

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
        "e000004": "cannot delete/purge backup file on file system - id |{0}| - file name |{1}| error details |{2}|",
        "e000005": "cannot delete/purge backup information on the storage layer "
                   "- id |{0}| - file name |{1}| error details |{2}|",
        "e000007": "backup failed.",
        "e000008": "cannot execute the backup, either a backup or a restore is already running - pid |{0}|",
        "e000009": "cannot retrieve information for the backup id |{0}|",
        "e000010": "directory used to store backups doesn't exist - dir |{0}|",
        "e000011": "directory used to store semaphores for backup/restore synchronization doesn't exist - dir |{0}|",
        "e000012": "cannot create the configuration cache file, neither FOGLAMP_DATA or FOGLAMP_ROOT are defined.",
        "e000013": "cannot create the configuration cache file, provided path is not a directory - dir |{0}|",
        "e000014": "the identified path doesn't exists, tried the creation - dir |{0}| - error details |{1}|",
    }
    """ Messages used for Information, Warning and Error notice """

    _CONFIG_CACHE_FILE = "backup_postgres_configuration_cache.json"
    """ Stores a configuration cache in case the configuration Manager is not available"""

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
        "backup-dir": {
            "description": "Directory where backups will be created, "
                           "it uses FOGLAMP_BACKUP or FOGLAMP_DATA or FOGLAMP_BACKUP if none.",
            "type": "string",
            "default": "none"
        },
        "semaphores-dir": {
            "description": "Directory used to store semaphores for backup/restore synchronization."
                           "it uses backup-dir if none.",
            "type": "string",
            "default": "none"
        },
        "retention": {
            "description": "Number of backups to maintain, old ones will be deleted.",
            "type": "integer",
            "default": "5"
        },
        "max_retry": {
            "description": "Number of retries for the operations.",
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
            # FIXME:
            # self._logger = logger.setup(self._MODULE_NAME)
            self._logger = logger.setup(self._MODULE_NAME,
                                        # destination=logger.CONSOLE,
                                        level=logging.DEBUG)

        except Exception as _ex:
            _message = self._MESSAGES_LIST["e000001"].format(str(_ex))
            _current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    
            print("[FOGLAMP] {0} - ERROR - {1}".format(_current_time, _message), file=sys.stderr)
            sys.exit(1)            

        self._config_from_manager = {}
        self._config = {}
        self._job = lib.Job()
        self._event_loop = asyncio.get_event_loop()

        self._foglamp_backup = ""
        self._foglamp_data = ""
        self._foglamp_data_etc = ""
        self._foglamp_root = ""

        self._backups_dir = ""
        self._semaphores_dir = ""

        # Creates the objects references used by the library
        lib._logger = self._logger
        lib._storage = self._storage

    def _generate_file_name(self):
        """ Generates the file name for the backup operation, it uses hours/minutes/seconds for the file name generation

        Args:
        Returns:
            _backup_file: generated file name
        Raises:
        """

        self._logger.debug("{func}".format(func="_generate_file_name"))

        # Evaluates the parameters
        execution_time = time.strftime("%Y_%m_%d_%H_%M_%S")

        full_file_name = self._backups_dir + "/" + self._BACKUP_FILE_NAME_PREFIX + execution_time
        ext = "dump"

        _backup_file = "{file}.{ext}".format(file=full_file_name, ext=ext)

        return _backup_file

    def _evaluate_paths(self):
        """  Evaluates paths in relation to the environment variables
             FOGLAMP_ROOT, FOGLAMP_DATA and FOGLAMP_BACKUP

        Args:
        Returns:
        Raises:
        """

        # Evaluates FOGLAMP_ROOT
        if "FOGLAMP_ROOT" in os.environ:
            self._foglamp_root = os.getenv("FOGLAMP_ROOT")
        else:
            self._foglamp_root = self._DEFAULT_FOGLAMP_ROOT

        # Evaluates FOGLAMP_DATA
        if "FOGLAMP_DATA" in os.environ:
            self._foglamp_data = os.getenv("FOGLAMP_DATA")
        else:
            self._foglamp_data = self._foglamp_root + "/data"

        # Evaluates FOGLAMP_BACKUP
        if "FOGLAMP_BACKUP" in os.environ:
            self._foglamp_backup = os.getenv("FOGLAMP_BACKUP")
        else:
            self._foglamp_backup = self._foglamp_data + "/backup"

        # Evaluates etc directory
        self._foglamp_data_etc = self._foglamp_data + "/etc"

        self._check_create_path(self._foglamp_backup)
        self._check_create_path(self._foglamp_data_etc)

    def _check_create_path(self, path):
        """  Checks path existences and creates it if needed
        Args:
        Returns:
        Raises:
            exceptions.InvalidBackupsPath
        """

        # Check the path existence
        if not os.path.isdir(path):

            # The path doesn't exists, tries to create it
            try:
                os.makedirs(path)

            except OSError as _ex:
                _message = self._MESSAGES_LIST["e000014"].format(path, _ex)
                self._logger.error("{0}".format(_message))

                raise exceptions.InvalidPath(_message)

    def init(self):
        """  Setups the correct state for the execution of the backup

        Args:
        Returns:
        Raises:
        """

        self._logger.debug("{func}".format(func="init"))

        self._evaluate_paths()

        self._retrieve_configuration()

        # Identifies backups directory and checks the existence
        if self._config['backup-dir'] != "none":

            self._backups_dir = self._config['backup-dir']
        else:
            self._backups_dir = self._foglamp_backup

        self._check_create_path(self._backups_dir)

        # Identifies semaphores directory and checks the existence
        # Stores semaphores in the _backups_dir if semaphores-dir is not defined
        if self._config['semaphores-dir'] != "none":

            self._semaphores_dir = self._config['semaphores-dir']
        else:
            self._semaphores_dir = self._backups_dir
            lib.JOB_SEM_FILE_PATH = self._semaphores_dir

        self._check_create_path(self._semaphores_dir)

        # Checks for backup/restore synchronization
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
            exceptions.BackupFailed
        """

        self._logger.debug("{func}".format(func="run"))

        self._purge_old_backups()

        backup_file = self._generate_file_name()

        lib.backup_status_create(backup_file, lib.BACKUP_TYPE_FULL, lib.BACKUP_STATUS_RUNNING)
        status, exit_code = self._exec_backup(backup_file)

        backup_information = lib.get_backup_details_from_file_name(backup_file)

        lib.backup_status_update(backup_information['id'], status, exit_code)

        if status != lib.BACKUP_STATUS_SUCCESSFUL:

            self._logger.error(self._MESSAGES_LIST["e000007"])
            raise exceptions.BackupFailed

    # noinspection PyUnusedLocal
    def get_backup_list(self, limit, skip, status):
        """  Retrieves backups information

        Args:
            limit: maximum number of backups information to retrieve
            skip: TBD - # FIXME:
            status: BACKUP_STATUS_UNDEFINED= retrieves the information for all the backups state
                    or for a specific state only
        Returns:
        Raises:
        """

        if status == lib.BACKUP_STATUS_UNDEFINED:
            payload = payload_builder.PayloadBuilder() \
                .LIMIT(limit) \
                .ORDER_BY(['ts', 'ASC']) \
                .payload()
        else:
            payload = payload_builder.PayloadBuilder() \
                .WHERE(['state', '=', status]) \
                .LIMIT(limit) \
                .ORDER_BY(['ts', 'ASC']) \
                .payload()

        backups_from_storage = self._storage.query_tbl_with_payload(lib.STORAGE_TABLE_BACKUPS, payload)
        backups_information = backups_from_storage['rows']

        return backups_information

    def _purge_old_backups(self):
        """  Deletes old backups in relation at the retention parameter

        Args:
        Returns:
        Raises:
        """

        backups_info = self.get_backup_list(lib.MAX_NUMBER_OF_BACKUPS_TO_RETRIEVE,
                                            0,
                                            lib.BACKUP_STATUS_UNDEFINED)

        # Evaluates which backup should be deleted
        backups_n = len(backups_info)
        # -1 so at the end of the current backup up to 'retention' backups will be available
        last_to_delete = backups_n - (self._config['retention'] - 1)

        if last_to_delete > 0:

            # Deletes backups
            backups_to_delete = backups_info[:last_to_delete]

            for row in backups_to_delete:
                backup_id = row['id']
                file_name = row['file_name']

                self._logger.debug("{func} - id |{id}| - file_name |{file}|".format(func="_purge_old_backups",
                                                                                    id=backup_id,
                                                                                    file=file_name))
                self.delete_backup(backup_id)

    def get_backup_details(self, _id):
        """ Retrieves information for a specific backup

        Args:
            _id: Backup id to retrieve
        Returns:
            backup_information: information related to the requested backup
        Raises:
            exceptions.DoesNotExist
        """

        payload = payload_builder.PayloadBuilder() \
            .WHERE(['id', '=', _id]) \
            .payload()

        backup_from_storage = self._storage.query_tbl_with_payload(lib.STORAGE_TABLE_BACKUPS, payload)

        if backup_from_storage['count'] == 0:
            raise exceptions.DoesNotExist

        elif backup_from_storage['count'] == 1:

            backup_information = backup_from_storage['rows'][0]
        else:
            raise exceptions.NotUniqueBackup

        return backup_information

    def delete_backup(self, _id):
        """ Deletes a specific backup

        Args:
            _id: Backup id to delete
        Returns:
        Raises:
        """

        try:
            backup_information = self.get_backup_details(_id)

            file_name = backup_information['file_name']

            # Deletes backup file from the file system
            if os.path.exists(file_name):

                try:
                    os.remove(file_name)

                except Exception as _ex:
                    _message = self._MESSAGES_LIST["e000004"].format(_id, file_name, _ex)
                    self._logger.warning(_message)

            # Deletes backup information from the Storage layer
            # only if it was possible to delete the file from the file system
            self._delete_backup_information(_id, file_name)

        except exceptions.DoesNotExist:
            _message = self._MESSAGES_LIST["e000009"].format(_id)
            self._logger.warning(_message)

    def _delete_backup_information(self, _id, _file_name):
        """ Deletes backup information from the Storage layer

        Args:
            _id: Backup id to delete
            _file_name: file name to delete
        Returns:
        Raises:
        """

        try:
            payload = payload_builder.PayloadBuilder() \
                .WHERE(['id', '=', _id]) \
                .payload()

            self._storage.delete_from_tbl(lib.STORAGE_TABLE_BACKUPS, payload)

        except Exception as _ex:
            _message = self._MESSAGES_LIST["e000005"].format(_id, _file_name, _ex)
            self._logger.warning(_message)

    def _exec_backup(self, _backup_file):
        """ Backups the entire FogLAMP repository into a file in the local file system

        Args:
            _backup_file: backup file to create  as a full path
        Returns:
            _status: status of the backup
            _exit_code: exit status of the operation, 0=Successful
        Raises:
        """

        self._logger.debug("{func} - file_name |{file}|".format(func="_exec_backup", file=_backup_file))

        # Prepares the backup command
        cmd = "pg_dump"
        cmd += " --serializable-deferrable -Fc  "
        cmd += " -h {host} -p {port} {db} > {file}".format(
            host=self._config['host'],
            port=self._config['port'],
            db=self._config['database'],
            file=_backup_file)

        # Executes the backup waiting for the completion and using a retry mechanism
        # noinspection PyArgumentEqualDefault
        _exit_code, output = lib.exec_wait_retry(cmd,
                                                 output_capture=True,
                                                 exit_code_ok=0,
                                                 max_retry=self._config['max_retry'],
                                                 timeout=self._config['timeout']
                                                 )

        if _exit_code == 0:
            _status = lib.BACKUP_STATUS_SUCCESSFUL
        else:
            _status = lib.BACKUP_STATUS_FAILED

        self._logger.debug("{func} - status |{status}| - exit_code |{exit_code}| "
                           "- cmd |{cmd}|  output |{output}| ".format(
                                                                        func="_exec_backup",
                                                                        status=_status,
                                                                        exit_code=_exit_code,
                                                                        cmd=cmd,
                                                                        output=output))

        return _status, _exit_code

    def shutdown(self):
        """ Sets the correct state to terminate the execution

        Args:
        Returns:
        Raises:
        """

        self._logger.debug("{func}".format(func="shutdown"))

        self._job.set_as_completed(lib.JOB_SEM_FILE_BACKUP)

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

        self._decode_configuration_from_manager(self._config_from_manager)

    def _decode_configuration_from_manager(self, _config_from_manager):
        """" Decodes a json configuration as generated by the configuration manager

        Args:
            _config_from_manager: Json configuration to decode
        Returns:
        Raises:
        """

        self._config['host'] = _config_from_manager['host']['value']

        self._config['port'] = int(_config_from_manager['port']['value'])
        self._config['database'] = _config_from_manager['database']['value']
        self._config['backup-dir'] = _config_from_manager['backup-dir']['value']
        self._config['semaphores-dir'] = _config_from_manager['semaphores-dir']['value']
        self._config['retention'] = int(_config_from_manager['retention']['value'])
        self._config['max_retry'] = int(_config_from_manager['max_retry']['value'])
        self._config['timeout'] = int(_config_from_manager['timeout']['value'])

    def _retrieve_configuration_from_file(self):
        """" Retrieves the configuration from the local file

        Args:
        Returns:
        Raises:
        """

        file_full_path = self._identify_configuration_file_path()

        with open(file_full_path) as file:
            self._config_from_manager = json.load(file)

        self._decode_configuration_from_manager(self._config_from_manager)

    def _update_configuration_file(self):
        """ Updates the configuration file with the values retrieved from tha manager.

        Args:
        Returns:
        Raises:
        """

        file_full_path = self._identify_configuration_file_path()

        with open(file_full_path, 'w') as file:
            json.dump(self._config_from_manager, file)

    def _identify_configuration_file_path(self):
        """ Identifies configuration cache file's path,

        Args:
        Returns:
        Raises:
        """

        file_full_path = self._foglamp_data_etc + "/" + self._CONFIG_CACHE_FILE

        return file_full_path

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

                raise exceptions.ConfigRetrievalError(_message)
        else:
            self._update_configuration_file()

    def execute_backup(self):
        """  Creates a new backup

        Args:
        Returns:
        Raises:
        """

        self.init()
        self.run()
        self.shutdown()


if __name__ == "__main__":

    # Initializes the logger
    try:
        # FIXME: for debug purpose
        # _logger = logger.setup(_MODULE_NAME)
        _logger = logger.setup(_MODULE_NAME,
                               # destination=logger.CONSOLE,
                               level=logging.DEBUG)

        _logger.info(_MESSAGES_LIST["i000001"])

    except Exception as ex:
        message = _MESSAGES_LIST["e000001"].format(str(ex))
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")

        print("[FOGLAMP] {0} - ERROR - {1}".format(current_time, message), file=sys.stderr)
        sys.exit(1)

    # Initializes FoglampProcess and Backup classes - handling the command line parameters
    try:
        backup = BackupProcess()

    except Exception as ex:
        message = _MESSAGES_LIST["e000002"].format(ex)
        _logger.exception(message)

        _logger.info(_MESSAGES_LIST["i000002"])
        sys.exit(1)

    # Executes the backup
    try:
        # noinspection PyProtectedMember
        _logger.debug("{module} - name |{name}| - address |{addr}| - port |{port}|".format(
            module=_MODULE_NAME,
            name=backup._name,
            addr=backup._core_management_host,
            port=backup._core_management_port))

        backup.execute_backup()

        _logger.info(_MESSAGES_LIST["i000002"])
        sys.exit(0)

    except Exception as ex:
        message = _MESSAGES_LIST["e000002"].format(ex)
        _logger.exception(message)

        backup.shutdown()
        _logger.info(_MESSAGES_LIST["i000002"])
        sys.exit(1)
