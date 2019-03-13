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
