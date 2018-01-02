#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" A simple implementation using the jq product to apply a transformation to the JSON document
"""

from jq import jq

from foglamp.common import logger
from foglamp.common.process import FoglampProcess

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSI Soft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class JQFilter(FoglampProcess):

    def __init__(self):
        super().__init__()
        self._logger = logger.setup("JQFilter")

    def _transform(self, reading_block, filter_string):
        return jq(filter_string).transform(reading_block)

    def deregister_interest(self):
        pass

    def register_interest(self):
        pass

    def run(self):
        try:
            print(self._transform([{"value": 0, "key": "BUFFERED", "descr": "Bla"},
                                   {"value": 0, "key": "READINGS", "descr": "Bla2"}], "[0]"))
        except Exception as ex:
            self._logger.error("Failed to transform, exception", str(ex))
