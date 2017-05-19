import os

RUN_ENV = "DEV"  # DEV | PROD | TEST

DB_CONFIG_STORAGE = "INSTANCE"  # ENV_VARIABLES | INSTANCE
# TODO: may (do?) want to deploy  with a ask to pick config from system env var only?


"""
Connection string to primary database, Set via FOGLAMP_DB environment variable.
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


class DbConfig:

    conn_str = None  # See http://docs.sqlalchemy.org/en/latest/core/engines.html

    @classmethod
    def get_config(cls):
        return cls.conn_str

    @classmethod
    def initialize_config(cls):
        if DB_CONFIG_STORAGE == "ENV_VARIABLES":
            db = os.environ.get('FOGLAMP_DB')
            host = os.environ.get('FOGLAMP_DB_HOST')
            port = os.environ.get('FOGLAMP_DB_PORT')
            user = os.environ.get('FOGLAMP_DB_USER')
            passwd = os.environ.get('FOGLAMP_DB_PASSWORD')

            if any(k is None for k in [db, host, port, user, passwd]) \
                    or any(k is "" for k in [db, host, port, user, passwd]):
                # TODO: log the FATAL error
                assert False, "Environment variables are not set in correct way, for database configuration."
            else:
                cls.conn_str = 'postgresql://{}:{}@{}:{}/{}'.format(user, passwd, host, port, db)

        else:
            # load from instance yaml as per ENV
            import yaml
            config_file_path = os.path.join(os.path.dirname(__file__), 'db.yaml')
            with open(config_file_path, 'r') as dbconfig_file:
                cfg = yaml.load(dbconfig_file)

            config_params = cfg['FOGLAMP_DB'][RUN_ENV]
            # print(config_params)

            cls.conn_str = "postgresql://{}:{}@{}:{}/{}".format(
                config_params['user'], config_params['passwd'], config_params['host'], config_params['port'],
                config_params['db']
            )
