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

    @pytest.mark.parametrize("request_data, exception_name, msg", [
        ({"username": "blah", "password": "blah"}, User.DoesNotExist, 'User does not exist'),
        ({"username": "admin", "password": "blah"}, User.PasswordDoesNotMatch, 'Username or Password do not match'),
        ({"username": "admin", "password": 123}, User.PasswordDoesNotMatch, 'Username or Password do not match'),
        ({"username": 1, "password": 1}, ValueError, 'Username should be a valid string')
    ])
    async def test_login_exception(self, client, request_data, exception_name, msg):
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(User.Objects, 'login', side_effect=exception_name(msg)) as patch_user_login:
                with patch.object(auth._logger, 'warning') as patch_logger:
                    resp = await client.post('/foglamp/login', data=json.dumps(request_data))
                    assert 400 == resp.status
                patch_logger.assert_called_once_with(msg)
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
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(User.Objects, 'login', return_value=ret_val) as patch_user_login:
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

    async def test_update_admin_user_without_authentication(self, client):
        warn_msg = 'Super admin user can not be updated'
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth._logger, 'warning') as patch_logger_warning:
                resp = await client.put('/foglamp/user/1')
                assert 406 == resp.status
                assert warn_msg == resp.reason
            patch_logger_warning.assert_called_once_with(warn_msg)
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/user/1')

    @pytest.mark.parametrize("request_data", [
        {},
        {"invalid": 1},
        {"role": 1},
        {"pwd": "blah"},
        {"role": 1, "pwd": 12}
    ])
    async def test_update_user_with_bad_data(self, client, request_data):
        warn_msg = 'Nothing to update the user'
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth._logger, 'warning') as patch_logger_warning:
                resp = await client.put('/foglamp/user/2', data=json.dumps(request_data))
                assert 400 == resp.status
                assert warn_msg == resp.reason
            patch_logger_warning.assert_called_once_with(warn_msg)
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/user/2')

    @pytest.mark.parametrize("request_data", [
        {'role_id': -3},
        {'role_id': 'blah'},
    ])
    async def test_update_user_with_bad_role(self, client, request_data):
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth, 'is_valid_role', return_value=False) as patch_role:
                with patch.object(auth._logger, 'warning') as patch_logger_warning:
                    resp = await client.put('/foglamp/user/2', data=json.dumps(request_data))
                    assert 400 == resp.status
                    assert 'Invalid or bad role id' == resp.reason
                patch_logger_warning.assert_called_once_with('Update user requested with bad role id')
            patch_role.assert_called_once_with(request_data['role_id'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/user/2')

    @pytest.mark.parametrize("request_data", [
        {'role_id': 1},
        {'role_id': 2}
    ])
    async def test_update_role_with_normal_user(self, client, request_data):
        msg = 'Only admin can update the role for a user'
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth, 'is_valid_role', return_value=True) as patch_role:
                with patch.object(auth, 'has_admin_permissions', return_value=False) as patch_admin_permission:
                    with patch.object(auth._logger, 'warning') as patch_logger_warning:
                        resp = await client.put('/foglamp/user/2', data=json.dumps(request_data))
                        assert 401 == resp.status
                        assert msg == resp.reason
                    patch_logger_warning.assert_called_once_with(msg)
                # TODO: Request patch VERB and Url
                # patch_admin_permission.assert_called_once_with()
            patch_role.assert_called_once_with(request_data['role_id'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/user/2')

    @pytest.mark.parametrize("request_data", [
        {'password': 1},
        {'password': "blah"}
    ])
    async def test_update_bad_password(self, client, request_data):
        msg = 'Password must contain at least one digit, one lowercase, one uppercase & one special character and length of minimum 6 characters'
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth._logger, 'warning') as patch_logger_warning:
                resp = await client.put('/foglamp/user/2', data=json.dumps(request_data))
                assert 400 == resp.status
                assert msg == resp.reason
            patch_logger_warning.assert_called_once_with(msg)
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/user/2')

    async def test_update_user(self, client):
        ret_val = {'response': 'updated', 'rows_affected': 1}
        user_id = 2
        msg = 'User with id:<{}> has been updated successfully'.format(user_id)
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth, 'check_authorization', return_value=True) as patch_check_authorization:
                with patch.object(User.Objects, 'update', return_value=ret_val) as patch_user_update:
                    with patch.object(auth._logger, 'info') as patch_auth_logger_info:
                        resp = await client.put('/foglamp/user/{}'.format(user_id), data=json.dumps({'password': 'F0gl@mp'}))
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
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/user/{}'.format(user_id))

    @pytest.mark.parametrize("exception_name, code, msg", [
        (ValueError, 400, 'None'),
        (User.DoesNotExist, 404, 'User with id:<2> does not exist')
    ])
    async def test_update_user_custom_exception(self, client, exception_name, code, msg):
        user_id = 2
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth, 'check_authorization', return_value=True) as patch_check_authorization:
                with patch.object(User.Objects, 'update', side_effect=exception_name(msg)) as patch_user_update:
                    with patch.object(auth._logger, 'warning') as patch_auth_logger_warn:
                        resp = await client.put('/foglamp/user/{}'.format(user_id), data=json.dumps({'password': 'F0gl@mp'}))
                        assert code == resp.status
                        assert msg == resp.reason
                    patch_user_update.assert_called_once_with(str(user_id), {'password': 'F0gl@mp'})
                    patch_auth_logger_warn.assert_called_once_with(msg)
            # TODO: Request patch VERB and Url
            args, kwargs = patch_check_authorization.call_args
            assert str(user_id) == args[1]
            assert 'update' == args[2]
            # patch_check_authorization.assert_called_once_with()
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/user/{}'.format(user_id))

    async def test_update_user_exception(self, client):
        user_id = 2
        msg = 'Something went wrong'
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth, 'check_authorization', return_value=True) as patch_check_authorization:
                with patch.object(User.Objects, 'update', side_effect=Exception(msg)) as patch_user_update:
                    with patch.object(auth._logger, 'exception') as patch_auth_logger_warn:
                        resp = await client.put('/foglamp/user/{}'.format(user_id), data=json.dumps({'password': 'F0gl@mp'}))
                        assert 500 == resp.status
                        assert msg == resp.reason
                    patch_user_update.assert_called_once_with(str(user_id), {'password': 'F0gl@mp'})
                    patch_auth_logger_warn.assert_called_once_with(msg)
            # TODO: Request patch VERB and Url
            args, kwargs = patch_check_authorization.call_args
            assert str(user_id) == args[1]
            assert 'update' == args[2]
            # patch_check_authorization.assert_called_once_with()
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'PUT', '/foglamp/user/{}'.format(user_id))

    @pytest.mark.parametrize("request_data", [
        'blah',
        '123blah'
    ])
    async def test_delete_bad_user(self, client, request_data):
        msg = "invalid literal for int() with base 10: '{}'".format(request_data)
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth._logger, 'warning') as patch_auth_logger_warn:
                resp = await client.delete('/foglamp/user/{}'.format(request_data))
                assert 400 == resp.status
                assert msg == resp.reason
            patch_auth_logger_warn.assert_called_once_with(msg)
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'DELETE', '/foglamp/user/{}'.format(request_data))

    async def test_delete_admin_user(self, client):
        msg = "Super admin user can not be deleted"
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth._logger, 'warning') as patch_auth_logger_warn:
                resp = await client.delete('/foglamp/user/1')
                assert 406 == resp.status
                assert msg == resp.reason
            patch_auth_logger_warn.assert_called_once_with(msg)
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'DELETE', '/foglamp/user/1')

    async def test_delete_user(self, client):
        ret_val = {"response": "deleted", "rows_affected": 1}
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth._logger, 'info') as patch_auth_logger_info:
                with patch.object(User.Objects, 'delete', return_value=ret_val) as patch_user_delete:
                    resp = await client.delete('/foglamp/user/2')
                    assert 200 == resp.status
                    r = await resp.text()
                    assert {'message': 'User has been deleted successfully'} == json.loads(r)
                patch_user_delete.assert_called_once_with(2)
            patch_auth_logger_info.assert_called_once_with('User with id:<2> has been deleted successfully.')
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'DELETE', '/foglamp/user/2')

    @pytest.mark.parametrize("exception_name, code, msg", [
        (ValueError, 400, 'None'),
        (User.DoesNotExist, 404, 'User with id:<2> does not exist')
    ])
    async def test_delete_user_custom_exception(self, client, exception_name, code, msg):
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth._logger, 'warning') as patch_auth_logger_warn:
                with patch.object(User.Objects, 'delete', side_effect=exception_name(msg)) as patch_user_delete:
                    resp = await client.delete('/foglamp/user/2')
                    assert code == resp.status
                    assert msg == resp.reason
                patch_user_delete.assert_called_once_with(2)
            patch_auth_logger_warn.assert_called_once_with(msg)
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'DELETE', '/foglamp/user/2')

    async def test_delete_user_exception(self, client):
        msg = 'Something went wrong'
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth._logger, 'exception') as patch_auth_logger_exc:
                with patch.object(User.Objects, 'delete', side_effect=Exception(msg)) as patch_user_delete:
                    resp = await client.delete('/foglamp/user/2')
                    assert 500 == resp.status
                    assert msg == resp.reason
                patch_user_delete.assert_called_once_with(2)
            patch_auth_logger_exc.assert_called_once_with(msg)
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'DELETE', '/foglamp/user/2')

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
    async def test_create_bad_user(self, client, request_data):
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth._logger, 'warning') as patch_logger_warn:
                resp = await client.post('/foglamp/user', data=json.dumps(request_data))
                assert 400 == resp.status
                assert 'Username or password is missing' == resp.reason
                patch_logger_warn.assert_called_once_with('Username and password are required to create user')
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/foglamp/user')

    @pytest.mark.parametrize("request_data", [
        {"username": "blah", "password": 1},
        {"username": "blah", "password": "blah"}
    ])
    async def test_create_user_bad_password(self, client, request_data):
        msg = 'Password must contain at least one digit, one lowercase, one uppercase & one special character and length of minimum 6 characters'
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth._logger, 'warning') as patch_logger_warning:
                resp = await client.post('/foglamp/user', data=json.dumps(request_data))
                assert 400 == resp.status
                assert msg == resp.reason
            patch_logger_warning.assert_called_once_with(msg)
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/foglamp/user')

    @pytest.mark.parametrize("request_data", [
        {"username": "aj", "password": "F0gl@mp", "role_id": -3},
        {"username": "aj", "password": "F0gl@mp", "role_id": "blah"}
    ])
    async def test_create_user_with_bad_role(self, client, request_data):
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth, 'is_valid_role', return_value=False) as patch_role:
                with patch.object(auth._logger, 'warning') as patch_logger_warning:
                    resp = await client.post('/foglamp/user', data=json.dumps(request_data))
                    assert 400 == resp.status
                    assert 'Invalid or bad role id' == resp.reason
                patch_logger_warning.assert_called_once_with('Create user requested with bad role id')
            patch_role.assert_called_once_with(request_data['role_id'])
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
    async def test_create_user_bad_username(self, client, request_data):
        msg = 'Username should be of minimum 4 characters'
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth, 'is_valid_role', return_value=True) as patch_role:
                with patch.object(auth._logger, 'warning') as patch_logger_warning:
                    resp = await client.post('/foglamp/user', data=json.dumps(request_data))
                    assert 400 == resp.status
                    assert msg == resp.reason
                patch_logger_warning.assert_called_once_with(msg)
            patch_role.assert_called_once_with(2)
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/foglamp/user')

    async def test_create_dupe_user_name(self, client):
        request_data = {"username": "ajtest", "password": "F0gl@mp"}
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth, 'is_valid_role', return_value=True) as patch_role:
                with patch.object(User.Objects, 'get', return_value={'role_id': '2', 'uname': 'ajtest', 'id': '2'}) as patch_get_user:
                    with patch.object(auth._logger, 'warning') as patch_logger_warning:
                        resp = await client.post('/foglamp/user', data=json.dumps(request_data))
                        assert 409 == resp.status
                        assert 'User with the requested username already exists' == resp.reason
                    patch_logger_warning.assert_called_once_with('Can not create a user, username already exists')
                args, kwargs = patch_get_user.call_args
                assert {'username': 'ajtest'} == kwargs
            patch_role.assert_called_once_with(2)
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/foglamp/user')

    async def test_create_user(self, client):
        data = {'id': '3', 'uname': 'ajtest', 'role_id': '2'}
        expected = {}
        expected.update(data)
        request_data = {"username": "ajtest", "password": "F0gl@mp"}
        ret_val = {"response": "inserted", "rows_affected": 1}
        msg = 'User has been created successfully'
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth, 'is_valid_role', return_value=True) as patch_role:
                with patch.object(User.Objects, 'get', side_effect=[User.DoesNotExist, data]):
                    with patch.object(User.Objects, 'create', return_value=ret_val) as patch_create_user:
                            with patch.object(auth._logger, 'info') as patch_audit_logger_info:
                                resp = await client.post('/foglamp/user', data=json.dumps(request_data))
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
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/foglamp/user')

    async def test_create_user_exception(self, client):
        request_data = {"username": "ajtest", "password": "F0gl@mp"}
        exc_msg = "Something went wrong"
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth, 'is_valid_role', return_value=True) as patch_role:
                with patch.object(User.Objects, 'get', side_effect=User.DoesNotExist):
                    with patch.object(User.Objects, 'create', side_effect=Exception(exc_msg)) as patch_create_user:
                        with patch.object(auth._logger, 'exception') as patch_audit_logger_exc:
                            resp = await client.post('/foglamp/user', data=json.dumps(request_data))
                            assert 500 == resp.status
                            assert exc_msg == resp.reason
                        patch_audit_logger_exc.assert_called_once_with(exc_msg)
                    patch_create_user.assert_called_once_with(request_data['username'], request_data['password'], 2)
            patch_role.assert_called_once_with(2)
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/foglamp/user')

    async def test_create_user_value_error(self, client):
        request_data = {"username": "ajtest", "password": "F0gl@mp"}
        exc_msg = "Value Error occurred"
        with patch.object(middleware._logger, 'info') as patch_logger_info:
            with patch.object(auth, 'is_valid_role', return_value=True) as patch_role:
                with patch.object(User.Objects, 'get', side_effect=User.DoesNotExist):
                    with patch.object(User.Objects, 'create', side_effect=ValueError(exc_msg)) as patch_create_user:
                        with patch.object(auth._logger, 'warning') as patch_audit_logger_warn:
                            resp = await client.post('/foglamp/user', data=json.dumps(request_data))
                            assert 400 == resp.status
                            assert exc_msg == resp.reason
                        patch_audit_logger_warn.assert_called_once_with(exc_msg)
                    patch_create_user.assert_called_once_with(request_data['username'], request_data['password'], 2)
            patch_role.assert_called_once_with(2)
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/foglamp/user')

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
