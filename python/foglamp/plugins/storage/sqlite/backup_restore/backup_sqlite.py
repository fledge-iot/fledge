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
import asyncio

from foglamp.common.process import FoglampProcess
from foglamp.common import logger
from foglamp.common.audit_logger import AuditLogger

from foglamp.plugins.storage.common.backup import Backup
import foglamp.plugins.storage.common.lib as lib
import foglamp.plugins.storage.common.exceptions as exceptions

__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_MODULE_NAME = "foglamp_backup_sqlite_module"

_MESSAGES_LIST = {

    # Information messages
    "i000001": "Execution started.",
    "i000002": "Execution completed.",

    # Warning / Error messages
    "e000001": "cannot initialize the logger - error details |{0}|",
    "e000002": "an error occurred during the backup operation - error details |{0}|",
    "e000004": "cannot complete the initialization - error details |{0}|",
}
""" Messages used for Information, Warning and Error notice """


# Log definitions
_logger = None

_LOG_LEVEL_DEBUG = 10
_LOG_LEVEL_INFO = 20

_LOGGER_LEVEL = _LOG_LEVEL_INFO
_LOGGER_DESTINATION = logger.SYSLOG


# noinspection PyAbstractClass
class BackupProcess(FoglampProcess):
    """ Backups the entire FogLAMP repository into a file in the local filesystem,
        it executes a full warm backup
    """

    _MODULE_NAME = "foglamp_backup_sqlite_process"

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
        "e000019": "The command is not available using the managed approach"
                   " - command |{0}|",

    }
    """ Messages used for Information, Warning and Error notice """

    _logger = None

    def __init__(self):

        super().__init__()

        if not self._logger:
            self._logger = logger.setup(self._MODULE_NAME,
                                        destination=_LOGGER_DESTINATION,
                                        level=_LOGGER_LEVEL)

        self._backup = Backup(self._storage_async)
        self._backup_lib = lib.BackupRestoreLib(self._storage_async, self._logger)

        self._job = lib.Job()

        # Creates the objects references used by the library
        lib._logger = self._logger
        lib._storage = self._storage_async

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

        full_file_name = self._backup_lib.dir_backups + "/" + self._BACKUP_FILE_NAME_PREFIX + execution_time
        ext = "db"

        _backup_file = "{file}.{ext}".format(file=full_file_name, ext=ext)

        return _backup_file

    def check_for_execution_backup(self):
        """ Executes all the checks to ensure the prerequisites to execute the backup are met

        Args:
        Returns:
        Raises:
        """

    def init(self):
        """ Setups the correct state for the execution of the backup

        Args:
        Returns:
        Raises:
            exceptions.BackupOrRestoreAlreadyRunning
        """

        self._logger.debug("{func}".format(func="init"))

        self._backup_lib.evaluate_paths()

        self._backup_lib.retrieve_configuration()

        self.check_for_execution_backup()

        # Checks for backup/restore synchronization
        pid = self._job.is_running()
        if pid == 0:

            # no job is running
            pid = os.getpid()
            self._job.set_as_running(self._backup_lib.JOB_SEM_FILE_BACKUP, pid)

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

        self._backup_lib.sl_backup_status_create(backup_file, lib.BackupType.FULL, lib.BackupStatus.RUNNING)

        status, exit_code = self._run_backup_command(backup_file)

        backup_information = self._backup_lib.sl_get_backup_details_from_file_name(backup_file)

        self._backup_lib.sl_backup_status_update(backup_information['id'], status, exit_code)

        audit = AuditLogger(self._storage_async)
        loop = asyncio.get_event_loop()
        if status != lib.BackupStatus.COMPLETED:

            self._logger.error(self._MESSAGES_LIST["e000007"])
            loop.run_until_complete(audit.information('BKEXC', {'status': 'failed'}))
            raise exceptions.BackupFailed
        else:
            loop.run_until_complete(audit.information('BKEXC', {'status': 'completed'}))

    def _purge_old_backups(self):
        """  Deletes old backups in relation at the retention parameter

        Args:
        Returns:
        Raises:
        """

        backups_info = asyncio.get_event_loop().run_until_complete(self._backup.get_all_backups(
                                            self._backup_lib.MAX_NUMBER_OF_BACKUPS_TO_RETRIEVE,
                                            0,
                                            None,
                                            lib.SortOrder.ASC))

        # Evaluates which backup should be deleted
        backups_n = len(backups_info)
        # -1 so at the end of the current backup up to 'retention' backups will be available
        last_to_delete = backups_n - (self._backup_lib.config['retention'] - 1)

        if last_to_delete > 0:

            # Deletes backups
            backups_to_delete = backups_info[:last_to_delete]

            for row in backups_to_delete:
                backup_id = row['id']
                file_name = row['file_name']

                self._logger.debug("{func} - id |{id}| - file_name |{file}|".format(func="_purge_old_backups",
                                                                                    id=backup_id,
                                                                                    file=file_name))
                asyncio.get_event_loop().run_until_complete(self._backup.delete_backup(backup_id))

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
        cmd = "{sqlite_cmd} {path}/{db} '{backup_cmd} {file}'".format(
                                                sqlite_cmd=self._backup_lib.SQLITE_SQLITE,
                                                path=self._backup_lib.dir_foglamp_data,
                                                db=self._backup_lib.config['database-filename'],
                                                backup_cmd=self._backup_lib.SQLITE_BACKUP,
                                                file=_backup_file
        )

        # Executes the backup waiting for the completion and using a retry mechanism
        # noinspection PyArgumentEqualDefault
        _exit_code, output = lib.exec_wait_retry(cmd,
                                                 output_capture=True,
                                                 exit_code_ok=0,
                                                 max_retry=self._backup_lib.config['max_retry'],
                                                 timeout=self._backup_lib.config['timeout']
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

        self._job.set_as_completed(self._backup_lib.JOB_SEM_FILE_BACKUP)

    def run(self):
        """  Creates a new backup

        Args:
        Returns:
        Raises:
        """

        self.init()

        try:
            self.execute_backup()

        except Exception as _ex:
            _message = _MESSAGES_LIST["e000002"].format(_ex)
            _logger.error(_message)

            self.shutdown()

            raise exceptions.RestoreFailed(_message)
        else:
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
        message = _MESSAGES_LIST["e000004"].format(ex)
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
