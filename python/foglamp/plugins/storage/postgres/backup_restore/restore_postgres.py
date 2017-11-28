#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2017

""" Restores the entire FogLAMP repository from a previous backup.

# FIXME:
# CURRENTLY NOT IMPLEMENTED !!

It executes a full cold restore,
FogLAMP will be stopped before the start of the restore and restarted at the end.

# FIXME:
The option -f is available to restore a specific file,
the full path should be provided like for example : -f /tmp/foglamp_2017_09_25_15_10_22.dump

The latest backup will be restored if no -f option will be used.

It could work also without the configuration manager,
retrieving the parameters for the execution from the local file 'configuration.ini'.

"""

import time
import sys

from foglamp.common import logger
import logging

# import foglamp.backup_restore.lib as lib

__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_MODULE_NAME = "foglamp_restore_module"

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


if __name__ == "__main__":

    # FIXME:
    # CURRENTLY NOT IMPLEMENTED !!

    try:
        # FIXME: for debug purpose
        # _logger = logger.setup(_MODULE_NAME)
        _logger = logger.setup(_MODULE_NAME,
                               destination=logger.CONSOLE,
                               level=logging.DEBUG)

        _logger.info(_MESSAGES_LIST["i000001"])

    except Exception as ex:
        message = _MESSAGES_LIST["e000001"].format(str(ex))
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")

        print("[FOGLAMP] {0} - ERROR - {1}".format(current_time, message), file=sys.stderr)
        sys.exit(1)

    else:

        try:
            exit_value = 1

            # FIXME:
            _logger.info("RESTORE DBG !!!!!!!!!!!!!!!!!!!!!!!!!!")

            _logger.info(_MESSAGES_LIST["i000002"])
            sys.exit(exit_value)

        except Exception as ex:
            message = _MESSAGES_LIST["e000002"].format(ex)
            _logger.exception(message)

            _logger.info(_MESSAGES_LIST["i000002"])
            sys.exit(1)
