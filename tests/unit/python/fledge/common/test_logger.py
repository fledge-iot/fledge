# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import pytest
import logging

from fledge.common import logger

""" Test python/fledge/common/logger.py"""

__author__ = "Ori Shadmon"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("common", "logger")
class TestLogger:
    """ Logger Tests

        :assert:
          - Test the type that gets returned
          - Test that ValueError gets returned for invalid destination
          - Test the different logging levels

        :todo:
          - Test handler SysLogHandler or StreamHandler
          - Test Format of log entry
          - Test propagate is set to False
    """
    def test_logger_instance(self):
        """ Test the logger type being returned at setup

        :assert:
           Assert that setup returns instance of type logger.Logger
           Assert instance name
           Assert instance hasHandler
           Assert instance default log level WARNING
        """
        instance = logger.setup(__name__)
        assert isinstance(instance, logging.Logger)
        assert "test_logger" == instance.name
        assert instance.hasHandlers()
        assert logging.WARNING == instance.getEffectiveLevel()

    def test_destination_console(self):
        """ Test the logger type being returned when destination=1

        :assert:
            Assert that the setup returns instance of type logging.Logger
        """
        instance = logger.setup(__name__, destination=1)
        assert isinstance(instance, logging.Logger) is True

    def test_logger_destination_error(self):
        """ Test Error gets returned when destination isn't 0 or 1

        :assert:
            Assert ValueError is returned when destination=2
        """ 
        with pytest.raises(ValueError) as error_exec:        
            logger.setup(__name__, destination=2)
        assert "ValueError: Invalid destination 2" in str(error_exec)
 
    def test_logger_level(self):
        """ Test logger level gets updated

        :assert:
            Assert that unless i==0, output.getEffectiveLevel() == i
        """
        for i in range(0, 60, 10):
            output = logger.setup(__name__, level=i)
            if i == 0:
                # Level NOTSET (0) so inherits level WARNING (30)
                assert logging.WARNING == output.getEffectiveLevel()
            else:  
                assert i == output.getEffectiveLevel()

    def test_compare_setup(self):
        """
        Test that logger.setup() generates the same value as logging for 
          level - 10 to 50 
          propagate: True or False
        :assert:
            Assert logging.getLogger() and logger.setup return the same value(s)
        """
        for name in (__name__, 'aaa'):
            log = logging.getLogger(name)
            for level in range(10, 60, 10): 
                for propagate in (True, False):
                    log.setLevel(level) 
                    log.propagate = propagate
                    assert log is logger.setup(name, propagate=propagate, level=level)
