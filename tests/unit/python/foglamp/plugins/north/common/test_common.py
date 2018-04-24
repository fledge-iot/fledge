# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Unit tests about the common code available in plugins.north.common.common """

import pytest
import foglamp.plugins.north.common.common as plugin_common


class TestPluginsNorthCommon(object):
    """ Unit tests about the common code available in plugins.north.common.common """

    @pytest.mark.parametrize("value, expected", [
        # Cases - standard
        ("String 1", "string"),
        (-999, "integer"),
        (-1, "integer"),
        (0, "integer"),
        (-999, "integer"),
        (-999.0,  "number"),
        (-1.2,  "number"),
        (0.,  "number"),
        (1.2,  "number"),
        (999.0,  "number"),

        # Cases - Number as string
        ("-1.2",  "number"),
        ("-1.0",  "number"),
        (".0",  "number"),
        ("1.0",  "number"),
        ("1.2",  "number"),

        # Cases - Integer as string
        ("-1",  "integer"),
        ("0",  "integer"),
        ("1",  "integer"),

        # Cases - real cases generated using fogbench
        (90774.998,  "number"),
        (41,  "integer"),
        (-2,  "integer"),
        (-159,  "integer"),
        ("up",  "string"),
        ("tock",  "string")

    ])
    def test_evaluate_type(self, value, expected):
        """ tests evaluate_type available in plugins.north.common.common """

        assert plugin_common.evaluate_type(value) == expected
