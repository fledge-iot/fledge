#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2017

""" Restores the entire FogLAMP repository from a previous backup.

It executes a full cold restore,
FogLAMP will be stopped before the start of the restore and restarted at the end.

It could work also without the Configuration Manager
retrieving the parameters for the execution from the local file 'restore_configuration_cache.json'.
The local file is used as a cache of information retrieved from the Configuration Manager.

Usage:
    --backup-id                     Restore a specific backup retrieving the related information from the
                                    Storage Layer.
         --file                     Restore a backup from a specific file, the full path should be provided
                                    like for example : --file=/tmp/foglamp_2017_09_25_15_10_22.dump

    The latest backup will be restored if no options is used.

Execution samples :

restore_postgres --port=45549 --address=127.0.0.1 --name=restore --backup-id=29
restore_postgres --port=45549 --address=127.0.0.1 --name=restore --file=/tmp/foglamp_backup_2017_12_04_13_57_37.dump

Exit code :
    0    = OK
    >=1  = Warning/Error

"""

import time
# noinspection PyUnresolvedReferences
import sys
import signal
import os

# from foglamp.common.storage_client import payload_builder
from foglamp.common.process import FoglampProcess
from foglamp.common import logger

import foglamp.plugins.storage.postgres.backup_restore.lib as lib
import foglamp.plugins.storage.postgres.backup_restore.exceptions as exceptions


__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_MODULE_NAME = "foglamp_restore_postgres"

_MESSAGES_LIST = {

    # Information messages
    "i000001": "Execution started.",
    "i000002": "Execution completed.",

    # Warning / Error messages
    "e000001": "cannot start the logger - error details |{0}|",
    "e000002": "an error occurred during the restore operation - error details |{0}|",
    "e000003": "invalid command line arguments - error details |{0}|",
    "e000004": "cannot complete the initialization - error details |{0}|",
}
""" Messages used for Information, Warning and Error notice """

# Initializes the logger
try:
    _LOG_LEVEL_DEBUG = 10
    _LOG_LEVEL_INFO = 20

    # FIXME: for debug purpose
    # _logger = logger.setup(_MODULE_NAME, level=20)
    _logger = logger.setup(_MODULE_NAME,
                           destination=logger.CONSOLE,
                           level=_LOG_LEVEL_DEBUG)

except Exception as ex:
    message = _MESSAGES_LIST["e000001"].format(str(ex))
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")

    print("[FOGLAMP] {0} - ERROR - {1}".format(current_time, message), file=sys.stderr)
    sys.exit(1)


def _signal_handler(_signo,  _stack_frame):
    """ Handles signals to avoid restore termination doing FogLAMP stop

    Args:
    Returns:
    Raises:
    """

    short_stack_frame = str(_stack_frame)[:100]
    _logger.debug("{func} - signal |{signo}| - info |{ssf}| ".format(
                                                                    func="_signal_handler",
                                                                    signo=_signo,
                                                                    ssf=short_stack_frame))


class Restore(object):
    """ Provides external functionality/integration to Restore a Backup
    """

    _logger = None

    def __init__(self, _storage):
        self._storage = _storage

        if not Restore._logger:
            Restore._logger = _logger

    def restore_backup(self, backup_id: int):
        """ Starts an asynchronous restore process to restore the state of FogLAMP.

        Args:
            backup_id: int - the id of the backup to restore from

        Returns:
        Raises:
        """
        # FIXME:


class RestoreProcess(FoglampProcess):
    """ Restore the entire FogLAMP repository.
    """

    _logger = None

    _backup_id = None
    """ Used to store the optional command line parameter value """

    _file_name = None
    """ Used to store the optional command line parameter value """

    class FogLampStatus(object):
        """ FogLamp possible status """

        NOT_DEFINED = 0
        STOPPED = 1
        RUNNING = 2

    _FOGLAMP_CMD = "python3 -m foglamp {0}"
    """ Command for managing FogLAMP, stop/start/status """

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
        "e000006": "cannot start FogLAMP after the restore - error details |{0}|",
        "e000007": "cannot restore the backup, restarting FogLAMP - error details |{0}|",
        "e000008": "cannot identify FogLAMP status, the maximum number of retries has been reached "
                   "- error details |{0}|",
        "e000009": "cannot restore the backup, either a backup or a restore is already running - pid |{0}|",
        "e000010": "cannot retrieve the FogLamp status - error details |{0}|",
    }
    """ Messages used for Information, Warning and Error notice """

    def __init__(self):

        super().__init__()

        if not self._logger:
            self._logger = _logger

        try:
            self._backup_id = super().get_arg_value("--backup-id")
            self._file_name = super().get_arg_value("--file")

        except Exception as _ex:

            _message = _MESSAGES_LIST["e000003"].format(_ex)
            _logger.exception(_message)

            raise exceptions.ArgumentParserError(_message)

        self._restore = Restore(self._storage)
        self._restore_lib = lib.BackupRestoreLib(self._storage, self._logger)

        self._config_from_manager = None
        self._config = None
        self._job = lib.Job()

        # Creates the objects references used by the library
        lib._logger = self._logger
        lib._storage = self._storage

    def _identifies_backup_to_restore(self):
        """  # FIXME:

        Args:
        Returns:
        Raises:
        """

        # if not file_name:
        #     file_name = self._identify_last_backup()
        # else:
        #     if not os.path.exists(file_name):
        #         _message = self._MESSAGES_LIST["e000004"].format(file_name)
        #
        #         raise FileNotFoundError(_message)

    def _foglamp_stop(self):
        """ Stops FogLAMP before for the execution of the backup, doing a cold backup

        Args:
        Returns:
        Raises:
            FogLAMPStopError
        Todo:
        """

        self._logger.debug("{func}".format(func="_foglamp_stop"))

        # FIXME: Temporary workaround as the stop option is not currently available
        # cmd = self._FOGLAMP_CMD.format("stop")
        cmd = "pkill python3; pkill storage"

        # Stops FogLamp
        status, output = lib.exec_wait_retry(cmd, True,
                                             max_retry=self._restore_lib.config['max_retry'],
                                             timeout=self._restore_lib.config['timeout'])

        self._logger.debug("{func} - status |{status}| - cmd |{cmd}| - output |{output}|   ".format(
                    func="_foglamp_stop",
                    status=status,
                    cmd=cmd,
                    output=output))

        if status == 0:
            if self._foglamp_status() != self.FogLampStatus.STOPPED:
                raise exceptions.FogLAMPStopError(output)
        else:
            raise exceptions.FogLAMPStopError(output)

    def _foglamp_status(self):
        """ Checks FogLAMP status

        to unsure the status is stable and reliable,
        It executes the FogLamp 'status' command until either
        it returns the same value for 3 times in a row or it reaches the maximum number of retries allowed.

        # FIXME: Temporary implementation as the 'foglamp' command doesn't currently implement the status option

        Args:
        Returns:
            status: FogLampStatus - {STATUS_NOT_DEFINED|STATUS_STOPPED|STATUS_RUNNING}
        Raises:
        """

        status = self.FogLampStatus.NOT_DEFINED

        num_exec = 0
        max_exec = 10
        same_status = 0
        same_status_ok = 3
        sleep_time = 1

        while (same_status < same_status_ok) and (num_exec <= max_exec):

            try:
                # FIXME: Temporary workaround as the status option is not currently available
                # cmd = self._FOGLAMP_CMD.format("status")
                cmd = "pgrep -lf 'python3 -m foglamp.services.core' | grep -v timeout | grep -v grep | grep -v sh"

                cmd_status, output = lib.exec_wait(cmd, True, _timeout=self._restore_lib.config['timeout'])

                self._logger.debug("{func} - output |{output}| \r - status |{status}|  ".format(
                                                                                            func="_foglamp_status",
                                                                                            output=output,
                                                                                            status=cmd_status))

                num_exec += 1

                if cmd_status == 0:
                    new_status = self.FogLampStatus.RUNNING

                elif cmd_status == 1:
                    new_status = self.FogLampStatus.STOPPED

                else:
                    new_status = self.FogLampStatus.NOT_DEFINED

            except Exception as _ex:
                _message = self._MESSAGES_LIST["e000010"].format(_ex)
                _logger.exception(_message)

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

            status = self.FogLampStatus.NOT_DEFINED

        return status

    def execute_restore(self):
        """Executes the restore operation

        Args:
        Returns:
        Raises:
        """

        # FIXME:
        # self._identifies_backup_to_restore()

        if self._foglamp_status() == self.FogLampStatus.RUNNING:
            self._foglamp_stop()




    def init(self):
        """"Setups the correct state for the execution of the restore

        Args:
        Returns:
        Raises:
        """

        self._logger.debug("{func}".format(func="init"))

        self._restore_lib.evaluate_paths()

        self._restore_lib.retrieve_configuration()

        # Checks for backup/restore synchronization
        # FIXME:
        # pid = self._job.is_running()
        # if pid == 0:
        #
        #     # no job is running
        #     pid = os.getpid()
        #     self._job.set_as_running(lib.JOB_SEM_FILE_RESTORE, pid)
        # else:
        #     _message = self._MESSAGES_LIST["e000009"].format(pid)
        #     self._logger.warning("{0}".format(_message))
        #
        #     raise exceptions.BackupOrRestoreAlreadyRunning

    def shutdown(self):
        """"Sets the correct state to terminate the execution

        Args:
        Returns:
        Raises:
        """

        self._logger.debug("{func}".format(func="shutdown"))

        self._job.set_as_completed(lib.JOB_SEM_FILE_RESTORE)

    def run(self):
        """Restores a backup

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

    # Starts
    _logger.info(_MESSAGES_LIST["i000001"])

    # Initializes FoglampProcess and RestoreProcess classes - handling also the command line parameters
    try:
        restore_process = RestoreProcess()

    except Exception as ex:
        message = _MESSAGES_LIST["e000004"].format(ex)
        _logger.exception(message)

        _logger.info(_MESSAGES_LIST["i000002"])
        sys.exit(1)

    # Executes the Restore
    try:
        # Setup signals handlers, to avoid the termination of the restore
        # a) SIGINT: Keyboard interrupt
        # b) SIGTERM: kill or system shutdown
        # c) SIGHUP: Controlling shell exiting
        # FIXME:
        # noinspection PyUnresolvedReferences
        signal.signal(signal.SIGINT, _signal_handler)
        # noinspection PyUnresolvedReferences
        signal.signal(signal.SIGTERM, _signal_handler)
        # noinspection PyUnresolvedReferences
        signal.signal(signal.SIGHUP, _signal_handler)
        # FIXME:
        # signal.signal(signal.SIGALRM, _signal_handler)

        # noinspection PyProtectedMember
        _logger.debug("{module} - name |{name}| - address |{addr}| - port |{port}| "
                      "- file |{file}| - backup_id |{backup_id}| ".format(
                                                                        module=_MODULE_NAME,
                                                                        name=restore_process._name,
                                                                        addr=restore_process._core_management_host,
                                                                        port=restore_process._core_management_port,
                                                                        file=restore_process._file_name,
                                                                        backup_id=restore_process._backup_id))

        restore_process.run()

        _logger.info(_MESSAGES_LIST["i000002"])
        sys.exit(0)

    except Exception as ex:
        message = _MESSAGES_LIST["e000002"].format(ex)
        _logger.exception(message)

        _logger.info(_MESSAGES_LIST["i000002"])
        sys.exit(1)
