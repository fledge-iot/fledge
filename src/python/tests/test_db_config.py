import pytest
import foglamp.env as env


# noinspection PyClassHasNoInit
@pytest.allure.feature("TestConnection")
class TestConnection:

    def test_conn_str_is_initialized(self):
        env.load_config()
        assert "postgresql://postgres:postgres@localhost:5432/foglamp" == env.db_connection_string

