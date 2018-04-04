# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from unittest.mock import MagicMock, patch
import pytest

from foglamp.services.core import connect
from foglamp.common.storage_client.storage_client import StorageClient
from foglamp.common.storage_client.exceptions import StorageServerError
from foglamp.services.core.user_model import User
from foglamp.common.configuration_manager import ConfigurationManager

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("services", "core", "user-model")
class TestUserModel:

    def test_initial_value(self):
        obj = User(1, 'admin', 'foglamp')
        assert obj.uid == 1
        assert obj.username == 'admin'
        assert obj.password == 'foglamp'
        assert obj.is_admin is False

    def test_value_with_is_admin(self):
        obj = User(1, 'admin', 'foglamp', True)
        assert obj.uid == 1
        assert obj.username == 'admin'
        assert obj.password == 'foglamp'
        assert obj.is_admin is True

    def test_no_value(self):
        with pytest.raises(Exception) as excinfo:
            User()
        assert excinfo.type is TypeError
        assert str(
            excinfo.value) == "__init__() missing 3 required positional arguments: 'uid', 'username', and 'password'"

    def test_get_roles(self):
        expected = {'rows': [], 'count': 0}
        storage_client_mock = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl', return_value=expected) as query_tbl_patch:
                actual = User.Objects.get_roles()
                assert actual == expected['rows']
            query_tbl_patch.assert_called_once_with('roles', )

    def test_get_role_id_by_name(self):
        expected = {'rows': [{'id': '1'}], 'count': 1}
        payload = '{"return": ["id"], "where": {"column": "name", "condition": "=", "value": "admin"}}'
        storage_client_mock = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=expected) as query_tbl_patch:
                actual = User.Objects.get_role_id_by_name("admin")
                assert actual == expected['rows']
            query_tbl_patch.assert_called_once_with('roles', payload)

    def test_get_all(self):
        expected = {'rows': [], 'count': 0}
        payload = '{"return": ["id", "uname", "role_id"], "where": {"column": "enabled", "condition": "=", "value": "True"}}'
        storage_client_mock = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=expected) as query_tbl_patch:
                actual = User.Objects.all()
                assert actual == expected['rows']
            query_tbl_patch.assert_called_once_with('users', payload)

    @pytest.mark.parametrize("kwargs, payload", [
        ({'username': None, 'uid': None}, '{"return": ["id", "uname", "role_id"], "where": {"column": "enabled", "condition": "=", "value": "True"}}'),
        ({'username': None, 'uid': 1}, '{"return": ["id", "uname", "role_id"], "where": {"column": "enabled", "condition": "=", "value": "True", "and": {"column": "id", "condition": "=", "value": 1}}}'),
        ({'username': 'aj', 'uid': None}, '{"return": ["id", "uname", "role_id"], "where": {"column": "enabled", "condition": "=", "value": "True", "and": {"column": "uname", "condition": "=", "value": "aj"}}}'),
        ({'username': 'aj', 'uid': 1}, '{"return": ["id", "uname", "role_id"], "where": {"column": "enabled", "condition": "=", "value": "True", "and": {"column": "id", "condition": "=", "value": 1, "and": {"column": "uname", "condition": "=", "value": "aj"}}}}')
    ])
    def test_get_filter(self, kwargs, payload):
        expected = {'rows': [], 'count': 0}
        storage_client_mock = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=expected) as query_tbl_patch:
                actual = User.Objects.filter(**kwargs)
                assert actual == expected['rows']
        query_tbl_patch.assert_called_once_with('users', payload)

    @pytest.mark.parametrize("exp_kwargs, error_msg", [
        ({'username': None, 'uid': None}, ''),
        ({'username': None, 'uid': 1}, 'User with id:<1> does not exist'),
        ({'username': 'aj', 'uid': None}, 'User with name:<aj> does not exist'),
        ({'username': 'aj', 'uid': 1}, 'User with id:<1> and name:<aj> does not exist')
    ])
    def test_get_exception(self, exp_kwargs, error_msg):
        with patch.object(User.Objects, 'filter', return_value=[]) as filter_patch:
            with pytest.raises(Exception) as excinfo:
                User.Objects.get(uid=exp_kwargs['uid'], username=exp_kwargs['username'])
            assert str(excinfo.value) == error_msg
            assert excinfo.type is User.DoesNotExist
            assert issubclass(excinfo.type, Exception)
        args, kwargs = filter_patch.call_args
        assert kwargs == exp_kwargs

    def test_get(self):
        expected = [{'role_id': '1', 'id': '1', 'uname': 'admin'}]
        exp_kwargs = {'uid': 1, 'username': 'admin'}
        with patch.object(User.Objects, 'filter', return_value=expected) as filter_patch:
            actual = User.Objects.get(uid=exp_kwargs['uid'], username=exp_kwargs['username'])
            assert actual == expected[0]
        args, kwargs = filter_patch.call_args
        assert kwargs == exp_kwargs

    @pytest.mark.parametrize("expected, user_pwd", [(True, 'foglamp'), (False, 'invalid')])
    def test_hash_password_check(self, expected, user_pwd):
        password = User.Objects.hash_password("foglamp")
        actual = User.Objects.check_password(password, user_pwd)
        assert actual == expected

    def test_create_user(self):
        hashed_password = "dd7171406eaf4baa8bc805857f719bca"
        expected = {'rows_affected': 1, "response": "inserted"}
        payload = '{"pwd": "dd7171406eaf4baa8bc805857f719bca", "role_id": 1, "uname": "aj"}'
        storage_client_mock = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(User.Objects, 'hash_password', return_value=hashed_password) as hash_pwd_patch:
                with patch.object(storage_client_mock, 'insert_into_tbl', return_value=expected) as insert_tbl_patch:
                    actual = User.Objects.create("aj", "foglamp", 1)
                    assert actual == expected
                assert 1 == insert_tbl_patch.call_count
                assert insert_tbl_patch.called is True

                # FIXME: payload ordering issue
                args, kwargs = insert_tbl_patch.call_args
                assert args[0] == 'users'
                # assert args[1] in payload
                # insert_tbl_patch.assert_called_once_with('users', payload)
            hash_pwd_patch.assert_called_once_with('foglamp',)

    def test_create_user_exception(self):
        hashed_password = "dd7171406eaf4baa8bc805857f719bca"
        expected = {'message': 'Something went wrong', 'retryable': False, 'entryPoint': 'insert'}
        payload = '{"pwd": "dd7171406eaf4baa8bc805857f719bca", "role_id": 1, "uname": "aj"}'
        storage_client_mock = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(User.Objects, 'hash_password', return_value=hashed_password) as hash_pwd_patch:
                with patch.object(storage_client_mock, 'insert_into_tbl', side_effect=StorageServerError(code=400, reason="blah", error=expected)) as insert_tbl_patch:
                    with pytest.raises(ValueError) as excinfo:
                        User.Objects.create("aj", "foglamp", 1)
                    assert str(excinfo.value) == expected['message']
                # FIXME: payload ordering issue
                args, kwargs = insert_tbl_patch.call_args
                assert args[0] == 'users'
                # assert args[1] in payload
                # insert_tbl_patch.assert_called_once_with('users', payload)
            hash_pwd_patch.assert_called_once_with('foglamp', )

    def test_delete_user(self):
        p1 = '{"where": {"column": "user_id", "condition": "=", "value": 2}}'
        p2 = '{"values": {"enabled": "False"}, "where": {"column": "id", "condition": "=", "value": 2, "and": {"column": "enabled", "condition": "=", "value": "True"}}}'
        r1 = {'response': 'deleted', 'rows_affected': 1}
        r2 = {'response': 'updated', 'rows_affected': 1}

        storage_client_mock = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'delete_from_tbl', return_value=r1) as delete_tbl_patch:
                with patch.object(storage_client_mock, 'update_tbl', return_value=r2) as update_tbl_patch:
                    actual = User.Objects.delete(2)
                    assert r2 == actual
                update_tbl_patch.assert_called_once_with('users', p2)
            delete_tbl_patch.assert_called_once_with('user_logins', p1)

    def test_delete_admin_user(self):
        with pytest.raises(ValueError) as excinfo:
            User.Objects.delete(1)
        assert str(excinfo.value) == 'Super admin user can not be deleted'

    def test_delete_user_exception(self):
        expected = {'message': 'Something went wrong', 'retryable': False, 'entryPoint': 'delete'}
        payload = '{"values": {"enabled": "False"}, "where": {"column": "id", "condition": "=", "value": 2, "and": {"column": "enabled", "condition": "=", "value": "True"}}}'
        storage_client_mock = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'update_tbl', side_effect=StorageServerError(code=400, reason="blah",
                                                                                                error=expected)) as update_tbl_patch:
                with pytest.raises(ValueError) as excinfo:
                    User.Objects.delete(2)
                assert str(excinfo.value) == expected['message']
        update_tbl_patch.assert_called_once_with('users', payload)

    @pytest.mark.parametrize("user_data, payload", [
        ({'role_id': 2}, '{"values": {"role_id": 2}, "where": {"column": "id", "condition": "=", "value": 2}}'),
        ({'role_id': '2'}, '{"values": {"role_id": "2"}, "where": {"column": "id", "condition": "=", "value": 2}}')
    ])
    def test_update_user_role(self, user_data, payload):
        expected = {'response': 'updated', 'rows_affected': 1}
        storage_client_mock = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'update_tbl', return_value=expected) as update_tbl_patch:
                with patch.object(User.Objects, 'delete_user_tokens') as delete_token_patch:
                    actual = User.Objects.update(2, user_data)
                    assert actual is True
                delete_token_patch.assert_called_once_with(2)
            args, kwargs = update_tbl_patch.call_args
            assert args[0] == 'users'
            # FIXME: payload ordering issue
            # update_tbl_patch.assert_called_once_with('users', payload)

    @pytest.mark.parametrize("user_data, payload", [
        ({'password': "Test@123"}, '{"values": {"pwd": "HASHED_PASSWORD"}, "where": {"column": "id", "condition": "=", "value": 2}}')
    ])
    def test_update_user_password(self, user_data, payload):
        expected = {'response': 'updated', 'rows_affected': 1}
        storage_client_mock = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(User.Objects, 'hash_password', return_value='HASHED_PWD') as hash_pwd_patch:
                with patch.object(User.Objects, '_get_password_history', return_value=['HASHED_PWD']) as pwd_list_patch:
                    with patch.object(storage_client_mock, 'update_tbl', return_value=expected) as update_tbl_patch:
                        with patch.object(User.Objects, 'delete_user_tokens') as delete_token_patch:
                            with patch.object(User.Objects, '_insert_pwd_history_with_oldest_pwd_deletion_if_count_exceeds') as pwd_history_patch:
                                actual = User.Objects.update(2, user_data)
                                assert actual is True
                            pwd_history_patch.assert_called_once_with(storage_client_mock, 2, 'HASHED_PWD', ['HASHED_PWD'])
                        delete_token_patch.assert_called_once_with(2)
                    args, kwargs = update_tbl_patch.call_args
                    assert args[0] == 'users'
                    # FIXME: payload ordering issue
                    # update_tbl_patch.assert_called_once_with('users', payload)
                pwd_list_patch.assert_called_once_with(storage_client_mock, 2, user_data)
            hash_pwd_patch.assert_called_once_with(user_data['password'])

    def test_update_user_storage_exception(self):
        expected = {'message': 'Something went wrong', 'retryable': False, 'entryPoint': 'update'}
        payload = '{"values": {"role_id": 2}, "where": {"column": "id", "condition": "=", "value": 2, "and": {"column": "enabled", "condition": "=", "value": "True"}}}'
        storage_client_mock = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'update_tbl', side_effect=StorageServerError(code=400, reason="blah", error=expected)) as update_tbl_patch:
                with pytest.raises(ValueError) as excinfo:
                    User.Objects.update(2, {'role_id': 2})
                assert str(excinfo.value) == expected['message']
        update_tbl_patch.assert_called_once_with('users', payload)

    def test_update_user_exception(self):
        payload = '{"values": {"role_id": "blah"}, "where": {"column": "id", "condition": "=", "value": 2, "and": {"column": "enabled", "condition": "=", "value": "True"}}}'
        msg = 'Bad role id'
        storage_client_mock = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'update_tbl', side_effect=ValueError(msg)) as update_tbl_patch:
                with pytest.raises(Exception) as excinfo:
                    User.Objects.update(2, {'role_id': 'blah'})
                assert excinfo.type is ValueError
                assert str(excinfo.value) == msg
            update_tbl_patch.assert_called_once_with('users', payload)

    async def test_login_if_no_user_exists(self):
        async def mock_get_category_item():
            return {"value": "0"}

        payload = '{"return": ["pwd", "id", "role_id", "pwd_last_changed"], "where": {"column": "uname", "condition": "=", "value": "admin", "and": {"column": "enabled", "condition": "=", "value": "True"}}}'
        storage_client_mock = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(ConfigurationManager, "get_category_item", return_value=mock_get_category_item()) as mock_get_cat_patch:
                with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value={'rows': [], 'count': 0}) as query_tbl_patch:
                    with pytest.raises(Exception) as excinfo:
                        await User.Objects.login('admin', 'blah', '0.0.0.0')
                    assert str(excinfo.value) == 'User does not exist'
                    assert excinfo.type is User.DoesNotExist
                    assert issubclass(excinfo.type, Exception)
                query_tbl_patch.assert_called_once_with('users', payload)
            mock_get_cat_patch.assert_called_once_with('rest_api', 'passwordChange')

    async def test_login_if_invalid_password(self):
        async def mock_get_category_item():
            return {"value": "0"}

        pwd_result = {'count': 1, 'rows': [{'role_id': '2', 'pwd': '3759bf3302f5481e8c9cc9472c6088ac', 'id': '2', 'pwd_last_changed': '2018-03-30 12:32:08.216159+05:30'}]}
        payload = '{"return": ["pwd", "id", "role_id", "pwd_last_changed"], "where": {"column": "uname", "condition": "=", "value": "user", "and": {"column": "enabled", "condition": "=", "value": "True"}}}'
        storage_client_mock = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(ConfigurationManager, "get_category_item", return_value=mock_get_category_item()) as mock_get_cat_patch:
                with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=pwd_result) as query_tbl_patch:
                    with patch.object(User.Objects, 'check_password', return_value=False) as check_pwd_patch:
                        with pytest.raises(Exception) as excinfo:
                            await User.Objects.login('user', 'blah', '0.0.0.0')
                        assert str(excinfo.value) == 'Username or Password do not match'
                        assert excinfo.type is User.PasswordDoesNotMatch
                        assert issubclass(excinfo.type, Exception)
                    check_pwd_patch.assert_called_once_with('3759bf3302f5481e8c9cc9472c6088ac', 'blah')
                query_tbl_patch.assert_called_once_with('users', payload)
            mock_get_cat_patch.assert_called_once_with('rest_api', 'passwordChange')

    async def test_login_age_pwd_expiration(self):
        async def mock_get_category_item():
            return {"value": "30"}

        pwd_result = {'count': 1, 'rows': [{'role_id': '2', 'pwd': '3759bf3302f5481e8c9cc9472c6088ac', 'id': '2', 'pwd_last_changed': '2018-01-30 12:32:08.216159+05:30'}]}
        payload = '{"return": ["pwd", "id", "role_id", "pwd_last_changed"], "where": {"column": "uname", "condition": "=", "value": "user", "and": {"column": "enabled", "condition": "=", "value": "True"}}}'
        storage_client_mock = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(ConfigurationManager, "get_category_item", return_value=mock_get_category_item()) as mock_get_cat_patch:
                with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=pwd_result) as query_tbl_patch:
                    with pytest.raises(Exception) as excinfo:
                        await User.Objects.login('user', 'foglamp', '0.0.0.0')
                    assert pwd_result['rows'][0]['id'] == str(excinfo.value)
                    assert excinfo.type is User.PasswordExpired
                    assert issubclass(excinfo.type, Exception)
                query_tbl_patch.assert_called_once_with('users', payload)
            mock_get_cat_patch.assert_called_once_with('rest_api', 'passwordChange')

    @pytest.mark.parametrize("user_data", [
        ({'count': 1, 'rows': [{'role_id': '1', 'pwd': '3759bf3302f5481e8c9cc9472c6088ac', 'id': '1', 'is_admin': True, 'pwd_last_changed': '2018-03-30 12:32:08.216159+05:30'}]}),
        ({'count': 1, 'rows': [{'role_id': '2', 'pwd': '3759bf3302f5481e8c9cc9472c6088ac', 'id': '2', 'is_admin': False, 'pwd_last_changed': '2018-03-29 05:05:08.216159+05:30'}]})
    ])
    async def test_login(self, user_data):
        async def mock_get_category_item():
            return {"value": "0"}

        payload = '{"return": ["pwd", "id", "role_id", "pwd_last_changed"], "where": {"column": "uname", "condition": "=", "value": "user", "and": {"column": "enabled", "condition": "=", "value": "True"}}}'
        storage_client_mock = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(ConfigurationManager, "get_category_item", return_value=mock_get_category_item()) as mock_get_cat_patch:
                with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=user_data) as query_tbl_patch:
                    with patch.object(User.Objects, 'check_password', return_value=True) as check_pwd_patch:
                        with patch.object(storage_client_mock, 'insert_into_tbl', return_value=True) as insert_tbl_patch:
                            uid, jwt_token, is_admin = await User.Objects.login('user', 'foglamp', '0.0.0.0')
                            expected = user_data['rows'][0]
                            assert uid == expected['id']
                            assert is_admin == expected['is_admin']
                            # FIXME: token patch
                            # assert jwt_token

                        # FIXME: payload ordering issue and datetime.now() patch
                        # insert_tbl_patch.assert_called_once_with('user_logins', )
                        args, kwargs = insert_tbl_patch.call_args
                        assert args[0] == 'user_logins'
                    check_pwd_patch.assert_called_once_with('3759bf3302f5481e8c9cc9472c6088ac', 'foglamp')
                query_tbl_patch.assert_called_once_with('users', payload)
            mock_get_cat_patch.assert_called_once_with('rest_api', 'passwordChange')

    async def test_login_exception(self):
        async def mock_get_category_item():
            return {"value": "0"}

        pwd_result = {'count': 1, 'rows': [{'role_id': '1', 'pwd': '3759bf3302f5481e8c9cc9472c6088ac', 'id': '1', 'pwd_last_changed': '2018-03-30 12:32:08.216159+05:30'}]}
        expected = {'message': 'Something went wrong', 'retryable': False, 'entryPoint': 'delete'}
        payload = '{"return": ["pwd", "id", "role_id", "pwd_last_changed"], "where": {"column": "uname", "condition": "=", "value": "user", "and": {"column": "enabled", "condition": "=", "value": "True"}}}'
        storage_client_mock = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(ConfigurationManager, "get_category_item", return_value=mock_get_category_item()) as mock_get_cat_patch:
                with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=pwd_result) as query_tbl_patch:
                    with patch.object(User.Objects, 'check_password', return_value=True) as check_pwd_patch:
                        with patch.object(storage_client_mock, 'insert_into_tbl', side_effect=StorageServerError(code=400, reason="blah", error=expected)):
                            with pytest.raises(ValueError) as excinfo:
                                await User.Objects.login('user', 'foglamp', '0.0.0.0')
                            assert str(excinfo.value) == expected['message']
                    check_pwd_patch.assert_called_once_with('3759bf3302f5481e8c9cc9472c6088ac', 'foglamp')
                query_tbl_patch.assert_called_once_with('users', payload)
            mock_get_cat_patch.assert_called_once_with('rest_api', 'passwordChange')

    def test_delete_user_tokens(self):
        expected = {'response': 'deleted', 'rows_affected': 1}
        payload = '{"where": {"column": "user_id", "condition": "=", "value": 2}}'
        storage_client_mock = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'delete_from_tbl', return_value=expected) as delete_tbl_patch:
                actual = User.Objects.delete_user_tokens(2)
                assert actual == expected
            delete_tbl_patch.assert_called_once_with('user_logins', payload)

    def test_delete_user_tokens_exception(self):
        expected = {'message': 'Something went wrong', 'retryable': False, 'entryPoint': 'delete'}
        payload = '{"where": {"column": "user_id", "condition": "=", "value": 2}}'
        storage_client_mock = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'delete_from_tbl', side_effect=StorageServerError(code=400, reason="blah", error=expected)) as delete_tbl_patch:
                with pytest.raises(ValueError) as excinfo:
                    User.Objects.delete_user_tokens(2)
                assert str(excinfo.value) == expected['message']
        delete_tbl_patch.assert_called_once_with('user_logins', payload)

    def test_refresh_token_expiry(self):
        expected = {'rows_affected': 1, "response": "updated"}
        token = "RDSlaEtgXuxbYHlDgJURbEeBua2ccwvHeB7MVDeIHq4"
        payload = '{"values": {"token_expiration": "2018-03-13 15:33:25.959408"}, "where": {"column": "token", "condition": "=", "value": "RDSlaEtgXuxbYHlDgJURbEeBua2ccwvHeB7MVDeIHq4"}}'
        storage_client_mock = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'update_tbl', return_value=expected) as update_tbl_patch:
                User.Objects.refresh_token_expiry(token)
            # FIXME: datetime.now() patch
            args, kwargs = update_tbl_patch.call_args
            assert args[0] == 'user_logins'
            # assert args[1] in payload
            # update_tbl_patch.assert_called_once_with('user_logins', payload)

    def test_invalid_token(self):
        storage_client_mock = MagicMock(StorageClient)
        payload = '{"return": ["token_expiration"], "where": {"column": "token", "condition": "=", "value": "blah"}}'
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value={'rows': [], 'count': 0}) as query_tbl_patch:
                with pytest.raises(Exception) as excinfo:
                    User.Objects.validate_token('blah')
                assert str(excinfo.value) == 'Token appears to be invalid'
                assert excinfo.type is User.InvalidToken
                assert issubclass(excinfo.type, Exception)
            query_tbl_patch.assert_called_once_with('user_logins', payload)

    def test_validate_token(self):
        valid_token_result = {'rows': [{"token_expiration": "2017-03-14 15:09:19.800648+05:30"}], 'count': 1}
        storage_client_mock = MagicMock(StorageClient)
        payload = '{"return": ["token_expiration"], "where": {"column": "token", "condition": "=", "value": "foglamp"}}'
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=valid_token_result) as query_tbl_patch:
                # FIXME: jwt.decode patch
                uid = User.Objects.validate_token("eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE1MjEwNDAxNTksInVpZCI6IjIifQ.oeWfDuRStunPQciCuRSSGdZaT42wnh4ODavJ62LSEvI")
                assert uid == '2'
            # FIXME: datetime.now() patch
            args, kwargs = query_tbl_patch.call_args
            assert args[0] == 'user_logins'
            # assert args[1] in payload
            # query_tbl_patch.assert_called_once_with('user_logins', payload)

    @pytest.mark.skip(reason="Need to patch jwt token and datetime")
    def test_token_expiration(self):
        pass

    def test_delete_token(self):
        expected = {'response': 'deleted', 'rows_affected': 1}
        payload = '{"where": {"column": "token", "condition": "=", "value": "eyz"}}'
        storage_client_mock = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'delete_from_tbl', return_value=expected) as delete_tbl_patch:
                actual = User.Objects.delete_token("eyz")
                assert actual == expected
            delete_tbl_patch.assert_called_once_with('user_logins', payload)

    def test_delete_token_exception(self):
        expected = {'message': 'Something went wrong', 'retryable': False, 'entryPoint': 'delete'}
        payload = '{"where": {"column": "token", "condition": "=", "value": "eyx"}}'
        storage_client_mock = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'delete_from_tbl', side_effect=StorageServerError(code=400, reason="blah", error=expected)) as delete_tbl_patch:
                with pytest.raises(ValueError) as excinfo:
                    User.Objects.delete_token("eyx")
                assert str(excinfo.value) == expected['message']
        delete_tbl_patch.assert_called_once_with('user_logins', payload)

    def test_delete_all_user_tokens(self):
        storage_client_mock = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'delete_from_tbl') as delete_tbl_patch:
                User.Objects.delete_all_user_tokens()
        delete_tbl_patch.assert_called_once_with('user_logins')

    def test_no_user_exists(self):
        storage_client_mock = MagicMock(StorageClient)
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value={'rows': []}) as query_tbl_patch:
                result = User.Objects.is_user_exists('blah', 'blah')
                assert result is None
            query_tbl_patch.assert_called_once_with('users', '{"return": ["id", "pwd"], "where": {"column": "uname", "condition": "=", "value": "blah", "and": {"column": "enabled", "condition": "=", "value": "True"}}}')

    @pytest.mark.parametrize("ret_val_check_pwd, expected", [(True, 1), (False, None)])
    def test_user_exists(self, ret_val_check_pwd, expected):
        storage_client_mock = MagicMock(StorageClient)
        ret_val = {'rows': [{'id': 1, 'pwd': 'HASHED_PWD'}]}
        with patch.object(connect, 'get_storage', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=ret_val) as query_tbl_patch:
                with patch.object(User.Objects, 'check_password', return_value=ret_val_check_pwd) as check_pwd_patch:
                    actual = User.Objects.is_user_exists('admin', 'admin')
                    assert expected == actual
                check_pwd_patch.assert_called_once_with(ret_val['rows'][0]['pwd'], 'admin')
            query_tbl_patch.assert_called_once_with('users', '{"return": ["id", "pwd"], "where": {"column": "uname", "condition": "=", "value": "admin", "and": {"column": "enabled", "condition": "=", "value": "True"}}}')

    def test__get_password_history(self):
        storage_client_mock = MagicMock(StorageClient)
        user_data = {'password': 'HASHED_PWD'}
        ret_val = {'rows': [{'id': 1, 'user_id': 2, 'pwd': 'HASHED_PWD'}]}
        row = ret_val['rows'][0]
        with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=ret_val) as query_tbl_patch:
            with patch.object(User.Objects, 'check_password', return_value=False) as check_pwd_patch:
                result = User.Objects._get_password_history(storage_client_mock, row['user_id'], user_data)
                assert [user_data['password']] == result
            check_pwd_patch.assert_called_once_with(row['pwd'], user_data['password'])
        query_tbl_patch.assert_called_once_with('user_pwd_history', '{"where": {"column": "user_id", "condition": "=", "value": 2}}')

    def test__get_password_history_exception(self):
        storage_client_mock = MagicMock(StorageClient)
        user_data = {'password': 'HASHED_PWD'}
        ret_val = {'rows': [{'id': 1, 'user_id': 2, 'pwd': 'HASHED_PWD'}]}
        row = ret_val['rows'][0]
        with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=ret_val) as query_tbl_patch:
            with patch.object(User.Objects, 'check_password', return_value=True) as check_pwd_patch:
                with pytest.raises(Exception) as excinfo:
                    User.Objects._get_password_history(storage_client_mock, row['user_id'], user_data)
                assert str(excinfo.value) == ''
                assert excinfo.type is User.PasswordAlreadyUsed
                assert issubclass(excinfo.type, Exception)
            check_pwd_patch.assert_called_once_with(row['pwd'], user_data['password'])
        query_tbl_patch.assert_called_once_with('user_pwd_history', '{"where": {"column": "user_id", "condition": "=", "value": 2}}')

    @pytest.mark.parametrize("hashed_pwd, pwd_history_list, payload", [
        ('HASHED_PWD_1', ['HASHED_PWD_1'], '{"pwd": "HASHED_PWD_1", "user_id": 2}'),
        ('HASHED_PWD_2', ['HASHED_PWD_2', 'HASHED_PWD_1'], '{"pwd": "HASHED_PWD_2", "user_id": 2}')
    ])
    def test__insert_pwd_history(self, hashed_pwd, pwd_history_list, payload):
        storage_client_mock = MagicMock(StorageClient)
        with patch.object(storage_client_mock, 'insert_into_tbl') as insert_tbl_patch:
            User.Objects._insert_pwd_history_with_oldest_pwd_deletion_if_count_exceeds(storage_client_mock, 2, hashed_pwd, pwd_history_list)

        # FIXME: payload ordering issue
        # insert_tbl_patch.assert_called_once_with('user_pwd_history', payload)
        args, kwargs = insert_tbl_patch.call_args
        assert args[0] == 'user_pwd_history'

    @pytest.mark.parametrize("hashed_pwd, pwd_history_list", [
        ('HASHED_PWD_4', ['HASHED_PWD_3', 'HASHED_PWD_2', 'HASHED_PWD_1'])
    ])
    def test__insert_pwd_history_and_delete_oldest_pwd_if_count_exceeds(self, hashed_pwd, pwd_history_list):
        storage_client_mock = MagicMock(StorageClient)
        with patch.object(storage_client_mock, 'delete_from_tbl') as delete_tbl_patch:
            with patch.object(storage_client_mock, 'insert_into_tbl') as insert_tbl_patch:
                User.Objects._insert_pwd_history_with_oldest_pwd_deletion_if_count_exceeds(storage_client_mock, 2, hashed_pwd, pwd_history_list)

            # FIXME: payload ordering issue
            # insert_tbl_patch.assert_called_once_with('user_pwd_history', '{"pwd": "HASHED_PWD_4", "user_id": 2}')
            args, kwargs = insert_tbl_patch.call_args
            assert args[0] == 'user_pwd_history'

        # FIXME: payload ordering issue
        #  delete_tbl_patch.assert_called_once_with('user_pwd_history', '{"where": {"column": "user_id", "condition": "=", "value": 2, "and": {"column": "pwd", "condition": "=", "value": "HASHED_PWD_1"}}}')
        args, kwargs = delete_tbl_patch.call_args
        assert args[0] == 'user_pwd_history'
