# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" FogLAMP Arg Parser """

import argparse


def setup(prog_name, required_args, optional_args, argv, version=None):
    """

    :param prog_name:
    :param required_args:
    :param optional_args: for optional arg then check if namespace has it? if no assign your default as needed

    :param argv: received argument vector i.e. sys.argv[1:]
    :param version: optional
    :return:
    """
    parser = argparse.ArgumentParser(prog=prog_name)
    parser.description = 'FogLAMP %(prog)s'
    parser.epilog = 'FogLAMP %(prog)s'
    if version:
        parser.add_argument('-v', '--version', action='version', version='%(prog)s {0!s}'.format(version))

    if required_args:
        [parser.add_argument(a, required=True) for a in required_args]
    if optional_args:
        [parser.add_argument(a) for a in optional_args]

    namespace = parser.parse_args(argv)
    return namespace
