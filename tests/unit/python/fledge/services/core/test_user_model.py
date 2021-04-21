# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import json
import asyncio
from unittest.mock import MagicMock, patch
import pytest

from fledge.services.core import connect
from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.common.storage_client.exceptions import StorageServerError
from fledge.services.core.user_model import User
from fledge.common.configuration_manager import ConfigurationManager

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

pytestmark = pytest.mark.asyncio

@asyncio.coroutine
def mock_coro(*args, **kwargs):
    return None if len(args) == 0 else args[0]

@pytest.allure.feature("unit")
@pytest.allure.story("services", "core", "user-model")
class TestUserModel:

    async def test_initial_value(self):
        obj = User(1, 'admin', 'fledge')
        assert obj.uid == 1
        assert obj.username == 'admin'
        assert obj.password == 'fledge'
        assert obj.is_admin is False

    async def test_value_with_is_admin(self):
        obj = User(1, 'admin', 'fledge', True)
        assert obj.uid == 1
        assert obj.username == 'admin'
        assert obj.password == 'fledge'
        assert obj.is_admin is True

    async def test_no_value(self):
        with pytest.raises(Exception) as excinfo:
            User()
        assert excinfo.type is TypeError
        assert str(
            excinfo.value) == "__init__() missing 3 required positional arguments: 'uid', 'username', and 'password'"

    async def test_get_roles(self):
        expected = {'rows': [], 'count': 0}
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl', return_value=mock_coro(expected)) as query_tbl_patch:
                actual = await User.Objects.get_roles()
                assert actual == expected['rows']
            query_tbl_patch.assert_called_once_with('roles', )

    async def test_get_role_id_by_name(self):
        expected = {'rows': [{'id': '1'}], 'count': 1}
        payload = '{"return": ["id"], "where": {"column": "name", "condition": "=", "value": "admin"}}'
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=mock_coro(expected)) as query_tbl_patch:
                actual = await User.Objects.get_role_id_by_name("admin")
                assert actual == expected['rows']
            query_tbl_patch.assert_called_once_with('roles', payload)

    async def test_get_all(self):
        expected = {'rows': [], 'count': 0}
        payload = '{"return": ["id", "uname", "role_id", "access_method", "real_name", "description"], "where": {"column": "enabled", "condition": "=", "value": "t"}}'
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=mock_coro(expected)) as query_tbl_patch:
                actual = await User.Objects.all()
                assert actual == expected['rows']
            query_tbl_patch.assert_called_once_with('users', payload)

    @pytest.mark.parametrize("kwargs, payload", [
        ({'username': None, 'uid': None}, '{"return": ["id", "uname", "role_id", "access_method", "real_name", "description"], "where": {"column": "enabled", "condition": "=", "value": "t"}}'),
        ({'username': None, 'uid': 1}, '{"return": ["id", "uname", "role_id", "access_method", "real_name", "description"], "where": {"column": "enabled", "condition": "=", "value": "t", "and": {"column": "id", "condition": "=", "value": 1}}}'),
        ({'username': 'aj', 'uid': None}, '{"return": ["id", "uname", "role_id", "access_method", "real_name", "description"], "where": {"column": "enabled", "condition": "=", "value": "t", "and": {"column": "uname", "condition": "=", "value": "aj"}}}'),
        ({'username': 'aj', 'uid': 1}, '{"return": ["id", "uname", "role_id", "access_method", "real_name", "description"], "where": {"column": "enabled", "condition": "=", "value": "t", "and": {"column": "id", "condition": "=", "value": 1, "and": {"column": "uname", "condition": "=", "value": "aj"}}}}')
    ])
    async def test_get_filter(self, kwargs, payload):
        expected = {'rows': [], 'count': 0}
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=mock_coro(expected)) as query_tbl_patch:
                actual = await User.Objects.filter(**kwargs)
                assert actual == expected['rows']
        query_tbl_patch.assert_called_once_with('users', payload)

    @pytest.mark.parametrize("exp_kwargs, error_msg", [
        ({'username': None, 'uid': None}, ''),
        ({'username': None, 'uid': 1}, 'User with id:<1> does not exist'),
        ({'username': 'aj', 'uid': None}, 'User with name:<aj> does not exist'),
        ({'username': 'aj', 'uid': 1}, 'User with id:<1> and name:<aj> does not exist')
    ])
    async def test_get_exception(self, exp_kwargs, error_msg):
        with patch.object(User.Objects, 'filter', return_value=mock_coro([])) as filter_patch:
            with pytest.raises(Exception) as excinfo:
                await User.Objects.get(uid=exp_kwargs['uid'], username=exp_kwargs['username'])
            assert str(excinfo.value) == error_msg
            assert excinfo.type is User.DoesNotExist
            assert issubclass(excinfo.type, Exception)
        args, kwargs = filter_patch.call_args
        assert kwargs == exp_kwargs

    async def test_get(self):
        expected = [{'role_id': '1', 'id': '1', 'uname': 'admin'}]
        exp_kwargs = {'uid': 1, 'username': 'admin'}
        with patch.object(User.Objects, 'filter', return_value=mock_coro(expected)) as filter_patch:
            actual = await User.Objects.get(uid=exp_kwargs['uid'], username=exp_kwargs['username'])
            assert actual == expected[0]
        args, kwargs = filter_patch.call_args
        assert kwargs == exp_kwargs

    @pytest.mark.parametrize("expected, user_pwd", [(True, 'fledge'), (False, 'invalid')])
    async def test_hash_password_check(self, expected, user_pwd):
        password = User.Objects.hash_password("fledge")
        actual = User.Objects.check_password(password, user_pwd)
        assert actual == expected

    async def test_create_user(self):
        hashed_password = "dd7171406eaf4baa8bc805857f719bca"
        expected = {'rows_affected': 1, "response": "inserted"}
        payload = {"pwd": "dd7171406eaf4baa8bc805857f719bca", "role_id": 1, "uname": "aj", 'access_method': 'any',
                   'description': '', 'real_name': ''}
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(User.Objects, 'hash_password', return_value=hashed_password) as hash_pwd_patch:
                with patch.object(storage_client_mock, 'insert_into_tbl', return_value=mock_coro(expected)) as insert_tbl_patch:
                    actual = await User.Objects.create("aj", "fledge", 1)
                    assert actual == expected
                assert 1 == insert_tbl_patch.call_count
                assert insert_tbl_patch.called is True
                args, kwargs = insert_tbl_patch.call_args
                assert 'users' == args[0]
                p = json.loads(args[1])
                assert payload == p
            hash_pwd_patch.assert_called_once_with('fledge',)

    async def test_create_user_exception(self):
        hashed_password = "dd7171406eaf4baa8bc805857f719bca"
        expected = {'message': 'Something went wrong', 'retryable': False, 'entryPoint': 'insert'}
        payload = {"pwd": "dd7171406eaf4baa8bc805857f719bca", "role_id": 1, "uname": "aj", 'access_method': 'any',
                   'description': '', 'real_name': ''}
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(User.Objects, 'hash_password', return_value=hashed_password) as hash_pwd_patch:
                with patch.object(storage_client_mock, 'insert_into_tbl', return_value=mock_coro(), side_effect=StorageServerError(code=400, reason="blah", error=expected)) as insert_tbl_patch:
                    with pytest.raises(ValueError) as excinfo:
                        await User.Objects.create("aj", "fledge", 1)
                    assert str(excinfo.value) == expected['message']
                args, kwargs = insert_tbl_patch.call_args
                assert 'users' == args[0]
                p = json.loads(args[1])
                assert payload == p
            hash_pwd_patch.assert_called_once_with('fledge', )

    async def test_delete_user(self):
        p1 = '{"where": {"column": "user_id", "condition": "=", "value": 2}}'
        p2 = '{"values": {"enabled": "f"}, "where": {"column": "id", "condition": "=", "value": 2, "and": {"column": "enabled", "condition": "=", "value": "t"}}}'
        r1 = {'response': 'deleted', 'rows_affected': 1}
        r2 = {'response': 'updated', 'rows_affected': 1}

        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'delete_from_tbl', return_value=mock_coro(r1)) as delete_tbl_patch:
                with patch.object(storage_client_mock, 'update_tbl', return_value=mock_coro(r2)) as update_tbl_patch:
                    actual = await User.Objects.delete(2)
                    assert r2 == actual
                update_tbl_patch.assert_called_once_with('users', p2)
            delete_tbl_patch.assert_called_once_with('user_logins', p1)

    async def test_delete_admin_user(self):
        with pytest.raises(ValueError) as excinfo:
            await User.Objects.delete(1)
        assert str(excinfo.value) == 'Super admin user can not be deleted'

    async def test_delete_user_exception(self):
        expected = {'message': 'Something went wrong', 'retryable': False, 'entryPoint': 'delete'}
        payload = '{"values": {"enabled": "f"}, "where": {"column": "id", "condition": "=", "value": 2, "and": {"column": "enabled", "condition": "=", "value": "t"}}}'
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'delete_from_tbl', return_value=mock_coro()) as delete_tbl_patch:
                with patch.object(storage_client_mock, 'update_tbl', side_effect=StorageServerError(code=400, reason="blah",
                                                                                                    error=expected)) as update_tbl_patch:
                    with pytest.raises(ValueError) as excinfo:
                        await User.Objects.delete(2)
                    assert str(excinfo.value) == expected['message']
            update_tbl_patch.assert_called_once_with('users', payload)

    @pytest.mark.parametrize("user_data, payload", [
        ({'role_id': 2}, {"values": {"role_id": 2}, "where": {"column": "id", "condition": "=", "value": 2, "and": {"column": "enabled", "condition": "=", "value": "t"}}}),
        ({'role_id': '2'}, {"values": {"role_id": "2"}, "where": {"column": "id", "condition": "=", "value": 2, "and": {"column": "enabled", "condition": "=", "value": "t"}}})
    ])
    async def test_update_user_role(self, user_data, payload):
        expected = {'response': 'updated', 'rows_affected': 1}
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'update_tbl', return_value=mock_coro(expected)) as update_tbl_patch:
                with patch.object(User.Objects, 'delete_user_tokens', return_value=mock_coro()) as delete_token_patch:
                    actual = await User.Objects.update(2, user_data)
                    assert actual is True
                delete_token_patch.assert_called_once_with(2)
            args, kwargs = update_tbl_patch.call_args
            assert 'users' == args[0]
            p = json.loads(args[1])
            assert payload == p

    @pytest.mark.parametrize("user_data, payload", [
        ({'password': "Test@123"}, {"values": {"pwd": "HASHED_PASSWORD"}, "where": {"column": "id", "condition": "=", "value": 2}})
    ])
    async def test_update_user_password(self, user_data, payload):
        expected = {'response': 'updated', 'rows_affected': 1}
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(User.Objects, 'hash_password', return_value='HASHED_PWD') as hash_pwd_patch:
                with patch.object(User.Objects, '_get_password_history', return_value=mock_coro(['HASHED_PWD'])) as pwd_list_patch:
                    with patch.object(storage_client_mock, 'update_tbl', return_value=mock_coro(expected)) as update_tbl_patch:
                        with patch.object(User.Objects, 'delete_user_tokens', return_value=mock_coro()) as delete_token_patch:
                            with patch.object(User.Objects, '_insert_pwd_history_with_oldest_pwd_deletion_if_count_exceeds', return_value=mock_coro()) as pwd_history_patch:
                                actual = await User.Objects.update(2, user_data)
                                assert actual is True
                            pwd_history_patch.assert_called_once_with(storage_client_mock, 2, 'HASHED_PWD', ['HASHED_PWD'])
                        delete_token_patch.assert_called_once_with(2)
                    args, kwargs = update_tbl_patch.call_args
                    assert 'users' == args[0]
                    # FIXME: payload ordering issue after datetime patch
                    # update_tbl_patch.assert_called_once_with('users', payload)
                pwd_list_patch.assert_called_once_with(storage_client_mock, 2, user_data)
            hash_pwd_patch.assert_called_once_with(user_data['password'])

    async def test_update_user_storage_exception(self):
        expected = {'message': 'Something went wrong', 'retryable': False, 'entryPoint': 'update'}
        payload = '{"values": {"role_id": 2}, "where": {"column": "id", "condition": "=", "value": 2, "and": {"column": "enabled", "condition": "=", "value": "t"}}}'
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'update_tbl', side_effect=StorageServerError(code=400, reason="blah", error=expected)) as update_tbl_patch:
                with pytest.raises(ValueError) as excinfo:
                    await User.Objects.update(2, {'role_id': 2})
                assert str(excinfo.value) == expected['message']
        update_tbl_patch.assert_called_once_with('users', payload)

    async def test_update_user_exception(self):
        payload = '{"values": {"role_id": "blah"}, "where": {"column": "id", "condition": "=", "value": 2, "and": {"column": "enabled", "condition": "=", "value": "t"}}}'
        msg = 'Bad role id'
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'update_tbl', side_effect=ValueError(msg)) as update_tbl_patch:
                with pytest.raises(Exception) as excinfo:
                    await User.Objects.update(2, {'role_id': 'blah'})
                assert excinfo.type is ValueError
                assert str(excinfo.value) == msg
            update_tbl_patch.assert_called_once_with('users', payload)

    @pytest.mark.parametrize("user_data", [
        {'real_name': 'MSD'}, {'description': 'Captain Cool'}, {'real_name': 'MSD', 'description': 'Captain Cool'}
    ])
    async def test_update_user_other_fields(self, user_data):
        expected = {'response': 'updated', 'rows_affected': 1}
        expected_payload = {'where': {'column': 'id', 'condition': '=', 'value': 2,
                                      'and': {'column': 'enabled', 'condition': '=', 'value': 't'}}}
        expected_payload.update({'values': user_data})
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'update_tbl', return_value=mock_coro(expected)) as update_tbl_patch:
                with patch.object(User.Objects, 'delete_user_tokens', return_value=mock_coro()) as delete_token_patch:
                    actual = await User.Objects.update(2, user_data)
                    assert actual is True
                delete_token_patch.assert_not_called()
            args, kwargs = update_tbl_patch.call_args
            assert 'users' == args[0]
            p = json.loads(args[1])
            assert expected_payload == p

    async def test_login_if_no_user_exists(self):
        async def mock_get_category_item():
            return {"value": "0"}

        payload = {"return": ["pwd", "id", "role_id", "access_method", {"column": "pwd_last_changed", "format": "YYYY-MM-DD HH24:MI:SS.MS", "alias": "pwd_last_changed"}, "real_name", "description"], "where": {"column": "uname", "condition": "=", "value": "admin", "and": {"column": "enabled", "condition": "=", "value": "t"}}}
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(ConfigurationManager, "get_category_item", return_value=mock_get_category_item()) as mock_get_cat_patch:
                with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=mock_coro({'rows': [], 'count': 0})) as query_tbl_patch:
                    with pytest.raises(Exception) as excinfo:
                        await User.Objects.login('admin', 'blah', '0.0.0.0')
                    assert str(excinfo.value) == 'User does not exist'
                    assert excinfo.type is User.DoesNotExist
                    assert issubclass(excinfo.type, Exception)
                args, kwargs = query_tbl_patch.call_args
                assert 'users' == args[0]
                p = json.loads(args[1])
                assert payload == p
            mock_get_cat_patch.assert_called_once_with('rest_api', 'passwordChange')

    async def test_login_if_invalid_password(self):
        async def mock_get_category_item():
            return {"value": "0"}

        pwd_result = {'count': 1, 'rows': [{'role_id': '2', 'pwd': '3759bf3302f5481e8c9cc9472c6088ac', 'id': '2', 'pwd_last_changed': '2018-03-30 12:32:08.216159'}]}
        payload = {"return": ["pwd", "id", "role_id", "access_method", {"column": "pwd_last_changed", "format": "YYYY-MM-DD HH24:MI:SS.MS", "alias": "pwd_last_changed"}, "real_name", "description"], "where": {"column": "uname", "condition": "=", "value": "user", "and": {"column": "enabled", "condition": "=", "value": "t"}}}
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(ConfigurationManager, "get_category_item", return_value=mock_get_category_item()) as mock_get_cat_patch:
                with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=mock_coro(pwd_result)) as query_tbl_patch:
                    with patch.object(User.Objects, 'check_password', return_value=False) as check_pwd_patch:
                        with pytest.raises(Exception) as excinfo:
                            await User.Objects.login('user', 'blah', '0.0.0.0')
                        assert str(excinfo.value) == 'Username or Password do not match'
                        assert excinfo.type is User.PasswordDoesNotMatch
                        assert issubclass(excinfo.type, Exception)
                    check_pwd_patch.assert_called_once_with('3759bf3302f5481e8c9cc9472c6088ac', 'blah')
                args, kwargs = query_tbl_patch.call_args
                assert 'users' == args[0]
                p = json.loads(args[1])
                assert payload == p
            mock_get_cat_patch.assert_called_once_with('rest_api', 'passwordChange')

    async def test_login_age_pwd_expiration(self):
        async def mock_get_category_item():
            return {"value": "30"}

        pwd_result = {'count': 1, 'rows': [{'role_id': '2', 'pwd': '3759bf3302f5481e8c9cc9472c6088ac', 'id': '2', 'pwd_last_changed': '2018-01-30 12:32:08.216159'}]}
        payload = {"return": ["pwd", "id", "role_id", "access_method", {"column": "pwd_last_changed", "format": "YYYY-MM-DD HH24:MI:SS.MS", "alias": "pwd_last_changed"}, "real_name", "description"], "where": {"column": "uname", "condition": "=", "value": "user", "and": {"column": "enabled", "condition": "=", "value": "t"}}}
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(ConfigurationManager, "get_category_item", return_value=mock_get_category_item()) as mock_get_cat_patch:
                with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=mock_coro(pwd_result)) as query_tbl_patch:
                    with pytest.raises(Exception) as excinfo:
                        await User.Objects.login('user', 'fledge', '0.0.0.0')
                    assert pwd_result['rows'][0]['id'] == str(excinfo.value)
                    assert excinfo.type is User.PasswordExpired
                    assert issubclass(excinfo.type, Exception)
                args, kwargs = query_tbl_patch.call_args
                assert 'users' == args[0]
                p = json.loads(args[1])
                assert payload == p
            mock_get_cat_patch.assert_called_once_with('rest_api', 'passwordChange')

    @pytest.mark.parametrize("user_data", [
        ({'count': 1, 'rows': [{'role_id': '1', 'pwd': '3759bf3302f5481e8c9cc9472c6088ac', 'id': '1', 'is_admin': True, 'pwd_last_changed': '2018-03-30 12:32:08.216159'}]}),
        ({'count': 1, 'rows': [{'role_id': '2', 'pwd': '3759bf3302f5481e8c9cc9472c6088ac', 'id': '2', 'is_admin': False, 'pwd_last_changed': '2018-03-29 05:05:08.216159'}]})
    ])
    async def test_login(self, user_data):
        async def mock_get_category_item():
            return {"value": "0"}

        payload = {"return": ["pwd", "id", "role_id", "access_method", {"column": "pwd_last_changed", "format": "YYYY-MM-DD HH24:MI:SS.MS", "alias": "pwd_last_changed"}, "real_name", "description"], "where": {"column": "uname", "condition": "=", "value": "user", "and": {"column": "enabled", "condition": "=", "value": "t"}}}
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(ConfigurationManager, "get_category_item", return_value=mock_get_category_item()) as mock_get_cat_patch:
                with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=mock_coro(user_data)) as query_tbl_patch:
                    with patch.object(User.Objects, 'check_password', return_value=True) as check_pwd_patch:
                        with patch.object(storage_client_mock, 'insert_into_tbl', return_value=mock_coro(True)) as insert_tbl_patch:
                            uid, jwt_token, is_admin = await User.Objects.login('user', 'fledge', '0.0.0.0')
                            expected = user_data['rows'][0]
                            assert uid == expected['id']
                            assert is_admin == expected['is_admin']
                            # FIXME: token patch
                            # assert jwt_token

                        # FIXME: datetime.now() patch and then payload assertion
                        args, kwargs = insert_tbl_patch.call_args
                        assert 'user_logins' == args[0]
                    check_pwd_patch.assert_called_once_with('3759bf3302f5481e8c9cc9472c6088ac', 'fledge')
                args1, kwargs1 = query_tbl_patch.call_args
                assert 'users' == args1[0]
                p = json.loads(args1[1])
                assert payload == p
            mock_get_cat_patch.assert_called_once_with('rest_api', 'passwordChange')

    async def test_login_exception(self):
        async def mock_get_category_item():
            return {"value": "0"}

        pwd_result = {'count': 1, 'rows': [{'role_id': '1', 'pwd': '3759bf3302f5481e8c9cc9472c6088ac', 'id': '1', 'pwd_last_changed': '2018-03-30 12:32:08.216159'}]}
        expected = {'message': 'Something went wrong', 'retryable': False, 'entryPoint': 'delete'}
        payload = {"return": ["pwd", "id", "role_id", "access_method", {"column": "pwd_last_changed", "format": "YYYY-MM-DD HH24:MI:SS.MS", "alias": "pwd_last_changed"}, "real_name", "description"], "where": {"column": "uname", "condition": "=", "value": "user", "and": {"column": "enabled", "condition": "=", "value": "t"}}}
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(ConfigurationManager, "get_category_item", return_value=mock_get_category_item()) as mock_get_cat_patch:
                with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=mock_coro(pwd_result)) as query_tbl_patch:
                    with patch.object(User.Objects, 'check_password', return_value=True) as check_pwd_patch:
                        with patch.object(storage_client_mock, 'insert_into_tbl', side_effect=StorageServerError(code=400, reason="blah", error=expected)):
                            with pytest.raises(ValueError) as excinfo:
                                await User.Objects.login('user', 'fledge', '0.0.0.0')
                            assert str(excinfo.value) == expected['message']
                    check_pwd_patch.assert_called_once_with('3759bf3302f5481e8c9cc9472c6088ac', 'fledge')
                args, kwargs = query_tbl_patch.call_args
                assert 'users' == args[0]
                p = json.loads(args[1])
                assert payload == p
            mock_get_cat_patch.assert_called_once_with('rest_api', 'passwordChange')

    async def test_delete_user_tokens(self):
        expected = {'response': 'deleted', 'rows_affected': 1}
        payload = '{"where": {"column": "user_id", "condition": "=", "value": 2}}'
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'delete_from_tbl', return_value=mock_coro(expected)) as delete_tbl_patch:
                actual = await User.Objects.delete_user_tokens(2)
                assert actual == expected
            delete_tbl_patch.assert_called_once_with('user_logins', payload)

    async def test_delete_user_tokens_exception(self):
        expected = {'message': 'Something went wrong', 'retryable': False, 'entryPoint': 'delete'}
        payload = '{"where": {"column": "user_id", "condition": "=", "value": 2}}'
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'delete_from_tbl', side_effect=StorageServerError(code=400, reason="blah", error=expected)) as delete_tbl_patch:
                with pytest.raises(ValueError) as excinfo:
                    await User.Objects.delete_user_tokens(2)
                assert str(excinfo.value) == expected['message']
        delete_tbl_patch.assert_called_once_with('user_logins', payload)

    async def test_refresh_token_expiry(self):
        expected = {'rows_affected': 1, "response": "updated"}
        token = "RDSlaEtgXuxbYHlDgJURbEeBua2ccwvHeB7MVDeIHq4"
        payload = {"values": {"token_expiration": "2018-03-13 15:33:25.959408"}, "where": {"column": "token", "condition": "=", "value": "RDSlaEtgXuxbYHlDgJURbEeBua2ccwvHeB7MVDeIHq4"}}
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'update_tbl', return_value=mock_coro(expected)) as update_tbl_patch:
                await User.Objects.refresh_token_expiry(token)
            # FIXME: datetime.now() patch and then payload assertion
            args, kwargs = update_tbl_patch.call_args
            assert 'user_logins' == args[0]

    async def test_invalid_token(self):
        storage_client_mock = MagicMock(StorageClientAsync)
        payload = {"return": [{"column": "token_expiration", "format": "YYYY-MM-DD HH24:MI:SS.MS", "alias": "token_expiration"}], "where": {"column": "token", "condition": "=", "value": "blah"}}
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=mock_coro({'rows': [], 'count': 0})) as query_tbl_patch:
                with pytest.raises(Exception) as excinfo:
                    await User.Objects.validate_token('blah')
                assert str(excinfo.value) == 'Token appears to be invalid'
                assert excinfo.type is User.InvalidToken
                assert issubclass(excinfo.type, Exception)
            args, kwargs = query_tbl_patch.call_args
            assert 'user_logins' == args[0]
            p = json.loads(args[1])
            assert payload == p

    async def test_validate_token(self):
        token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE1MjEwNDAxNTksInVpZCI6IjIifQ.oeWfDuRStunPQciCuRSSGdZaT42wnh4ODavJ62LSEvI"
        valid_token_result = {'rows': [{"token_expiration": "2017-03-14 15:09:19.800648"}], 'count': 1}
        storage_client_mock = MagicMock(StorageClientAsync)
        payload = {"return": [{"column": "token_expiration", "format": "YYYY-MM-DD HH24:MI:SS.MS", "alias": "token_expiration"}], "where": {"column": "token", "condition": "=", "value": token}}
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=mock_coro(valid_token_result)) as query_tbl_patch:
                # FIXME: jwt.decode patch
                uid = await User.Objects.validate_token(token)
                assert '2' == uid
            # FIXME: datetime.now() patch
            args, kwargs = query_tbl_patch.call_args
            assert 'user_logins' == args[0]
            p = json.loads(args[1])
            assert payload == p

    @pytest.mark.skip(reason="Need to patch jwt token and datetime")
    async def test_token_expiration(self):
        pass

    async def test_delete_token(self):
        expected = {'response': 'deleted', 'rows_affected': 1}
        payload = '{"where": {"column": "token", "condition": "=", "value": "eyz"}}'
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'delete_from_tbl', return_value=mock_coro(expected)) as delete_tbl_patch:
                actual = await User.Objects.delete_token("eyz")
                assert actual == expected
            delete_tbl_patch.assert_called_once_with('user_logins', payload)

    async def test_delete_token_exception(self):
        expected = {'message': 'Something went wrong', 'retryable': False, 'entryPoint': 'delete'}
        payload = '{"where": {"column": "token", "condition": "=", "value": "eyx"}}'
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'delete_from_tbl', side_effect=StorageServerError(code=400, reason="blah", error=expected)) as delete_tbl_patch:
                with pytest.raises(ValueError) as excinfo:
                    await User.Objects.delete_token("eyx")
                assert str(excinfo.value) == expected['message']
        delete_tbl_patch.assert_called_once_with('user_logins', payload)

    async def test_delete_all_user_tokens(self):
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'delete_from_tbl', return_value=mock_coro()) as delete_tbl_patch:
                await User.Objects.delete_all_user_tokens()
        delete_tbl_patch.assert_called_once_with('user_logins')

    async def test_no_user_exists(self):
        expected_payload = '{"return": ["uname", "pwd"], "where": {"column": "id", "condition": "=", "value": 2, ' \
                           '"and": {"column": "enabled", "condition": "=", "value": "t"}}}'
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=mock_coro(
                    {'rows': []})) as query_tbl_patch:
                result = await User.Objects.is_user_exists(2, 'blah')
                assert result is None
            query_tbl_patch.assert_called_once_with('users', expected_payload)

    @pytest.mark.parametrize("ret_val_check_pwd, expected", [(True, 1), (False, None)])
    async def test_user_exists(self, ret_val_check_pwd, expected):
        expected_payload = '{"return": ["uname", "pwd"], "where": {"column": "id", "condition": "=", "value": 1, ' \
                           '"and": {"column": "enabled", "condition": "=", "value": "t"}}}'
        storage_client_mock = MagicMock(StorageClientAsync)
        ret_val = {'rows': [{'id': 1, 'pwd': 'HASHED_PWD'}]}
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=mock_coro(ret_val)) as query_tbl_patch:
                with patch.object(User.Objects, 'check_password', return_value=ret_val_check_pwd) as check_pwd_patch:
                    actual = await User.Objects.is_user_exists(1, 'admin')
                    assert expected == actual
                check_pwd_patch.assert_called_once_with(ret_val['rows'][0]['pwd'], 'admin')
            query_tbl_patch.assert_called_once_with('users', expected_payload)

    async def test__get_password_history(self):
        storage_client_mock = MagicMock(StorageClientAsync)
        user_data = {'password': 'HASHED_PWD'}
        ret_val = {'rows': [{'id': 1, 'user_id': 2, 'pwd': 'HASHED_PWD'}]}
        row = ret_val['rows'][0]
        with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=mock_coro(ret_val)) as query_tbl_patch:
            with patch.object(User.Objects, 'check_password', return_value=False) as check_pwd_patch:
                result = await User.Objects._get_password_history(storage_client_mock, row['user_id'], user_data)
                assert [user_data['password']] == result
            check_pwd_patch.assert_called_once_with(row['pwd'], user_data['password'])
        query_tbl_patch.assert_called_once_with('user_pwd_history', '{"where": {"column": "user_id", "condition": "=", "value": 2}}')

    async def test__get_password_history_exception(self):
        storage_client_mock = MagicMock(StorageClientAsync)
        user_data = {'password': 'HASHED_PWD'}
        ret_val = {'rows': [{'id': 1, 'user_id': 2, 'pwd': 'HASHED_PWD'}]}
        row = ret_val['rows'][0]
        with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=mock_coro(ret_val)) as query_tbl_patch:
            with patch.object(User.Objects, 'check_password', return_value=True) as check_pwd_patch:
                with pytest.raises(Exception) as excinfo:
                    await User.Objects._get_password_history(storage_client_mock, row['user_id'], user_data)
                # assert str(excinfo.value) == ''
                assert excinfo.type is User.PasswordAlreadyUsed
                assert issubclass(excinfo.type, Exception)
            check_pwd_patch.assert_called_once_with(row['pwd'], user_data['password'])
        query_tbl_patch.assert_called_once_with('user_pwd_history', '{"where": {"column": "user_id", "condition": "=", "value": 2}}')

    @pytest.mark.parametrize("hashed_pwd, pwd_history_list, payload", [
        ('HASHED_PWD_1', ['HASHED_PWD_1'], {"pwd": "HASHED_PWD_1", "user_id": 2}),
        ('HASHED_PWD_2', ['HASHED_PWD_2', 'HASHED_PWD_1'], {"pwd": "HASHED_PWD_2", "user_id": 2})
    ])
    async def test__insert_pwd_history(self, hashed_pwd, pwd_history_list, payload):
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(storage_client_mock, 'insert_into_tbl', return_value=mock_coro()) as insert_tbl_patch:
            await User.Objects._insert_pwd_history_with_oldest_pwd_deletion_if_count_exceeds(storage_client_mock, 2, hashed_pwd, pwd_history_list)
        args, kwargs = insert_tbl_patch.call_args
        assert 'user_pwd_history' == args[0]
        p = json.loads(args[1])
        assert payload == p

    @pytest.mark.parametrize("hashed_pwd, pwd_history_list", [
        ('HASHED_PWD_4', ['HASHED_PWD_3', 'HASHED_PWD_2', 'HASHED_PWD_1'])
    ])
    async def test__insert_pwd_history_and_delete_oldest_pwd_if_count_exceeds(self, hashed_pwd, pwd_history_list):
        storage_client_mock = MagicMock(StorageClientAsync)
        payload = {"where": {"column": "user_id", "condition": "=", "value": 2, "and": {"column": "pwd", "condition": "=", "value": "HASHED_PWD_1"}}}
        with patch.object(storage_client_mock, 'delete_from_tbl', return_value=mock_coro()) as delete_tbl_patch:
            with patch.object(storage_client_mock, 'insert_into_tbl', return_value=mock_coro()) as insert_tbl_patch:
                await User.Objects._insert_pwd_history_with_oldest_pwd_deletion_if_count_exceeds(storage_client_mock, 2, hashed_pwd, pwd_history_list)
            args, kwargs = insert_tbl_patch.call_args
            assert 'user_pwd_history' == args[0]
            p = json.loads(args[1])
            assert {"pwd": "HASHED_PWD_4", "user_id": 2} == p
        args1, kwargs1 = delete_tbl_patch.call_args
        assert 'user_pwd_history' == args1[0]
        p = json.loads(args1[1])
        assert payload == p

    @pytest.mark.parametrize("user_data", [
        ({'count': 1, 'rows': [{'role_id': '1', 'pwd': '3759bf3302f5481e8c9cc9472c6088ac', 'id': '1', 'is_admin': True, 'pwd_last_changed': '2018-03-30 12:32:08.216159'}]}),
        ({'count': 1, 'rows': [{'role_id': '2', 'pwd': '3759bf3302f5481e8c9cc9472c6088ac', 'id': '2', 'is_admin': False, 'pwd_last_changed': '2018-03-29 05:05:08.216159'}]})
    ])
    async def test_certficate_login(self, user_data):
        payload = {"return": ["id", "role_id"], "where": {"column": "uname", "condition": "=", "value": "user", "and": {"column": "enabled", "condition": "=", "value": "t"}}}
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=mock_coro(user_data)) as query_tbl_patch:
                with patch.object(storage_client_mock, 'insert_into_tbl', return_value=mock_coro(True)) as insert_tbl_patch:
                    uid, jwt_token, is_admin = await User.Objects.certificate_login('user', '0.0.0.0')
                    expected = user_data['rows'][0]
                    assert uid == expected['id']
                    assert is_admin == expected['is_admin']
                    # FIXME: token patch
                    # assert jwt_token

                # FIXME: datetime.now() patch and then payload assertion
                args, kwargs = insert_tbl_patch.call_args
                assert 'user_logins' == args[0]
            args1, kwargs1 = query_tbl_patch.call_args
            assert 'users' == args1[0]
            p = json.loads(args1[1])
            assert payload == p
