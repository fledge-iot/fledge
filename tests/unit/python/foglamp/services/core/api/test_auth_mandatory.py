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
                resp = await client.post('/foglamp/user', data=json.dumps(request_data), headers=ADMIN_USER_HEADER)
                assert 400 == resp.status
                assert 'Username or password is missing' == resp.reason
                patch_logger_warn.assert_called_once_with('Username and password are required to create user')
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/foglamp/user')

    @pytest.mark.parametrize("request_data", [
        {"username": "blah", "password": 1},
        {"username": "blah", "password": "blah"}
    ])
    async def test_create_user_bad_password(self, client, mocker, request_data):
        msg = 'Password must contain at least one digit, one lowercase, one uppercase & one special character and length of minimum 6 characters'
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)

        with patch.object(User.Objects, 'get_role_id_by_name', return_value=[{'id': '1'}]) as patch_role_id:
            with patch.object(auth._logger, 'warning') as patch_logger_warning:
                resp = await client.post('/foglamp/user', data=json.dumps(request_data), headers=ADMIN_USER_HEADER)
                assert 400 == resp.status
                assert msg == resp.reason
            patch_logger_warning.assert_called_once_with(msg)
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/foglamp/user')

    @pytest.mark.parametrize("request_data", [
        {"username": "aj", "password": "F0gl@mp", "role_id": -3},
        {"username": "aj", "password": "F0gl@mp", "role_id": "blah"}
    ])
    async def test_create_user_with_bad_role(self, client, mocker, request_data):
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)

        with patch.object(User.Objects, 'get_role_id_by_name', return_value=[{'id': '1'}]) as patch_role_id:
            with patch.object(auth, 'is_valid_role', return_value=False) as patch_role:
                with patch.object(auth._logger, 'warning') as patch_logger_warning:
                    resp = await client.post('/foglamp/user', data=json.dumps(request_data), headers=ADMIN_USER_HEADER)
                    assert 400 == resp.status
                    assert 'Invalid or bad role id' == resp.reason
                patch_logger_warning.assert_called_once_with('Create user requested with bad role id')
            patch_role.assert_called_once_with(request_data['role_id'])
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/foglamp/user')

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
                    resp = await client.post('/foglamp/user', data=json.dumps(request_data), headers=ADMIN_USER_HEADER)
                    assert 400 == resp.status
                    assert msg == resp.reason
                patch_logger_warning.assert_called_once_with(msg)
            patch_role.assert_called_once_with(2)
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/foglamp/user')

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
                                    resp = await client.post('/foglamp/user', data=json.dumps(request_data), headers=ADMIN_USER_HEADER)
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
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/foglamp/user')

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
                                    with patch.object(auth._logger, 'info') as patch_audit_logger_info:
                                        resp = await client.post('/foglamp/user', data=json.dumps(request_data), headers=ADMIN_USER_HEADER)
                                        assert 200 == resp.status
                                        r = await resp.text()
                                        actual = json.loads(r)
                                        assert msg == actual['message']
                                        assert expected['id'] == actual['user']['userId']
                                        assert expected['uname'] == actual['user']['userName']
                                        assert expected['role_id'] == actual['user']['roleId']
                                    patch_audit_logger_info.assert_called_once_with(msg)
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
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/foglamp/user')

    async def test_create_user_exception(self, client):
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
                                        resp = await client.post('/foglamp/user', data=json.dumps(request_data), headers=ADMIN_USER_HEADER)
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
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/foglamp/user')

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
                                        resp = await client.post('/foglamp/user', data=json.dumps(request_data), headers=ADMIN_USER_HEADER)
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
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/foglamp/user')

    @pytest.mark.parametrize("request_data", [
        {},
        {"invalid": 1},
        {"role": 1},
        {"pwd": "blah"},
        {"role": 1, "pwd": 12}
    ])
    async def test_update_user_with_bad_data(self, client, mocker, request_data):
        warn_msg = 'Nothing to update the user'
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)
        with patch.object(auth._logger, 'warning') as patch_logger_warning:
            resp = await client.put('/foglamp/user/2', data=json.dumps(request_data), headers=ADMIN_USER_HEADER)
            assert 400 == resp.status
            assert warn_msg == resp.reason
        patch_logger_warning.assert_called_once_with(warn_msg)
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/user/2')

    @pytest.mark.parametrize("request_data", [
        {'role_id': -3},
        {'role_id': 'blah'},
    ])
    async def test_update_user_with_bad_role(self, client, mocker, request_data):
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)
        with patch.object(auth, 'is_valid_role', return_value=False) as patch_role:
            with patch.object(auth._logger, 'warning') as patch_logger_warning:
                resp = await client.put('/foglamp/user/2', data=json.dumps(request_data), headers=ADMIN_USER_HEADER)
                assert 400 == resp.status
                assert 'Invalid or bad role id' == resp.reason
            patch_logger_warning.assert_called_once_with('Update user requested with bad role id')
        patch_role.assert_called_once_with(request_data['role_id'])
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/user/2')

    @pytest.mark.parametrize("request_data", [
        {'role_id': 1},
        {'role_id': 2}
    ])
    async def test_update_role_with_normal_user(self, client, mocker, request_data):
        msg = 'Only admin can update the role for a user'
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker, is_admin=False)

        with patch.object(auth, 'is_valid_role', return_value=True) as patch_role:
            with patch.object(auth, 'has_admin_permissions', return_value=False) as patch_admin_permission:
                with patch.object(auth._logger, 'warning') as patch_logger_warning:
                    resp = await client.put('/foglamp/user/2', data=json.dumps(request_data), headers=NORMAL_USER_HEADER)
                    assert 401 == resp.status
                    assert msg == resp.reason
                patch_logger_warning.assert_called_once_with(msg)
            # TODO: Request patch VERB and Url
            # patch_admin_permission.assert_called_once_with()
        patch_role.assert_called_once_with(request_data['role_id'])
        patch_user_get.assert_called_once_with(uid=2)
        patch_refresh_token.assert_called_once_with(NORMAL_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(NORMAL_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/user/2')

    async def test_update_admin_role(self, client, mocker):
        msg = 'Role updation restricted for Super Admin user'
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)

        with patch.object(auth, 'is_valid_role', return_value=True) as patch_role:
            with patch.object(auth, 'has_admin_permissions', return_value=True) as patch_admin_permission:
                with patch.object(auth._logger, 'warning') as patch_logger_warning:
                    resp = await client.put('/foglamp/user/1', data=json.dumps({'role_id': 2}), headers=ADMIN_USER_HEADER)
                    assert 406 == resp.status
                    assert msg == resp.reason
                patch_logger_warning.assert_called_once_with(msg)
            # TODO: Request patch VERB and Url
            # patch_admin_permission.assert_called_once_with()
        patch_role.assert_called_once_with(2)
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/user/1')

    async def test_update_role(self, client, mocker):
        request_data = {'role_id': 2}
        ret_val = {'response': 'updated', 'rows_affected': 1}
        user_id = 2
        msg = 'User with id:<{}> has been updated successfully'.format(user_id)
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)

        with patch.object(auth, 'is_valid_role', return_value=True) as patch_role:
            with patch.object(auth, 'has_admin_permissions', return_value=True) as patch_admin_permission:
                with patch.object(auth, 'check_authorization', return_value=True) as patch_check_authorization:
                    with patch.object(User.Objects, 'update', return_value=ret_val) as patch_user_update:
                        with patch.object(auth._logger, 'info') as patch_auth_logger_info:
                            resp = await client.put('/foglamp/user/{}'.format(user_id), data=json.dumps(request_data), headers=ADMIN_USER_HEADER)
                            assert 200 == resp.status
                            r = await resp.text()
                            assert {'message': msg} == json.loads(r)
                        patch_auth_logger_info.assert_called_once_with(msg)
                    patch_user_update.assert_called_once_with(str(user_id), request_data)
                # patch_check_authorization.assert_called_once_with()
                # TODO: Request patch VERB and Url
                args, kwargs = patch_check_authorization.call_args
                assert str(user_id) == args[1]
                assert 'update' == args[2]
            # TODO: Request patch VERB and Url
            # patch_admin_permission.assert_called_once_with()
        patch_role.assert_called_once_with(request_data['role_id'])
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/user/2')

    @pytest.mark.parametrize("request_data", [
        {'password': 1},
        {'password': "blah"}
    ])
    async def test_update_bad_password(self, client, mocker, request_data):
        msg = 'Password must contain at least one digit, one lowercase, one uppercase & one special character and length of minimum 6 characters'
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)
        with patch.object(auth._logger, 'warning') as patch_logger_warning:
            resp = await client.put('/foglamp/user/2', data=json.dumps(request_data), headers=ADMIN_USER_HEADER)
            assert 400 == resp.status
            assert msg == resp.reason
        patch_logger_warning.assert_called_once_with(msg)
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/user/2')

    async def test_update_user(self, client, mocker):
        ret_val = {'response': 'updated', 'rows_affected': 1}
        user_id = 2
        msg = 'User with id:<{}> has been updated successfully'.format(user_id)
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)
        with patch.object(auth, 'check_authorization', return_value=True) as patch_check_authorization:
            with patch.object(User.Objects, 'update', return_value=ret_val) as patch_user_update:
                with patch.object(auth._logger, 'info') as patch_auth_logger_info:
                    resp = await client.put('/foglamp/user/{}'.format(user_id), data=json.dumps({'password': 'F0gl@mp'}), headers=ADMIN_USER_HEADER)
                    assert 200 == resp.status
                    r = await resp.text()
                    assert {'message': msg} == json.loads(r)
                patch_user_update.assert_called_once_with(str(user_id), {'password': 'F0gl@mp'})
            patch_auth_logger_info.assert_called_once_with(msg)
        # TODO: Request patch VERB and Url
        args, kwargs = patch_check_authorization.call_args
        assert str(user_id) == args[1]
        assert 'update' == args[2]
        # patch_check_authorization.assert_called_once_with()
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/user/{}'.format(user_id))

    @pytest.mark.parametrize("exception_name, code, msg", [
        (ValueError, 400, 'None'),
        (User.DoesNotExist, 404, 'User with id:<2> does not exist')
    ])
    async def test_update_user_custom_exception(self, client, mocker, exception_name, code, msg):
        user_id = 2
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)
        with patch.object(auth, 'check_authorization', return_value=True) as patch_check_authorization:
            with patch.object(User.Objects, 'update', side_effect=exception_name(msg)) as patch_user_update:
                with patch.object(auth._logger, 'warning') as patch_auth_logger_warn:
                    resp = await client.put('/foglamp/user/{}'.format(user_id), data=json.dumps({'password': 'F0gl@mp'}), headers=ADMIN_USER_HEADER)
                    assert code == resp.status
                    assert msg == resp.reason
                patch_user_update.assert_called_once_with(str(user_id), {'password': 'F0gl@mp'})
                patch_auth_logger_warn.assert_called_once_with(msg)
        # TODO: Request patch VERB and Url
        args, kwargs = patch_check_authorization.call_args
        assert str(user_id) == args[1]
        assert 'update' == args[2]
        # patch_check_authorization.assert_called_once_with()
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/user/{}'.format(user_id))

    async def test_update_user_exception(self, client, mocker):
        user_id = 2
        msg = 'Something went wrong'
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)

        with patch.object(auth, 'check_authorization', return_value=True) as patch_check_authorization:
            with patch.object(User.Objects, 'update', side_effect=Exception(msg)) as patch_user_update:
                with patch.object(auth._logger, 'exception') as patch_auth_logger_warn:
                    resp = await client.put('/foglamp/user/{}'.format(user_id), data=json.dumps({'password': 'F0gl@mp'}), headers=ADMIN_USER_HEADER)
                    assert 500 == resp.status
                    assert msg == resp.reason
                patch_auth_logger_warn.assert_called_once_with(msg)
            patch_user_update.assert_called_once_with(str(user_id), {'password': 'F0gl@mp'})
        # TODO: Request patch VERB and Url
        args, kwargs = patch_check_authorization.call_args
        assert str(user_id) == args[1]
        assert 'update' == args[2]
        # patch_check_authorization.assert_called_once_with()
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/user/{}'.format(user_id))

    @pytest.mark.parametrize("request_data", [
        'blah',
        '123blah'
    ])
    async def test_delete_bad_user(self, client, mocker, request_data):
        msg = "invalid literal for int() with base 10: '{}'".format(request_data)
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)

        with patch.object(User.Objects, 'get_role_id_by_name', return_value=[{'id': '1'}]) as patch_role_id:
            with patch.object(auth._logger, 'warning') as patch_auth_logger_warn:
                resp = await client.delete('/foglamp/user/{}'.format(request_data), headers=ADMIN_USER_HEADER)
                assert 400 == resp.status
                assert msg == resp.reason
            patch_auth_logger_warn.assert_called_once_with(msg)
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'DELETE', '/foglamp/user/{}'.format(request_data))

    async def test_delete_admin_user(self, client, mocker):
        msg = "Super admin user can not be deleted"
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)
        with patch.object(User.Objects, 'get_role_id_by_name', return_value=[{'id': '1'}]) as patch_role_id:
            with patch.object(auth._logger, 'warning') as patch_auth_logger_warn:
                    resp = await client.delete('/foglamp/user/1', headers=ADMIN_USER_HEADER)
                    assert 406 == resp.status
                    assert msg == resp.reason
            patch_auth_logger_warn.assert_called_once_with(msg)
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'DELETE', '/foglamp/user/1')

    async def test_delete_own_account(self, client, mocker):
        msg = "You can not delete your own account"
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker, is_admin=False)
        with patch.object(User.Objects, 'get_role_id_by_name', return_value=[{'id': '2'}]) as patch_role_id:
            with patch.object(auth._logger, 'warning') as patch_auth_logger_warn:
                    resp = await client.delete('/foglamp/user/2', headers=NORMAL_USER_HEADER)
                    assert 400 == resp.status
                    assert msg == resp.reason
            patch_auth_logger_warn.assert_called_once_with(msg)
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=2)
        patch_refresh_token.assert_called_once_with(NORMAL_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(NORMAL_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'DELETE', '/foglamp/user/2')

    async def test_delete_user(self, client, mocker):
        ret_val = {"response": "deleted", "rows_affected": 1}
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)

        with patch.object(User.Objects, 'get_role_id_by_name', return_value=[{'id': '1'}]) as patch_role_id:
            with patch.object(auth._logger, 'info') as patch_auth_logger_info:
                    with patch.object(User.Objects, 'delete', return_value=ret_val) as patch_user_delete:
                        resp = await client.delete('/foglamp/user/2', headers=ADMIN_USER_HEADER)
                        assert 200 == resp.status
                        r = await resp.text()
                        assert {'message': 'User has been deleted successfully'} == json.loads(r)
                    patch_user_delete.assert_called_once_with(2)
            patch_auth_logger_info.assert_called_once_with('User with id:<2> has been deleted successfully.')
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'DELETE', '/foglamp/user/2')

    @pytest.mark.parametrize("exception_name, code, msg", [
        (ValueError, 400, 'None'),
        (User.DoesNotExist, 404, 'User with id:<2> does not exist')
    ])
    async def test_delete_user_custom_exception(self, client, mocker, exception_name, code, msg):
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)

        with patch.object(User.Objects, 'get_role_id_by_name', return_value=[{'id': '1'}]) as patch_role_id:
            with patch.object(auth._logger, 'warning') as patch_auth_logger_warn:
                with patch.object(User.Objects, 'delete', side_effect=exception_name(msg)) as patch_user_delete:
                    resp = await client.delete('/foglamp/user/2', headers=ADMIN_USER_HEADER)
                    assert code == resp.status
                    assert msg == resp.reason
                patch_user_delete.assert_called_once_with(2)
            patch_auth_logger_warn.assert_called_once_with(msg)
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'DELETE', '/foglamp/user/2')

    async def test_delete_user_exception(self, client, mocker):
        msg = 'Something went wrong'
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)

        with patch.object(User.Objects, 'get_role_id_by_name', return_value=[{'id': '1'}]) as patch_role_id:
            with patch.object(auth._logger, 'exception') as patch_auth_logger_exc:
                with patch.object(User.Objects, 'delete', side_effect=Exception(msg)) as patch_user_delete:
                    resp = await client.delete('/foglamp/user/2', headers=ADMIN_USER_HEADER)
                    assert 500 == resp.status
                    assert msg == resp.reason
                patch_user_delete.assert_called_once_with(2)
            patch_auth_logger_exc.assert_called_once_with(msg)
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'DELETE', '/foglamp/user/2')

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
