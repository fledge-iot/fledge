# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import json
from unittest.mock import patch
from aiohttp import web
import pytest

from foglamp.common.web import middleware
from foglamp.services.core import routes
from foglamp.services.core.user_model import User
from foglamp.services.core.api import auth

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

ADMIN_USER_HEADER = {'content-type': 'application/json', 'Authorization': 'admin_user_token'}
NORMAL_USER_HEADER = {'content-type': 'application/json', 'Authorization': 'normal_user_token'}


@pytest.allure.feature("unit")
@pytest.allure.story("api", "auth-mandatory")
class TestAuthMandatory:

    @pytest.fixture
    def client(self, loop, test_server, test_client):
        app = web.Application(loop=loop,  middlewares=[middleware.auth_middleware])
        # fill the routes table
        routes.setup(app)
        server = loop.run_until_complete(test_server(app))
        server.start_server(loop=loop)
        client = loop.run_until_complete(test_client(server))
        return client

    def auth_token_fixture(self, mocker, is_admin=True):
        user = {'id': 1, 'uname': 'admin', 'role_id': '1'} if is_admin else {'id': 2, 'uname': 'user', 'role_id': '2'}
        patch_logger_info = mocker.patch.object(middleware._logger, 'info')
        patch_validate_token = mocker.patch.object(User.Objects, 'validate_token', return_value=user['id'])
        patch_refresh_token = mocker.patch.object(User.Objects, 'refresh_token_expiry', return_value=None)
        patch_user_get = mocker.patch.object(User.Objects, 'get', return_value=user)

        return patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get

    @pytest.mark.parametrize("request_data", [
        {},
        {"username": 12},
        {"password": 12},
        {"username": "blah"},
        {"password": "blah"},
        {"invalid": "blah"},
        {"username": "blah", "pwd": "blah"},
        {"uname": "blah", "password": "blah"},
    ])
    async def test_create_bad_user(self, client, mocker, request_data):
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)

        with patch.object(User.Objects, 'get_role_id_by_name', return_value=[{'id': '1'}]) as patch_role_id:
            with patch.object(auth._logger, 'warning') as patch_logger_warn:
                resp = await client.post('/foglamp/admin/user', data=json.dumps(request_data), headers=ADMIN_USER_HEADER)
                assert 400 == resp.status
                assert 'Username or password is missing' == resp.reason
                patch_logger_warn.assert_called_once_with('Username and password are required to create user')
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/foglamp/admin/user')

    @pytest.mark.parametrize("request_data", [
        {"username": "blah", "password": 1},
        {"username": "blah", "password": "blah"}
    ])
    async def test_create_user_bad_password(self, client, mocker, request_data):
        msg = 'Password must contain at least one digit, one lowercase, one uppercase & one special character and length of minimum 6 characters'
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)

        with patch.object(User.Objects, 'get_role_id_by_name', return_value=[{'id': '1'}]) as patch_role_id:
            with patch.object(auth._logger, 'warning') as patch_logger_warning:
                resp = await client.post('/foglamp/admin/user', data=json.dumps(request_data), headers=ADMIN_USER_HEADER)
                assert 400 == resp.status
                assert msg == resp.reason
            patch_logger_warning.assert_called_once_with(msg)
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/foglamp/admin/user')

    @pytest.mark.parametrize("request_data", [
        {"username": "aj", "password": "F0gl@mp", "role_id": -3},
        {"username": "aj", "password": "F0gl@mp", "role_id": "blah"}
    ])
    async def test_create_user_with_bad_role(self, client, mocker, request_data):
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)

        with patch.object(User.Objects, 'get_role_id_by_name', return_value=[{'id': '1'}]) as patch_role_id:
            with patch.object(auth, 'is_valid_role', return_value=False) as patch_role:
                with patch.object(auth._logger, 'warning') as patch_logger_warning:
                    resp = await client.post('/foglamp/admin/user', data=json.dumps(request_data), headers=ADMIN_USER_HEADER)
                    assert 400 == resp.status
                    assert 'Invalid or bad role id' == resp.reason
                patch_logger_warning.assert_called_once_with('Create user requested with bad role id')
            patch_role.assert_called_once_with(request_data['role_id'])
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/foglamp/admin/user')

    @pytest.mark.parametrize("request_data", [
        {"username": "bla", "password": "F0gl@mp"},
        {"username": "  b", "password": "F0gl@mp"},
        {"username": "b  ", "password": "F0gl@mp"},
        {"username": "  b la", "password": "F0gl@mp"},
        {"username": "b l A  ", "password": "F0gl@mp"},
        {"username": "Bla", "password": "F0gl@mp"},
        {"username": "BLA", "password": "F0gl@mp"}
    ])
    async def test_create_user_bad_username(self, client, mocker, request_data):
        msg = 'Username should be of minimum 4 characters'
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)

        with patch.object(User.Objects, 'get_role_id_by_name', return_value=[{'id': '1'}]) as patch_role_id:
            with patch.object(auth, 'is_valid_role', return_value=True) as patch_role:
                with patch.object(auth._logger, 'warning') as patch_logger_warning:
                    resp = await client.post('/foglamp/admin/user', data=json.dumps(request_data), headers=ADMIN_USER_HEADER)
                    assert 400 == resp.status
                    assert msg == resp.reason
                patch_logger_warning.assert_called_once_with(msg)
            patch_role.assert_called_once_with(2)
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/foglamp/admin/user')

    async def test_create_dupe_user_name(self, client):
        request_data = {"username": "ajtest", "password": "F0gl@mp"}
        valid_user = {'id': 1, 'uname': 'admin', 'role_id': '1'}
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(User.Objects, 'validate_token', return_value=valid_user['id']) as patch_validate_token:
                with patch.object(User.Objects, 'refresh_token_expiry', return_value=None) as patch_refresh_token:
                    with patch.object(User.Objects, 'get', side_effect=[valid_user, {'role_id': '2', 'uname': 'ajtest', 'id': '2'}]) as patch_user_get:
                        with patch.object(User.Objects, 'get_role_id_by_name', return_value=[{'id': '1'}]) as patch_role_id:
                            with patch.object(auth, 'is_valid_role', return_value=True) as patch_role:
                                with patch.object(auth._logger, 'warning') as patch_logger_warning:
                                    resp = await client.post('/foglamp/admin/user', data=json.dumps(request_data), headers=ADMIN_USER_HEADER)
                                    assert 409 == resp.status
                                    assert 'User with the requested username already exists' == resp.reason
                                patch_logger_warning.assert_called_once_with('Can not create a user, username already exists')
                            patch_role.assert_called_once_with(2)
                        patch_role_id.assert_called_once_with('admin')
                    assert 2 == patch_user_get.call_count
                    args, kwargs = patch_user_get.call_args_list[0]
                    assert {'uid': valid_user['id']} == kwargs
                    args, kwargs = patch_user_get.call_args_list[1]
                    assert {'username': request_data['username']} == kwargs
                patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
            patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/foglamp/admin/user')

    async def test_create_user(self, client):
        data = {'id': '3', 'uname': 'ajtest', 'role_id': '2'}
        expected = {}
        expected.update(data)
        request_data = {"username": "ajtest", "password": "F0gl@mp"}
        ret_val = {"response": "inserted", "rows_affected": 1}
        msg = 'User has been created successfully'

        valid_user = {'id': 1, 'uname': 'admin', 'role_id': '1'}
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(User.Objects, 'validate_token', return_value=valid_user['id']) as patch_validate_token:
                with patch.object(User.Objects, 'refresh_token_expiry', return_value=None) as patch_refresh_token:
                    with patch.object(User.Objects, 'get', side_effect=[valid_user, User.DoesNotExist, data]) as patch_user_get:
                        with patch.object(User.Objects, 'get_role_id_by_name', return_value=[{'id': '1'}]) as patch_role_id:
                            with patch.object(auth, 'is_valid_role', return_value=True) as patch_role:
                                with patch.object(User.Objects, 'create', return_value=ret_val) as patch_create_user:
                                    with patch.object(auth._logger, 'info') as patch_auth_logger_info:
                                        resp = await client.post('/foglamp/admin/user', data=json.dumps(request_data), headers=ADMIN_USER_HEADER)
                                        assert 200 == resp.status
                                        r = await resp.text()
                                        actual = json.loads(r)
                                        assert msg == actual['message']
                                        assert expected['id'] == actual['user']['userId']
                                        assert expected['uname'] == actual['user']['userName']
                                        assert expected['role_id'] == actual['user']['roleId']
                                    patch_auth_logger_info.assert_called_once_with(msg)
                                patch_create_user.assert_called_once_with(request_data['username'], request_data['password'], int(expected['role_id']))
                            patch_role.assert_called_once_with(int(expected['role_id']))
                        patch_role_id.assert_called_once_with('admin')
                    assert 3 == patch_user_get.call_count
                    args, kwargs = patch_user_get.call_args_list[0]
                    assert {'uid': valid_user['id']} == kwargs
                    args, kwargs = patch_user_get.call_args_list[1]
                    assert {'username': request_data['username']} == kwargs
                    args, kwargs = patch_user_get.call_args_list[2]
                    assert {'username': expected['uname']} == kwargs
                patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
            patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/foglamp/admin/user')

    async def test_create_user_unknown_exception(self, client):
        request_data = {"username": "ajtest", "password": "F0gl@mp"}
        exc_msg = "Something went wrong"
        valid_user = {'id': 1, 'uname': 'admin', 'role_id': '1'}

        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(User.Objects, 'validate_token', return_value=valid_user['id']) as patch_validate_token:
                with patch.object(User.Objects, 'refresh_token_expiry', return_value=None) as patch_refresh_token:
                    with patch.object(User.Objects, 'get', side_effect=[valid_user, User.DoesNotExist]) as patch_user_get:
                        with patch.object(User.Objects, 'get_role_id_by_name', return_value=[{'id': '1'}]) as patch_role_id:
                            with patch.object(auth, 'is_valid_role', return_value=True) as patch_role:
                                with patch.object(User.Objects, 'create', side_effect=Exception(exc_msg)) as patch_create_user:
                                    with patch.object(auth._logger, 'exception') as patch_audit_logger_exc:
                                        resp = await client.post('/foglamp/admin/user', data=json.dumps(request_data), headers=ADMIN_USER_HEADER)
                                        assert 500 == resp.status
                                        assert exc_msg == resp.reason
                                    patch_audit_logger_exc.assert_called_once_with(exc_msg)
                                patch_create_user.assert_called_once_with(request_data['username'], request_data['password'], 2)
                            patch_role.assert_called_once_with(2)
                        patch_role_id.assert_called_once_with('admin')
                assert 2 == patch_user_get.call_count
                args, kwargs = patch_user_get.call_args_list[0]
                assert {'uid': valid_user['id']} == kwargs
                args, kwargs = patch_user_get.call_args_list[1]
                assert {'username': request_data['username']} == kwargs
                patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
            patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/foglamp/admin/user')

    async def test_create_user_value_error(self, client):
        valid_user = {'id': 1, 'uname': 'admin', 'role_id': '1'}
        request_data = {"username": "ajtest", "password": "F0gl@mp"}
        exc_msg = "Value Error occurred"
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(User.Objects, 'validate_token', return_value=valid_user['id']) as patch_validate_token:
                with patch.object(User.Objects, 'refresh_token_expiry', return_value=None) as patch_refresh_token:
                    with patch.object(User.Objects, 'get', side_effect=[valid_user, User.DoesNotExist]) as patch_user_get:
                        with patch.object(User.Objects, 'get_role_id_by_name', return_value=[{'id': '1'}]) as patch_role_id:
                            with patch.object(auth, 'is_valid_role', return_value=True) as patch_role:
                                with patch.object(User.Objects, 'create', side_effect=ValueError(exc_msg)) as patch_create_user:
                                    with patch.object(auth._logger, 'warning') as patch_audit_logger_warn:
                                        resp = await client.post('/foglamp/admin/user', data=json.dumps(request_data), headers=ADMIN_USER_HEADER)
                                        assert 400 == resp.status
                                        assert exc_msg == resp.reason
                                    patch_audit_logger_warn.assert_called_once_with(exc_msg)
                                patch_create_user.assert_called_once_with(request_data['username'], request_data['password'], 2)
                            patch_role.assert_called_once_with(2)
                        patch_role_id.assert_called_once_with('admin')
                    assert 2 == patch_user_get.call_count
                    args, kwargs = patch_user_get.call_args_list[0]
                    assert {'uid': valid_user['id']} == kwargs
                    args, kwargs = patch_user_get.call_args_list[1]
                    assert {'username': request_data['username']} == kwargs
                patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
            patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/foglamp/admin/user')

    async def test_update_user(self, client, mocker):
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)

        resp = await client.put('/foglamp/user/2', data=json.dumps({"a": 1}), headers=NORMAL_USER_HEADER)
        assert 501 == resp.status
        assert 'FOGL-1226' == resp.reason
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(NORMAL_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(NORMAL_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/user/2')

    @pytest.mark.parametrize("request_data, msg", [
        ({}, "Current or new password is missing"),
        ({"invalid": 1}, "Current or new password is missing"),
        ({"current_password": 1}, "Current or new password is missing"),
        ({"current_password": "foglamp"}, "Current or new password is missing"),
        ({"new_password": 1}, "Current or new password is missing"),
        ({"new_password": "foglamp"}, "Current or new password is missing"),
        ({"current_pwd": "foglamp", "new_pwd": "foglamp1"}, "Current or new password is missing"),
        ({"current_password": "F0gl@mp", "new_password": "F0gl@mp"}, "New password should not be same as current password"),
        ({"current_password": "F0gl@mp", "new_password": "foglamp"}, "Password must contain at least one digit, one lowercase, one uppercase & one special character and length of minimum 6 characters"),
        ({"current_password": "F0gl@mp", "new_password": 1}, "Password must contain at least one digit, one lowercase, one uppercase & one special character and length of minimum 6 characters")
    ])
    async def test_update_password_with_bad_data(self, client, request_data, msg):
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth._logger, 'warning') as patch_logger_warning:
                resp = await client.put('/foglamp/user/aj/password', data=json.dumps(request_data))
                assert 400 == resp.status
                assert msg == resp.reason
            patch_logger_warning.assert_called_once_with(msg)
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/user/aj/password')

    async def test_update_password_with_invalid_current_password(self, client):
        request_data = {"current_password": "blah", "new_password": "F0gl@mp"}
        uname = 'aj'
        msg = 'Invalid current password'
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(User.Objects, 'is_user_exists', return_value=None) as patch_user_exists:
                with patch.object(auth._logger, 'warning') as patch_logger_warning:
                    resp = await client.put('/foglamp/user/{}/password'.format(uname), data=json.dumps(request_data))
                    assert 404 == resp.status
                    assert msg == resp.reason
                patch_logger_warning.assert_called_once_with(msg)
            patch_user_exists.assert_called_once_with(uname, request_data['current_password'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/user/aj/password')

    @pytest.mark.parametrize("exception_name, status_code, msg", [
        (ValueError, 400, 'None'),
        (User.DoesNotExist, 404, 'User with id:<2> does not exist'),
        (User.PasswordAlreadyUsed, 400, 'The new password should be different from previous 3 used')
    ])
    async def test_update_password_exceptions(self, client, exception_name, status_code, msg):
        request_data = {"current_password": "foglamp", "new_password": "F0gl@mp"}
        uname = 'aj'
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(User.Objects, 'is_user_exists', return_value=2) as patch_user_exists:
                with patch.object(User.Objects, 'update', side_effect=exception_name(msg)) as patch_update:
                    with patch.object(auth._logger, 'warning') as patch_logger_warning:
                        resp = await client.put('/foglamp/user/{}/password'.format(uname), data=json.dumps(request_data))
                        assert status_code == resp.status
                        assert msg == resp.reason
                    patch_logger_warning.assert_called_once_with(msg)
                patch_update.assert_called_once_with(2, {'password': request_data['new_password']})
            patch_user_exists.assert_called_once_with(uname, request_data['current_password'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/user/aj/password')

    async def test_update_password_unknown_exception(self, client):
        request_data = {"current_password": "foglamp", "new_password": "F0gl@mp"}
        uname = 'aj'
        msg = 'Something went wrong'
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(User.Objects, 'is_user_exists', return_value=2) as patch_user_exists:
                with patch.object(User.Objects, 'update', side_effect=Exception(msg)) as patch_update:
                    with patch.object(auth._logger, 'exception') as patch_logger_exception:
                        resp = await client.put('/foglamp/user/{}/password'.format(uname), data=json.dumps(request_data))
                        assert 500 == resp.status
                        assert msg == resp.reason
                    patch_logger_exception.assert_called_once_with(msg)
                patch_update.assert_called_once_with(2, {'password': request_data['new_password']})
            patch_user_exists.assert_called_once_with(uname, request_data['current_password'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/user/aj/password')

    async def test_update_password(self, client):
        request_data = {"current_password": "foglamp", "new_password": "F0gl@mp"}
        ret_val = {'response': 'updated', 'rows_affected': 1}
        uname = 'aj'
        user_id = 2
        msg = "Password has been updated successfully for user id:<{}>".format(user_id)
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(User.Objects, 'is_user_exists', return_value=user_id) as patch_user_exists:
                with patch.object(User.Objects, 'update', return_value=ret_val) as patch_update:
                    with patch.object(auth._logger, 'info') as patch_auth_logger_info:
                        resp = await client.put('/foglamp/user/{}/password'.format(uname), data=json.dumps(request_data))
                        assert 200 == resp.status
                        r = await resp.text()
                        assert {'message': msg} == json.loads(r)
                    patch_auth_logger_info.assert_called_once_with(msg)
                patch_update.assert_called_once_with(user_id, {'password': request_data['new_password']})
            patch_user_exists.assert_called_once_with(uname, request_data['current_password'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/user/aj/password')

    @pytest.mark.parametrize("request_data", [
        'blah',
        '123blah'
    ])
    async def test_delete_bad_user(self, client, mocker, request_data):
        msg = "invalid literal for int() with base 10: '{}'".format(request_data)
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)

        with patch.object(User.Objects, 'get_role_id_by_name', return_value=[{'id': '1'}]) as patch_role_id:
            with patch.object(auth._logger, 'warning') as patch_auth_logger_warn:
                resp = await client.delete('/foglamp/admin/{}/delete'.format(request_data), headers=ADMIN_USER_HEADER)
                assert 400 == resp.status
                assert msg == resp.reason
            patch_auth_logger_warn.assert_called_once_with(msg)
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'DELETE', '/foglamp/admin/{}/delete'.format(request_data))

    async def test_delete_admin_user(self, client, mocker):
        msg = "Super admin user can not be deleted"
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)
        with patch.object(User.Objects, 'get_role_id_by_name', return_value=[{'id': '1'}]) as patch_role_id:
            with patch.object(auth._logger, 'warning') as patch_auth_logger_warn:
                    resp = await client.delete('/foglamp/admin/1/delete', headers=ADMIN_USER_HEADER)
                    assert 406 == resp.status
                    assert msg == resp.reason
            patch_auth_logger_warn.assert_called_once_with(msg)
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'DELETE', '/foglamp/admin/1/delete')

    async def test_delete_own_account(self, client, mocker):
        msg = "You can not delete your own account"
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker, is_admin=False)
        with patch.object(User.Objects, 'get_role_id_by_name', return_value=[{'id': '2'}]) as patch_role_id:
            with patch.object(auth._logger, 'warning') as patch_auth_logger_warn:
                    resp = await client.delete('/foglamp/admin/2/delete', headers=NORMAL_USER_HEADER)
                    assert 400 == resp.status
                    assert msg == resp.reason
            patch_auth_logger_warn.assert_called_once_with(msg)
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=2)
        patch_refresh_token.assert_called_once_with(NORMAL_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(NORMAL_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'DELETE', '/foglamp/admin/2/delete')

    async def test_delete_invalid_user(self, client, mocker):
        ret_val = {"response": "deleted", "rows_affected": 0}
        msg = 'User with id:<2> does not exist'
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)

        with patch.object(User.Objects, 'get_role_id_by_name', return_value=[{'id': '1'}]) as patch_role_id:
            with patch.object(auth._logger, 'warning') as patch_auth_logger_warning:
                    with patch.object(User.Objects, 'delete', return_value=ret_val) as patch_user_delete:
                        resp = await client.delete('/foglamp/admin/2/delete', headers=ADMIN_USER_HEADER)
                        assert 404 == resp.status
                        assert msg == resp.reason
                    patch_user_delete.assert_called_once_with(2)
            patch_auth_logger_warning.assert_called_once_with(msg)
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'DELETE', '/foglamp/admin/2/delete')

    async def test_delete_user(self, client, mocker):
        ret_val = {"response": "deleted", "rows_affected": 1}
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)

        with patch.object(User.Objects, 'get_role_id_by_name', return_value=[{'id': '1'}]) as patch_role_id:
            with patch.object(auth._logger, 'info') as patch_auth_logger_info:
                    with patch.object(User.Objects, 'delete', return_value=ret_val) as patch_user_delete:
                        resp = await client.delete('/foglamp/admin/2/delete', headers=ADMIN_USER_HEADER)
                        assert 200 == resp.status
                        r = await resp.text()
                        assert {'message': 'User has been deleted successfully'} == json.loads(r)
                    patch_user_delete.assert_called_once_with(2)
            patch_auth_logger_info.assert_called_once_with('User with id:<2> has been deleted successfully.')
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'DELETE', '/foglamp/admin/2/delete')

    @pytest.mark.parametrize("exception_name, code, msg", [
        (ValueError, 400, 'None'),
        (User.DoesNotExist, 404, 'User with id:<2> does not exist')
    ])
    async def test_delete_user_exceptions(self, client, mocker, exception_name, code, msg):
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)

        with patch.object(User.Objects, 'get_role_id_by_name', return_value=[{'id': '1'}]) as patch_role_id:
            with patch.object(auth._logger, 'warning') as patch_auth_logger_warn:
                with patch.object(User.Objects, 'delete', side_effect=exception_name(msg)) as patch_user_delete:
                    resp = await client.delete('/foglamp/admin/2/delete', headers=ADMIN_USER_HEADER)
                    assert code == resp.status
                    assert msg == resp.reason
                patch_user_delete.assert_called_once_with(2)
            patch_auth_logger_warn.assert_called_once_with(msg)
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'DELETE', '/foglamp/admin/2/delete')

    async def test_delete_user_unknown_exception(self, client, mocker):
        msg = 'Something went wrong'
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)

        with patch.object(User.Objects, 'get_role_id_by_name', return_value=[{'id': '1'}]) as patch_role_id:
            with patch.object(auth._logger, 'exception') as patch_auth_logger_exc:
                with patch.object(User.Objects, 'delete', side_effect=Exception(msg)) as patch_user_delete:
                    resp = await client.delete('/foglamp/admin/2/delete', headers=ADMIN_USER_HEADER)
                    assert 500 == resp.status
                    assert msg == resp.reason
                patch_user_delete.assert_called_once_with(2)
            patch_auth_logger_exc.assert_called_once_with(msg)
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'DELETE', '/foglamp/admin/2/delete')

    async def test_logout_me(self, client, mocker):
        ret_val = {'response': 'deleted', 'rows_affected': 1}
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)

        with patch.object(auth._logger, 'info') as patch_auth_logger_info:
            with patch.object(User.Objects, 'delete_token', return_value=ret_val) as patch_delete_token:
                resp = await client.put('/foglamp/logout', headers=ADMIN_USER_HEADER)
                assert 200 == resp.status
                r = await resp.text()
                assert {'logout': True} == json.loads(r)
            patch_delete_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_auth_logger_info.assert_called_once_with('User has been logged out successfully')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/logout')

    async def test_logout_me_with_bad_token(self, client, mocker):
        ret_val = {'response': 'deleted', 'rows_affected': 0}
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)

        with patch.object(auth._logger, 'warning') as patch_auth_logger_warn:
            with patch.object(User.Objects, 'delete_token', return_value=ret_val) as patch_delete_token:
                resp = await client.put('/foglamp/logout', headers=ADMIN_USER_HEADER)
                assert 404 == resp.status
            patch_delete_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_auth_logger_warn.assert_called_once_with('Logout requested with bad user token')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/logout')

    async def test_reset_super_admin(self, client, mocker):
        msg = 'Restricted for Super Admin user'
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)

        with patch.object(User.Objects, 'get_role_id_by_name', return_value=[{'id': '1'}]) as patch_role_id:
            with patch.object(auth._logger, 'warning') as patch_logger_warning:
                resp = await client.put('/foglamp/admin/1/reset', data=json.dumps({'role_id': 2}), headers=ADMIN_USER_HEADER)
                assert 406 == resp.status
                assert msg == resp.reason
            patch_logger_warning.assert_called_once_with(msg)
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/admin/1/reset')

    @pytest.mark.parametrize("request_data, msg", [
        ({}, "Nothing to update the user"),
        ({"invalid": 1}, "Nothing to update the user"),
        ({"password": "foglamp"}, "Password must contain at least one digit, one lowercase, one uppercase & one special character and length of minimum 6 characters"),
        ({"password": 1}, "Password must contain at least one digit, one lowercase, one uppercase & one special character and length of minimum 6 characters")
    ])
    async def test_reset_with_bad_data(self, client, mocker, request_data, msg):
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)

        with patch.object(User.Objects, 'get_role_id_by_name', return_value=[{'id': '1'}]) as patch_role_id:
            with patch.object(auth._logger, 'warning') as patch_logger_warning:
                resp = await client.put('/foglamp/admin/2/reset', data=json.dumps(request_data), headers=ADMIN_USER_HEADER)
                assert 400 == resp.status
                assert msg == resp.reason
            patch_logger_warning.assert_called_once_with(msg)
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/admin/2/reset')

    async def test_reset_with_bad_role(self, client, mocker):
        request_data = {"role_id": "blah"}
        msg = "Invalid or bad role id"
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)
        with patch.object(User.Objects, 'get_role_id_by_name', return_value=[{'id': '1'}]) as patch_role_id:
            with patch.object(auth, 'is_valid_role', return_value=False) as patch_role:
                with patch.object(auth._logger, 'warning') as patch_logger_warning:
                    resp = await client.put('/foglamp/admin/2/reset', data=json.dumps(request_data), headers=ADMIN_USER_HEADER)
                    assert 400 == resp.status
                    assert msg == resp.reason
                patch_logger_warning.assert_called_once_with(msg)
            patch_role.assert_called_once_with(request_data['role_id'])
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/admin/2/reset')

    @pytest.mark.parametrize("exception_name, status_code, msg", [
        (ValueError, 400, 'None'),
        (User.DoesNotExist, 404, 'User with id:<2> does not exist'),
        (User.PasswordAlreadyUsed, 400, 'The new password should be different from previous 3 used')
    ])
    async def test_reset_exceptions(self, client, mocker, exception_name, status_code, msg):
        request_data = {'role_id': '2'}
        user_id = 2
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)
        with patch.object(User.Objects, 'get_role_id_by_name', return_value=[{'id': '1'}]) as patch_role_id:
            with patch.object(auth, 'is_valid_role', return_value=True) as patch_role:
                with patch.object(User.Objects, 'update', side_effect=exception_name(msg)) as patch_update:
                    with patch.object(auth._logger, 'warning') as patch_logger_warning:
                        resp = await client.put('/foglamp/admin/{}/reset'.format(user_id), data=json.dumps(request_data), headers=ADMIN_USER_HEADER)
                        assert status_code == resp.status
                        assert msg == resp.reason
                    patch_logger_warning.assert_called_once_with(msg)
                patch_update.assert_called_once_with(str(user_id), request_data)
            patch_role.assert_called_once_with(request_data['role_id'])
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/admin/2/reset')

    async def test_reset_unknown_exception(self, client, mocker):
        request_data = {'role_id': '2'}
        user_id = 2
        msg = 'Something went wrong'
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)
        with patch.object(User.Objects, 'get_role_id_by_name', return_value=[{'id': '1'}]) as patch_role_id:
            with patch.object(auth, 'is_valid_role', return_value=True) as patch_role:
                with patch.object(User.Objects, 'update', side_effect=Exception(msg)) as patch_update:
                    with patch.object(auth._logger, 'exception') as patch_logger_exception:
                        resp = await client.put('/foglamp/admin/{}/reset'.format(user_id), data=json.dumps(request_data), headers=ADMIN_USER_HEADER)
                        assert 500 == resp.status
                        assert msg == resp.reason
                    patch_logger_exception.assert_called_once_with(msg)
                patch_update.assert_called_once_with(str(user_id), request_data)
            patch_role.assert_called_once_with(request_data['role_id'])
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/admin/2/reset')

    async def test_reset_role_and_password(self, client, mocker):
        request_data = {'role_id': '2', 'password': 'Test@123'}
        user_id = 2
        msg = 'User with id:<{}> has been updated successfully'.format(user_id)
        ret_val = {'response': 'updated', 'rows_affected': 1}
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)
        with patch.object(User.Objects, 'get_role_id_by_name', return_value=[{'id': '1'}]) as patch_role_id:
            with patch.object(auth, 'is_valid_role', return_value=True) as patch_role:
                with patch.object(User.Objects, 'update', return_value=ret_val) as patch_update:
                    with patch.object(auth._logger, 'info') as patch_auth_logger_info:
                        resp = await client.put('/foglamp/admin/{}/reset'.format(user_id), data=json.dumps(request_data), headers=ADMIN_USER_HEADER)
                        assert 200 == resp.status
                        r = await resp.text()
                        assert {'message': msg} == json.loads(r)
                    patch_auth_logger_info.assert_called_once_with(msg)
                patch_update.assert_called_once_with(str(user_id), request_data)
            patch_role.assert_called_once_with(request_data['role_id'])
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/admin/2/reset')
