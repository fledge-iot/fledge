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


FORBIDDEN = 'Forbidden'
WARN_MSG = 'Resource you were trying to reach is absolutely forbidden for some reason'


@pytest.allure.feature("unit")
@pytest.allure.story("api", "auth-optional")
class TestAuthOptional:

    @pytest.fixture
    def client(self, loop, test_server, test_client):
        app = web.Application(loop=loop,  middlewares=[middleware.optional_auth_middleware])
        # fill the routes table
        routes.setup(app)
        server = loop.run_until_complete(test_server(app))
        server.start_server(loop=loop)
        client = loop.run_until_complete(test_client(server))
        return client

    async def test_get_roles(self, client):
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(User.Objects, 'get_roles', return_value=[]) as patch_user_obj:
                resp = await client.get('/foglamp/user/role')
                assert 200 == resp.status
                r = await resp.text()
                assert {'roles': []} == json.loads(r)
            patch_user_obj.assert_called_once_with()
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'GET', '/foglamp/user/role')

    @pytest.mark.parametrize("ret_val, exp_result", [
        ([], []),
        ([{'uname': 'admin', 'role_id': '1', 'id': '1'}, {'uname': 'user', 'role_id': '2', 'id': '2'}],
         [{"userId": "1", "userName": "admin", "roleId": "1"}, {"userId": "2", "userName": "user", "roleId": "2"}])
    ])
    async def test_get_all_users(self, client, ret_val, exp_result):
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(User.Objects, 'all', return_value=ret_val) as patch_user_obj:
                resp = await client.get('/foglamp/user')
                assert 200 == resp.status
                r = await resp.text()
                assert {'users': exp_result} == json.loads(r)
            patch_user_obj.assert_called_once_with()
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'GET', '/foglamp/user')

    @pytest.mark.parametrize("request_params, exp_result, arg1, arg2", [
        ('?id=1', {'uname': 'admin', 'role_id': '1', 'id': '1'}, 1, None),
        ('?username=admin', {'uname': 'admin', 'role_id': '1', 'id': '1'},  None, 'admin'),
        ('?id=1&username=admin', {'uname': 'admin', 'role_id': '1', 'id': '1'}, 1, 'admin'),
        ('?id=1&user=admin', {'uname': 'admin', 'role_id': '1', 'id': '1'}, 1, None),
        ('?uid=1&username=admin', {'uname': 'admin', 'role_id': '1', 'id': '1'}, None, 'admin'),
    ])
    async def test_get_user_by_param(self, client, request_params, exp_result, arg1, arg2):
        result = {}
        result.update(exp_result)
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(User.Objects, 'get', return_value=result) as patch_user_obj:
                resp = await client.get('/foglamp/user{}'.format(request_params))
                assert 200 == resp.status
                r = await resp.text()
                actual = json.loads(r)
                assert actual['userId'] == exp_result['id']
                assert actual['roleId'] == exp_result['role_id']
                assert actual['userName'] == exp_result['uname']
            patch_user_obj.assert_called_once_with(arg1, arg2)
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'GET', '/foglamp/user')

    @pytest.mark.parametrize("request_params, error_msg, arg1, arg2", [
        ('?id=10', 'User with id:<10> does not exist', 10, None),
        ('?username=blah', 'User with name:<blah> does not exist', None, 'blah')
    ])
    async def test_get_user_exception_by_param(self, client, request_params, error_msg, arg1, arg2):
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(User.Objects, 'get', side_effect=User.DoesNotExist(error_msg)) as patch_user_get:
                with patch.object(auth._logger, 'warning') as patch_logger:
                    resp = await client.get('/foglamp/user{}'.format(request_params))
                    assert 404 == resp.status
                    assert error_msg == resp.reason
                patch_logger.assert_called_once_with(error_msg)
            patch_user_get.assert_called_once_with(arg1, arg2)
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'GET', '/foglamp/user')

    @pytest.mark.parametrize("request_params", ['?id=0', '?id=blah', '?id=-1'])
    async def test_get_bad_user_id_param_exception(self, client, request_params):
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth._logger, 'warning') as patch_logger:
                resp = await client.get('/foglamp/user{}'.format(request_params))
                assert 400 == resp.status
                assert 'Bad user id' == resp.reason
            patch_logger.assert_called_once_with('Get user requested with bad user id')
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'GET', '/foglamp/user')

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
    async def test_bad_login(self, client, request_data):
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth._logger, 'warning') as patch_logger:
                resp = await client.post('/foglamp/login', data=json.dumps(request_data))
                assert 400 == resp.status
                assert 'Username or password is missing' == resp.reason
            patch_logger.assert_called_once_with('Username and password are required to login')
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/foglamp/login')

    @pytest.mark.parametrize("request_data, status_code, exception_name, msg", [
        ({"username": "blah", "password": "blah"}, 404, User.DoesNotExist, 'User does not exist'),
        ({"username": "admin", "password": "blah"}, 404, User.PasswordDoesNotMatch, 'Username or Password do not match'),
        ({"username": "admin", "password": 123}, 404, User.PasswordDoesNotMatch, 'Username or Password do not match'),
        ({"username": 1, "password": 1}, 404, ValueError, 'Username should be a valid string'),
        ({"username": "user", "password": "foglamp"}, 401, User.PasswordExpired, 'Your password has been expired. Please set your password again')
    ])
    async def test_login_exception(self, client, request_data, status_code, exception_name, msg):
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(User.Objects, 'login', side_effect=exception_name(msg)) as patch_user_login:
                with patch.object(User.Objects, 'delete_user_tokens', return_value=[]) as patch_delete_token:
                    with patch.object(auth._logger, 'warning') as patch_logger:
                        resp = await client.post('/foglamp/login', data=json.dumps(request_data))
                        assert status_code == resp.status
                        assert msg == resp.reason
                    patch_logger.assert_called_once_with(msg)
                if status_code == 401:
                    patch_delete_token.assert_called_once_with(msg)
            # TODO: host arg patch transport.request.extra_info
            args, kwargs = patch_user_login.call_args
            assert str(request_data['username']) == args[0]
            assert request_data['password'] == args[1]
            # patch_user_login.assert_called_once_with()
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/foglamp/login')

    @pytest.mark.parametrize("request_data, ret_val", [
        ({"username": "admin", "password": "foglamp"}, (1, "token1", True)),
        ({"username": "user", "password": "foglamp"}, (2, "token2", False))
    ])
    async def test_login(self, client, request_data, ret_val):
        async def async_mock():
            return ret_val

        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(User.Objects, 'login', return_value=async_mock()) as patch_user_login:
                with patch.object(auth._logger, 'info') as patch_logger:
                    resp = await client.post('/foglamp/login', data=json.dumps(request_data))
                    assert 200 == resp.status
                    r = await resp.text()
                    actual = json.loads(r)
                    assert ret_val[0] == actual['uid']
                    assert ret_val[1] == actual['token']
                    assert ret_val[2] == actual['admin']
                patch_logger.assert_called_once_with('User with username:<{}> has been logged in successfully'.format(request_data['username']))
            # TODO: host arg patch transport.request.extra_info
            args, kwargs = patch_user_login.call_args
            assert request_data['username'] == args[0]
            assert request_data['password'] == args[1]
            # patch_user_login.assert_called_once_with()
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/foglamp/login')

    async def test_logout(self, client):
        ret_val = {'response': 'deleted', 'rows_affected': 1}
        user_id = 1
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth, 'check_authorization', return_value=True) as patch_check_authorization:
                with patch.object(User.Objects, 'delete_user_tokens', return_value=ret_val) as patch_user_logout:
                    with patch.object(auth._logger, 'info') as patch_logger:
                        resp = await client.put('/foglamp/{}/logout'.format(user_id))
                        assert 200 == resp.status
                        r = await resp.text()
                        assert {"logout": True} == json.loads(r)
                    patch_logger.assert_called_once_with('User with id:<{}> has been logged out successfully'.format(user_id))
                patch_user_logout.assert_called_once_with(str(user_id))
            # TODO: Request patch VERB and Url
            args, kwargs = patch_check_authorization.call_args
            assert str(user_id) == args[1]
            assert 'logout' == args[2]
            # patch_check_authorization.assert_called_once_with('<Request PUT /foglamp/1/logout >', '1', 'logout')
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/{}/logout'.format(user_id))

    async def test_logout_with_bad_user(self, client):
        ret_val = {'response': 'deleted', 'rows_affected': 0}
        user_id = 111
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth, 'check_authorization', return_value=True) as patch_check_authorization:
                with patch.object(User.Objects, 'delete_user_tokens', return_value=ret_val) as patch_user_logout:
                    with patch.object(auth._logger, 'warning') as patch_logger:
                        resp = await client.put('/foglamp/{}/logout'.format(user_id))
                        assert 404 == resp.status
                        assert 'Not Found' == resp.reason
                    patch_logger.assert_called_once_with('Logout requested with bad user')
                patch_user_logout.assert_called_once_with(str(user_id))
            # TODO: Request patch VERB and Url
            args, kwargs = patch_check_authorization.call_args
            assert str(user_id) == args[1]
            assert 'logout' == args[2]
            # patch_check_authorization.assert_called_once_with('<Request PUT /foglamp/1/logout >', '1', 'logout')
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/111/logout')

    async def test_update_password(self, client):
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth._logger, 'warning') as patch_logger_warning:
                resp = await client.put('/foglamp/user/admin/password')
                assert 403 == resp.status
                assert FORBIDDEN == resp.reason
            patch_logger_warning.assert_called_once_with(WARN_MSG)
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/user/admin/password')

    async def test_update_user(self, client):
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth._logger, 'warning') as patch_logger_warning:
                resp = await client.put('/foglamp/user/1')
                assert 403 == resp.status
                assert FORBIDDEN == resp.reason
            patch_logger_warning.assert_called_once_with(WARN_MSG)
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/user/1')

    async def test_delete_user(self, client):
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth._logger, 'warning') as patch_auth_logger_warn:
                resp = await client.delete('/foglamp/admin/1/delete')
                assert 403 == resp.status
                assert FORBIDDEN == resp.reason
            patch_auth_logger_warn.assert_called_once_with(WARN_MSG)
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'DELETE', '/foglamp/admin/1/delete')

    async def test_create_user(self, client):
        request_data = {"username": "ajtest", "password": "F0gl@mp"}
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth._logger, 'warning') as patch_logger_warning:
                resp = await client.post('/foglamp/admin/user', data=json.dumps(request_data))
                assert 403 == resp.status
                assert FORBIDDEN == resp.reason
            patch_logger_warning.assert_called_once_with(WARN_MSG)
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/foglamp/admin/user')

    async def test_reset(self, client):
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth._logger, 'warning') as patch_logger_warning:
                resp = await client.put('/foglamp/admin/2/reset')
                assert 403 == resp.status
                assert FORBIDDEN == resp.reason
            patch_logger_warning.assert_called_once_with(WARN_MSG)
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/admin/2/reset')

    @pytest.mark.parametrize("role_id, expected", [
        (1, True),
        (2, True),
        (3, False)
    ])
    def test_valid_role(self, role_id, expected):
        ret_val = [{"id": "1", "description": "for the users having all CRUD privileges including other admin users", "name": "admin"}, {"id": "2", "description": "all CRUD operations and self profile management", "name": "user"}]
        with patch.object(User.Objects, 'get_roles', return_value=ret_val) as patch_get_roles:
            actual = auth.is_valid_role(role_id)
            assert expected is actual
        patch_get_roles.assert_called_once_with()
