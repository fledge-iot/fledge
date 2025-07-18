# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import asyncio
import json
from unittest.mock import patch
from aiohttp import web
import pytest
import sys

from fledge.common.web import middleware
from fledge.services.core import routes
from fledge.services.core.user_model import User
from fledge.services.core.api import auth

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


FORBIDDEN = 'Forbidden'
WARN_MSG = 'Resource you were trying to reach is absolutely forbidden for some reason'


async def mock_coro(*args, **kwargs):
    return None if len(args) == 0 else args[0]


class TestAuthOptional:

    @pytest.fixture
    def client(self, loop, aiohttp_server, aiohttp_client):
        app = web.Application(loop=loop,  middlewares=[middleware.optional_auth_middleware])
        # fill the routes table
        routes.setup(app)
        server = loop.run_until_complete(aiohttp_server(app))
        loop.run_until_complete(server.start_server(loop=loop))
        client = loop.run_until_complete(aiohttp_client(server))
        return client

    async def test_get_roles(self, client):
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await mock_coro([])
        else:
            _rv = asyncio.ensure_future(mock_coro([]))
        
        with patch.object(middleware._logger, 'debug') as patch_logger:
            with patch.object(User.Objects, 'get_roles', return_value=_rv) as patch_user_obj:
                resp = await client.get('/fledge/user/role')
                assert 200 == resp.status
                r = await resp.text()
                assert {'roles': []} == json.loads(r)
            patch_user_obj.assert_called_once_with()
        patch_logger.assert_called_once_with('Received %s request for %s', 'GET', '/fledge/user/role')

    @pytest.mark.parametrize("ret_val, exp_result", [
        ([], []),
        ([{'uname': 'admin', 'role_id': '1', 'access_method': 'any', 'id': '1', 'real_name': 'Admin',
           'description': 'Admin user', 'enabled': 't', 'failed_attempts': 0, 'block_until': ''},
          {'uname': 'user', 'role_id': '2', 'access_method': 'any', 'id': '2', 'real_name': 'Non-admin',
           'description': 'Normal user', 'enabled': 't', 'failed_attempts': 0, 'block_until': ''},
          {'uname': 'dviewer', 'role_id': '3', 'access_method': 'any', 'id': '3', 'real_name': 'Data-Viewer',
           'description': 'Data user', 'enabled': 'f', 'failed_attempts': 0, 'block_until': ''}
          ],
         [{"userId": "1", "userName": "admin", "roleId": "1", "accessMethod": "any", "realName": "Admin",
           "description": "Admin user"},
          {"userId": "2", "userName": "user", "roleId": "2", "accessMethod": "any", "realName": "Non-admin",
           "description": "Normal user"}])
    ])
    async def test_get_all_users(self, client, ret_val, exp_result):
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await mock_coro(ret_val)
        else:
            _rv = asyncio.ensure_future(mock_coro(ret_val))
        with patch.object(middleware._logger, 'debug') as patch_logger:
            with patch.object(User.Objects, 'all', return_value=_rv) as patch_user_obj:
                resp = await client.get('/fledge/user')
                assert 200 == resp.status
                r = await resp.text()
                assert {'users': exp_result} == json.loads(r)
            patch_user_obj.assert_called_once_with()
        patch_logger.assert_called_once_with('Received %s request for %s', 'GET', '/fledge/user')

    @pytest.mark.parametrize("request_params, exp_result, arg1, arg2", [
        ('?id=1', {'uname': 'admin', 'role_id': '1', 'id': '1', 'access_method': 'any', 'real_name': 'Admin', 'description': 'Admin user','failed_attempts': 0, 'block_until': ''}, 1, None),
        ('?username=admin', {'uname': 'admin', 'role_id': '1', 'id': '1', 'access_method': 'any', 'real_name': 'Admin', 'description': 'Admin user', 'failed_attempts': 0, 'block_until': ''},  None, 'admin'),
        ('?id=1&username=admin', {'uname': 'admin', 'role_id': '1', 'id': '1', 'access_method': 'any', 'real_name': 'Admin', 'description': 'Admin user', 'failed_attempts': 0, 'block_until': ''}, 1, 'admin'),
        ('?id=1&user=admin', {'uname': 'admin', 'role_id': '1', 'id': '1', 'access_method': 'any', 'real_name': 'Admin', 'description': 'Admin user', 'failed_attempts': 0, 'block_until': ''}, 1, None),
        ('?uid=1&username=admin', {'uname': 'admin', 'role_id': '1', 'id': '1', 'access_method': 'any', 'real_name': 'Admin', 'description': 'Admin user', 'failed_attempts': 0, 'block_until': ''}, None, 'admin'),
    ])
    async def test_get_user_by_param(self, client, request_params, exp_result, arg1, arg2):
        result = {}
        result.update(exp_result)
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await mock_coro(result)
        else:
            _rv = asyncio.ensure_future(mock_coro(result))
        
        with patch.object(middleware._logger, 'debug') as patch_logger:
            with patch.object(User.Objects, 'get', return_value=_rv) as patch_user_obj:
                resp = await client.get('/fledge/user{}'.format(request_params))
                assert 200 == resp.status
                r = await resp.text()
                actual = json.loads(r)
                assert actual['userId'] == exp_result['id']
                assert actual['roleId'] == exp_result['role_id']
                assert actual['userName'] == exp_result['uname']
                assert actual['accessMethod'] == exp_result['access_method']
                assert actual['realName'] == exp_result['real_name']
                assert actual['description'] == exp_result['description']
            patch_user_obj.assert_called_once_with(arg1, arg2)
        patch_logger.assert_called_once_with('Received %s request for %s', 'GET', '/fledge/user')

    @pytest.mark.parametrize("request_params, error_msg, arg1, arg2", [
        ('?id=10', 'User with id:<10> does not exist', 10, None),
        ('?username=blah', 'User with name:<blah> does not exist', None, 'blah')
    ])
    async def test_get_user_exception_by_param(self, client, request_params, error_msg, arg1, arg2):
        with patch.object(middleware._logger, 'debug') as patch_logger:
            with patch.object(User.Objects, 'get', side_effect=User.DoesNotExist(error_msg)) as patch_user_get:
                resp = await client.get('/fledge/user{}'.format(request_params))
                assert 404 == resp.status
                assert error_msg == resp.reason
            patch_user_get.assert_called_once_with(arg1, arg2)
        patch_logger.assert_called_once_with('Received %s request for %s', 'GET', '/fledge/user')

    @pytest.mark.parametrize("request_params", ['?id=0', '?id=blah', '?id=-1'])
    async def test_get_bad_user_id_param_exception(self, client, request_params):
        with patch.object(middleware._logger, 'debug') as patch_logger:
            resp = await client.get('/fledge/user{}'.format(request_params))
            assert 400 == resp.status
            assert 'Bad user ID' == resp.reason
        patch_logger.assert_called_once_with('Received %s request for %s', 'GET', '/fledge/user')

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
        with patch.object(middleware._logger, 'debug') as patch_logger:
            resp = await client.post('/fledge/login', data=json.dumps(request_data))
            assert 400 == resp.status
            assert 'Username or password is missing' == resp.reason
        patch_logger.assert_called_once_with('Received %s request for %s', 'POST', '/fledge/login')

    @pytest.mark.parametrize("request_data, status_code, exception_name, msg", [
        ({"username": "blah", "password": "blah"}, 404, User.DoesNotExist, 'User does not exist'),
        ({"username": "admin", "password": "blah"}, 404, User.PasswordDoesNotMatch, 'Username or Password do not match'),
        ({"username": "admin", "password": 123}, 404, User.PasswordDoesNotMatch, 'Username or Password do not match'),
        ({"username": 1, "password": 1}, 404, ValueError, 'Username should be a valid string'),
        ({"username": "user", "password": "fledge"}, 401, User.PasswordExpired,
         'Your password has been expired. Please set your password again.'),
        ({"username": "user1", "password": "blah"}, 400, User.PasswordNotSetError,
         'Password is not set for this user.')

    ])
    async def test_login_exception(self, client, request_data, status_code, exception_name, msg):
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await mock_coro([])
        else:
            _rv = asyncio.ensure_future(mock_coro([]))
        
        with patch.object(middleware._logger, 'debug') as patch_logger:
            with patch.object(User.Objects, 'login', side_effect=exception_name(msg)) as patch_user_login:
                with patch.object(User.Objects, 'delete_user_tokens', return_value=_rv) as patch_delete_token:
                    with patch.object(auth._logger, 'warning') as patch_auth_logger:
                        resp = await client.post('/fledge/login', data=json.dumps(request_data))
                        assert status_code == resp.status
                        assert msg == resp.reason
                    if status_code == 401:
                        patch_auth_logger.assert_called_once_with(msg)
                if status_code == 401:
                    patch_delete_token.assert_called_once_with(msg)
            # TODO: host arg patch transport.request.extra_info
            args, kwargs = patch_user_login.call_args
            assert str(request_data['username']) == args[0]
            assert request_data['password'] == args[1]
            # patch_user_login.assert_called_once_with()
        patch_logger.assert_called_once_with('Received %s request for %s', 'POST', '/fledge/login')

    @pytest.mark.parametrize("request_data, ret_val", [
        ({"username": "admin", "password": "fledge"}, (1, "token1", True)),
        ({"username": "user", "password": "fledge"}, (2, "token2", False))
    ])
    async def test_login(self, client, request_data, ret_val):
        async def async_mock():
            return ret_val

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await async_mock()
        else:
            _rv = asyncio.ensure_future(async_mock())        
        
        with patch.object(middleware._logger, 'debug') as patch_logger:
            with patch.object(User.Objects, 'login', return_value=_rv) as patch_user_login:
                with patch.object(auth._logger, 'info') as patch_auth_logger:
                    resp = await client.post('/fledge/login', data=json.dumps(request_data))
                    assert 200 == resp.status
                    r = await resp.text()
                    actual = json.loads(r)
                    assert ret_val[0] == actual['uid']
                    assert ret_val[1] == actual['token']
                    assert ret_val[2] == actual['admin']
                patch_auth_logger.assert_called_once_with('User with username:<{}> logged in successfully.'.format(
                    request_data['username']))
            # TODO: host arg patch transport.request.extra_info
            args, kwargs = patch_user_login.call_args
            assert request_data['username'] == args[0]
            assert request_data['password'] == args[1]
            # patch_user_login.assert_called_once_with()
        patch_logger.assert_called_once_with('Received %s request for %s', 'POST', '/fledge/login')

    async def test_logout(self, client):
        with patch.object(middleware._logger, 'debug') as patch_logger:
            with patch.object(auth._logger, 'warning') as patch_logger_warning:
                resp = await client.put('/fledge/2/logout')
                assert 403 == resp.status
                assert FORBIDDEN == resp.reason
            patch_logger_warning.assert_called_once_with(WARN_MSG)
        patch_logger.assert_called_once_with('Received %s request for %s', 'PUT', '/fledge/2/logout')

    async def test_update_password(self, client):
        with patch.object(middleware._logger, 'debug') as patch_logger:
            with patch.object(auth._logger, 'warning') as patch_logger_warning:
                resp = await client.put('/fledge/user/1/password')
                assert 403 == resp.status
                assert FORBIDDEN == resp.reason
            patch_logger_warning.assert_called_once_with(WARN_MSG)
        patch_logger.assert_called_once_with('Received %s request for %s', 'PUT', '/fledge/user/1/password')

    async def test_update_me(self, client):
        with patch.object(middleware._logger, 'debug') as patch_logger:
            with patch.object(auth._logger, 'warning') as patch_logger_warning:
                resp = await client.put('/fledge/user')
                assert 403 == resp.status
                assert FORBIDDEN == resp.reason
            patch_logger_warning.assert_called_once_with(WARN_MSG)
        patch_logger.assert_called_once_with('Received %s request for %s', 'PUT', '/fledge/user')

    async def test_update_user(self, client):
        with patch.object(middleware._logger, 'debug') as patch_logger:
            with patch.object(auth._logger, 'warning') as patch_logger_warning:
                resp = await client.put('/fledge/admin/1')
                assert 403 == resp.status
                assert FORBIDDEN == resp.reason
            patch_logger_warning.assert_called_once_with(WARN_MSG)
        patch_logger.assert_called_once_with('Received %s request for %s', 'PUT', '/fledge/admin/1')

    async def test_delete_user(self, client):
        with patch.object(middleware._logger, 'debug') as patch_logger:
            with patch.object(auth._logger, 'warning') as patch_auth_logger_warn:
                resp = await client.delete('/fledge/admin/1/delete')
                assert 403 == resp.status
                assert FORBIDDEN == resp.reason
            patch_auth_logger_warn.assert_called_once_with(WARN_MSG)
        patch_logger.assert_called_once_with('Received %s request for %s', 'DELETE', '/fledge/admin/1/delete')

    async def test_create_user(self, client):
        request_data = {"username": "ajtest", "password": "F0gl@mp"}
        with patch.object(middleware._logger, 'debug') as patch_logger:
            with patch.object(auth._logger, 'warning') as patch_logger_warning:
                resp = await client.post('/fledge/admin/user', data=json.dumps(request_data))
                assert 403 == resp.status
                assert FORBIDDEN == resp.reason
            patch_logger_warning.assert_called_once_with(WARN_MSG)
        patch_logger.assert_called_once_with('Received %s request for %s', 'POST', '/fledge/admin/user')

    async def test_enable_user(self, client):
        with patch.object(middleware._logger, 'debug') as patch_logger:
            with patch.object(auth._logger, 'warning') as patch_logger_warning:
                resp = await client.put('/fledge/admin/2/enable')
                assert 403 == resp.status
                assert FORBIDDEN == resp.reason
            patch_logger_warning.assert_called_once_with(WARN_MSG)
        patch_logger.assert_called_once_with('Received %s request for %s', 'PUT', '/fledge/admin/2/enable')

    async def test_reset(self, client):
        with patch.object(middleware._logger, 'debug') as patch_logger:
            with patch.object(auth._logger, 'warning') as patch_logger_warning:
                resp = await client.put('/fledge/admin/2/reset')
                assert 403 == resp.status
                assert FORBIDDEN == resp.reason
            patch_logger_warning.assert_called_once_with(WARN_MSG)
        patch_logger.assert_called_once_with('Received %s request for %s', 'PUT', '/fledge/admin/2/reset')

    @pytest.mark.parametrize("role_id, expected", [
        (1, True),
        (2, True),
        (3, False)
    ])
    async def test_valid_role(self, role_id, expected):
        ret_val = [{"id": "1", "description": "for the users having all CRUD privileges including other admin users", "name": "admin"}, {"id": "2", "description": "all CRUD operations and self profile management", "name": "user"}]

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await mock_coro(ret_val)
        else:
            _rv = asyncio.ensure_future(mock_coro(ret_val))

        with patch.object(User.Objects, 'get_roles', return_value=_rv) as patch_get_roles:
            actual = await auth.is_valid_role(role_id)
            assert expected is actual
        patch_get_roles.assert_called_once_with()

    async def test_certificate(self, client):
        with patch.object(middleware._logger, 'debug') as patch_logger:
            with patch.object(auth._logger, 'warning') as patch_logger_warning:
                resp = await client.post('/fledge/admin/2/authcertificate')
                assert 403 == resp.status
                assert FORBIDDEN == resp.reason
            patch_logger_warning.assert_called_once_with(WARN_MSG)
        patch_logger.assert_called_once_with('Received %s request for %s', 'POST',
                                             '/fledge/admin/2/authcertificate')

