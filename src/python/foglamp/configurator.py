import os
import yaml

FOGLAMP_DEPLOYMENT = "dev"  # dev | test | prod

FOGLAMP_DIR = os.path.dirname(os.path.abspath(__file__))

# we may want to avoid this.
# what if env variable is set, but
#  - we (tests) want to use from instance
#  - or we want to ignore env variables explicitly
# then, we must ensure env variable is being *UN*set

FOGLAMP_ENV_CONFIG = os.environ.get('FOGLAMP_ENV_CONFIG', os.path.join(FOGLAMP_DIR, 'foglamp-env.yaml'))

# FOGLAMP_ENV_CONFIG env variable should have a valid YAML (copied from foglamp-env.yaml.example) file


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

        if cls.cfg['database']['config_storage'] == "env_variables":
            # TODO: log info, found ['database']['config_storage'] == "env_variables":
            db = os.environ.get('FOGLAMP_DB')
            host = os.environ.get('FOGLAMP_DB_HOST')
            port = os.environ.get('FOGLAMP_DB_PORT')
            user = os.environ.get('FOGLAMP_DB_USER')
            password = os.environ.get('FOGLAMP_DB_PASSWORD')

            if any(k is None for k in [db, host, port, user, password]) \
                    or any(k is "" for k in [db, host, port, user, password]):
                # TODO: log the FATAL error
                assert False, "Environment variables are not set in correct way, for database configuration."
            else:
                cls.db_conn_str = 'postgresql://{}:{}@{}:{}/{}'.format(user, password, host, port, db)

        elif cls.cfg['database']['config_storage'] == "instance":
            # load from instance yaml
            # TODO: log info, found ['database']['config_storage'] == "instance":

            config_params = cls.cfg['database'][FOGLAMP_DEPLOYMENT]
            # print(config_params)

            cls.db_conn_str = "postgresql://{}:{}@{}:{}/{}".format(
                config_params['user'], config_params['password'], config_params['host'], config_params['port'],
                config_params['db']
            )
        else:
            print("loading strategy?")
            # TODO: log error, nothing found for ['database']['config_storage'] == ? in FOGLAMP_CONFIG_PATH file.


# TODO: add this to docs

"""
Set via environment variable.
(TODO: should provide a bash script?)

# for mac ??
# export to bash profile

# for *nix?!
export FOGLAMP_DB_HOST=localhost
export FOGLAMP_DB_PORT=5432
export FOGLAMP_DB_USER=postgres
export FOGLAMP_DB_PASSWORD=postgres
export FOGLAMP_DB=postgres

# for Windows?!
set FOGLAMP_DB_HOST=localhost
set FOGLAMP_DB_PORT=5432
set FOGLAMP_DB_USER=postgres
set FOGLAMP_DB_PASSWORD=postgres
set FOGLAMP_DB=postgres

"""
