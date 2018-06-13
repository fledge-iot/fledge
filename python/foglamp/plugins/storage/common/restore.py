#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2017

""" Common functionalities for the Restore, they are also used for the integration with the API.
"""

import uuid

from foglamp.services.core import server
from foglamp.common import logger

__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


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


class Restore(object):
    """ Provides external functionality/integration to Restore a Backup
    """

    _MODULE_NAME = "foglamp_restore_common"

    SCHEDULE_RESTORE_ON_DEMAND = "8d4d3ca0-de80-11e7-80c1-9a214cf093ae"

    _MESSAGES_LIST = {

        # Information messages
        "i000000": "general information",
        "i000001": "On demand restore successfully launched.",

        # Warning / Error messages
        "e000000": "general error",
        "e000001": "cannot launch on demand restore - error details |{0}|",
    }
    """ Messages used for Information, Warning and Error notice """

    _logger = None

    def __init__(self, _storage):
        self._storage = _storage

        if not Restore._logger:
            Restore._logger = logger.setup(
                                            self._MODULE_NAME,
                                            destination=_LOGGER_DESTINATION,
                                            level=_LOGGER_LEVEL)

    async def restore_backup(self, backup_id: int):
        """ Starts an asynchronous restore process to restore the state of FogLAMP.

        Important Note : The current version restores the latest backup

        Args:
            backup_id: int - the id of the backup to restore from

        Returns:
            status: str - {"running"|"failed"}
        Raises:
        """

        self._logger.debug("{func} - backup id |{backup_id}|".format(
                                                                    func="restore_backup",
                                                                    backup_id=backup_id))

        try:
            await server.Server.scheduler.queue_task(uuid.UUID(Restore.SCHEDULE_RESTORE_ON_DEMAND))

            _message = self._MESSAGES_LIST["i000001"]
            Restore._logger.info("{0}".format(_message))
            status = "running"

        except Exception as _ex:
            _message = self._MESSAGES_LIST["e000001"].format(_ex)
            Restore._logger.error("{0}".format(_message))

            status = "failed"

        return status
