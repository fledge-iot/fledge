# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Example of docstring of test purpose"""

# package imports, utilities that will be used for running this module., e.g:
import pytest

# FogLAMP imports
# For integration tests, import all dependencies that are required to run this test, e.g:
# from foglamp.common.storage_client.payload_builder import PayloadBuilder


__author__ = "${FULL_NAME}"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# All fixtures defined in conftest.py are available to be used here.
# Test environment variables can be used from conftest.py too, e.g.:
_address = pytest.test_env.address
_m_port = pytest.test_env.core_mgmt_port


@pytest.allure.feature("integration")
@pytest.allure.story("test_component")
class IntegrationTestTemplateClass:
    """
    Example of docstring of Test Class. This class organises the unit tests of test_module
    """

    @pytest.fixture(scope="", params="", autouse=False, ids=None, name=None)
    def _module_fixture(self):
        """Test fixtures that is specific for this class. This fixture can be used with any test definition"""
        pass

    @pytest.mark.parametrize("test_input, expected", [
        ("input_data1", "expected_data_1"),
        ("input_data1", "expected_data_2")
    ])
    def test_some_integration_component(self, _module_fixture, test_input, expected):
        """Purpose of the test, This test is called twice with different test inputs and expected values.
        """
        # assertions to verify that the actual output of a component is equal to the expected output
        assert test_input == expected
