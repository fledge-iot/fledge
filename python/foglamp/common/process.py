from abc import ABC, abstractmethod
import argparse

__author__ = "Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

class ArgumentParserError(Exception):
    pass
            

class FoglampProcess(ABC):
    _core_management_host = None
    _core_management_port = None
    _name = None

    def __init__(self):
        try:    
            self._core_management_host = self.get_arg_value("--address")
            self._core_management_port = self.get_arg_value("--port")
            self._name = self.get_arg_value("--name")
        except ArgumentParserError:
            raise
        if self._core_management_host is None:
            raise ValueError("--address is not specified")
        elif self._core_management_port is None:
            raise ValueError("--port is not specified")
        elif self._name:
            raise ValueError("--name is not specified")

    @abstractmethod
    def run(self):
        pass

    def get_arg_value(self, argument_name):
        """Parses command line arguments for a single argument of name argument_name. Returns the value of the argument specified or None if argument was not specified.

        Keyword Arguments:
        argument_name -- name of command line argument to retrieve value for

        Return Values:
        Argument value (as a string)
        None (if argument was not passed)

        Side Effects:
        None

        Known Exceptions:
        ArgumentParserError
        """

        class SilentArgParse(argparse.ArgumentParser):
            def error(self, message):
                raise ArgumentParserError(message)
        
        parser = SilentArgParse()
        parser.add_argument(argument_name)
        try:
            parser_result = parser.parse_known_args()
        except ArgumentParserError:
            raise
        else:
            return list(vars(parser_result[0]).values())[0]

