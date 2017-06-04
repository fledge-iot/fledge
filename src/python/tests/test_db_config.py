import pytest
import foglamp.env as env
import foglamp.model.env as model_env


# noinspection PyClassHasNoInit
@pytest.allure.feature("TestConnection")
class TestConnection:

    def test_conn_str_is_initialized(self):
        env.read()
        model_env.read()
        assert "postgresql://postgres:postgres@localhost:5432/foglamp" == model_env.db_connection_string

