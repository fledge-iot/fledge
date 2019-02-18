# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Unit tests for common utils """

import pytest
from foglamp.common import utils as common_utils
from collections import Counter


@pytest.allure.feature("unit")
@pytest.allure.story("common", "utils")
class TestCommonUtils:
    @pytest.mark.parametrize("test_string, expected", [
        ("Gabbar&Gang", False),
        ("with;Sambha", False),
        ("andothers,halkats", False),
        ("@Rampur", False),
        ("triedloot/arson", False),
        ("For$Gold", False),
        ("Andlot{more", False),
        ("Andmore}", False),
        ("Veeru+Jai", False),
        ("Gaonwale,Thakur", False),
        ("=resisted", False),
        ("successfully:", False),
        ("any attack!", True),
    ])
    def test_check_reserved(self, test_string, expected):
        actual = common_utils.check_reserved(test_string)
        assert expected == actual

    @pytest.mark.parametrize("test_input_old, test_input_new, expected", [
        ({'a': 1, 'b': 2, 'c': 3}, {'a': 11, 'b': 22, 'c': 33}, ['a', 'b', 'c']),
        ({'a': 1, 'b': 2, 'c': 3}, {'a': 11, 'b': 22, 'd': 44}, ['a', 'b', 'd']),
        ({'a': 1, 'b': 2, 'c': 3}, {'a': 11, 'b': 22}, ['a', 'b']),
        ({'a': 1, 'b': 2, 'c': 3}, {'d': 11, 'e': 22, 'c': 33}, ['d', 'e', 'c'])
    ])
    def test_get_diff(self, test_input_old, test_input_new, expected):
        actual = common_utils.get_diff(test_input_old, test_input_new)
        assert Counter(expected) == Counter(actual)
