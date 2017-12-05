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
import sys
import signal


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
                           # destination=logger.CONSOLE,
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

    def __init__(self):

        super().__init__()

        if not self._logger:
            self._logger = _logger

        # FIXME:
        try:
            self._backup_id = super().get_arg_value("--backup-id")
            self._file_name = super().get_arg_value("--file")

        except Exception as _ex:

            _message = _MESSAGES_LIST["e000003"].format(_ex)
            _logger.exception(_message)

            raise exceptions.ArgumentParserError(_message)

        # Creates the objects references used by the library
        lib._logger = self._logger
        lib._storage = self._storage

    def execute_restore(self):
        """Executes the restore operation

        Args:
        Returns:
        Raises:
        """

    def init(self):
        """"Setups the correct state for the execution of the restore

        Args:
        Returns:
        Raises:
        """
        pass

    def shutdown(self):
        """"Sets the correct state to terminate the execution

        Args:
        Returns:
        Raises:
        """

        pass

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
        signal.signal(signal.SIGHUP, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)
        signal.signal(signal.SIGALRM, _signal_handler)

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
