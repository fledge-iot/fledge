"""
Environment variables

# FOGLAMP_DB_PASSWORD
"""
import os
import yaml
import foglamp.config as config

# TODO: write tests


db_connection_string = None
"""
See http://docs.sqlalchemy.org/en/latest/core/engines.html
"""


def read_config():
    """
    reading the YAML config_file as defined via FOGLAMP_CONFIG_PATH
    FOGLAMP_CONFIG_PATH env variable should point to a valid YAML (copied
    from foglamp-env.example.yaml) file
    """

    cfg = config.config

    if cfg is None:
        return

    config_params = cfg['database']

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

read_config()

