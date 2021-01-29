# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test common/storage_client/utils.py """

import pytest
from fledge.common.storage_client.utils import Utils

__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("common", "storage_client")
class TestUtils:

    @pytest.mark.parametrize("test_input", ['{"k": "v"}',
                                            '{"k": 1}',
                                            '{"k": []}',
                                            '{"k": {}}',
                                            '[]',
                                            '[{"k": {"k1": "v1"}}]',
                                            '{}',
                                            "{\"k\": \"v\"}",
                                            "{\"k\": 1}",
                                            ])
    def test_is_json_return_true_with_valid_json(self, test_input):
        ret_val = Utils.is_json(test_input)
        assert ret_val is True

    @pytest.mark.parametrize("test_input", ['{ k": "v"}',
                                            '["k": {}]',
                                            1,
                                            'a',
                                            b'any',
                                            {"k", "v"},
                                            '{k: v}',
                                            "{'k': 'v'}",
                                            "{\'k\": \"v\"}"
                                            ])
    def test_is_json_return_false_with_invalid_json(self, test_input):
        ret_val = Utils.is_json(test_input)
        assert ret_val is False
