# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Unit tests for utils """

import pytest
import fledge.plugins.common.utils as utils
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

    @pytest.mark.parametrize("number, bit_pos, expected", [
        (32, 5, 1),
        (32, 4, 0),
        (2, 0, 0),
        (2, 1, 1),
        (96, 5, 1)
    ])
    def test_bit_at_given_position_set_or_unset(self, number, bit_pos, expected):
        actual = utils.bit_at_given_position_set_or_unset(number, bit_pos)
        assert expected == actual
