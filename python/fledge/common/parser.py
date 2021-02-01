# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import argparse
__author__ = "Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

class ArgumentParserError(Exception):
    pass

class SilentArgParse(argparse.ArgumentParser):
    def error(self, message):
        raise ArgumentParserError(message)

class Parser(object):
    """ Fledge argument parser.

     Used to parse command line arguments of various Fledge processes
    """

    @staticmethod
    def get(argument_name):
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

        parser = SilentArgParse()
        parser.add_argument(argument_name)
        try:
            parser.parse_known_args()
        except ArgumentParserError:
            raise
        else:
            return list(vars(parser.parse_known_args()[0]).values())[0]

