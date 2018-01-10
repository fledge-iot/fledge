# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Unit tests about the common code available in plugins.north.common.common """

import pytest
import foglamp.plugins.north.common.common as plugin_common


class TestPluginsNorthCommon(object):
    """ Unit tests about the common code available in plugins.north.common.common """

    def test_evaluate_type(self):
        """ tests evaluate_type available in plugins.north.common.common """

        # Cases - standard
        assert plugin_common.evaluate_type("String 1") == "string"
        assert plugin_common.evaluate_type("1 String") == "string"
        assert plugin_common.evaluate_type(1) == "integer"
        assert plugin_common.evaluate_type(1.2) == "number"

        # Cases - Number as string
        assert plugin_common.evaluate_type("1.2") == "number"
        assert plugin_common.evaluate_type("1.0") == "number"

        # Cases - Integer as string
        assert plugin_common.evaluate_type("1") == "integer"
