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

HEADERS = {'content-type': 'application/json', 'Authorization': 'token'}


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

    def auth_token_fixture(self, mocker):
        user = {'id': '1', 'uname': 'admin', 'role_id': '1'}
        patch_logger_info = mocker.patch.object(middleware._logger, 'info')
        patch_validate_token = mocker.patch.object(User.Objects, 'validate_token', return_value=1)
        patch_refresh_token = mocker.patch.object(User.Objects, 'refresh_token_expiry', return_value=None)
        patch_user_get = mocker.patch.object(User.Objects, 'get', return_value=user)

        return patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get

    async def test_get_roles(self, client, mocker):
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)
        with patch.object(User.Objects, 'get_roles', return_value=[]) as patch_user_role:
            resp = await client.get('/foglamp/user/role', headers=HEADERS)
            assert 200 == resp.status
            r = await resp.text()
            assert {'roles': []} == json.loads(r)
        patch_user_role.assert_called_once_with()
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with('token')
        patch_validate_token.assert_called_once_with('token')
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'GET', '/foglamp/user/role')

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
            resp = await client.put('/foglamp/user/2', data=json.dumps(request_data), headers=HEADERS)
            assert 400 == resp.status
            assert warn_msg == resp.reason
        patch_logger_warning.assert_called_once_with(warn_msg)
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with('token')
        patch_validate_token.assert_called_once_with('token')
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/user/2')

    @pytest.mark.parametrize("request_data", [
        {'role_id': -3},
        {'role_id': 'blah'},
    ])
    async def test_update_user_with_bad_role(self, client, mocker, request_data):
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)
        with patch.object(auth, 'is_valid_role', return_value=False) as patch_role:
            with patch.object(auth._logger, 'warning') as patch_logger_warning:
                resp = await client.put('/foglamp/user/2', data=json.dumps(request_data), headers=HEADERS)
                assert 400 == resp.status
                assert 'Invalid or bad role id' == resp.reason
            patch_logger_warning.assert_called_once_with('Update user requested with bad role id')
        patch_role.assert_called_once_with(request_data['role_id'])
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with('token')
        patch_validate_token.assert_called_once_with('token')
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/user/2')

    @pytest.mark.parametrize("request_data", [
        {'password': 1},
        {'password': "blah"}
    ])
    async def test_update_bad_password(self, client, mocker, request_data):
        msg = 'Password must contain at least one digit, one lowercase, one uppercase & one special character and length of minimum 6 characters'
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)
        with patch.object(auth._logger, 'warning') as patch_logger_warning:
            resp = await client.put('/foglamp/user/2', data=json.dumps(request_data), headers=HEADERS)
            assert 400 == resp.status
            assert msg == resp.reason
        patch_logger_warning.assert_called_once_with(msg)
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with('token')
        patch_validate_token.assert_called_once_with('token')
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/user/2')

    async def test_update_user(self, client, mocker):
        ret_val = {'response': 'updated', 'rows_affected': 1}
        user_id = 2
        msg = 'User with id:<{}> has been updated successfully'.format(user_id)
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)
        with patch.object(auth, 'check_authorization', return_value=True) as patch_check_authorization:
            with patch.object(User.Objects, 'update', return_value=ret_val) as patch_user_update:
                with patch.object(auth._logger, 'info') as patch_auth_logger_info:
                    resp = await client.put('/foglamp/user/{}'.format(user_id),
                                            data=json.dumps({'password': 'F0gl@mp'}), headers=HEADERS)
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
        patch_refresh_token.assert_called_once_with('token')
        patch_validate_token.assert_called_once_with('token')
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
                    resp = await client.put('/foglamp/user/{}'.format(user_id), data=json.dumps({'password': 'F0gl@mp'}), headers=HEADERS)
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
        patch_refresh_token.assert_called_once_with('token')
        patch_validate_token.assert_called_once_with('token')
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/user/{}'.format(user_id))

    async def test_update_user_exception(self, client, mocker):
        user_id = 2
        msg = 'Something went wrong'
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)

        with patch.object(auth, 'check_authorization', return_value=True) as patch_check_authorization:
            with patch.object(User.Objects, 'update', side_effect=Exception(msg)) as patch_user_update:
                with patch.object(auth._logger, 'exception') as patch_auth_logger_warn:
                    resp = await client.put('/foglamp/user/{}'.format(user_id),
                                            data=json.dumps({'password': 'F0gl@mp'}), headers=HEADERS)
                    assert 500 == resp.status
                    assert msg == resp.reason
                patch_user_update.assert_called_once_with(str(user_id), {'password': 'F0gl@mp'})
                patch_auth_logger_warn.assert_called_once_with(msg)
        # TODO: Request patch VERB and Url
        args, kwargs = patch_check_authorization.call_args
        assert str(user_id) == args[1]
        assert 'update' == args[2]
        # patch_check_authorization.assert_called_once_with()
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with('token')
        patch_validate_token.assert_called_once_with('token')
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/user/{}'.format(user_id))

    async def test_logout_me(self, client, mocker):
        ret_val = {'response': 'deleted', 'rows_affected': 1}
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)

        with patch.object(auth._logger, 'info') as patch_auth_logger_info:
            with patch.object(User.Objects, 'delete_token', return_value=ret_val) as patch_delete_token:
                resp = await client.put('/foglamp/logout', headers=HEADERS)
                assert 200 == resp.status
                r = await resp.text()
                assert {'logout': True} == json.loads(r)
            patch_delete_token.assert_called_once_with('token')
        patch_auth_logger_info.assert_called_once_with('User has been logged out successfully')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with('token')
        patch_validate_token.assert_called_once_with('token')
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/logout')

    async def test_logout_me_with_bad_token(self, client, mocker):
        ret_val = {'response': 'deleted', 'rows_affected': 0}
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = self.auth_token_fixture(mocker)

        with patch.object(auth._logger, 'warning') as patch_auth_logger_warn:
            with patch.object(User.Objects, 'delete_token', return_value=ret_val) as patch_delete_token:
                resp = await client.put('/foglamp/logout', headers=HEADERS)
                assert 404 == resp.status
            patch_delete_token.assert_called_once_with('token')
        patch_auth_logger_warn.assert_called_once_with('Logout requested with bad user token')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with('token')
        patch_validate_token.assert_called_once_with('token')
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/logout')

    # TODO: create, update, delete, logout
