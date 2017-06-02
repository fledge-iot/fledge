import os
import foglamp.config as config

db_connection_string = None
"""Database connection string.
See http://docs.sqlalchemy.org/en/latest/core/engines.html
"""


def read_config():
    """Sets the db_connection_string module attribute using
    static configuration (see foglamp.config).
    |
    The FOGLAMP_DB_PASSWORD environment variable
    overrides the database password specified in config.
    """

    config_params = config.config['database']

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
def start():
    read_config()
