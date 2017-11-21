#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Starts South Microservice"""

import sys

from foglamp.services.south import exceptions
from foglamp.services.south.server import Server
from foglamp.common.parser import Parser
from foglamp.common.parser import ArgumentParserError
from foglamp.common import logger


__author__ = "Terris Linenbach"
__copyright_ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_MODULE_NAME = "services_south"

_MESSAGES_LIST = {

    # Information messages
    "i000000": "",

    # Warning / Error messages
    "e000000": "generic error.",
    "e000001": "cannot proceed the execution, unable to parse command line argument"
               " - command line parameters |{0}|",
    "e000002": "cannot proceed the execution, required argument '--name' is missing",
    "e000003": "cannot proceed the execution, required argument '--port' is missing",
    "e000004": "cannot proceed the execution, required argument '--address' is missing",
    "e000005": "cannot complete the operation - error details |{0}|",

}
""" Messages used for Information, Warning and Error notice """

_logger = logger.setup(_MODULE_NAME)


def _handling_input_parameters():
    """ Handles command line parameters

    Args:
    Returns:
        _microservice_name: Unique name representing the microservice
        _core_mgt_address: IP address of the core's management API
        _core_mgt_port: Port of the core's management API

    Raises:
        InvalidCommandLineParametersError
        InvalidMicroserviceNameError
        InvalidAddressError
        InvalidPortError
    """

    _logger.debug("{func} - argv {v0} ".format(
                func="handling_input_parameters",
                v0=str(sys.argv[1:])))

    try:
        _microservice_name = Parser.get('--name')
        _core_mgt_port = Parser.get('--port')
        _core_mgt_address = Parser.get('--address')

    except ArgumentParserError:
        _message = _MESSAGES_LIST["e000001"].format(str(sys.argv))

        _logger.error(_message)
        raise exceptions.InvalidCommandLineParametersError()

    # Evaluates mandatory parameters
    if _microservice_name is None:
        _message = _MESSAGES_LIST["e000002"]
        _logger.error(_message)

        raise exceptions.InvalidMicroserviceNameError()

    elif _core_mgt_address is None:
        _message = _MESSAGES_LIST["e000004"]
        _logger.error(_message)

        raise exceptions.InvalidAddressError

    elif _core_mgt_port is None:
        _message = _MESSAGES_LIST["e000003"]
        _logger.error(_message)

        raise exceptions.InvalidPortError

    # to avoid any possible problems with the case
    _microservice_name = _microservice_name.upper()

    return _microservice_name, _core_mgt_address, _core_mgt_port


try:
    _logger.debug("South Microservice - start")

    microservice_name, core_mgt_address, core_mgt_port = _handling_input_parameters()

    _logger.debug("South Microservice - microservice name |{name}| - address |{addr}| - port |{port}|".format(
            name=microservice_name,
            addr=core_mgt_address,
            port=core_mgt_port))

    Server.start(microservice_name, core_mgt_address, core_mgt_port)

    _logger.debug("South Microservice - end")
    sys.exit(0)

except Exception as ex:
    message = _MESSAGES_LIST["e000005"].format(str(ex))

    _logger.exception(message)
    _logger.debug("South Microservice - end")
    sys.exit(1)
