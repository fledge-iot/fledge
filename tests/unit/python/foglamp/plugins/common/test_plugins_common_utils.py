# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Unit tests for utils """

import pytest
import foglamp.plugins.common.utils as utils
from collections import Counter


@pytest.allure.feature("unit")
@pytest.allure.story("plugins", "common")
class TestUtils:
    @pytest.mark.parametrize("test_input_old, test_input_new, expected", [
        ({'a': 1, 'b': 2, 'c': 3}, {'a': 11, 'b': 22, 'c': 33}, ['a', 'b', 'c']),
        ({'a': 1, 'b': 2, 'c': 3}, {'a': 11, 'b': 22, 'd': 44}, ['a', 'b', 'd']),
        ({'a': 1, 'b': 2, 'c': 3}, {'a': 11, 'b': 22}, ['a', 'b']),
        ({'a': 1, 'b': 2, 'c': 3}, {'d': 11, 'e': 22, 'c': 33}, ['d', 'e', 'c'])
    ])
    def test_get_diff(self, test_input_old, test_input_new, expected):
        actual = utils.get_diff(test_input_old, test_input_new)
        assert Counter(expected) == Counter(actual)
