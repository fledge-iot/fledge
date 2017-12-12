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

import sys
import time
import os
import json
import asyncio
import uuid

from foglamp.services.core import server

from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.common.storage_client import payload_builder
from foglamp.common.process import FoglampProcess
from foglamp.common import logger

import foglamp.plugins.storage.postgres.backup_restore.lib as lib
import foglamp.plugins.storage.postgres.backup_restore.exceptions as exceptions

__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_MODULE_NAME = "foglamp_backup_postgres_module"

# Log definitions
_logger = None

_LOG_LEVEL_DEBUG = 10
_LOG_LEVEL_INFO = 20

# FIXME:
# _LOGGER_LEVEL = _LOG_LEVEL_INFO
# _LOGGER_DESTINATION = logger.SYSLOG
_LOGGER_LEVEL = _LOG_LEVEL_DEBUG
_LOGGER_DESTINATION = logger.SYSLOG

_MESSAGES_LIST = {

    # Information messages
    "i000001": "Execution started.",
    "i000002": "Execution completed.",

    # Warning / Error messages
    "e000001": "cannot initialize the logger - error details |{0}|",
    "e000002": "an error occurred during the backup operation - error details |{0}|",
}
""" Messages used for Information, Warning and Error notice """


class Backup(object):
    """ Provides external functionality/integration for Backup operations

        the constructor expects to receive a reference to a StorageClient object to being able to access
        the Storage Layer
    """

    _logger = None

    _SCHEDULE_BACKUP_ON_DEMAND = "fac8dae6-d8d1-11e7-9296-cec278b6b50a"
    _MODULE_NAME = "foglamp_backup_postgres_api"

    _MESSAGES_LIST = {

        # Information messages
        "i000001": "Execution started.",
        "i000002": "Execution completed.",
        "i000003": "On demand backup successfully launched.",

        # Warning / Error messages
        "e000000": "general error",
        "e000001": "cannot delete/purge backup file on file system - id |{0}| - file name |{1}| error details |{2}|",
        "e000002": "cannot delete/purge backup information on the storage layer "
                   "- id |{0}| - file name |{1}| error details |{2}|",
        "e000003": "cannot retrieve information for the backup id |{0}|",
        "e000004": "cannot launch on demand backup - error details |{0}|",
    }
    """ Messages used for Information, Warning and Error notice """

    def __init__(self, _storage):
        self._storage = _storage

        if not Backup._logger:
            Backup._logger = logger.setup(self._MODULE_NAME,
                                          destination=_LOGGER_DESTINATION,
                                          level=_LOGGER_LEVEL)

    def get_all_backups(self,
                        limit: int,
                        skip: int,
                        status: [lib.BackupStatus, None],
                        sort_order: lib.SortOrder = lib.SortOrder.DESC) -> list:

        """ Returns a list of backups sorted in chronological order with the most recent backup first.

        Args:
            limit: int - limit the number of backups returned to the number given
            skip: int - skip the number of backups specified before returning backups-
                  this, in conjunction with the limit option, allows for a paged interface to be built
            status: lib.BackupStatus - limit the returned backups to those only with the specified status,
                    None = retrieves information for all the backups
            sort_order: lib.SortOrder - Defines the order used to present information, DESC by default

        Returns:
            backups_information: list/dict - Backups information, it is provided for each :
                id: An identifier for the backup
                date: The date the backup started
                status: The status of the backup; one of running, failed, completed
        Raises:
        """

        backups_information_complete = self.get_all_backups_complete(limit, skip, status, sort_order)

        backups_information = []
        for row in backups_information_complete:

            status_decoded = lib.BackupStatus.text[int(row['status'])]

            backups_information.append({'id': row['id'],
                                        'date': row['ts'],
                                        'status': status_decoded}
                                       )

        return backups_information

    def get_all_backups_complete(
                                self,
                                limit: int,
                                skip: int,
                                status: [lib.BackupStatus, None],
                                sort_order: lib.SortOrder = lib.SortOrder.DESC) -> list:

        """ Returns a list of backups is returned sorted in chronological order with the most recent backup first.

        Args:
            limit: int - limit the number of backups returned to the number given
            skip: int - skip the number of backups specified before returning backups-
                  this, in conjunction with the limit option, allows for a paged interface to be built
            status: lib.BackupStatus - limit the returned backups to those only with the specified status,
                    None = retrieves information for all the backups
            sort_order: lib.SortOrder - Defines the order used to present information, DESC by default

        Returns:
            backups_information: all the information available related to the requested backups

        Raises:
        """

        if status is None:
            payload = payload_builder.PayloadBuilder() \
                .LIMIT(limit) \
                .SKIP(skip) \
                .ORDER_BY(['ts', sort_order]) \
                .payload()
        else:
            payload = payload_builder.PayloadBuilder() \
                .WHERE(['status', '=', status]) \
                .LIMIT(limit) \
                .SKIP(skip) \
                .ORDER_BY(['ts', sort_order]) \
                .payload()

        backups_from_storage = self._storage.query_tbl_with_payload(lib.STORAGE_TABLE_BACKUPS, payload)

        backups_information = backups_from_storage['rows']

        return backups_information

    def get_backup_details(self, backup_id: int) -> dict:
        """ Returns the details of a backup

        Args:
            backup_id: int - the id of the backup to return

        Returns:
            backup_info: dict - Backup information :
                id: An identifier for the backup
                date: The date the backup started
                status: The status of the backup; one of running, failed, completed
        Raises:
            exceptions.DoesNotExist
            exceptions.NotUniqueBackup

        """

        backup_information_complete = self.get_backup_details_complete(backup_id)

        status_decoded = lib.BackupStatus.text[int(backup_information_complete['status'])]

        backups_information = {
                                'id': backup_information_complete['id'],
                                'date': backup_information_complete['ts'],
                                'status': status_decoded
                                }

        return backups_information

    def get_backup_details_complete(self, backup_id: int) -> dict:
        """ Returns the details of a backup

        Args:
            backup_id: int - the id of the backup to return

        Returns:
            backup_information: all the information available related to the requested backup_id

        Raises:
            exceptions.DoesNotExist
            exceptions.NotUniqueBackup
        """

        payload = payload_builder.PayloadBuilder() \
            .WHERE(['id', '=', backup_id]) \
            .payload()

        backup_from_storage = self._storage.query_tbl_with_payload(lib.STORAGE_TABLE_BACKUPS, payload)

        if backup_from_storage['count'] == 0:
            raise exceptions.DoesNotExist

        elif backup_from_storage['count'] == 1:

            backup_information = backup_from_storage['rows'][0]
        else:
            raise exceptions.NotUniqueBackup

        return backup_information

    def delete_backup(self, backup_id: int):
        """ Deletes a backup

        Args:
            backup_id: int - the id of the backup to delete

        Returns:
        Raises:
        """

        try:
            backup_information = self.get_backup_details_complete(backup_id)

            file_name = backup_information['file_name']

            # Deletes backup file from the file system
            if os.path.exists(file_name):

                try:
                    os.remove(file_name)

                except Exception as _ex:
                    _message = self._MESSAGES_LIST["e000001"].format(backup_id, file_name, _ex)
                    Backup._logger.error(_message)

                    raise

            # Deletes backup information from the Storage layer
            # only if it was possible to delete the file from the file system
            try:
                self._delete_backup_information(backup_id)

            except Exception as _ex:
                _message = self._MESSAGES_LIST["e000002"].format(backup_id, file_name, _ex)
                self._logger.error(_message)

                raise

        except exceptions.DoesNotExist:
            _message = self._MESSAGES_LIST["e000003"].format(backup_id)
            self._logger.warning(_message)

            raise

    def _delete_backup_information(self, _id):
        """ Deletes backup information from the Storage layer

        Args:
            _id: Backup id to delete
        Returns:
        Raises:
        """

        payload = payload_builder.PayloadBuilder() \
            .WHERE(['id', '=', _id]) \
            .payload()

        self._storage.delete_from_tbl(lib.STORAGE_TABLE_BACKUPS, payload)

    async def create_backup(self):
        """ Run a backup task using the scheduler on-demand schedule mechanism to run the script,
            the backup will proceed asynchronously.

        Args:
        Returns:
            status: str - "failed" or "running"
        Raises:
        """

        self._logger.debug("{func}".format(func="create_backup"))

        try:
            await server.Server.scheduler.queue_task(uuid.UUID(Backup._SCHEDULE_BACKUP_ON_DEMAND))

            _message = self._MESSAGES_LIST["i000003"]
            Backup._logger.info("{0}".format(_message))

        except Exception as _ex:
            _message = self._MESSAGES_LIST["e000004"].format(_ex)
            Backup._logger.error("{0}".format(_message))

            raise exceptions.BackupFailed(_message)


class BackupProcess(FoglampProcess):
    """ Backups the entire FogLAMP repository into a file in the local filesystem,
        it executes a full warm backup
    """

    _logger = None

    # Postgres commands
    _PG_COMMAND_PG_DUMP = "pg_dump"
    _PG_COMMAND_PSQL = "psql"

    _PG_COMMANDS_TO_CHECK = {_PG_COMMAND_PG_DUMP: None,
                             _PG_COMMAND_PSQL: None
                             }
    """List of Postgres commands to check/validate if they are available and usable
       and the actual Postgres commands to use """

    _DIR_MANAGED_FOGLAMP_PG_COMMANDS = "plugins/storage/postgres/plsql/bin"
    """Directory for Postgres commands in a managed configuration"""

    _MODULE_NAME = "foglamp_backup_postgres_process"

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
        "e000004": "...",
        "e000005": "...",
        "e000006": "...",
        "e000007": "backup failed.",
        "e000008": "cannot execute the backup, either a backup or a restore is already running - pid |{0}|",
        "e000009": "...",
        "e000010": "directory used to store backups doesn't exist - dir |{0}|",
        "e000011": "directory used to store semaphores for backup/restore synchronization doesn't exist - dir |{0}|",
        "e000012": "cannot create the configuration cache file, neither FOGLAMP_DATA nor FOGLAMP_ROOT are defined.",
        "e000013": "cannot create the configuration cache file, provided path is not a directory - dir |{0}|",
        "e000014": "the identified path of backups doesn't exists, creation was tried "
                   "- dir |{0}| - error details |{1}|",
        "e000015": "The command is not available neither using the unmanaged approach"
                   " - command |{0}|",
        "e000016": "Postgres command is not executable - command |{0}|",
        "e000017": "The execution of the Postgres command using the -V option produce an error"
                   " - command |{0}| - output |{1}|",
        "e000018": "It is not possible to read data from Postgres"
                   " - command |{0}| - exit code |{1}| - output |{2}|",
        "e000019": "The command is not available using the managed approach"
                   " - command |{0}|",

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
        "schema": {
            "description": "Schema for backup and restore operations.",
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
            if not self._logger:
                self._logger = logger.setup(self._MODULE_NAME,
                                            destination=_LOGGER_DESTINATION,
                                            level=_LOGGER_LEVEL)
        except Exception as _ex:
            _message = self._MESSAGES_LIST["e000001"].format(str(_ex))
            _current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    
            print("[FOGLAMP] {0} - ERROR - {1}".format(_current_time, _message), file=sys.stderr)
            sys.exit(1)

        self._backup = Backup(self._storage)

        self._config_from_manager = {}
        self._config = {}
        self._job = lib.Job()
        self._event_loop = asyncio.get_event_loop()

        self._dir_foglamp_root = ""
        self._dir_foglamp_data = ""
        self._dir_foglamp_data_etc = ""
        self._dir_foglamp_backup = ""

        self._dir_backups = ""
        self._dir_semaphores = ""

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

        full_file_name = self._dir_backups + "/" + self._BACKUP_FILE_NAME_PREFIX + execution_time
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
            self._dir_foglamp_root = os.getenv("FOGLAMP_ROOT")
        else:
            self._dir_foglamp_root = self._DEFAULT_FOGLAMP_ROOT

        # Evaluates FOGLAMP_DATA
        if "FOGLAMP_DATA" in os.environ:
            self._dir_foglamp_data = os.getenv("FOGLAMP_DATA")
        else:
            self._dir_foglamp_data = self._dir_foglamp_root + "/data"

        # Evaluates FOGLAMP_BACKUP
        if "FOGLAMP_BACKUP" in os.environ:
            self._dir_foglamp_backup = os.getenv("FOGLAMP_BACKUP")
        else:
            self._dir_foglamp_backup = self._dir_foglamp_data + "/backup"

        # Evaluates etc directory
        self._dir_foglamp_data_etc = self._dir_foglamp_data + "/etc"

        self._check_create_path(self._dir_foglamp_backup)
        self._check_create_path(self._dir_foglamp_data_etc)

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

    def _check_for_execution(self):
        """ Executes all the checks to ensure the prerequisites to execute the backup are met

        Args:
        Returns:
        Raises:
        """

        self._check_commands()
        self._check_db()

    def _check_commands(self):
        """ Identify and checks the Postgres commands

        Args:
        Returns:
        Raises:
        """

        for cmd in self._PG_COMMANDS_TO_CHECK:

            cmd_identified = self._check_command_identification(cmd)
            self._check_command_test(cmd_identified)

    def _is_plugin_managed(self, plugin_to_identify):
        """ Identifies the type of plugin, Managed or not, looking at the foglamp.json configuration file

        Args:
            plugin_to_identify: str - plugin to evaluate if it is managed or not
        Returns:
            type: boolean - True if it is a managed plugin
        Raises:
        """

        plugin_type = False

        file_full_path = self._dir_foglamp_data + lib.FOGLAMP_CFG_FILE

        with open(file_full_path) as file:
            cfg_file = json.load(file)

        plugins = cfg_file["storage plugins"]

        for plugin in plugins:
            if plugin["plugin"] == plugin_to_identify:
                plugin_type = plugin["managed"]

        return plugin_type

    def _check_command_identification(self, cmd_to_identify):
        """ Identifies the proper Postgres command to use, 2 possible cases :

        Managed    - command is available in $FOGLAMP_ROOT/plugins/storage/postgres/pgsql/bin
        Unmanaged  - checks using the path and it identifies the used command through 'command -v'

        Args:
            cmd_to_identify: str - command to identify

        Returns:
            cmd_identified: str - actual identified command to use

        Raises:
            exceptions.PgCommandUnAvailable
        """

        is_managed = self._is_plugin_managed("postgres")

        if is_managed:
            # Checks for Managed
            cmd_managed = "{root}/{path}/{cmd}".format(
                                                        root=self._dir_foglamp_root,
                                                        path=self._DIR_MANAGED_FOGLAMP_PG_COMMANDS,
                                                        cmd=cmd_to_identify)

            if os.path.exists(cmd_managed):
                cmd_identified = cmd_managed
            else:
                _message = self._MESSAGES_LIST["e000019"].format(cmd_to_identify)
                self._logger.error("{0}".format(_message))

                raise exceptions.PgCommandUnAvailable(_message)
        else:
            # Checks for Unmanaged
            cmd = "command -v " + cmd_to_identify

            # The timeout command can't be used with 'command'
            # noinspection PyArgumentEqualDefault
            _exit_code, output = lib.exec_wait(_cmd=cmd,
                                               _output_capture=True,
                                               _timeout=0
                                               )

            self._logger.debug("{func} - cmd |{cmd}| - exit_code |{exit_code}| output |{output}| ".format(
                                                                            func="_check_command_identification",
                                                                            cmd=cmd,
                                                                            exit_code=_exit_code,
                                                                            output=output))

            if _exit_code == 0:
                cmd_identified = lib.cr_strip(output)
            else:
                _message = self._MESSAGES_LIST["e000015"].format(cmd)
                self._logger.error("{0}".format(_message))

                raise exceptions.PgCommandUnAvailable(_message)

        self._PG_COMMANDS_TO_CHECK[cmd_to_identify] = cmd_identified

        return cmd_identified

    def _check_command_test(self, cmd_to_test):
        """ Tests if the Postgres command could be successfully launched/used

        Args:
            cmd_to_test: str -  Command to test

        Returns:
        Raises:
            exceptions.PgCommandUnAvailable
            exceptions.PgCommandNotExecutable
        """

        if os.access(cmd_to_test, os.X_OK):
            cmd = cmd_to_test + " -V"

            _exit_code, output = lib.exec_wait(_cmd=cmd,
                                               _output_capture=True,
                                               _timeout=self._config['timeout']
                                               )

            self._logger.debug("{func} - cmd |{cmd}| - exit_code |{exit_code}| output |{output}| ".format(
                                                                            func="_check_command_test",
                                                                            cmd=cmd,
                                                                            exit_code=_exit_code,
                                                                            output=output))

            if _exit_code != 0:
                _message = self._MESSAGES_LIST["e000017"].format(cmd_to_test, output)
                self._logger.error("{0}".format(_message))

                raise exceptions.PgCommandUnAvailable(_message)

        else:
            _message = self._MESSAGES_LIST["e000016"].format(cmd_to_test)
            self._logger.error("{0}".format(_message))

            raise exceptions.PgCommandNotExecutable(_message)

    def _check_db(self):
        """ Checks if the database is working properly reading a sample row from the backups table

        Args:
        Returns:
        Raises:
            exceptions.CannotReadPostgres
        """

        cmd_psql = self._PG_COMMANDS_TO_CHECK[self._PG_COMMAND_PSQL]

        cmd = '{psql} -d {db} -t -c "SELECT id FROM {schema}.{table} LIMIT 1;"'.format(
                                                                psql=cmd_psql,
                                                                db=self._config['database'],
                                                                schema=self._config['schema'],
                                                                table=lib.STORAGE_TABLE_BACKUPS)

        _exit_code, output = lib.exec_wait(_cmd=cmd,
                                           _output_capture=True,
                                           _timeout=self._config['timeout']
                                           )

        self._logger.debug("{func} - cmd |{cmd}| - exit_code |{exit_code}| output |{output}| ".format(
                            func="_check_db",
                            cmd=cmd,
                            exit_code=_exit_code,
                            output=lib.cr_strip(output)))

        if _exit_code != 0:
            _message = self._MESSAGES_LIST["e000018"].format(cmd, _exit_code, output)
            self._logger.error("{0}".format(_message))

            raise exceptions.CannotReadPostgres(_message)

    def init(self):
        """ Setups the correct state for the execution of the backup

        Args:
        Returns:
        Raises:
            exceptions.BackupOrRestoreAlreadyRunning
        """

        self._logger.debug("{func}".format(func="init"))

        self._evaluate_paths()

        self._retrieve_configuration()

        self._check_for_execution()

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

    def execute_backup(self):
        """ Executes the backup functionality

        Args:
        Returns:
        Raises:
            exceptions.BackupFailed
        """

        self._logger.debug("{func}".format(func="execute_backup"))

        self._purge_old_backups()

        backup_file = self._generate_file_name()

        lib.sl_backup_status_create(backup_file, lib.BackupType.FULL, lib.BackupStatus.RUNNING)

        status, exit_code = self._run_backup_command(backup_file)

        backup_information = lib.get_backup_details_from_file_name(backup_file)

        lib.sl_backup_status_update(backup_information['id'], status, exit_code)

        if status != lib.BackupStatus.COMPLETED:

            self._logger.error(self._MESSAGES_LIST["e000007"])
            raise exceptions.BackupFailed

    def _purge_old_backups(self):
        """  Deletes old backups in relation at the retention parameter

        Args:
        Returns:
        Raises:
        """

        backups_info = self._backup.get_all_backups_complete(
                                            lib.MAX_NUMBER_OF_BACKUPS_TO_RETRIEVE,
                                            0,
                                            None,
                                            lib.SortOrder.ASC)

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
                self._backup.delete_backup(backup_id)

    def _run_backup_command(self, _backup_file):
        """ Backups the entire FogLAMP repository into a file in the local file system

        Args:
            _backup_file: backup file to create  as a full path
        Returns:
            _status: status of the backup
            _exit_code: exit status of the operation, 0=Successful
        Raises:
        """

        self._logger.debug("{func} - file_name |{file}|".format(func="_run_backup_command",
                                                                file=_backup_file))

        # Prepares the backup command
        cmd = "{cmd} {options} {db} > {file}".format(
                                                cmd=self._PG_COMMANDS_TO_CHECK[self._PG_COMMAND_PG_DUMP],
                                                options="--serializable-deferrable -Fc",
                                                db=self._config['database'],
                                                file=_backup_file
        )

        # Executes the backup waiting for the completion and using a retry mechanism
        # noinspection PyArgumentEqualDefault
        _exit_code, output = lib.exec_wait_retry(cmd,
                                                 output_capture=True,
                                                 exit_code_ok=0,
                                                 max_retry=self._config['max_retry'],
                                                 timeout=self._config['timeout']
                                                 )

        if _exit_code == 0:
            _status = lib.BackupStatus.COMPLETED
        else:
            _status = lib.BackupStatus.FAILED

        self._logger.debug("{func} - status |{status}| - exit_code |{exit_code}| "
                           "- cmd |{cmd}|  output |{output}| ".format(
                                                                        func="_run_backup_command",
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
        self._config['schema'] = _config_from_manager['schema']['value']
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
        """ Identifies the path of the configuration cache file,

        Args:
        Returns:
        Raises:
        """

        file_full_path = self._dir_foglamp_data_etc + "/" + self._CONFIG_CACHE_FILE

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

        # Identifies the directory of backups and checks its existence
        if self._config['backup-dir'] != "none":

            self._dir_backups = self._config['backup-dir']
        else:
            self._dir_backups = self._dir_foglamp_backup

        self._check_create_path(self._dir_backups)

        # Identifies the directory for the semaphores and checks its existence
        # Stores semaphores in the _backups_dir if semaphores-dir is not defined
        if self._config['semaphores-dir'] != "none":

            self._dir_semaphores = self._config['semaphores-dir']
        else:
            self._dir_semaphores = self._dir_backups
            lib.JOB_SEM_FILE_PATH = self._dir_semaphores

        self._check_create_path(self._dir_semaphores)

    def run(self):
        """  Creates a new backup

        Args:
        Returns:
        Raises:
        """

        self.init()
        self.execute_backup()
        self.shutdown()


if __name__ == "__main__":

    # Initializes the logger
    try:
        _logger = logger.setup(_MODULE_NAME,
                               destination=_LOGGER_DESTINATION,
                               level=_LOGGER_LEVEL)

    except Exception as ex:
        message = _MESSAGES_LIST["e000001"].format(str(ex))
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")

        print("[FOGLAMP] {0} - ERROR - {1}".format(current_time, message), file=sys.stderr)
        sys.exit(1)

    # Starts
    _logger.info(_MESSAGES_LIST["i000001"])

    # Initializes FoglampProcess and Backup classes - handling the command line parameters
    try:
        backup_process = BackupProcess()

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
            name=backup_process._name,
            addr=backup_process._core_management_host,
            port=backup_process._core_management_port))

        backup_process.run()

        _logger.info(_MESSAGES_LIST["i000002"])
        sys.exit(0)

    except Exception as ex:
        message = _MESSAGES_LIST["e000002"].format(ex)
        _logger.exception(message)

        backup_process.shutdown()
        _logger.info(_MESSAGES_LIST["i000002"])
        sys.exit(1)
