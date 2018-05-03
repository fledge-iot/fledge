# -*- coding: utf-8 -*-
""" Unit tests for the OCS plugin """

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

import pytest
import json
import time
import sys
import requests

from unittest.mock import patch, MagicMock

from foglamp.plugins.north.ocs import ocs
import foglamp.tasks.north.sending_process as module_sp

from foglamp.common.storage_client.storage_client import StorageClient


# noinspection PyPep8Naming
class to_dev_null(object):
    """ Used to ignore messages sent to the stderr """

    def write(self, _data):
        """" """
        pass


# noinspection PyUnresolvedReferences
@pytest.allure.feature("unit")
@pytest.allure.story("plugin", "north", "ocs")
class TestOCS:
    """Unit tests related to the public methods of the OCS plugin """

    def test_plugin_info(self):

        plugin_info = ocs.plugin_info()

        assert plugin_info == {
            'name': "OCS North",
            'version': "1.0.0",
            'type': "north",
            'interface': "1.0",
            'config': ocs._CONFIG_DEFAULT_OMF
        }
