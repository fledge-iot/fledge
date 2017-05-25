import pytest
from foglamp.configurator import Configurator


def test_conn_str_is_none():
    assert Configurator().db_conn_str is None


def test_conn_str_is_initialized():
    Configurator().initialize_dbconfig()
    assert Configurator().db_conn_str is not None
    assert "postgresql://postgres:postgres@localhost:5432/foglamp" == Configurator().db_conn_str

@pytest.mark.skip(reason="mock the env variables")
def test_conn_str_is_initialized_with_env_var():
    Configurator().initialize_dbconfig()
    assert Configurator().db_conn_str is not None
    assert "postgresql://postgres:postgres-password-env-variable@localhost:5432/foglamp" == Configurator().db_conn_str

# TODO: write more tests
# FOGLAMP_DEPLOYMENT
