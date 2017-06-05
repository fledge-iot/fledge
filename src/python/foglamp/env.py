import os
import yaml
import pkg_resources
import logging

# TODO: write tests

logger = logging.getLogger(__name__)

config = None
""" Contents of the yaml configuration file, as a dict object """

db_connection_string = None
""" Database connection string. http://docs.sqlalchemy.org/en/latest/core/engines.html"""
# should be this?
# http://docs.sqlalchemy.org/en/latest/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.psycopg2


# this could have been a BaseConfig class
def load_config():
    """Reads foglamp-env.yaml from the foglamp root directory
    or a YAML file specified via FOGLAMP_ENV_PATH. Sets
    the 'dict' module variable.
    """
    global config
    path = os.environ.get('FOGLAMP_ENV_PATH')
    if path is None:
        resource_str = pkg_resources.resource_string('foglamp', 'foglamp-env.yaml')
        config = yaml.load(resource_str)

    else:
        with open(path, 'r') as config_file:
            config = yaml.load(config_file)

    global db_connection_string
    db_connection_string = get_db_connection_string()


# this could have been a DbConfig class extending BaseConfig/ Config class
def get_db_connection_string():
    """ Sets the db_connection_string module attribute.

    The FOGLAMP_DB_PASSWORD environment variable overrides the database password specified in YAML file.
    """

    # TODO deployment env ['dev'] should be as per the env set
    config_params = config['database']['dev']

    password = os.environ.get('FOGLAMP_DB_PASSWORD')
    if password is "":
        # TODO log warning
        print("FOGLAMP_DB_PASSWORD env variable is set, but with empty string")
    elif password is None:
        # TODO log notice
        print("FOGLAMP_DB_PASSWORD env variable is not set. Using yaml.")
        password = config_params['password']

    db_conn_str = "{}://{}:{}@{}:{}/{}".format(
        config_params['driver'], config_params['user'], password,
        config_params['host'], config_params['port'], config_params['db']
    )
    return db_conn_str

