#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

"""Core server starter"""

import sys
from fledge.services.core.server import Server

__author__ = "Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


is_safe_mode = True if sys.argv[1] == 'safe-mode' else False
Server().start(is_safe_mode)
