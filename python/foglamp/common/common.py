# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Common definitions"""

import os

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_FOGLAMP_DATA = os.getenv("FOGLAMP_DATA", default=None)
_FOGLAMP_ROOT = os.getenv("FOGLAMP_ROOT", default='/usr/local/foglamp')
