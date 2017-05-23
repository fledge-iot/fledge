from foglamp.configurator import Configurator
# TODO rename this module to test_* module
# TODO make these tests real tests with
# RUN_ENV
# DB_CONFIG_STORAGE


def conn_str_is_none():
    assert Configurator().db_conn_str is None
    print("Test conn_str_is_none passed")


def conn_str_is_initialized():
    Configurator().initialize_dbconfig()
    assert Configurator().db_conn_str is not None
    print(Configurator().db_conn_str)
    assert "postgresql://postgres:postgres@localhost:5432/foglamp" == Configurator().db_conn_str
    print("Test conn_str_is_initialized passed")


if __name__ == "__main__":
    conn_str_is_none()
    conn_str_is_initialized()
