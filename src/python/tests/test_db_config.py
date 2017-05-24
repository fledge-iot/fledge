import pytest
from foglamp.configurator import Configurator


def test_conn_str_is_none():
    assert Configurator().db_conn_str is None


def test_conn_str_is_initialized():
    Configurator().initialize_dbconfig()
    assert Configurator().db_conn_str is not None
    assert "postgresql://postgres:postgres@localhost:5432/foglamp" == Configurator().db_conn_str


# TODO
# FOGLAMP_DEPLOYMENT
# database:
    # config_storage: instance # env_variables | instance
