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

        assert plugin_common.evaluate_type(-999) == "integer"
        assert plugin_common.evaluate_type(-1) == "integer"
        assert plugin_common.evaluate_type(0) == "integer"
        assert plugin_common.evaluate_type(-999) == "integer"

        assert plugin_common.evaluate_type(-999.0) == "number"
        assert plugin_common.evaluate_type(-1.2) == "number"
        assert plugin_common.evaluate_type(0.) == "number"
        assert plugin_common.evaluate_type(1.2) == "number"
        assert plugin_common.evaluate_type(999.0) == "number"

        # Cases - Number as string
        assert plugin_common.evaluate_type("-1.2") == "number"
        assert plugin_common.evaluate_type("-1.0") == "number"
        assert plugin_common.evaluate_type(".0") == "number"
        assert plugin_common.evaluate_type("1.0") == "number"
        assert plugin_common.evaluate_type("1.2") == "number"

        # Cases - Integer as string
        assert plugin_common.evaluate_type("-1") == "integer"
        assert plugin_common.evaluate_type("0") == "integer"
        assert plugin_common.evaluate_type("1") == "integer"

        # Cases - real cases generated using fogbench
        assert plugin_common.evaluate_type(90774.998) == "number"
        assert plugin_common.evaluate_type(41) == "integer"
        assert plugin_common.evaluate_type(-2) == "integer"
        assert plugin_common.evaluate_type(-159) == "integer"
        assert plugin_common.evaluate_type("up") == "string"
        assert plugin_common.evaluate_type("tock") == "string"
