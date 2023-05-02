# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test common/jqfilter.py

"""
from unittest.mock import patch
import pytest
import pyjq
from fledge.common.logger import FLCoreLogger
from fledge.common.jqfilter import JQFilter

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("common", "jqfilter")
class TestJQFilter:
    def test_init(self):
        with patch.object(FLCoreLogger, "get_logger") as log:
            jqfilter_instance = JQFilter()
            assert isinstance(jqfilter_instance, JQFilter)
        log.assert_called_once_with("JQFilter")

    @pytest.mark.parametrize("input_filter_string, input_reading_block, expected_return", [
        (".", '{"a": 1}', '{"a": 1}')
    ])
    def test_transform(self, input_filter_string, input_reading_block, expected_return):
        jqfilter_instance = JQFilter()
        with patch.object(pyjq, "all", return_value=expected_return) as mock_pyjq:
            ret = jqfilter_instance.transform(input_filter_string, input_reading_block)
            assert ret == expected_return
        mock_pyjq.assert_called_once_with(input_reading_block, input_filter_string)

    @pytest.mark.parametrize("input_filter_string, input_reading_block, expected_error, expected_log", [
        (".", '{"a" 1}', TypeError, 'Invalid JSON passed during jq transform.'),
        ("..", '{"a" 1}', ValueError, 'Failed to transform, please check the transformation rule.')
    ])
    def test_transform_exceptions(self, input_filter_string, input_reading_block, expected_error, expected_log):
        jqfilter_instance = JQFilter()
        with patch.object(pyjq, "all", side_effect=expected_error) as mock_pyjq:
            with patch.object(jqfilter_instance._logger, "error") as patch_log:
                with pytest.raises(expected_error):
                    jqfilter_instance.transform(input_filter_string, input_reading_block)
            args = patch_log.call_args
            assert expected_error == args[0][0].__class__
            assert expected_log == args[0][1]
        mock_pyjq.assert_called_once_with(input_reading_block, input_filter_string)
