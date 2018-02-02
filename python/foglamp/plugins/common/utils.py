# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Common Utilities"""

from foglamp.common import logger

__author__ = "Amarendra Kumar Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_logger = logger.setup(__name__, level=20)


def get_diff(old, new):
    diff = list()
    for key in new:
        if key in old:
            if old[key] != new[key]:
                diff.append(key)
        else:
            diff.append(key)
    return diff
