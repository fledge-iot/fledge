# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

"""Common Utilities"""

import datetime

__author__ = "Amarendra Kumar Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

DEPRECATED_BIT_POSITION = 7
DEPRECATED_BIT_MASK_VALUE = 1 << DEPRECATED_BIT_POSITION


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
    :example '2018-05-08 14:06:40.517313+05:30'
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
