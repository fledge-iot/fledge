import os
import yaml
import pkg_resources

# TODO: write tests

config = None
"""Contents of the yaml configuration file, as a dict object"""


def read_config():
    """Reads foglamp-config.yaml in the foglamp root directory
    or a YAML file specified via FOGLAMP_CONFIG_PATH. Sets
    the config module variable.

    :return: The config file's contents parsed as YAML
    :rtype: dict
    """
    path = os.environ.get('FOGLAMP_CONFIG_PATH')

    global config

    if path is None:
        resource_str = pkg_resources.resource_string('foglamp', 'foglamp-config.yaml')
        config = yaml.load(resource_str)

    else:
        with open(path, 'r') as config_file:
            config = yaml.load(config_file)

def start():
    read_config()


