# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Storage layer python client utility methods
"""

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


# TODO: add utils method here to keep stuff DRY

import json


class Utils(object):

    @staticmethod
    def is_json(payload):
        try:
            json_object = json.loads(payload)
        except ValueError:
            return False
        return True
