# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from foglamp.plugins.north.omf import omf

__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class TestOMF:
    """Unit tests for the omf plugin"""

    def test_plugin_info(self):

        assert omf.plugin_info() == {
            'name': "OMF North",
            'version': "1.0.0",
            'type': "north",
            'interface': "1.0",
            'config': omf._CONFIG_DEFAULT_OMF
        }
