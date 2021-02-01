# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

"""Example of docstring of test purpose"""

# package imports, utilities that will be used for running this module., e.g:
import pytest
from unittest import mock
from unittest.mock import patch

# Fledge imports
# from fledge.common.storage_client.payload_builder import PayloadBuilder


__author__ = "${FULL_NAME}"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("test_module")
class UnitTestTemplateClass:
    """
    Example of docstring of Test Class. This class organises the unit tests of test_module
    """

    @pytest.fixture(scope="", params="", autouse=False, ids=None, name=None)
    def _module_fixture(self):
        """Test fixtures that is specific for this class. This fixture can be used with any test definition"""
        pass

    @pytest.mark.parametrize("input, expected", [
        ("input_data1", "expected_result_1"),
        ("input_data1", "expected_result_2")
    ])
    def test_some_unit(self, _module_fixture, input, expected):
        """Purpose of the test, This test is called twice with different test inputs and expected values.
        """
        # assertions to verify that the actual output after running a code block is equal to the expected output
        # Use test doubles (like mocks and patch) to remove dependencies on the external services/code referred in your function under test
        mock_dependency = mock.MagicMock()
        with patch.object(mock_dependency, 'some_method', return_value='bla'):
            actual = None
            # actual = code_under_test(input)
            assert expected == actual

    def test_other_unit_component(self, _module_fixture):
        """Purpose of the test, This test is called once.
        """
        # assertions to verify that the actual output of a component is equal to the expected output
        assert "expected" == "actual"
