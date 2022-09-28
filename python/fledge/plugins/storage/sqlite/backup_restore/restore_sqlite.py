#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2017

""" Restores the entire Fledge repository from a previous backup.

It executes a full cold restore,
Fledge will be stopped before the start of the restore and restarted at the end.

It could work also without the Configuration Manager
retrieving the parameters for the execution from the local file 'restore_configuration_cache.json'.
The local file is used as a cache of information retrieved from the Configuration Manager.

The restore operation executes the following macro steps :

    - stops Fledge
    - executes the restore
    - starts Fledge again

so it needs also to interact with SQLite directly executing SQL commands
because at the restart of Fledge the reference to the Storage Layer, previously obtained through
the FledgeProcess class, will be no more valid.


Usage:
    --backup-id                     Restore a specific backup retrieving the related information from the
                                    Storage Layer.
    --file                          Restore a backup from a specific file, the full path should be provided
                                    like for example : --file=/tmp/fledge_2017_09_25_15_10_22.dump

    The latest backup will be restored if no options is used.

Execution samples :
    restore_sqlite --backup-id=29 --port=${adm_port} --address=127.0.0.1 --name=restore
    restore_sqlite --file=/tmp/fledge_backup_2017_12_04_13_57_37.dump \
                     --port=${adm_port} --address=127.0.0.1 --name=restore
    restore_sqlite --port=${adm_port} --address=127.0.0.1 --name=restore

    Note : ${adm_port} should correspond to the Management API port of the core.

Exit code :
    0    = OK
    >=1  = Warning/Error

"""

import time
import sys
import os
import signal
import sqlite3
import json
import tarfile
import shutil
from distutils.dir_util import copy_tree

from fledge.common.parser import Parser
from fledge.common.process import FledgeProcess
from fledge.common import logger
import fledge.plugins.storage.common.lib as lib
import fledge.plugins.storage.common.exceptions as exceptions

__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_MODULE_NAME = "fledge_restore_sqlite_module"

_MESSAGES_LIST = {

    # Information messages
    "i000001": "Execution started.",
    "i000002": "Execution completed.",

    # Warning / Error messages
    "e000001": "cannot initialize the logger - error details |{0}|",
    "e000002": "an error occurred during the restore operation - error details |{0}|",
    "e000003": "invalid command line arguments - error details |{0}|",
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
class RestoreProcess(FledgeProcess):
    """ Restore the entire Fledge repository.
    """

    _MODULE_NAME = "fledge_restore_sqlite_process"

    _FLEDGE_ENVIRONMENT_DEV = "dev"
    _FLEDGE_ENVIRONMENT_DEPLOY = "deploy"

    _FLEDGE_CMD_PATH_DEV = "scripts/fledge"
    _FLEDGE_CMD_PATH_DEPLOY = "bin/fledge"

    # The init method will evaluate the running environment setting the variables accordingly
    _fledge_environment = _FLEDGE_ENVIRONMENT_DEV
    _fledge_cmd = _FLEDGE_CMD_PATH_DEV + " {0}"
    """ Command for managing Fledge, stop/start/status """

    _MESSAGES_LIST = {

        # Information messages
        "i000001": "Execution started.",
        "i000002": "Execution completed.",

        # Warning / Error messages
        "e000000": "general error",
        "e000001": "Invalid file name",
        "e000002": "cannot retrieve the configuration from the manager, trying retrieving from file "
                   "- error details |{0}|",
        "e000003": "cannot retrieve the configuration from file - error details |{0}|",
        "e000004": "cannot restore the backup, file doesn't exists - file name |{0}|",
        "e000006": "cannot start Fledge after the restore - error details |{0}|",
        "e000007": "cannot restore the backup, restarting Fledge - error details |{0}|",
        "e000008": "cannot identify Fledge status, the maximum number of retries has been reached "
                   "- error details |{0}|",
        "e000009": "cannot restore the backup, either a backup or a restore is already running - pid |{0}|",
        "e000010": "cannot retrieve the Fledge status - error details |{0}|",
        "e000011": "cannot restore the backup, the selected backup doesn't exists - backup id |{0}|",
        "e000012": "cannot restore the backup, the selected backup doesn't exists - backup file name |{0}|",
        "e000013": "cannot proceed the execution, "
                   "It is not possible to determine the environment in which the code is running"
                   " neither Deployment nor Development",
    }
    """ Messages used for Information, Warning and Error notice """

    _logger = None

    _backup_id = None
    """ Used to store the optional command line parameter value """

    _file_name = None
    """ Used to store the optional command line parameter value """

    class FledgeStatus(object):
        """ Fledge - possible status """

        NOT_DEFINED = 0
        STOPPED = 1
        RUNNING = 2

    @staticmethod
    def _signal_handler(_signo, _stack_frame):
        """ Handles signals to avoid restore termination doing Fledge stop

        Args:
        Returns:
        Raises:
        """

        short_stack_frame = str(_stack_frame)[:100]
        _logger.debug("{func} - signal |{signo}| - info |{ssf}| ".format(
            func="_signal_handler",
            signo=_signo,
            ssf=short_stack_frame))

    def __init__(self):

        super().__init__()

        if not self._logger:
            self._logger = logger.setup(self._MODULE_NAME,
                                        destination=_LOGGER_DESTINATION,
                                        level=_LOGGER_LEVEL)

        # Handled Restore command line parameters
        try:
            self._backup_id = Parser.get('--backup-id')
            self._file_name = Parser.get('--file')

        except Exception as _ex:

            _message = _MESSAGES_LIST["e000003"].format(_ex)
            _logger.exception(_message)

            raise exceptions.ArgumentParserError(_message)

        self._restore_lib = lib.BackupRestoreLib(self._storage_async, self._logger)

        self._job = lib.Job()

        self._force_restore = True
        """ Restore a backup doesn't exist in the backups table """

        # Creates the objects references used by the library
        lib._logger = self._logger
        lib._storage = self._storage_async

    def _identifies_backup_to_restore(self):
        """Identifies the backup to restore either
        - latest backup
        - or a specific backup_id
        - or a specific file_name

        Args:
        Returns:
        Raises:
            FileNotFoundError
        """

        backup_id = None
        file_name = None

        # Case - last backup
        if self._backup_id is None and \
           self._file_name is None:

            backup_id,  file_name = self._identify_last_backup()

        # Case - backup-id
        elif self._backup_id is not None:

            try:
                backup_info = self._restore_lib.sl_get_backup_details(self._backup_id)
                backup_id = backup_info["id"]
                file_name = backup_info["file_name"]

            except exceptions.DoesNotExist:
                _message = self._MESSAGES_LIST["e000011"].format(self._backup_id)
                _logger.error(_message)

                raise exceptions.DoesNotExist(_message)

        # Case - file-name
        elif self._file_name is not None:

            try:
                backup_info = self._restore_lib.sl_get_backup_details_from_file_name(self._file_name)
                backup_id = backup_info["id"]
                file_name = backup_info["file_name"]

            except exceptions.DoesNotExist:
                if self._force_restore:
                    file_name = self._file_name

                else:
                    _message = self._MESSAGES_LIST["e000012"].format(self._file_name)
                    _logger.error(_message)

                    raise exceptions.DoesNotExist(_message)

        if not os.path.exists(file_name):

            _message = self._MESSAGES_LIST["e000004"].format(file_name)
            _logger.error(_message)

            raise FileNotFoundError(_message)

        return backup_id, file_name

    def storage_retrieve(self, sql_cmd):
        """  Executes a sql command against SQLite directly

        Args:
        Returns:
            raw_data:list - Python list containing the rows retrieved from the Storage layer
        Raises:
        """

        _logger.debug("{func} - sql cmd |{cmd}| ".format(func="storage_retrieve",
                                                         cmd=sql_cmd))

        db_connection_string = "{path}/{db}".format(
                                                        path=self._restore_lib.dir_fledge_data,
                                                        db=self._restore_lib.config['database-filename']
                                                    )

        comm = sqlite3.connect(db_connection_string)

        cur = comm.cursor()

        cur.execute(sql_cmd)

        raw_data = cur.fetchall()
        cur.close()

        return raw_data

    def storage_update(self, sql_cmd, records=None):
        """ Executes a sql command against SQLite directly

        Args:
            sql_cmd: sql command to execute
            records: to insert multiple records only if records are there otherwise default None and will treat as single execution
        Returns:
        Raises:
        """

        _logger.debug("{func} - sql cmd |{cmd} | {records}|".format(func="storage_update", cmd=sql_cmd,
                                                                    records=records))

        db_connection_string = "{path}/{db}".format(
                                                        path=self._restore_lib.dir_fledge_data,
                                                        db=self._restore_lib.config['database-filename']
                                                    )

        comm = sqlite3.connect(db_connection_string)

        cur = comm.cursor()
        if records is None:
            cur.execute(sql_cmd)
        else:
            cur.executemany(sql_cmd, records)
        comm.commit()
        comm.close()

    def _identify_last_backup(self):
        """ Identifies latest executed backup either successfully executed (COMPLETED) or already RESTORED

        Args:
        Returns:
        Raises:
            NoBackupAvailableError: No backup either successfully executed or already restored available
            FileNameError: it is impossible to identify an unique backup to restore
        """

        self._logger.debug("{func} ".format(func="_identify_last_backup"))

        sql_cmd = """
            SELECT id, file_name FROM backups WHERE id=
            (SELECT  MAX(id) FROM backups WHERE status={0} or status={1});
        """.format(lib.BackupStatus.COMPLETED,
                   lib.BackupStatus.RESTORED)

        data = self.storage_retrieve(sql_cmd)

        if len(data) == 0:
            raise exceptions.NoBackupAvailableError

        elif len(data) == 1:

            _backup_id = data[0][0]
            _file_name = data[0][1]

        else:
            raise exceptions.FileNameError

        return _backup_id, _file_name

    def get_backup_details_from_file_name(self, _file_name):
        """ Retrieves backup information from file name

        Args:
            _file_name: file name to search in the Storage layer

        Returns:
            backup_information: Backup information related to the file name

        Raises:
            exceptions.NoBackupAvailableError
            exceptions.FileNameError
        """

        self._logger.debug("{func} ".format(func="get_backup_details_from_file_name"))

        sql_cmd = """
            SELECT * FROM backups WHERE file_name='{file}'
        """.format(file=_file_name)
        data = self.storage_retrieve(sql_cmd)

        if len(data) == 0:
            raise exceptions.NoBackupAvailableError

        elif len(data) == 1:
            backup_information = data[0]

        else:
            raise exceptions.FileNameError

        return backup_information

    def _fledge_stop(self):
        """ Stops Fledge before for the execution of the backup, doing a cold backup

        Args:
        Returns:
        Raises:
            FledgeStopError
        """

        self._logger.debug("{func}".format(func="_fledge_stop"))

        cmd = "{path}/{cmd}".format(
            path=self._restore_lib.dir_fledge_root,
            cmd=self._fledge_cmd.format("stop")
        )

        # Stops Fledge
        status, output = lib.exec_wait_retry(cmd, True,
                                             max_retry=self._restore_lib.config['max_retry'],
                                             timeout=self._restore_lib.config['timeout'])

        self._logger.debug("{func} - status |{status}| - cmd |{cmd}| - output |{output}|   ".format(
                    func="_fledge_stop",
                    status=status,
                    cmd=cmd,
                    output=output))

        if status == 0:

            # Checks to ensure the Fledge status
            if self._fledge_status() != self.FledgeStatus.STOPPED:
                raise exceptions.FledgeStopError(output)
        else:
            raise exceptions.FledgeStopError(output)

    def _decode_fledge_status(self, text):
        """
        Args:
        Returns:
        Raises:
        """

        text_upper = text.upper()

        if 'FLEDGE UPTIME' in text_upper:
            status = self.FledgeStatus.RUNNING

        elif 'FLEDGE NOT RUNNING.' in text_upper:
            status = self.FledgeStatus.STOPPED

        else:
            status = self.FledgeStatus.NOT_DEFINED

        return status

    def _check_wait_fledge_start(self):
        """ Checks and waits Fledge to start

        Args:
        Returns:
            status: FledgeStatus - {NOT_DEFINED|STOPPED|RUNNING}
        Raises:
        """

        self._logger.debug("{func}".format(func="_check_wait_fledge_start"))

        status = self.FledgeStatus.NOT_DEFINED

        n_retry = 0
        max_reties = self._restore_lib.config['restart-max-retries']
        sleep_time = self._restore_lib.config['restart-sleep']

        while n_retry < max_reties:

            self._logger.debug("{func}".format(func="_check_wait_fledge_start - checks Fledge status"))

            status = self._fledge_status()
            if status == self.FledgeStatus.RUNNING:
                break

            self._logger.debug("{func}".format(func="_check_wait_fledge_start - sleep {0}".format(sleep_time)))

            time.sleep(sleep_time)
            n_retry += 1

        return status

    def _fledge_status(self):
        """ Checks Fledge status

        to ensure the status is stable and reliable,
        It executes the Fledge 'status' command until either
        until the same value comes back for 3 times in a row  or it reaches the maximum number of retries allowed.

        Args:
        Returns:
            status: FledgeStatus - {STATUS_NOT_DEFINED|STATUS_STOPPED|STATUS_RUNNING}
        Raises:
        """

        status = self.FledgeStatus.NOT_DEFINED

        num_exec = 0
        max_exec = 10
        same_status = 0
        same_status_ok = 3
        sleep_time = 1

        while (same_status < same_status_ok) and (num_exec <= max_exec):

            try:

                cmd = "{path}/{cmd}".format(
                            path=self._restore_lib.dir_fledge_root,
                            cmd=self._fledge_cmd.format("status")
                )

                cmd_status, output = lib.exec_wait(cmd, True, _timeout=self._restore_lib.config['timeout'])

                self._logger.debug("{func} - output |{output}| \r - status |{status}|  ".format(
                                                                                            func="_fledge_status",
                                                                                            output=output,
                                                                                            status=cmd_status))

                num_exec += 1

                new_status = self._decode_fledge_status(output)

            except Exception as _ex:
                _message = self._MESSAGES_LIST["e000010"].format(_ex)
                _logger.error(_message)

                raise

            else:
                if new_status == status:
                    same_status += 1
                    time.sleep(sleep_time)
                else:
                    status = new_status
                    same_status = 0

        if num_exec >= max_exec:
            _message = self._MESSAGES_LIST["e000008"]
            self._logger.error(_message)

            status = self.FledgeStatus.NOT_DEFINED

        return status

    def _run_restore_command(self, backup_file, restore_command):
        """ Executes the restore of the storage layer from a backup

        Args:
            backup_file: backup file to restore
        Returns:
        Raises:
            RestoreError
        """

        self._logger.debug("{func} - Restore starts - file name |{file}|".format(
                                                                    func="_run_restore_command",
                                                                    file=backup_file))

        # Prepares the restore command
        cmd = "{cmd} {file} {path}/{db} ".format(
                                                cmd=restore_command,
                                                file=backup_file,
                                                path=self._restore_lib.dir_fledge_data,
                                                db=self._restore_lib.config['database-filename']

        )

        # Restores the backup
        status, output = lib.exec_wait_retry(cmd, True, timeout=self._restore_lib.config['timeout'])

        self._logger.debug("{func} - Restore ends - status |{status}| - cmd |{cmd}| - output |{output}|".format(
                                    func="_run_restore_command",
                                    status=status,
                                    cmd=cmd,
                                    output=output))

        if status != 0:
            raise exceptions.RestoreFailed

        # Delete files related to the WAL mechanism
        cmd = "rm  {path}/fledge.db-shm ".format(path=self._restore_lib.dir_fledge_data)
        status, output = lib.exec_wait_retry(cmd, True, timeout=self._restore_lib.config['timeout'])

        cmd = "rm  {path}/fledge.db-wal ".format(path=self._restore_lib.dir_fledge_data)
        status, output = lib.exec_wait_retry(cmd, True, timeout=self._restore_lib.config['timeout'])

    def _fledge_start(self):
        """ Starts Fledge after the execution of the restore

        Args:
        Returns:
        Raises:
            FledgeStartError
        """

        cmd = "{path}/{cmd}".format(
                                    path=self._restore_lib.dir_fledge_root,
                                    cmd=self._fledge_cmd.format("start")
        )

        exit_code, output = lib.exec_wait_retry(
                                                cmd,
                                                True,
                                                max_retry=self._restore_lib.config['max_retry'],
                                                timeout=self._restore_lib.config['timeout'])

        self._logger.debug("{func} - exit_code |{exit_code}| - cmd |{cmd}| - output |{output}|".format(
                                    func="_fledge_start",
                                    exit_code=exit_code,
                                    cmd=cmd,
                                    output=output))

        if exit_code == 0:
            if self._check_wait_fledge_start() != self.FledgeStatus.RUNNING:
                raise exceptions.FledgeStartError

        else:
            raise exceptions.FledgeStartError

    def insert_backup_entries(self, old_data: list, new_data: list) -> None:
        """ Insert those backup entries from old data which are not found in new data

        Args:
            old_data: Old backup data before restore
            new_data: New backup data after restore

        Returns:

        Raises:
        """
        self._logger.debug("Old backup data: {} - New backup data: {}".format(old_data, new_data))
        matched_entry_to_delete = []
        for idx, old_row in enumerate(old_data):
            for new_row in new_data:
                if old_row['file_name'] == new_row[1]:
                    matched_entry_to_delete.append(old_row['file_name'])
                    break
        self._logger.debug("Matched entry deletion list from old backup data: {}".format(matched_entry_to_delete))
        # Filter duplicate records between old and new backup data list
        filtered_list = [d for d in old_data if d['file_name'] not in matched_entry_to_delete]
        self._logger.debug("Filtered list: {}".format(filtered_list))
        # Prepare backup multiple records with execute many operation of sqlite
        backup_list = []
        for row in filtered_list:
            r_tuple = (row['file_name'], row['ts'], row['type'], row['status'], row['exit_code'])
            backup_list.append(r_tuple)
        # Insert new backup entries which were before restored checkpoint - this way we can't loose all backups
        sql_cmd = "INSERT INTO backups (file_name, ts, type, status, exit_code) VALUES (?, ?, ?, ?, ?)"
        self._logger.debug("Insert new entries from backup list: {}".format(backup_list))

        self.storage_update(sql_cmd, backup_list)

    def backup_status_update(self, backup_id, status):
        """ Updates the status of the backup in the Storage layer

        Args:
            backup_id: int -
            status: BackupStatus -
        Returns:
        Raises:
        """

        _logger.debug("{func} - backup id |{id}| ".format(func="backup_status_update",
                                                          id=backup_id))

        sql_cmd = """

            UPDATE backups SET  status={status} WHERE id='{id}';

            """.format(status=status,
                       id=backup_id, )

        self.storage_update(sql_cmd)

    def tar_extraction(self, file_name) -> str:
        """ Extracts the files from tar.gz backup file

        Args:
            file_name: filename of the backup
        Returns:
            Full backup filepath
        Raises:
        """
        dummy, file_extension = os.path.splitext(file_name)
        self._logger.debug("tar_extraction - filename  :{}: file_extension :{}: ".format(file_name, file_extension))
        # Removes tar.gz
        filename_base1 = os.path.basename(file_name)
        filename_base2, dummy = os.path.splitext(filename_base1)
        filename_base, dummy = os.path.splitext(filename_base2)
        extract_path = "{}/extract".format(self._restore_lib.dir_fledge_backup)
        if not os.path.isdir(extract_path):
            os.mkdir(extract_path)
        else:
            shutil.rmtree(extract_path)
            os.mkdir(extract_path)

        # Extracts the tar
        backup_tar = tarfile.open(file_name)
        backup_tar.extractall(extract_path)
        db_file_from_extract = [entry for entry in backup_tar.getnames() if entry.endswith(".db")]
        backup_tar.close()

        # Moves the db file to the right position
        db_file_to_restore = db_file_from_extract[0] if db_file_from_extract else "{}.db".format(filename_base)
        file_source = "{}/{}".format(extract_path, db_file_to_restore)
        file_target = "{}/{}.db".format(self._restore_lib.dir_fledge_backup, filename_base)
        self._logger.debug("tar_extraction 'db' - source :{}: target :{}: ".format(file_source, file_target))
        os.rename(file_source, file_target)

        # etc
        source = "{}/etc".format(extract_path)
        target = "{}/etc".format(self._restore_lib.dir_fledge_data)
        self._logger.debug("tar_extraction 'etc' - source :{}: target :{}: ".format(source, target))
        copy_tree(source, target)

        # external scripts
        dir_scripts = "{}/scripts".format(extract_path)
        if os.path.isdir(dir_scripts):
            target = "{}/scripts".format(self._restore_lib.dir_fledge_data)
            if not os.path.isdir(target):
                os.mkdir(target)
            source = dir_scripts
            self._logger.debug("tar_extraction 'scripts' - source :{}: target :{}: ".format(source, target))
            copy_tree(source, target)

        # software
        is_software = "{}/software.json".format(extract_path)
        if os.path.exists(is_software):
            # we don't need to install software as a part of restore automatically
            # It is a user responsibility to install
            with open(is_software, 'r') as f:
                data = json.load(f)
            self._logger.debug("tar_extraction 'data' :{}: ".format(data))
            software_list = []
            for p in data['plugins']:
                # Exclude inbuilt plugins
                if p['packageName'] != '':
                    software_list.append({p['packageName']: p['version']})
            for s in data['services']:
                # Exclude inbuilt services
                if s not in ('storage', 'south', 'north'):
                    # As such no version available for services, therefore keeping empty
                    software_list.append({"fledge-service-{}".format(s): ''})
            self._logger.info("Please check install software list: {}; "
                              "if any of software is not present onto your system, you need to install it "
                              "manually.".format(software_list))
        # Remove extract directory
        shutil.rmtree(extract_path)
        return file_target

    def execute_restore(self) -> None:
        """Executes the restore operation

        Args:
        Returns:
        Raises:
        """

        self._logger.debug("{func}".format(func="execute_restore"))

        # Fetch old backup table entries before restore
        old_backup_entries = self._restore_lib.sl_get_all_backups()
        self._logger.debug("{func} - old backup entries list - {backups}".format(func="execute_restore",
                                                                                 backups=old_backup_entries))

        backup_id, file_name = self._identifies_backup_to_restore()

        self._logger.debug("{func} - backup to restore |{id}| - |{file}| ".format(
                                                                                func="execute_restore",
                                                                                id=backup_id,
                                                                                file=file_name))
        # Stops Fledge if it is running
        if self._fledge_status() == self.FledgeStatus.RUNNING:
            self._fledge_stop()

        self._logger.debug("{func} - Fledge is down".format(func="execute_restore"))

        dummy, file_extension = os.path.splitext(file_name)
        # backward compatibility (<= 1.9.2)
        if file_extension == ".db":
            file_name_db = file_name
            restore_command = self._restore_lib.SQLITE_RESTORE_COPY
        elif file_extension == ".gz":
            file_name_db = self.tar_extraction(file_name)
            restore_command = self._restore_lib.SQLITE_RESTORE_MOVE
        else:
            raise Exception('Unsupported {} file extension found')
        # Executes the restore and then starts Fledge
        try:
            self._run_restore_command(file_name_db, restore_command)
            if self._force_restore and file_extension != ".gz":
                # Retrieve the backup-id after the restore operation
                backup_info = self.get_backup_details_from_file_name(file_name_db)
                backup_id = backup_info[0]
            # Updates the backup status as RESTORED
            self.backup_status_update(backup_id, lib.BackupStatus.RESTORED)
            # Fetch new backup entries after DB fully restored
            sql_cmd = """SELECT id, file_name, ts, type, status, exit_code FROM backups;"""
            new_backup_entries = self.storage_retrieve(sql_cmd)
            self._logger.debug("{func} - !!!New backup entries list - {backups}".format(func="execute_restore",
                                                                                        backups=new_backup_entries))
            # Insert old backup entries into newly restored Database
            self.insert_backup_entries(old_backup_entries, new_backup_entries)
        except Exception as _ex:
            _message = self._MESSAGES_LIST["e000007"].format(_ex)
            self._logger.error(_message)
            raise
        finally:
            try:
                self._fledge_start()
            except Exception as _ex:
                _message = self._MESSAGES_LIST["e000006"].format(_ex)
                self._logger.error(_message)
                raise

    def check_command(self, cmd_to_identify):
        """"Evaluates if the command is available or not

          Args:
          Returns:
              cmd_available: boolean
          Raises:
          """

        cmd = "command -v " + cmd_to_identify

        # The timeout command can't be used with 'command'
        # noinspection PyArgumentEqualDefault
        _exit_code, output = lib.exec_wait(
            _cmd=cmd,
            _output_capture=True,
            _timeout=0
        )

        self._logger.debug("{func} - cmd |{cmd}| - exit_code |{exit_code}| output |{output}| ".format(
            func="check_command",
            cmd=cmd,
            exit_code=_exit_code,
            output=output))

        if _exit_code == 0:
            cmd_available = True
        else:
            cmd_available = False

        return cmd_available

    def evaluate_fledge_env(self):
        """"Evaluates if the code is running either in Development or in Deploy environment

        Args:
        Returns:
            env: str - {_FLEDGE_CMD_PATH_DEPLOY|_FLEDGE_CMD_PATH_DEV}
        Raises:
            exceptions.InvalidFledgeEnvironment
        """

        cmd = self._restore_lib.dir_fledge_root + "/" + self._FLEDGE_CMD_PATH_DEPLOY

        if self.check_command(cmd):
            env = self._FLEDGE_ENVIRONMENT_DEPLOY
        else:

            cmd = self._restore_lib.dir_fledge_root + "/" + self._FLEDGE_CMD_PATH_DEV
            if self.check_command(cmd):

                env = self._FLEDGE_ENVIRONMENT_DEV
            else:
                _message = self._MESSAGES_LIST["e000013"]
                self._logger.error(_message)

                raise exceptions.InvalidFledgeEnvironment

        return env

    def set_fledge_env(self):
        """"Sets a proper configuration in relation to the environment in which the code is running
        either Development or Deploy

        Args:
        Returns:
        Raises:
        """

        self._fledge_environment = self.evaluate_fledge_env()

        # Configures in relation to the environment is use
        if self._fledge_environment == self._FLEDGE_ENVIRONMENT_DEPLOY:

            self._fledge_cmd = self._FLEDGE_CMD_PATH_DEPLOY + " {0}"
        else:
            self._fledge_cmd = self._FLEDGE_CMD_PATH_DEV + " {0}"

    def check_for_execution_restore(self):
        """ Executes all the checks to ensure the prerequisites to execute the backup are met

        Args:
        Returns:
        Raises:
        """

        pass

    def init(self):
        """"Setups the correct state for the execution of the restore

        Args:
        Returns:
        Raises:
        """
        # Setups signals handlers, to avoid the termination of the restore
        # a) SIGINT: Keyboard interrupt
        # b) SIGTERM: kill or system shutdown
        # c) SIGHUP: Controlling shell exiting
        signal.signal(signal.SIGINT, RestoreProcess._signal_handler)
        signal.signal(signal.SIGTERM, RestoreProcess._signal_handler)
        signal.signal(signal.SIGHUP, RestoreProcess._signal_handler)

        self._logger.debug("{func}".format(func="init"))

        self._restore_lib.evaluate_paths()

        self.set_fledge_env()

        self._restore_lib.retrieve_configuration()

        self.check_for_execution_restore()

        # Checks for backup/restore synchronization
        pid = self._job.is_running()
        if pid == 0:

            # no job is running
            pid = os.getpid()
            self._job.set_as_running(self._restore_lib.JOB_SEM_FILE_RESTORE, pid)
        else:
            _message = self._MESSAGES_LIST["e000009"].format(pid)
            self._logger.warning("{0}".format(_message))

            raise exceptions.BackupOrRestoreAlreadyRunning

    def shutdown(self):
        """"Sets the correct state to terminate the execution

        Args:
        Returns:
        Raises:
        """

        self._logger.debug("{func}".format(func="shutdown"))

        self._job.set_as_completed(self._restore_lib.JOB_SEM_FILE_RESTORE)

    def run(self):
        """ Restores a backup

        Args:
        Returns:
        Raises:
            exceptions.RestoreFailed
        """

        self.init()

        try:
            self.execute_restore()

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

        print("[FLEDGE] {0} - ERROR - {1}".format(current_time, message), file=sys.stderr)
        sys.exit(1)

    # Initializes FledgeProcess and RestoreProcess classes - handling also the command line parameters
    try:
        restore_process = RestoreProcess()
    except Exception as ex:
        message = _MESSAGES_LIST["e000004"].format(ex)
        _logger.exception(message)
        sys.exit(1)

    if not restore_process.is_dry_run():
        try:
            # noinspection PyProtectedMember
            _logger.debug("{module} - name |{name}| - address |{addr}| - port |{port}| "
                          "- file |{file}| - backup_id |{backup_id}| ".format(
                                                                            module=_MODULE_NAME,
                                                                            name=restore_process._name,
                                                                            addr=restore_process._core_management_host,
                                                                            port=restore_process._core_management_port,
                                                                            file=restore_process._file_name,
                                                                            backup_id=restore_process._backup_id))
            _logger.info(_MESSAGES_LIST["i000001"])
            restore_process.run()
            _logger.info(_MESSAGES_LIST["i000002"])
            sys.exit(0)
        except Exception as ex:
            message = _MESSAGES_LIST["e000002"].format(ex)
            _logger.exception(message)
            sys.exit(1)
    else:
        # Put any configuration here if required for the restore
        sys.exit()
