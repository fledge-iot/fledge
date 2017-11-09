"""The following tests the logger component""" 
import logging 
import pytest

from foglamp import logger

__author__ = "Ori Shadmon"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("logger testing")
class TestLogger:
    """
    Logger Tests
      - Test the type that gets returned 
      - Test that ValueError gets returned 
      - Test the different logging levels
      - Test handler
    """   
    def test_logger_type(self):
        """
        Test the logger type being returned at setup
        :assert:
           Assert that setup returns value of type logger.Logger
        """
        assert isinstance(logger.setup(__name__), logging.Logger) is True

    def test_destination_consule(self):
        """
        Test the logger type being returned when destination=1
        :assert:
            Assert that the setup returns value of type logging.Logger
        """
        assert isinstance(logger.setup(__name__, destination=1), logging.Logger) is True 

    def test_logger_destination_error(self):
        """
        Test Error gets returned when destination isn't 0 or 1
        :assert: 
            Assert ValueError is returned when destination=2
        """ 
        with pytest.raises(ValueError) as error_exec:        
            logger.setup(__name__, destination=2)
        assert "ValueError: Invalid destination 2" in str(error_exec)
 
    def test_logger_level(self):
        """
        Test logger level  gets updated 
        :assert: 
            Assert that unless i==0, output.getEffectiveLevel() == i
        """
        for i in range(0, 70, 10): 
            output = logger.setup(__name__, level=i)
            if i == 0: 
                assert output.getEffectiveLevel() == 30
            else:  
                assert output.getEffectiveLevel() == i

    def test_logger_handler(self): 
        """
        Test that handler has been added
        :assert: 
            Assert hasHandler returns True
        """
        output = logger.setup(__name__)
        assert output.hasHandlers() is True

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
                    assert log == logger.setup(name, propagate=propagate, level=level)
