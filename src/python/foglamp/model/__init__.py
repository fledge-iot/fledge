import os
import yaml

# TODO: write tests

"""
Environment variables

# FOGLAMP_CONFIG_PATH
# FOGLAMP_DB_PASSWORD
"""

db_connection_string = None
"""
See http://docs.sqlalchemy.org/en/latest/core/engines.html
"""

def init():
    """
    reading the YAML config_file as defined via FOGLAMP_CONFIG_PATH
    FOGLAMP_CONFIG_PATH env variable should point to a valid YAML (copied
    from foglamp-env.example.yaml) file
    """

    module_dir = os.path.dirname(os.path.abspath(__file__))

    config_path = os.environ.get('FOGLAMP_CONFIG_PATH', os.path.join(module_dir, '..', '..', 'foglamp-config.yaml'))

    if os.path.isfile(config_path):
        with open(config_path, 'r') as config_file:
            config = yaml.load(config_file)
            _initialize_dbconfig(config)


def _initialize_dbconfig(config):
    """ Sets db_connection_string """

    config_params = config['database']

    # print(config_params)
    # log if db password is not found in env variables

    password = os.environ.get('FOGLAMP_DB_PASSWORD')
    if password is "":
        #TODO log warning
        print("FOGLAMP_DB_PASSWORD env variable is set, but with empty string")
    elif password is None:
        #TODO log notice
        print("FOGLAMP_DB_PASSWORD env variable is not set. Using yaml.")
        password = config_params['password']

    global db_connection_string
    db_connection_string = "{}://{}:{}@{}:{}/{}".format(
        config_params['driver'],
        config_params['user'],
        password,
        config_params['host'],
        config_params['port'],
        config_params['db']
    )

init()

