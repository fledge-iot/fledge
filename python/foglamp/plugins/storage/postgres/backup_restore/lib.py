# -*- coding: utf-8 -*-
# Copyright (C) 2017

""" Library used for backup and restore operations
"""

import subprocess
import time
import os

from foglamp.common import logger
from foglamp.common.storage_client import payload_builder
from foglamp.common.storage_client.storage_client import StorageClient
import foglamp.tasks.backup_restore.exceptions as exceptions

__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_MODULE_NAME = "foglamp_backup_library"

_MESSAGES_LIST = {

    # Information messages
    "i000000": "Information",

    # Warning / Error messages
    "e000000": "general error",
    "e000001": "semaphore file deleted because it was already in existence - file |{0}|",
    "e000002": "semaphore file deleted because it existed even if the corresponding process was not running "
               "- file |{0}| - pid |{1}|",
    "e000003": "ERROR - the library cannot be executed directly.",
}
""" Messages used for Information, Warning and Error notice """

MAX_NUMBER_OF_BACKUPS_TO_RETRIEVE = 9999
"""" Maximum number of backup information to retrieve from the storage layer"""

STORAGE_TABLE_BACKUPS = "backups"
""" Table name containing the backup information"""

_CMD_TIMEOUT = " timeout --signal=9  "
""" Every external commands will be launched using timeout to avoid endless executions """

BACKUP_TYPE_FULL = 1
BACKUP_TYPE_INCREMENTAL = 2
""" Backup types supported """

BACKUP_STATUS_UNDEFINED = -1
BACKUP_STATUS_RUNNING = 1
BACKUP_STATUS_SUCCESSFUL = 2
BACKUP_STATUS_CANCELLED = 3
BACKUP_STATUS_INTERRUPTED = 4
BACKUP_STATUS_FAILED = 5
BACKUP_STATUS_RESTORED = 6
"""" Backup status"""

JOB_SEM_FILE_PATH = "/tmp"
""" Updated by the caller retrieving from the configuration manager """
JOB_SEM_FILE_BACKUP = ".backup.sem"
JOB_SEM_FILE_RESTORE = ".restore.sem"
"""" Semaphores information for the handling of the backup/restore synchronization """

_logger = {}
_storage = {}
"""" Objects references assigned by the caller """


def exec_wait(_cmd, _output_capture=False, _timeout=0):
    """  Executes an external/shell commands

    Args:
        _cmd: command to execute
        _output_capture: if the output of the command should be captured or not
        _timeout: 0 no timeout or the timeout in seconds for the execution of the command

    Returns:
        _exit_code: exit status of the command
        _output: output of the command
    Raises:
    """

    _output = ""

    if _timeout != 0:
        _cmd = _CMD_TIMEOUT + str(_timeout) + " " + _cmd
        _logger.debug("{func} - Executing command using the timeout |{timeout}| ".format(
                                        func="exec_wait",
                                        timeout=_timeout))

    _logger.debug("{func} - cmd |{cmd}| ".format(func="exec_wait",
                                                 cmd=_cmd))

    if _output_capture:
        process = subprocess.Popen(_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    else:
        process = subprocess.Popen(_cmd, shell=True)

    _exit_code = process.wait()

    if _output_capture:
        output_step1 = process.stdout.read()
        _output = output_step1.decode("utf-8")

    return _exit_code, _output


def exec_wait_retry(cmd, output_capture=False, exit_code_ok=0, max_retry=3, write_error=True, sleep_time=1, timeout=0):
    """ Executes an external command retrying x time the operation up to the exit status match a specific value

    Args:
        cmd: command to execute
        output_capture: if the output of the command should be captured or not
        exit_code_ok: exit status to achieve
        max_retry: maximum number of retries to achieve the desired exit status
        write_error: if a message should be generated for each retry
        sleep_time: seconds to sleep between each retry
        timeout: 0= no timeout, or the timeout in seconds for the execution of the external command

    Returns:
        _exit_code: exit status of the command
        _output: output of the command

    Raises:
    """

    global _logger

    _logger.debug("{func} - cmd |{cmd}| ".format(func="exec_wait_retry",
                                                 cmd=cmd))

    _exit_code = 0
    _output = ""

    # try X times the operation
    retry = 1
    loop_continue = True

    while loop_continue:

        _exit_code, _output = exec_wait(cmd, output_capture, timeout)

        if _exit_code == exit_code_ok:
            loop_continue = False

        elif retry <= max_retry:

            # Prepares for the retry operation
            if write_error:
                short_output = _output[0:50]
                _logger.debug("{func} - cmd |{cmd}| - N retry |{retry}| - message |{msg}| ".format(
                    func="exec_wait_retry",
                    cmd=cmd,
                    retry=retry,
                    msg=short_output)
                )

            time.sleep(sleep_time)
            retry += 1

        else:
            loop_continue = False

    return _exit_code, _output


def get_backup_details_from_file_name(_file_name):
    """ Retrieves backup information from file name

    Args:
        _file_name: file name to search in the Storage layer

    Returns:
        backup_information: Backup information related to the file name

    Raises:
        exceptions.DoesNotExist
        exceptions.NotUniqueBackup
    """

    payload = payload_builder.PayloadBuilder() \
        .WHERE(['file_name', '=', _file_name]) \
        .payload()

    backups_from_storage = _storage.query_tbl_with_payload(STORAGE_TABLE_BACKUPS, payload)

    if backups_from_storage['count'] == 1:

        backup_information = backups_from_storage['rows'][0]

    elif backups_from_storage['count'] == 0:
        raise exceptions.DoesNotExist

    else:
        raise exceptions.NotUniqueBackup

    return backup_information


def backup_status_create(_file_name, _type, _status):
    """ Logs the creation of the backup in the Storage layer

    Args:
        _file_name: file_name used for the backup as a full path
        _type: backup type {BACKUP_TYPE_FULL|BACKUP_TYPE_INCREMENTAL}
        _status: backup status, usually BACKUP_STATUS_RUNNING
    Returns:
    Raises:
    Todo:
    """

    _logger.debug("{func} - file name |{file}| ".format(func="backup_status_create", file=_file_name))

    payload = payload_builder.PayloadBuilder() \
        .INSERT(file_name=_file_name,
                ts="now()",
                type=_type,
                state=_status,
                exit_code=0) \
        .payload()

    _storage.insert_into_tbl(STORAGE_TABLE_BACKUPS, payload)


def backup_status_update(_id, _status, _exit_code):
    """ Updates the status of the backup in the Storage layer

    Args:
        _id: Backup's Id to update
        _status: status of the backup {BACKUP_STATUS_SUCCESSFUL|BACKUP_STATUS_RESTORED}
        _exit_code: exit status of the backup/restore execution
    Returns:
    Raises:
    Todo:
    """

    _logger.debug("{func} - id |{file}| ".format(func="backup_status_update", file=_id))

    payload = payload_builder.PayloadBuilder() \
        .SET(state=_status,
             ts="now()",
             exit_code=_exit_code) \
        .WHERE(['id', '=', _id]) \
        .payload()

    _storage.update_tbl(STORAGE_TABLE_BACKUPS, payload)


class Job:
    """" Handles backup and restore operations synchronization """

    @classmethod
    def _pid_file_retrieve(cls, file_name):
        """ Retrieves the PID from the semaphore file

        Args:
            file_name: full path of the semaphore file
        Returns:
            pid: pid retrieved from the semaphore file
        Raises:
        """

        with open(file_name) as f:
            pid = f.read()

        pid = int(pid)

        return pid

    @classmethod
    def _pid_file_create(cls, file_name, pid):
        """ Creates the semaphore file having the PID as content

        Args:
            file_name: full path of the semaphore file
            pid: pid to store into the semaphore file
        Returns:
        Raises:
        """

        file = open(file_name, "w")
        file.write(str(pid))
        file.close()

    @classmethod
    def _check_semaphore_file(cls, file_name):
        """ Evaluates if a specific either backup or restore operation is in execution

        Args:
            file_name: semaphore file, full path
        Returns:
            pid: 0= no operation is in execution or the pid retrieved from the semaphore file
        Raises:
        """

        _logger.debug("{func}".format(func="check_semaphore_file"))

        pid = 0

        if os.path.exists(file_name):
            pid = cls._pid_file_retrieve(file_name)

            # Check if the process is really running
            try:
                os.getpgid(pid)
            except ProcessLookupError:
                # Process is not running, removing the semaphore file
                os.remove(file_name)

                _message = _MESSAGES_LIST["e000002"].format(file_name, pid)
                _logger.warning("{0}".format(_message))

                pid = 0

        return pid

    @classmethod
    def is_running(cls):
        """ Evaluates if another either backup or restore job is already running

        Args:
        Returns:
            pid: 0= no operation is in execution or the pid retrieved from the semaphore file
        Raises:
        """

        _logger.debug("{func}".format(func="is_running"))

        # Checks if a backup process is still running
        full_path_backup = JOB_SEM_FILE_PATH + "/" + JOB_SEM_FILE_BACKUP
        pid = cls._check_semaphore_file(full_path_backup)

        # Checks if a restore process is still running
        if pid == 0:
            full_path_restore = JOB_SEM_FILE_PATH + "/" + JOB_SEM_FILE_RESTORE
            pid = cls._check_semaphore_file(full_path_restore)

        return pid

    @classmethod
    def set_as_running(cls, file_name, pid):
        """ Sets a job as running

        Args:
            file_name: semaphore file either fot backup or restore
            pid: pid of the process to be stored within the semaphore file
        Returns:
        Raises:
        """

        _logger.debug("{func}".format(func="set_as_running"))

        full_path = JOB_SEM_FILE_PATH + "/" + file_name

        if os.path.exists(full_path):

            os.remove(full_path)

            _message = _MESSAGES_LIST["e000001"].format(full_path)
            _logger.warning("{0}".format(_message))

        cls._pid_file_create(full_path, pid)

    @classmethod
    def set_as_completed(cls, file_name):
        """ Sets a job as completed

        Args:
            file_name: semaphore file either for backup or restore operations
        Returns:
        Raises:
        """

        _logger.debug("{func}".format(func="set_as_completed"))

        full_path = JOB_SEM_FILE_PATH + "/" + file_name

        if os.path.exists(full_path):
            os.remove(full_path)


if __name__ == "__main__":

    message = _MESSAGES_LIST["e000003"]
    print (message)

    if False:
        # Used to assign the proper objects type without actually executing them
        _storage = StorageClient("127.0.0.1", "0")
        _logger = logger.setup(_MODULE_NAME)
