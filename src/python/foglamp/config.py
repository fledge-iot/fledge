"""
Reads a yaml configuration file

Environment variables

# FOGLAMP_CONFIG_PATH
"""

import os
import yaml

# TODO: write tests

config = None
"""Contents of the yaml configuration file, as a dict object"""


def read_config():
    """
    Reads foglamp-config.yaml in the foglamp server root directory
    or a YAML file specified via FOGLAMP_CONFIG_PATH.
    """
    config_path = os.environ.get('FOGLAMP_CONFIG_PATH',
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     '..', 'foglamp-config.yaml'))

    global config

    if os.path.isfile(config_path):
        with open(config_path, 'r') as config_file:
            config = yaml.load(config_file)

    return

read_config()

