# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge.readthedocs.io/
# FLEDGE_END

import logging
from fledge.common import logger


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2020, Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_LOGGER = logger.setup(__name__, level=logging.INFO)


class PackageManagerSingleton(object):
    """ PackageManagerSingleton

    Used to make PackageManager a singleton via shared state
    """
    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state


class PackageManager(PackageManagerSingleton):
    """ Package Manager

    General naming convention:

    _packages_map_list:
        id - uuid string
        action - string
        name - string
        exit_code - integer
        link - string
    """
    _packages_map_list = None

    def __init__(self):
        PackageManagerSingleton.__init__(self)
        if self._packages_map_list is None:
            self._packages_map_list = []
