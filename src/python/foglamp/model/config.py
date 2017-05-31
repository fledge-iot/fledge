import os
import yaml
import foglamp.config as config

# TODO: write tests


db_connection_string = None
"""See http://docs.sqlalchemy.org/en/latest/core/engines.html"""


def set_db_connection_string():
    """
    Sets the db_connection_string module variable using
    static configuration (see foglamp.config).
    ---
    Optionally uses FOGLAMP_DB_PASSWORD environment variable.
    If present, it overrides the database
    password specified in config.
    """

    cfg = config.config

    # TODO need to decide whether it's legal to have no config
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

set_db_connection_string()

