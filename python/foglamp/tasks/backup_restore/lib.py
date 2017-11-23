#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2017

""" Library used for backup and restore operations
"""

import subprocess
import time
import os

from foglamp.common import logger

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
}
""" Messages used for Information, Warning and Error notice """

_CMD_TIMEOUT = " timeout --signal=9  "

_BACKUP_STATUS_SUCCESSFUL = 0
_BACKUP_STATUS_RUNNING = -1
_BACKUP_STATUS_RESTORED = -2

# FIXME:
_JOB_SEM_FILE_PATH = "/tmp"
JOB_SEM_FILE_BACKUP = "backup.sem"
JOB_SEM_FILE_RESTORE = "restore.sem"

_logger = ""


def exec_wait(_cmd, _output_capture=False, _timeout=0):
    """  Executes an external/shell commands

    Args:
        _cmd: command to execute
        _output_capture: if the output of the command should be captured or not
        _timeout: 0 no timeout or the timeout in seconds for the execution of the command

    Returns:
        _status: exit status of the command
        _output: output of the command
    Raises:
    """

    _output = ""

    if _timeout != 0:
        _cmd = _CMD_TIMEOUT + str(_timeout) + " " + _cmd
        _logger.debug("Executing command using the timeout |{timeout}| ".format(timeout=_timeout))

    _logger.debug("{func} - cmd |{cmd}| ".format(func="exec_wait",
                                                 cmd=_cmd))

    if _output_capture:
        process = subprocess.Popen(_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    else:
        process = subprocess.Popen(_cmd, shell=True)

    _status = process.wait()

    if _output_capture:
        output_tmp = process.stdout.read()

        output_tmp2 = output_tmp.decode("utf-8")
        _output = output_tmp2.replace("\n", "\n\r")

    return _status, _output


def exec_wait_retry(cmd, output_capture=False, status_ok=0, max_retry=3,  write_error=True, sleep_time=1, timeout=0):
    """ Executes an external command retrying x time the operation up to the exit status match a specific value

    Args:
        cmd: command to execute
        output_capture: if the _output of the command should be captured or not
        status_ok: exit status to achieve
        max_retry: maximum number of retries to achieve the desired exit status
        write_error: if a message should be generated for each retry
        sleep_time: seconds to sleep between each retry
        timeout: 0= no timeout, or the timeout in seconds for the execution of the external command

    Returns:
        _status: exit status of the command
        _output: output of the command

    Raises:
    """

    global _logger

    _logger.debug("{func} - cmd |{cmd}| ".format(func="exec_wait_retry",
                                                 cmd=cmd))

    _status = 0
    _output = ""

    # try X times the operation
    retry = 1
    loop_continue = True

    while loop_continue:

        _status, _output = exec_wait(cmd, output_capture, timeout)

        if _status == status_ok:
            loop_continue = False

        elif retry <= max_retry:

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

    return _status, _output


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
                pid = 0

                message = _MESSAGES_LIST["e000002"].format(file_name, pid)
                _logger.warning("{0}".format(message))

        return pid

    @classmethod
    def is_running(cls):
        """ Evaluates if another either backup or restore job is already running

        Args:
        Returns:
            pid: 0= no operation is in execution or the pid retrieved from the semaphore file
        Raises:
        """

        # FIXME: _JOB_SEM_FILE_PATH from config manager

        _logger.debug("{func}".format(func="is_running"))

        # Checks if a backup process is still running
        full_path_backup = _JOB_SEM_FILE_PATH + "/" + JOB_SEM_FILE_BACKUP
        pid = cls._check_semaphore_file(full_path_backup)

        # Checks if a restore process is still running
        if pid == 0:
            full_path_restore = _JOB_SEM_FILE_PATH + "/" + JOB_SEM_FILE_RESTORE
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

        full_path = _JOB_SEM_FILE_PATH + "/" + file_name

        if os.path.exists(full_path):

            os.remove(full_path)

            message = _MESSAGES_LIST["e000001"].format(full_path)
            _logger.warning("{0}".format(message))

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

        full_path = _JOB_SEM_FILE_PATH + "/" + file_name

        if os.path.exists(full_path):
            os.remove(full_path)


if __name__ == "__main__":

    _logger = logger.setup(_MODULE_NAME)
