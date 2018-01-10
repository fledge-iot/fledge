#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" A simple implementation using the jq product to apply a transformation to the JSON document
"""

import json
import pyjq

from foglamp.common import logger

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSI Soft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class JQFilter:

    def __init__(self):
        super().__init__()
        self._logger = logger.setup("JQFilter")

    def transform(self, applyFilter, reading_block, filter_string):
        if applyFilter.upper() == "TRUE":
            try:
                return json.dumps(pyjq.all(filter_string, reading_block))
            except TypeError as ex:
                self._logger.error("Failed to convert output to JSON, exception", str(ex))
                raise
            except Exception as e:
                self._logger.error("Failed to transform, please check the transformation rule syntax")
                raise
        else:
            return reading_block


# Other Transformations
# No transformation - "."
# First element of the JSON array - ".[0]"
# Get only certain field from JSON (e.g., descr) - ".[]|{descr}"
# Change the name of a JSON key (e.g., descr to Description - ".[]|{Description: .descr}"


# def main():
#
#     jqfilter = JQFilter()
#     test_data = [{"value": 0, "key": "BUFFERED", "descr": "Bla"},
#                  {"value": 0, "key": "READINGS", "descr": "Bla2"}]
#     t_string = ".[]"
#     t_data = jqfilter.transform("True", test_data, t_string)
#     print("Data : {}\nTransformation Rule : {}\nTransformed Data : {}\n".format(test_data, t_string, t_data))
#
#     t_string = ".[0]"
#     t_data = jqfilter.transform("True", test_data, t_string)
#     print("Data : {}\nTransformation Rule : {}\nTransformed Data : {}\n".format(test_data, t_string, t_data))
#
#     t_string = ".[]|{descr}"
#     t_data = jqfilter.transform("True", test_data, t_string)
#     print("Data : {}\nTransformation Rule : {}\nTransformed Data : {}\n".format(test_data, t_string, t_data))
#
#     t_string = ".[]|{Description: .descr}"
#     t_data = jqfilter.transform("True", test_data, t_string)
#     print("Data : {}\nTransformation Rule : {}\nTransformed Data : {}\n".format(test_data, t_string, t_data))
#
#     test_data = {'value': 0, "key": "BUFFERED", "descr": "Bla"}
#     t_string = ".|{Description: .descr}"
#     t_data = jqfilter.transform("True", test_data, t_string)
#     print("Data : {}\nTransformation Rule : {}\nTransformed Data : {}\n".format(test_data, t_string, t_data))
#
#
# main()
