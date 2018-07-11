# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Common Utilities"""

import datetime

__author__ = "Amarendra Kumar Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


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
