# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

"""Common Utilities"""

import datetime

from fledge.services.core.api import utils as api_utils

__author__ = "Amarendra Kumar Sinha, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

DEPRECATED_BIT_POSITION = 7
DEPRECATED_BIT_MASK_VALUE = 1 << DEPRECATED_BIT_POSITION
PERSIST_DATA_BIT_POSITION = 3


def get_diff(old, new):
    diff = list()
    for key in new:
        if key in old:
            if old[key] != new[key]:
                diff.append(key)
        else:
            diff.append(key)
    return diff


def local_timestamp():
    """
    :return: str - current time stamp with microseconds and machine timezone info
    :example: '2018-05-08 14:06:40.51731305:30'
    """
    return str(datetime.datetime.now(datetime.timezone.utc).astimezone())


def bit_at_given_position_set_or_unset(n, k):
    """ Check whether the bit at given position is set or unset

        :return: if it results to '1' then bit is set, else it results to '0' bit is unset
        :example:
              Input : n = 32, k = 5
              Output : Set
              (100000)
              The 5th bit from the right is set.

              Input : n = 32, k = 2
              Output : Unset
    """
    new_num = n >> k
    return new_num & 1


def get_persist_plugins():
    """ Get a list of south, north, filter types plugins that can persist data for a service
    :return: list - plugins
    :example: ["OMF"]
    """
    plugin_list = []
    supported_persist_dirs = ["south", "north", "filter"]
    for plugin_type in supported_persist_dirs:
        libs = api_utils.find_c_plugin_libs(plugin_type)
        for name, _type in libs:
            if _type == 'binary':
                jdoc = api_utils.get_plugin_info(name, dir=plugin_type)
                if jdoc:
                    if 'flag' in jdoc:
                        if bit_at_given_position_set_or_unset(jdoc['flag'], PERSIST_DATA_BIT_POSITION):
                            plugin_list.append(jdoc['name'])
    return plugin_list
