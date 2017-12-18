# -*- coding: utf-8 -*-
# Copyright (C) 2017

""" Library used for backup and restore operations
"""

import subprocess
import time
import os
import asyncio
import json
from enum import IntEnum
import psycopg2
from psycopg2.extras import RealDictCursor

from foglamp.common import logger
from foglamp.common.storage_client import payload_builder
from foglamp.common.storage_client.storage_client import StorageClient
from foglamp.common.configuration_manager import ConfigurationManager

import foglamp.plugins.storage.postgres.backup_restore.exceptions as exceptions

__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_MODULE_NAME = "foglamp_backup_postgres_library"

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

_CMD_TIMEOUT = " timeout --signal=9  "
""" Every external commands will be launched using timeout to avoid endless executions """

_logger = None
_storage = None
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

    _logger.debug("{func} - Executed command - cmd |{cmd}| - exit_code |{exit_code}| - output |{output}| ".format(
                                    func="exec_wait",
                                    cmd=_cmd,
                                    exit_code=_exit_code,
                                    output=_output))

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


def cr_strip(text):
    """
    Args:
    Returns:
    Raises:
    """

    text = text.replace("\n", "")
    text = text.replace("\r", "")

    return text


class BackupType (IntEnum):
    """ Supported backup types """

    FULL = 1
    INCREMENTAL = 2


class SortOrder (object):
    """ Define the order used to present information """

    ASC = 'ASC'
    DESC = 'DESC'


class BackupStatus (object):
    """ Backup status """

    UNDEFINED = -1
    RUNNING = 1
    COMPLETED = 2
    CANCELLED = 3
    INTERRUPTED = 4
    FAILED = 5
    RESTORED = 6
    ALL = 999

    text = {
        UNDEFINED: "undefined",
        RUNNING: "running",
        COMPLETED: "completed",
        CANCELLED: "cancelled",
        INTERRUPTED: "interrupted",
        FAILED: "failed",
        RESTORED: "restored",
        ALL: "all"
    }


class BackupRestoreLib(object):
    """ Library of functionalities for the backup restore operations that requires information/state to be stored """

    FOGLAMP_CFG_FILE = "/etc/foglamp.json"

    MAX_NUMBER_OF_BACKUPS_TO_RETRIEVE = 9999
    """" Maximum number of backup information to retrieve from the storage layer"""

    STORAGE_TABLE_BACKUPS = "backups"
    """ Table name containing the backups information"""

    JOB_SEM_FILE_PATH = "/tmp"
    """ Updated by the caller to the proper value """

    JOB_SEM_FILE_BACKUP = ".backup.sem"
    JOB_SEM_FILE_RESTORE = ".restore.sem"
    """" Semaphores information for the handling of the backup/restore synchronization """

    # Postgres commands
    PG_COMMAND_DUMP = "pg_dump"
    PG_COMMAND_RESTORE = "pg_restore"
    PG_COMMAND_PSQL = "psql"

    PG_COMMANDS = {PG_COMMAND_DUMP: None,
                   PG_COMMAND_RESTORE: None,
                   PG_COMMAND_PSQL: None
                   }
    """List of Postgres commands to check/validate if they are available and usable
       and the actual Postgres commands to use """

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
    }
    """ Messages used for Information, Warning and Error notice """

    _DIR_MANAGED_FOGLAMP_PG_COMMANDS = "plugins/storage/postgres/plsql/bin"
    """Directory for Postgres commands in a managed configuration"""

    _DB_CONNECTION_STRING = "dbname='{db}'"

    _DEFAULT_FOGLAMP_ROOT = "/usr/local/foglamp"
    """ Default value to use for the FOGLAMP_ROOT if the environment $FOGLAMP_ROOT is not defined """

    _BACKUP_FILE_NAME_PREFIX = "foglamp_backup_"
    """ Prefix used to generate a backup file name """

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
        "restart-max-retries": {
            "description": "Maximum number of retries at the restart of Foglamp to ensure it is started.",
            "type": "integer",
            "default": "10"
        },
        "restart-sleep": {
            "description": "Sleep time between each check of the status at the restart of Foglamp "
                           "to ensure it is started successfully.",
            "type": "integer",
            "default": "5"
        },
    }

    config = {}

    _storage = None
    _logger = None

    def __init__(self, _storage, _logger):

        self._storage = _storage
        self._logger = _logger

        self.config = {}

        # FogLAMP directories
        self.dir_foglamp_root = ""
        self.dir_foglamp_data = ""
        self.dir_foglamp_data_etc = ""
        self.dir_foglamp_backup = ""
        self.dir_backups = ""
        self.dir_semaphores = ""

    def sl_backup_status_create(self, _file_name, _type, _status):
        """ Logs the creation of the backup in the Storage layer

        Args:
            _file_name: file_name used for the backup as a full path
            _type: backup type {BackupType.FULL|BackupType.INCREMENTAL}
            _status: backup status, usually BackupStatus.RUNNING
        Returns:
        Raises:
        """

        _logger.debug("{func} - file name |{file}| ".format(func="sl_backup_status_create", file=_file_name))

        payload = payload_builder.PayloadBuilder() \
            .INSERT(file_name=_file_name,
                    ts="now()",
                    type=_type,
                    status=_status,
                    exit_code=0) \
            .payload()

        self._storage.insert_into_tbl(self.STORAGE_TABLE_BACKUPS, payload)

    def sl_backup_status_update(self, _id, _status, _exit_code):
        """ Updates the status of the backup using the Storage layer

        Args:
            _id: Backup's Id to update
            _status: status of the backup {BackupStatus.SUCCESSFUL|BackupStatus.RESTORED}
            _exit_code: exit status of the backup/restore execution
        Returns:
        Raises:
        """

        _logger.debug("{func} - id |{file}| ".format(func="sl_backup_status_update", file=_id))

        payload = payload_builder.PayloadBuilder() \
            .SET(status=_status,
                 ts="now()",
                 exit_code=_exit_code) \
            .WHERE(['id', '=', _id]) \
            .payload()

        self._storage.update_tbl(self.STORAGE_TABLE_BACKUPS, payload)

    def sl_get_backup_details_from_file_name(self, _file_name):
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

        backups_from_storage = self._storage.query_tbl_with_payload(self.STORAGE_TABLE_BACKUPS, payload)

        if backups_from_storage['count'] == 1:

            backup_information = backups_from_storage['rows'][0]

        elif backups_from_storage['count'] == 0:
            raise exceptions.DoesNotExist

        else:
            raise exceptions.NotUniqueBackup

        return backup_information

    def check_for_execution_restore(self):
        """ Executes all the checks to ensure the prerequisites to execute the backup are met

        Args:
        Returns:
        Raises:
        """

        self._check_commands()

    def check_for_execution_backup(self):
        """ Executes all the checks to ensure the prerequisites to execute the backup are met

        Args:
        Returns:
        Raises:
        """

        self._check_commands()
        self._check_db()

    def _check_db(self):
        """ Checks if the database is working properly reading a sample row from the backups table

        Args:
        Returns:
        Raises:
            exceptions.CannotReadPostgres
        """

        cmd_psql = self.PG_COMMANDS[self.PG_COMMAND_PSQL]

        cmd = '{psql} -d {db} -t -c "SELECT id FROM {schema}.{table} LIMIT 1;"'.format(
                                                                psql=cmd_psql,
                                                                db=self.config['database'],
                                                                schema=self.config['schema'],
                                                                table=self.STORAGE_TABLE_BACKUPS)

        _exit_code, output = exec_wait(
                                        _cmd=cmd,
                                        _output_capture=True,
                                        _timeout=self.config['timeout']
                                        )

        self._logger.debug("{func} - cmd |{cmd}| - exit_code |{exit_code}| output |{output}| ".format(
                            func="_check_db",
                            cmd=cmd,
                            exit_code=_exit_code,
                            output=cr_strip(output)))

        if _exit_code != 0:
            _message = self._MESSAGES_LIST["e000018"].format(cmd, _exit_code, output)
            self._logger.error("{0}".format(_message))

            raise exceptions.CannotReadPostgres(_message)

    def _check_commands(self):
        """ Identify and checks the Postgres commands

        Args:
        Returns:
        Raises:
        """

        for cmd in self.PG_COMMANDS:

            cmd_identified = self._check_command_identification(cmd)
            self._check_command_test(cmd_identified)

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
                                                        root=self.dir_foglamp_root,
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
            _exit_code, output = exec_wait(
                                            _cmd=cmd,
                                            _output_capture=True,
                                            _timeout=0
                                            )

            self._logger.debug("{func} - cmd |{cmd}| - exit_code |{exit_code}| output |{output}| ".format(
                                                                            func="_check_command_identification",
                                                                            cmd=cmd,
                                                                            exit_code=_exit_code,
                                                                            output=output))

            if _exit_code == 0:
                cmd_identified = cr_strip(output)
            else:
                _message = self._MESSAGES_LIST["e000015"].format(cmd)
                self._logger.error("{0}".format(_message))

                raise exceptions.PgCommandUnAvailable(_message)

        self.PG_COMMANDS[cmd_to_identify] = cmd_identified

        return cmd_identified

    def _is_plugin_managed(self, plugin_to_identify):
        """ Identifies the type of plugin, Managed or not, looking at the foglamp.json configuration file

        Args:
            plugin_to_identify: str - plugin to evaluate if it is managed or not
        Returns:
            type: boolean - True if it is a managed plugin
        Raises:
        """

        plugin_type = False

        file_full_path = self.dir_foglamp_data + self.FOGLAMP_CFG_FILE

        with open(file_full_path) as file:
            cfg_file = json.load(file)

        plugins = cfg_file["storage plugins"]

        for plugin in plugins:
            if plugin["plugin"] == plugin_to_identify:
                plugin_type = plugin["managed"]

        return plugin_type

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

            _exit_code, output = exec_wait(
                                            _cmd=cmd,
                                            _output_capture=True,
                                            _timeout=self.config['timeout']
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

    def sl_get_backup_details(self, backup_id: int) -> dict:
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

        backup_from_storage = self._storage.query_tbl_with_payload(self.STORAGE_TABLE_BACKUPS, payload)

        if backup_from_storage['count'] == 0:
            raise exceptions.DoesNotExist

        elif backup_from_storage['count'] == 1:

            backup_information = backup_from_storage['rows'][0]
        else:
            raise exceptions.NotUniqueBackup

        return backup_information

    def storage_retrieve(self, sql_cmd):
        """  Executes a sql command against the Storage layer that retrieves data

        Args:
        Returns:
            raw_data:list - Python list containing the rows retrieved from the Storage layer
        Raises:
        """

        _logger.debug("{func} - sql cmd |{cmd}| ".format(func="storage_retrieve",
                                                         cmd=sql_cmd))

        db_connection_string = self._DB_CONNECTION_STRING.format(db=self.config["database"])

        _pg_conn = psycopg2.connect(db_connection_string, cursor_factory=RealDictCursor)

        _pg_cur = _pg_conn.cursor()

        _pg_cur.execute(sql_cmd)
        raw_data = _pg_cur.fetchall()
        _pg_conn.close()

        return raw_data

    def storage_update(self, sql_cmd):
        """Executes a sql command against the Storage layer that updates data

        Args:
            sql_cmd: sql command to execute
        Returns:
        Raises:
        """

        _logger.debug("{func} - sql cmd |{cmd}| ".format(
                                                            func="storage_update",
                                                            cmd=sql_cmd))

        db_connection_string = self._DB_CONNECTION_STRING.format(db=self.config["database"])

        _pg_conn = psycopg2.connect(db_connection_string)
        _pg_cur = _pg_conn.cursor()

        _pg_cur.execute(sql_cmd)
        _pg_conn.commit()
        _pg_conn.close()

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

            UPDATE foglamp.backups SET  status={status} WHERE id='{id}';

            """.format(status=status,
                       id=backup_id, )

        self.storage_update(sql_cmd)

    def retrieve_configuration(self):
        """  Retrieves the configuration either from the manager or from a local file.
        the local configuration file is used if the configuration manager is not available
        and updated with the values retrieved from the manager when feasible.

        Args:
        Returns:
        Raises:
            exceptions.ConfigRetrievalError
        """

        global JOB_SEM_FILE_PATH

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
        if self.config['backup-dir'] != "none":

            self.dir_backups = self.config['backup-dir']
        else:
            self.dir_backups = self.dir_foglamp_backup

        self._check_create_path(self.dir_backups)

        # Identifies the directory for the semaphores and checks its existence
        # Stores semaphores in the _backups_dir if semaphores-dir is not defined
        if self.config['semaphores-dir'] != "none":

            self.dir_semaphores = self.config['semaphores-dir']
        else:
            self.dir_semaphores = self.dir_backups
            JOB_SEM_FILE_PATH = self.dir_semaphores

        self._check_create_path(self.dir_semaphores)

    def evaluate_paths(self):
        """  Evaluates paths in relation to the environment variables
             FOGLAMP_ROOT, FOGLAMP_DATA and FOGLAMP_BACKUP

        Args:
        Returns:
        Raises:
        """

        # Evaluates FOGLAMP_ROOT
        if "FOGLAMP_ROOT" in os.environ:
            self.dir_foglamp_root = os.getenv("FOGLAMP_ROOT")
        else:
            self.dir_foglamp_root = self._DEFAULT_FOGLAMP_ROOT

        # Evaluates FOGLAMP_DATA
        if "FOGLAMP_DATA" in os.environ:
            self.dir_foglamp_data = os.getenv("FOGLAMP_DATA")
        else:
            self.dir_foglamp_data = self.dir_foglamp_root + "/data"

        # Evaluates FOGLAMP_BACKUP
        if "FOGLAMP_BACKUP" in os.environ:
            self.dir_foglamp_backup = os.getenv("FOGLAMP_BACKUP")
        else:
            self.dir_foglamp_backup = self.dir_foglamp_data + "/backup"

        # Evaluates etc directory
        self.dir_foglamp_data_etc = self.dir_foglamp_data + "/etc"

        self._check_create_path(self.dir_foglamp_backup)
        self._check_create_path(self.dir_foglamp_data_etc)

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

    def _retrieve_configuration_from_manager(self):
        """" Retrieves the configuration from the configuration manager

        Args:
        Returns:
        Raises:
        """

        _event_loop = asyncio.get_event_loop()

        cfg_manager = ConfigurationManager(self._storage)

        _event_loop.run_until_complete(cfg_manager.create_category(
            self._CONFIG_CATEGORY_NAME,
            self._CONFIG_DEFAULT,
            self._CONFIG_CATEGORY_DESCRIPTION))
        self._config_from_manager = _event_loop.run_until_complete(cfg_manager.get_category_all_items
                                                                   (self._CONFIG_CATEGORY_NAME))

        self._decode_configuration_from_manager(self._config_from_manager)

    def _decode_configuration_from_manager(self, _config_from_manager):
        """" Decodes a json configuration as generated by the configuration manager

        Args:
            _config_from_manager: Json configuration to decode
        Returns:
        Raises:
        """

        self.config['host'] = _config_from_manager['host']['value']

        self.config['port'] = int(_config_from_manager['port']['value'])
        self.config['database'] = _config_from_manager['database']['value']
        self.config['schema'] = _config_from_manager['schema']['value']
        self.config['backup-dir'] = _config_from_manager['backup-dir']['value']
        self.config['semaphores-dir'] = _config_from_manager['semaphores-dir']['value']
        self.config['retention'] = int(_config_from_manager['retention']['value'])
        self.config['max_retry'] = int(_config_from_manager['max_retry']['value'])
        self.config['timeout'] = int(_config_from_manager['timeout']['value'])

        self.config['restart-max-retries'] = int(_config_from_manager['restart-max-retries']['value'])
        self.config['restart-sleep'] = int(_config_from_manager['restart-sleep']['value'])

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

        file_full_path = self.dir_foglamp_data_etc + "/" + self._CONFIG_CACHE_FILE

        return file_full_path


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
        full_path_backup = JOB_SEM_FILE_PATH + "/" + BackupRestoreLib.JOB_SEM_FILE_BACKUP
        pid = cls._check_semaphore_file(full_path_backup)

        # Checks if a restore process is still running
        if pid == 0:
            full_path_restore = JOB_SEM_FILE_PATH + "/" + BackupRestoreLib.JOB_SEM_FILE_RESTORE
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
    print(message)

    if False:
        # Used to assign the proper objects type without actually executing them
        _storage = StorageClient("127.0.0.1", "0")
        _logger = logger.setup(_MODULE_NAME)
