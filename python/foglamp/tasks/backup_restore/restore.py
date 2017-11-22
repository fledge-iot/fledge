#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2017

""" Restores the entire FogLAMP repository from a previous backup.

It executes a full cold restore,
FogLAMP will be stopped before the start of the restore and restarted at the end.

The option -f is available to restore a specific file,
the full path should be provided like for example : -f /tmp/foglamp_2017_09_25_15_10_22.dump

The latest backup will be restored if no -f option will be used.

It could work also without the configuration manager,
retrieving the parameters for the execution from the local file 'configuration.ini'.

"""

import argparse
import time
import sys
import asyncio
import configparser
import os
import signal

from foglamp import logger, configuration_manager

import foglamp.backup_restore.lib as lib

__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_MODULE_NAME = "foglamp_restore"

_MESSAGES_LIST = {

    # Information messages
    "i000001": "Execution started.",
    "i000002": "Execution completed.",

    # Warning / Error messages
    "e000001": "cannot start the logger - error details |{0}|",
    "e000002": "an error occurred during the restore operation - error details |{0}|",
}
""" Messages used for Information, Warning and Error notice """

_logger = ""


class ConfigRetrievalError(RuntimeError):
    """ Unable to retrieve the parameters from the configuration manager """
    pass


class RestoreError(RuntimeError):
    """ An error occurred during the restore operation """
    pass


class NoBackupAvailableError(RuntimeError):
    """ No backup in the proper state is available """
    pass


class InvalidFileNameError(RuntimeError):
    """ Unable to use provided file name """
    pass


class FileNameError(RuntimeError):
    """ Impossible to identify an unique backup to restore """
    pass


class FogLAMPStartError(RuntimeError):
    """ Unable to start FogLAMP """
    pass


class FogLAMPStopError(RuntimeError):
    """ Unable to stop FogLAMP """
    pass


class Restore:
    """ Restores the entire FogLAMP repository from a previous backup. """

    _MODULE_NAME = "foglamp_restore_Restore"

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

    _STATUS_NOT_DEFINED = 0
    _STATUS_STOPPED = 1
    _STATUS_RUNNING = 2

    _FOGLAMP_CMD = "python3 -m foglamp {0}"
    """ Command for managing FogLAMP, stop/start/status """

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

    def _foglamp_stop(self):
        """ Stops FogLAMP before for the execution of the backup, doing a cold backup

        Args:
        Returns:
        Raises:
            FogLAMPStopError
        Todo:
        """

        self._logger.debug("{func}".format(func=sys._getframe().f_code.co_name))

        cmd = self._FOGLAMP_CMD.format("stop")

        # Restore the backup
        status, output = lib.exec_wait_retry(cmd, True,
                                             max_retry=self._config['max_retry'],
                                             timeout=self._config['timeout'])

        self._logger.debug("{func} - status |{status}| - cmd |{cmd}| - output |{output}|   ".format(
                    func=sys._getframe().f_code.co_name,
                    status=status,
                    cmd=cmd,
                    output=output))

        if status == 0:
            if self._foglamp_status() != self._STATUS_STOPPED:
                raise FogLAMPStopError(output)
        else:
            raise FogLAMPStopError(output)

    def _foglamp_start(self):
        """ Starts FogLAMP after the execution of the restore

        Args:
        Returns:
        Raises:
            FogLAMPStartError
        Todo:
        """

        cmd = self._FOGLAMP_CMD.format("start")

        status, output = lib.exec_wait_retry(cmd, True,
                                             max_retry=self._config['max_retry'],
                                             timeout=self._config['timeout'])

        self._logger.debug("FogLAMP {0} - output |{1}| -  status |{2}|  ".format(
                                                                            sys._getframe().f_code.co_name,
                                                                            output,
                                                                            status))

        if status == 0:
            if self._foglamp_status() != self._STATUS_RUNNING:
                raise FogLAMPStartError

        else:
            raise FogLAMPStartError

    def _foglamp_status(self):
        """ Checks FogLAMP status

        Args:
        Returns:
            status: {STATUS_NOT_DEFINED|STATUS_STOPPED|STATUS_RUNNING}
        Raises:
            FogLAMPStartError
        Todo:
        """

        status = self._STATUS_NOT_DEFINED

        num_exec = 1
        max_exec = 20
        same_status = 1
        same_status_ok = 3
        sleep_time = 1

        while (same_status <= same_status_ok) and (num_exec <= max_exec):

            time.sleep(sleep_time)

            try:
                cmd = self._FOGLAMP_CMD.format("status")

                cmd_status, output = lib.exec_wait(cmd, True, _timeout=self._config['timeout'])

                self._logger.debug("{0} - output |{1}| \r - status |{2}|  ".format(
                                                                            sys._getframe().f_code.co_name,
                                                                            output,
                                                                            cmd_status))

                num_exec += 1

                if cmd_status == 0:
                    new_status = self._STATUS_RUNNING

                elif cmd_status == 2:
                    new_status = self._STATUS_STOPPED

            except Exception as e:
                _message = e
                raise _message

            else:
                if same_status == 1:
                    same_status += 1

                else:
                    if new_status == status:
                        same_status += 1

                status = new_status

        if num_exec >= max_exec:
            _message = self._MESSAGES_LIST["e000008"]

            self._logger.error(_message)
            status = self._STATUS_NOT_DEFINED

        return status

    def _exec_restore(self, backup_file):
        """ Executes the restore of the storage layer from a backup

        Args:
            backup_file: backup file to restore
        Returns:
        Raises:
            RestoreError
        Todo:
        """

        self._logger.debug("{func} - Restore start |{file}|".format(
                                                                    func=sys._getframe().f_code.co_name,
                                                                    file=backup_file))

        database = self._config['database']
        host = self._config['host']
        port = self._config['port']

        # Generates the restore command
        cmd = "pg_restore"
        cmd += " --verbose --clean --no-acl --no-owner "
        cmd += " -h {host} -p {port} -d {db} {file}".format(
            host=host,
            port=port,
            db=database,
            file=backup_file,)

        # Restore the backup
        status, output = lib.exec_wait_retry(cmd, True, timeout=self._config['timeout'])

        # Avoid output too long
        output_short = output.splitlines()[10]

        self._logger.debug("{func} - Restore end - status |{status}| - cmd |{cmd}| - output |{output}|".format(
                                    func=sys._getframe().f_code.co_name,
                                    status=status,
                                    cmd=cmd,
                                    output=output_short))

        if status != 0:
            raise RestoreError

    def _identify_last_backup(self):
        """ Identifies latest executed backup either successfully executed or already restored

        Args:
        Returns:
        Raises:
            NoBackupAvailableError: No backup either successfully executed or already restored available
            FileNameError: it is impossible to identify an unique backup to restore
        Todo:
        """

        self._logger.debug("{0} ".format(sys._getframe().f_code.co_name))

        sql_cmd = """
            SELECT file_name FROM foglamp.backups WHERE (ts,id)=
            (SELECT  max(ts),MAX(id) FROM foglamp.backups WHERE status=0 or status=-2);
        """

        data = lib.storage_retrieve(sql_cmd)

        if len(data) == 0:
            raise NoBackupAvailableError

        elif len(data) == 1:
            _file_name = data[0]['file_name']
        else:
            raise FileNameError

        return _file_name

    def _update_backup_status(self, _file_name, _exit_status):
        """ Updates the status of the backup in the storage layer

        Args:
            _file_name: backup to update
            _exit_status: backup exit status, stored as provided
        Returns:
        Raises:
        Todo:
        """

        self._logger.debug("{0} - file name |{1}| ".format(sys._getframe().f_code.co_name, _file_name))

        sql_cmd = """
    
            UPDATE foglamp.backups SET  status={status} WHERE file_name='{file}';
    
            """.format(status=_exit_status,
                       file=_file_name, )

        lib.storage_update(sql_cmd)

    def _handling_input_parameters(self):
        """ Handles command line parameters

        Args:
        Returns:
        Raises:
            InvalidFileNameError
        Todo:
        """

        parser = argparse.ArgumentParser(prog=_MODULE_NAME)
        parser.description = '%(prog)s -- restore a FogLAMP backup '

        parser.epilog = ' '

        parser.add_argument('-f', '--file_name',
                            required=False,
                            default=0,
                            help='Backup file to restore, a full path should be provided.')

        namespace = parser.parse_args(sys.argv[1:])

        try:
            _file_name = namespace.file_name if namespace.file_name else None

        except Exception:
            _message = self._MESSAGES_LIST["e000001"].format(str(sys.argv))

            self._logger.error(_message)
            raise InvalidFileNameError(_message)

        return _file_name

    def _retrieve_configuration_from_manager(self):
        """" Retrieves the configuration from the configuration manager

        Args:
        Returns:
        Raises:
        Todo:
        """

        self._logger.debug("{func}".format(func=sys._getframe().f_code.co_name))

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
        self._config['timeout'] = int(self._config_from_manager['timeout']['value'])
        self._config['max_retry'] = int(self._config_from_manager['max_retry']['value'])

    def _retrieve_configuration_from_file(self):
        """" Retrieves the configuration from a local file

        Args:
        Returns:
        Raises:
        Todo:
        """

        self._logger.debug("{func}".format(func=sys._getframe().f_code.co_name))

        config_file = configparser.ConfigParser()
        config_file.read(self._CONFIG_FILE)

        self._config['host'] = config_file['DEFAULT']['host']
        self._config['port'] = int(config_file['DEFAULT']['port'])
        self._config['database'] = config_file['DEFAULT']['database']
        self._config['backup_dir'] = config_file['DEFAULT']['backup_dir']
        self._config['timeout'] = int(config_file['DEFAULT']['timeout'])
        self._config['max_retry'] = int(config_file['DEFAULT']['max_retry'])

    def _update_configuration_file(self):
        """ Updates the configuration file with the values retrieved from tha manager.

        Args:
        Returns:
        Raises:
        Todo:
        """

        self._logger.debug("{func}".format(func=sys._getframe().f_code.co_name))

        config_file = configparser.ConfigParser()

        config_file['DEFAULT']['host'] = self._config['host']
        config_file['DEFAULT']['port'] = str(self._config['port'])
        config_file['DEFAULT']['database'] = self._config['database']
        config_file['DEFAULT']['backup_dir'] = self._config['backup_dir']
        config_file['DEFAULT']['timeout'] = str(self._config['timeout'])
        config_file['DEFAULT']['max_retry'] = str(self._config['max_retry'])

        with open(self._CONFIG_FILE, 'w') as file:
            config_file.write(file)

    def _retrieve_configuration(self):
        """  Retrieves the configuration either from the manager or from a local file.
        the local configuration file is used if the configuration manager is not available,
        and updated with the values retrieved from tha manager when feasible.

        Args:
        Returns:
        Raises:
        Todo:
        """

        self._logger.debug("{func}".format(func=sys._getframe().f_code.co_name))

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

    def start(self):
        """ Setups the correct state for the execution of the restore

        Args:
        Returns:
            proceed_execution: True= the restore could be executed
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
            self._job.set_as_running(lib._JOB_SEM_FILE_RESTORE, pid)
            proceed_execution = True
        else:
            _message = self._MESSAGES_LIST["e000009"].format(pid)
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

        self._job.set_as_completed(lib._JOB_SEM_FILE_RESTORE)

    def execute(self):
        """ Main - Executes the restore functionality

        Args:
        Returns:
            _exit_value: 0=Restore successfully executed

        Raises:
            FileNotFoundError
        Todo:
        """

        # Checks if a file name is provided as command line parameter, if not it considers latest backup
        file_name = self._handling_input_parameters()

        if not file_name:
            file_name = self._identify_last_backup()
        else:
            if not os.path.exists(file_name):
                _message = self._MESSAGES_LIST["e000004"].format(file_name)

                raise FileNotFoundError(_message)

        self._foglamp_stop()

        # Cases :
        # exit 0 - restore=ok, start=ok
        # exit 1 - restore=ok, start=error
        # exit 1 - restore=error, regardless of the start
        try:
            self._exec_restore(file_name)
            lib.backup_status_update(file_name, lib._BACKUP_STATUS_RESTORED)
            _exit_value = 0

        except Exception as _ex:
            _message = self._MESSAGES_LIST["e000007"].format(_ex)

            self._logger.exception(_message)
            _exit_value = 1

        finally:
            try:
                self._foglamp_start()

            except Exception as _ex:
                _message = self._MESSAGES_LIST["e000006"].format(_ex)

                self._logger.exception(_message)
                _exit_value = 1

        return _exit_value


def _signal_handler(_signo,  _stack_frame):
    """ Handles signals to avoid restore termination doing FogLAMP stop

    Args:
    Returns:
    Raises:
    Todo:
    """

    short_stack_frame = str(_stack_frame)[:50]
    _logger.debug("{func} - signal |{signo}| - info |{ssf}| ".format(
                                                                    func=sys._getframe().f_code.co_name,
                                                                    signo=_signo,
                                                                    ssf=short_stack_frame))

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
        restore = Restore()

        try:
            # Setup signals handlers, to avoid the termination of the restore
            signal.signal(signal.SIGHUP, _signal_handler)
            signal.signal(signal.SIGTERM, _signal_handler)
            signal.signal(signal.SIGINT, _signal_handler)

            exit_value = 1

            if restore.start():
                exit_value = restore.execute()

                restore.stop()

            _logger.info(_MESSAGES_LIST["i000002"])
            sys.exit(exit_value)

        except Exception as ex:
            message = _MESSAGES_LIST["e000002"].format(ex)
            _logger.exception(message)

            restore.stop()
            _logger.info(_MESSAGES_LIST["i000002"])
            sys.exit(1)
