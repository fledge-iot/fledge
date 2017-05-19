from foglamp.env import DbConfig

# TODO rename this module to test_* module
# TODO make these tests real tests with
# RUN_ENV
# DB_CONFIG_STORAGE

def conn_str_is_None():
    assert DbConfig.conn_str is None

def conn_str_is_initialized():
    DbConfig.initialize_config()
    assert DbConfig.conn_str is not None
    print(DbConfig.conn_str)
    assert "postgresql://postgres:postgres@localhost:5432/foglamp" == DbConfig.conn_str


if __name__ == "__main__":
    conn_str_is_None()
    conn_str_is_initialized()
