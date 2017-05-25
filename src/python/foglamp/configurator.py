import os
import yaml


FOGLAMP_DEPLOYMENT = "dev"  # dev | test | prod

FOGLAMP_DIR = os.path.dirname(os.path.abspath(__file__))

# TODO: write tests
FOGLAMP_ENV_CONFIG = os.environ.get('FOGLAMP_ENV_CONFIG', os.path.join(FOGLAMP_DIR, 'foglamp-env.yaml'))
"""FOGLAMP_ENV_CONFIG env variable should point to a valid YAML (copied from foglamp-env.example.yaml) file"""

class Configurator:

    cfg = None
    db_conn_str = None  # See http://docs.sqlalchemy.org/en/latest/core/engines.html

    def __init__(self):
        """Configurator class constructor, reading the YAML config_file as defined via FOGLAMP_CONFIG_PATH """
        with open(FOGLAMP_ENV_CONFIG, 'r') as config_file:
            Configurator.cfg = yaml.load(config_file)

    @classmethod
    def get_db_conn_str(cls):
        """ return database connection string"""
        return cls.db_conn_str

    @classmethod
    def initialize_dbconfig(cls):
        """ initialize database connection"""

        # loading from yaml
        config_params = cls.cfg['database'][FOGLAMP_DEPLOYMENT]
        # print(config_params)
        # log if db password is not found in env variables
        password = os.environ.get('FOGLAMP_DB_PASSWORD')
        if password is "":
            #TODO log warning
            print("FOGLAMP_DB_PASSWORD env variable is set, but with empty string")
        elif password is None:
            #TODO log notice
            print("FOGLAMP_DB_PASSWORD env variable is not set, Hence will try to pick from provided yaml")

        password = os.environ.get('FOGLAMP_DB_PASSWORD', config_params['password'])
        cls.db_conn_str = "postgresql://{}:{}@{}:{}/{}".format(
            config_params['user'], password, config_params['host'], config_params['port'],
            config_params['db']
        )

# TODO: add this to docs

"""
Set DB password and JWT secret environment variable.

# for mac ??
# export to bash profile

# for *nix
see export.sh
run export.sh -s to set and with -u to unset

# for Windows?!
set FOGLAMP_DB_PASSWORD=postgres
set FOGLAMP_JWT_SECRET=a-jwt-secret-with-no-space
unset FOGLAMP_DB_PASSWORD=postgres
unset FOGLAMP_JWT_SECRET=a-jwt-secret-with-no-space
"""
