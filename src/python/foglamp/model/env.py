import os
import foglamp.env as env

db_connection_string = None
"""Database connection string.
See http://docs.sqlalchemy.org/en/latest/core/engines.html
"""


def read():
    """Sets the db_connection_string module attribute using
    foglamp.config
    |
    The FOGLAMP_DB_PASSWORD environment variable
    overrides the database password specified in config.
    """

    config_params = env.data['database']['dev']

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

