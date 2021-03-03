# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Unit tests about the common code available in plugins.north.common.common """

import pytest
import fledge.plugins.north.common.common as plugin_common


class TestPluginsNorthCommon(object):
    """ Unit tests about the common code available in plugins.north.common.common """

    @pytest.mark.parametrize("value, expected", [
        # Good Cases
        ("xxx", "xxx"),
        ("1xx", "1xx"),
        ("x1x", "x1x"),
        ("xx1", "xx1"),

        ("26/04/2018 11:14", "26/04/2018 11:14"),

        (-180.2, -180.2),
        (0.0, 0.0),
        (180.0, 180.0),
        (180.2, 180.2),
        ("-180.2", -180.2),
        ("180.2", 180.2),
        ("180.0", 180.0),
        ("180.", 180.0),

        (-10, -10),
        (0, 0),
        (10, 10),
        ("-10", -10),
        ("0", 0),
        ("10", 10),

    ])
    def test_convert_to_type_good(self, value, expected):
        """ """

        assert plugin_common.convert_to_type(value) == expected

    @pytest.mark.parametrize("value, expected", [
        # Bad Cases
        ("111", "111"),

        ("26/04/2018 11:14", "26/04/2018 11:00"),

        ("-180.2", 180.2),

        (-10, 10),
    ])
    def test_convert_to_type_bad(self, value, expected):
        """ """

        assert plugin_common.convert_to_type(value) != expected

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

    @pytest.mark.parametrize("value, expected", [
        (
            # Case 1
            [
                {"asset_code": "temperature0", "reading": 20},
                {"asset_code": "temperature1", "reading": 21},
                {"asset_code": "temperature2", "reading": 22}
            ],
            # Expected
            [
                {"asset_code": "temperature0", "asset_data": 20},
                {"asset_code": "temperature1", "asset_data": 21},
                {"asset_code": "temperature2", "asset_data": 22}
            ]
        ),
        (
            # Case 2
            [
                {"asset_code": "temperature0", "reading": 20},
                {"asset_code": "temperature1", "reading": 21},
                {"asset_code": "temperature0", "reading": 22}  # Duplicated
            ],
            # Expected
            [
                {"asset_code": "temperature0", "asset_data": 20},
                {"asset_code": "temperature1", "asset_data": 21},
            ]

        ),
        (
            # Case 3
            [
                {"asset_code": "temperature1", "reading": 10},
                {"asset_code": "temperature2", "reading": 20},
                {"asset_code": "temperature1", "reading": 11},  # Duplicated
                {"asset_code": "temperature2", "reading": 21},  # Duplicated
                {"asset_code": "temperature3", "reading": 30},

            ],
            # Expected
            [
                {"asset_code": "temperature1", "asset_data": 10},
                {"asset_code": "temperature2", "asset_data": 20},
                {"asset_code": "temperature3", "asset_data": 30},
            ]

        ),

    ])
    def test_identify_unique_asset_codes(self, value, expected):
        """ """

        assert plugin_common.identify_unique_asset_codes(value) == expected
