import os
import yaml
import pkg_resources

# TODO: write tests

data = None
"""Contents of the yaml configuration file, as a dict object"""


def read():
    """Reads foglamp-config.yaml in the foglamp root directory
    or a YAML file specified via FOGLAMP_ENV_PATH. Sets
    the 'dict' module variable.
    """
    path = os.environ.get('FOGLAMP_ENV_PATH')

    global data

    if path is None:
        resource_str = pkg_resources.resource_string('foglamp', 'foglamp-env.yaml')
        data = yaml.load(resource_str)

    else:
        with open(path, 'r') as config_file:
            data = yaml.load(config_file)

