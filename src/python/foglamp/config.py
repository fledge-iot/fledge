import os
import yaml

# TODO: write tests

"""
Environment variables

# FOGLAMP_CONFIG_PATH
"""

def get_config():
    """
    reading the YAML config_file as defined via FOGLAMP_CONFIG_PATH
    FOGLAMP_CONFIG_PATH env variable should point to a valid YAML (copied
    from foglamp-env.example.yaml) file
    """

    module_dir = os.path.dirname(os.path.abspath(__file__))

    config_path = os.environ.get('FOGLAMP_CONFIG_PATH', os.path.join(module_dir, '..', 'foglamp-config.yaml'))

    if os.path.isfile(config_path):
        with open(config_path, 'r') as config_file:
            return yaml.load(config_file)

    return


