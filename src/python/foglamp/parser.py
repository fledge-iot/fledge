#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import argparse
__author__ = "Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"



class Parser(object):
    @staticmethod
    def get(key):
      parser = argparse.ArgumentParser()
      parser.add_argument(key)
      parser.parse_known_args()
      return list(vars(parser.parse_known_args()[0]).values())[0]

