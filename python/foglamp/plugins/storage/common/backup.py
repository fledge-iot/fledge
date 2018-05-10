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
import uuid
import asyncio

from foglamp.services.core import server

from foglamp.common.storage_client import payload_builder
from foglamp.common.process import FoglampProcess
from foglamp.common import logger
from foglamp.common.audit_logger import AuditLogger

import foglamp.plugins.storage.postgres.backup_restore.lib as lib
import foglamp.plugins.storage.postgres.backup_restore.exceptions as exceptions

__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_MODULE_NAME = "foglamp_backup_common_module"

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


class Backup(object):
    """ Provides external functionality/integration for Backup operations

        the constructor expects to receive a reference to a StorageClient object to being able to access
        the Storage Layer
    """

    _MODULE_NAME = "foglamp_backup_postgres_api"

    _SCHEDULE_BACKUP_ON_DEMAND = "fac8dae6-d8d1-11e7-9296-cec278b6b50a"

    _MESSAGES_LIST = {

        # Information messages
        "i000000": "general information",
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

    _logger = None

    def __init__(self, _storage):
        self._storage = _storage

        if not Backup._logger:
            Backup._logger = logger.setup(self._MODULE_NAME,
                                          destination=_LOGGER_DESTINATION,
                                          level=_LOGGER_LEVEL)

        self._backup_lib = lib.BackupRestoreLib(self._storage, self._logger)

    def get_all_backups(
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

        # FIXME:
        Backup._logger.info("BRK - Common get_all_backups ")

        payload = payload_builder.PayloadBuilder().SELECT("id", "status", "ts", "file_name", "type") \
            .ALIAS("return", ("ts", 'ts')).FORMAT("return", ("ts", "YYYY-MM-DD HH24:MI:SS.MS"))
        if status:
            payload.WHERE(['status', '=', status])
            
        backups_from_storage = self._storage.query_tbl_with_payload(self._backup_lib.STORAGE_TABLE_BACKUPS, payload.payload())

        backups_information = backups_from_storage['rows']

        return backups_information

    def get_backup_details(self, backup_id: int) -> dict:
        """ Returns the details of a backup

        Args:
            backup_id: int - the id of the backup to return

        Returns:
            backup_information: all the information available related to the requested backup_id

        Raises:
            exceptions.DoesNotExist
            exceptions.NotUniqueBackup
        """

        backup_information = self._backup_lib.sl_get_backup_details(backup_id)

        return backup_information

    def delete_backup(self, backup_id: int):
        """ Deletes a backup

        Args:
            backup_id: int - the id of the backup to delete

        Returns:
        Raises:
        """

        try:
            backup_information = self._backup_lib.sl_get_backup_details(backup_id)

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

        self._storage.delete_from_tbl(self._backup_lib.STORAGE_TABLE_BACKUPS, payload)

    async def create_backup(self):
        """ Run a backup task using the scheduler on-demand schedule mechanism to run the script,
            the backup will proceed asynchronously.

        Args:
        Returns:
            status: str - {"running"|"failed"}
        Raises:
        """

        self._logger.debug("{func}".format(func="create_backup"))

        try:
            await server.Server.scheduler.queue_task(uuid.UUID(Backup._SCHEDULE_BACKUP_ON_DEMAND))

            _message = self._MESSAGES_LIST["i000003"]
            Backup._logger.info("{0}".format(_message))
            status = "running"

        except Exception as _ex:
            _message = self._MESSAGES_LIST["e000004"].format(_ex)
            Backup._logger.error("{0}".format(_message))

            status = "failed"

        return status
