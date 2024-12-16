# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import asyncio
import json
from unittest.mock import MagicMock, patch
from aiohttp import web
import pytest
import sys

from fledge.common.audit_logger import AuditLogger
from fledge.common.configuration_manager import ConfigurationManager
from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.common.web import middleware
from fledge.common.web.ssl_wrapper import SSLVerifier
from fledge.services.core import connect, routes, server
from fledge.services.core.api import auth
from fledge.services.core.user_model import User

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

ADMIN_USER_HEADER = {'content-type': 'application/json', 'Authorization': 'admin_user_token'}
NORMAL_USER_HEADER = {'content-type': 'application/json', 'Authorization': 'normal_user_token'}
PASSWORD_MIN_LENGTH_ERROR_MSG = "Password should have minimum 6 characters."

async def mock_coro(*args, **kwargs):
    return None if len(args) == 0 else args[0]


class TestAuthMandatory:

    @pytest.fixture
    def client(self, loop, aiohttp_server, aiohttp_client):
        app = web.Application(loop=loop,  middlewares=[middleware.auth_middleware])
        # fill the routes table
        routes.setup(app)
        server = loop.run_until_complete(aiohttp_server(app))
        loop.run_until_complete(server.start_server(loop=loop))
        client = loop.run_until_complete(aiohttp_client(server))
        return client

    async def auth_token_fixture(self, mocker, is_admin=True):
        user = {'id': 1, 'uname': 'admin', 'role_id': '1'} if is_admin else {'id': 2, 'uname': 'user', 'role_id': '2'}
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await mock_coro(user['id'])
            _rv2 = await mock_coro(None)
            _rv3 = await mock_coro(user)
        else:
            _rv1 = asyncio.ensure_future(mock_coro(user['id']))
            _rv2 = asyncio.ensure_future(mock_coro(None))
            _rv3 = asyncio.ensure_future(mock_coro(user))
        patch_logger_debug = mocker.patch.object(middleware._logger, 'debug')
        patch_validate_token = mocker.patch.object(User.Objects, 'validate_token', return_value=_rv1)
        patch_refresh_token = mocker.patch.object(User.Objects, 'refresh_token_expiry', return_value=_rv2)
        patch_user_get = mocker.patch.object(User.Objects, 'get', return_value=_rv3)
        return patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get

    @pytest.mark.parametrize("payload, msg", [
        ({}, "Username is required to create user."),
        ({"username": 1}, "Values should be passed in string."),
        ({"username": "bla"}, "Username should be of minimum 4 characters."),
        ({"username": "  b"}, "Username should be of minimum 4 characters."),
        ({"username": "b  "}, "Username should be of minimum 4 characters."),
        ({"username": "  b la"}, "Username should be of minimum 4 characters."),
        ({"username": "b l A  "}, "Username should be of minimum 4 characters."),
        ({"username": "Bla"}, "Username should be of minimum 4 characters."),
        ({"username": "BLA"}, "Username should be of minimum 4 characters."),
        ({"username": "aj!aj"}, "Dot, hyphen, underscore special characters are allowed for username."),
        ({"username": "aj.aj", "access_method": "PEM"}, "Invalid access method. Must be 'any' or 'cert' or 'pwd'."),
        ({"username": "aj.aj", "access_method": 1}, "Values should be passed in string."),
        ({"username": "aj.aj", "access_method": 'pwd'}, "Password should not be an empty."),
        ({"username": "aj_123!"}, "Dot, hyphen, underscore special characters are allowed for username."),
        ({"username": "aj_123", "password": 1}, PASSWORD_MIN_LENGTH_ERROR_MSG),
        ({"username": "12-aj", "password": "blah"}, PASSWORD_MIN_LENGTH_ERROR_MSG),
        ({"username": "12-aj", "password": "12B l"}, PASSWORD_MIN_LENGTH_ERROR_MSG),
        ({"username": "aj.123", "password": "a!23"}, PASSWORD_MIN_LENGTH_ERROR_MSG),
        ({"username": "aj.123", "password": "A!23"}, PASSWORD_MIN_LENGTH_ERROR_MSG),
        ({"username": "aj.aj", "access_method": "any", "password": "blah"}, PASSWORD_MIN_LENGTH_ERROR_MSG),
        ({"username": "aj.aj", "access_method": "pwd", "password": "blah"}, PASSWORD_MIN_LENGTH_ERROR_MSG)
    ])
    async def test_create_bad_user(self, client, mocker, payload, msg):
        ret_val = [{'id': '1'}]
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info >= (3, 8):
            rv1 = await mock_coro(msg)
            rv2 = await mock_coro(ret_val)
        else:
            rv1 = asyncio.ensure_future(mock_coro(msg))
            rv2 = asyncio.ensure_future(mock_coro(ret_val))
        with patch.object(User.Objects, 'get_role_id_by_name', return_value=rv2) as patch_role_id:
            with patch.object(auth, 'validate_password', return_value=rv1):
                resp = await client.post('/fledge/admin/user', data=json.dumps(payload), headers=ADMIN_USER_HEADER)
                assert 400 == resp.status
                assert msg == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {"message": msg} == json_response
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s', 'POST', '/fledge/admin/user')

    @pytest.mark.parametrize("request_data", [
        {"username": "AdMin", "password": "F0gl@mp", "role_id": -3},
        {"username": "aj.aj", "password": "F0gl@mp", "role_id": "blah"}
    ])
    async def test_create_user_with_bad_role(self, client, mocker, request_data):
        msg = "Invalid role ID."
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await mock_coro([{'id': '1'}])
            _rv2 = await mock_coro(False)
            _rv3 = await mock_coro("")
        else:
            _rv1 = asyncio.ensure_future(mock_coro([{'id': '1'}]))
            _rv2 = asyncio.ensure_future(mock_coro(False))
            _rv3 = asyncio.ensure_future(mock_coro(""))
        with patch.object(User.Objects, 'get_role_id_by_name', return_value=_rv1) as patch_role_id:
            with patch.object(auth, 'validate_password', return_value=_rv3):
                with patch.object(auth, 'is_valid_role', return_value=_rv2) as patch_role:
                    resp = await client.post('/fledge/admin/user', data=json.dumps(request_data), headers=ADMIN_USER_HEADER)
                    assert 400 == resp.status
                    assert msg == resp.reason
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert {"message": msg} == json_response
                patch_role.assert_called_once_with(request_data['role_id'])
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s', 'POST', '/fledge/admin/user')

    async def test_create_dupe_user_name(self, client):
        msg = "Username already exists."
        request_data = {"username": "dviewer", "password": "F0gl@mp"}
        valid_user = {'id': 1, 'uname': 'admin', 'role_id': '1'}
        users = [{'id': 1, 'uname': 'admin', 'real_name': 'Admin user', 'role_id': 1, 'description': 'admin user',
                  'enabled': 't', 'access_method': 'any'},
                 {'id': 2, 'uname': 'user', 'real_name': 'Normal user', 'role_id': 2, 'description': 'normal user',
                  'enabled': 'f', 'access_method': 'any'},
                 {'id': 3, 'uname': 'dviewer', 'real_name': 'Data Viewer', 'role_id': 4, 'description': 'Test',
                  'enabled': 'f', 'access_method': 'any'}]
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await mock_coro(valid_user['id'])
            _rv2 = await mock_coro(None)
            _rv3 = await mock_coro([{'id': '1'}])
            _rv4 = await mock_coro(True)
            _rv5 = await mock_coro(valid_user)
            _rv6 = await mock_coro(users)
            _rv7 = await mock_coro("")
        else:
            _rv1 = asyncio.ensure_future(mock_coro(valid_user['id']))
            _rv2 = asyncio.ensure_future(mock_coro(None))
            _rv3 = asyncio.ensure_future(mock_coro([{'id': '1'}]))
            _rv4 = asyncio.ensure_future(mock_coro(True))
            _rv5 = asyncio.ensure_future(mock_coro(valid_user))
            _rv6 = asyncio.ensure_future(mock_coro(users))
            _rv7 = asyncio.ensure_future(mock_coro(""))

        with patch.object(middleware._logger, 'debug') as patch_logger_debug:
            with patch.object(User.Objects, 'validate_token', return_value=_rv1) as patch_validate_token:
                with patch.object(User.Objects, 'refresh_token_expiry', return_value=_rv2
                                  ) as patch_refresh_token:
                    with patch.object(User.Objects, 'get', return_value=_rv5) as patch_user_get:
                        with patch.object(User.Objects, 'all', return_value=_rv6) as patch_user_all:
                            with patch.object(User.Objects, 'get_role_id_by_name', return_value=_rv3
                                              ) as patch_role_id:
                                with patch.object(auth, 'validate_password', return_value=_rv7):
                                    with patch.object(auth, 'is_valid_role', return_value=_rv4) as patch_role:
                                        with patch.object(auth._logger, 'warning') as patch_logger_warning:
                                            resp = await client.post('/fledge/admin/user', data=json.dumps(
                                                request_data), headers=ADMIN_USER_HEADER)
                                            assert 409 == resp.status
                                            assert msg == resp.reason
                                            result = await resp.text()
                                            json_response = json.loads(result)
                                            assert {"message": msg} == json_response
                                        patch_logger_warning.assert_called_once_with(msg)
                                    patch_role.assert_called_once_with(2)
                            patch_role_id.assert_called_once_with('admin')
                        patch_user_all.assert_called_once_with()
                    patch_user_get.assert_called_once_with(uid=valid_user['id'])
                patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
            patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s', 'POST', '/fledge/admin/user')

    async def test_create_user(self, client):
        request_data = {"username": "aj123", "password": "F0gl@mp"}
        data = {'id': '3', 'uname': request_data['username'], 'role_id': '2', 'access_method': 'any',
                'real_name': '', 'description': ''}
        expected = {}
        expected.update(data)
        users = [{'id': 1, 'uname': 'admin', 'real_name': 'Admin user', 'role_id': 1, 'description': 'admin user',
                  'enabled': 't', 'access_method': 'any'},
                 {'id': 2, 'uname': 'user', 'real_name': 'Normal user', 'role_id': 2, 'description': 'normal user',
                  'enabled': 'f', 'access_method': 'any'},
                 {'id': 3, 'uname': 'dviewer', 'real_name': 'Data Viewer', 'role_id': 4, 'description': 'Test',
                  'enabled': 'f', 'access_method': 'any'}]
        ret_val = {"response": "inserted", "rows_affected": 1}
        msg = '{} user has been created successfully.'.format(request_data['username'])
        valid_user = {'id': 1, 'uname': 'admin', 'role_id': '1'}
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await mock_coro(valid_user['id'])
            _rv2 = await mock_coro(None)
            _rv3 = await mock_coro([{'id': '1'}])
            _rv4 = await mock_coro(True)
            _rv5 = await mock_coro(ret_val)
            _rv6 = await mock_coro(users)
            _rv7 = await mock_coro("")
            _se1 = await mock_coro(valid_user)
            _se2 = await mock_coro(data)
        else:
            _rv1 = asyncio.ensure_future(mock_coro(valid_user['id']))
            _rv2 = asyncio.ensure_future(mock_coro(None))
            _rv3 = asyncio.ensure_future(mock_coro([{'id': '1'}]))
            _rv4 = asyncio.ensure_future(mock_coro(True))
            _rv5 = asyncio.ensure_future(mock_coro(ret_val))
            _rv6 = asyncio.ensure_future(mock_coro(users))
            _rv7 = asyncio.ensure_future(mock_coro(""))
            _se1 = asyncio.ensure_future(mock_coro(valid_user))
            _se2 = asyncio.ensure_future(mock_coro(data))
        with patch.object(middleware._logger, 'debug') as patch_logger_debug:
            with patch.object(User.Objects, 'validate_token', return_value=_rv1) as patch_validate_token:
                with patch.object(User.Objects, 'refresh_token_expiry', return_value=_rv2) as patch_refresh_token:
                    with patch.object(User.Objects, 'get', side_effect=[_se1, _se2]) as patch_user_get:
                        with patch.object(User.Objects, 'all', return_value=_rv6) as patch_user_all:
                            with patch.object(User.Objects, 'get_role_id_by_name', return_value=_rv3
                                              ) as patch_role_id:
                                with patch.object(auth, 'validate_password', return_value=_rv7):
                                    with patch.object(auth, 'is_valid_role', return_value=_rv4) as patch_role:
                                        with patch.object(User.Objects, 'create', return_value=_rv5
                                                          ) as patch_create_user:
                                            with patch.object(auth._logger, 'info') as patch_auth_logger_info:
                                                resp = await client.post('/fledge/admin/user',
                                                                         data=json.dumps(request_data),
                                                                         headers=ADMIN_USER_HEADER)
                                                assert 200 == resp.status
                                                r = await resp.text()
                                                actual = json.loads(r)
                                                assert msg == actual['message']
                                                assert expected['id'] == actual['user']['userId']
                                                assert expected['uname'] == actual['user']['userName']
                                                assert expected['role_id'] == actual['user']['roleId']
                                            patch_auth_logger_info.assert_called_once_with(msg)
                                        patch_create_user.assert_called_once_with(
                                            request_data['username'], request_data['password'],
                                            int(expected['role_id']), 'any', '', '')
                                    patch_role.assert_called_once_with(int(expected['role_id']))
                            patch_role_id.assert_called_once_with('admin')
                        patch_user_all.assert_called_once_with()
                    assert 2 == patch_user_get.call_count
                    args, kwargs = patch_user_get.call_args_list[0]
                    assert {'uid': valid_user['id']} == kwargs
                    args, kwargs = patch_user_get.call_args_list[1]
                    assert {'username': expected['uname']} == kwargs
                patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
            patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s', 'POST', '/fledge/admin/user')

    async def test_create_user_unknown_exception(self, client):
        request_data = {"username": "ajtest", "password": "F0gl@mp"}
        exc_msg = "Internal Server Error"
        valid_user = {'id': 1, 'uname': 'admin', 'role_id': '1'}
        users = [{'id': 1, 'uname': 'admin', 'real_name': 'Admin user', 'role_id': 1, 'description': 'admin user',
                  'enabled': 't', 'access_method': 'any'}]
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await mock_coro(valid_user['id'])
            _rv2 = await mock_coro(None)
            _rv3 = await mock_coro([{'id': '1'}])
            _rv4 = await mock_coro(True)
            _rv5 = await mock_coro(valid_user)
            _rv6 = await mock_coro(users)
            _rv7 = await mock_coro("")
        else:
            _rv1 = asyncio.ensure_future(mock_coro(valid_user['id']))
            _rv2 = asyncio.ensure_future(mock_coro(None))
            _rv3 = asyncio.ensure_future(mock_coro([{'id': '1'}]))
            _rv4 = asyncio.ensure_future(mock_coro(True))
            _rv5 = asyncio.ensure_future(mock_coro(valid_user))
            _rv6 = asyncio.ensure_future(mock_coro(users))
            _rv7 = asyncio.ensure_future(mock_coro(""))
        with patch.object(middleware._logger, 'debug') as patch_logger_debug:
            with patch.object(User.Objects, 'validate_token', return_value=_rv1) as patch_validate_token:
                with patch.object(User.Objects, 'refresh_token_expiry', return_value=_rv2
                                  ) as patch_refresh_token:
                    with patch.object(User.Objects, 'get', return_value=_rv5) as patch_user_get:
                        with patch.object(User.Objects, 'all', return_value=_rv6) as patch_user_all:
                            with patch.object(User.Objects, 'get_role_id_by_name', return_value=_rv3
                                              ) as patch_role_id:
                                with patch.object(auth, 'validate_password', return_value=_rv7):
                                    with patch.object(auth, 'is_valid_role', return_value=_rv4) as patch_role:
                                        with patch.object(User.Objects, 'create', side_effect=Exception(
                                                exc_msg)) as patch_create_user:
                                            with patch.object(auth._logger, 'error') as patch_logger:
                                                resp = await client.post('/fledge/admin/user',
                                                                         data=json.dumps(request_data),
                                                                         headers=ADMIN_USER_HEADER)
                                                assert 500 == resp.status
                                                assert exc_msg == resp.reason
                                                result = await resp.text()
                                                json_response = json.loads(result)
                                                assert {"message": exc_msg} == json_response
                                            args = patch_logger.call_args
                                            assert 'Failed to create user.' == args[0][1]
                                        patch_create_user.assert_called_once_with(
                                            request_data['username'], request_data['password'], 2, 'any', '', '')
                                    patch_role.assert_called_once_with(2)
                            patch_role_id.assert_called_once_with('admin')
                        patch_user_all.assert_called_once_with()
                    patch_user_get.assert_called_once_with(uid=valid_user['id'])
                patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
            patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s', 'POST', '/fledge/admin/user')

    async def test_create_user_value_error(self, client):
        valid_user = {'id': 1, 'uname': 'admin', 'role_id': '1'}
        request_data = {"username": "ajtest", "password": "F0gl@mp"}
        exc_msg = "Value Error occurred"
        users = [{'id': 1, 'uname': 'admin', 'real_name': 'Admin user', 'role_id': 1, 'description': 'admin user',
                  'enabled': 't', 'access_method': 'any'}]
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await mock_coro(valid_user['id'])
            _rv2 = await mock_coro(None)
            _rv3 = await mock_coro([{'id': '1'}])
            _rv4 = await mock_coro(True)
            _rv5 = await mock_coro(valid_user)
            _rv6 = await mock_coro(users)
            _rv7 = await mock_coro("")
        else:
            _rv1 = asyncio.ensure_future(mock_coro(valid_user['id']))
            _rv2 = asyncio.ensure_future(mock_coro(None))
            _rv3 = asyncio.ensure_future(mock_coro([{'id': '1'}]))
            _rv4 = asyncio.ensure_future(mock_coro(True))
            _rv5 = asyncio.ensure_future(mock_coro(valid_user))
            _rv6 = asyncio.ensure_future(mock_coro(users))
            _rv7 = asyncio.ensure_future(mock_coro(""))
        with patch.object(middleware._logger, 'debug') as patch_logger_debug:
            with patch.object(User.Objects, 'validate_token', return_value=_rv1) as patch_validate_token:
                with patch.object(User.Objects, 'refresh_token_expiry', return_value=_rv2
                                  ) as patch_refresh_token:
                    with patch.object(User.Objects, 'get', return_value=_rv5) as patch_user_get:
                        with patch.object(User.Objects, 'all', return_value=_rv6) as patch_user_all:
                            with patch.object(User.Objects, 'get_role_id_by_name', return_value=_rv3
                                              ) as patch_role_id:
                                with patch.object(auth, 'validate_password', return_value=_rv7):
                                    with patch.object(auth, 'is_valid_role', return_value=_rv4) as patch_role:
                                        with patch.object(User.Objects, 'create', side_effect=ValueError(
                                                exc_msg)) as patch_create_user:
                                            resp = await client.post('/fledge/admin/user', data=json.dumps(
                                                request_data), headers=ADMIN_USER_HEADER)
                                            assert 400 == resp.status
                                            assert exc_msg == resp.reason
                                            result = await resp.text()
                                            json_response = json.loads(result)
                                            assert {"message": exc_msg} == json_response
                                        patch_create_user.assert_called_once_with(
                                            request_data['username'], request_data['password'], 2, 'any', '', '')
                                    patch_role.assert_called_once_with(2)
                            patch_role_id.assert_called_once_with('admin')
                        patch_user_all.assert_called_once_with()
                    patch_user_get.assert_called_once_with(uid=valid_user['id'])
                patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
            patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s', 'POST', '/fledge/admin/user')

    @pytest.mark.parametrize("payload, status_reason", [
        ({"realname": "dd"}, 'Nothing to update.'),
        ({"real_name": ""}, 'Real Name should not be empty.'),
        ({"real_name": "   "}, 'Real Name should not be empty.')
    ])
    async def test_bad_update_me(self, client, mocker, payload, status_reason):
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        user_info = {'role_id': '1', 'id': '2', 'uname': 'user', 'access_method': 'any',
                     'real_name': 'Sat', 'description': 'Normal User'}
        rv = await mock_coro(user_info) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(user_info))
        with patch.object(User.Objects, 'get', return_value=rv) as patch_get_user:
            resp = await client.put('/fledge/user', data=json.dumps(payload), headers=ADMIN_USER_HEADER)
            assert 400 == resp.status
            assert status_reason == resp.reason
            r = await resp.text()
            assert {"message": status_reason} == json.loads(r)
        patch_get_user.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s', 'PUT', '/fledge/user')

    @pytest.mark.parametrize("payload", [
        {"real_name": "AJ"}, {"real_name": "  AJ "}, {"real_name": "AJ "}, {"real_name": "  AJ"}
    ])
    async def test_update_me(self, client, mocker, payload):
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        user_info = {'role_id': '1', 'id': '2', 'uname': 'user', 'access_method': 'any',
                     'real_name': 'AJ', 'description': 'Normal User'}
        user_record = {'rows': [{'user_id': 2}], 'count': 1}
        update_result = {"rows_affected": 1, "response": "updated"}
        storage_client_mock = MagicMock(StorageClientAsync)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info >= (3, 8):
            rv1 = await mock_coro(user_info)
            rv2 = await mock_coro(user_record)
            rv3 = await mock_coro(update_result)
        else:
            rv1 = asyncio.ensure_future(mock_coro(user_info))
            rv2 = asyncio.ensure_future(mock_coro(user_record))
            rv3 = asyncio.ensure_future(mock_coro(update_result))
        with patch.object(User.Objects, 'get', return_value=rv1) as patch_get_user:
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=rv2) as q_tbl_patch:
                    with patch.object(storage_client_mock, 'update_tbl', return_value=rv3) as update_tbl_patch:
                        resp = await client.put('/fledge/user', data=json.dumps(payload), headers=ADMIN_USER_HEADER)
                        assert 200 == resp.status
                        r = await resp.text()
                        assert {"message": "Real name has been updated successfully!"} == json.loads(r)
                    update_tbl_patch.assert_called_once_with("users", '{"values": {"real_name": "AJ"}, '
                                                                      '"where": {"column": "id", "condition": "=", '
                                                                      '"value": 2}}')
                    q_tbl_patch.assert_called_once_with('user_logins', '{"return": ["user_id"], '
                                                                       '"where": {"column": "token", "condition": "=", '
                                                                       '"value": "admin_user_token"}}')
        patch_get_user.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s', 'PUT', '/fledge/user')

    @pytest.mark.parametrize("payload, status_reason", [
        ({"realname": "dd"}, 'Nothing to update.'),
        ({"real_name": ""}, 'Real Name should not be empty.'),
        ({"real_name": "   "}, 'Real Name should not be empty.'),
        ({"access_method": ""}, 'Access method should not be empty.'),
        ({"access_method": "blah"}, "Accepted access method values are ('any', 'pwd', 'cert').")
    ])
    async def test_bad_update_user(self, client, mocker, payload, status_reason):
        uid = 2
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        user_info = {'role_id': '1', 'id': str(uid), 'uname': 'user', 'access_method': 'any',
                     'real_name': 'Sat', 'description': 'Normal User'}
        ret_val = [{'id': '1'}]
        if sys.version_info >= (3, 8):
            _rv = await mock_coro(ret_val)
            _se = await mock_coro(user_info)
        else:
            _rv = asyncio.ensure_future(mock_coro(ret_val))
            _se = asyncio.ensure_future(mock_coro(user_info))

        with patch.object(User.Objects, 'get_role_id_by_name', return_value=_rv) as patch_role_id:
            with patch.object(User.Objects, 'get', return_value=_se) as patch_get_user:
                resp = await client.put('/fledge/admin/{}'.format(uid), data=json.dumps(payload),
                                        headers=ADMIN_USER_HEADER)
                assert 400 == resp.status
                assert status_reason == resp.reason
                r = await resp.text()
                assert {"message": status_reason} == json.loads(r)
            patch_get_user.assert_called_once_with(uid=1)
        patch_role_id.assert_called_once_with('admin')
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s', 'PUT', '/fledge/admin/{}'.format(uid))

    @pytest.mark.parametrize("payload, exp_result", [
        ({"real_name": "Sat"}, {'role_id': '2', 'id': '2', 'uname': 'user', 'access_method': 'any',
                                'real_name': 'Sat', 'description': 'Normal User'}),
        ({"description": "test desc"}, {'role_id': '2', 'id': '2', 'uname': 'user', 'access_method': 'any',
                                        'real_name': 'Normal', 'description': 'test desc'}),
        ({"real_name": "Yamraj", "description": "test desc"}, {'role_id': '2', 'id': '2', 'uname': 'user',
                                                               'access_method': 'any', 'real_name': 'Yamraj',
                                                               'description': 'test desc'}),
        ({"access_method": 'pwd', "real_name": "Yamraj", "description": "test desc"},
         {'role_id': '2', 'id': '2', 'uname': 'user', 'access_method': 'pwd', 'real_name': 'Yamraj',
          'description': 'test desc'})
    ])
    async def test_update_user(self, client, mocker, payload, exp_result):
        uid = 2
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await mock_coro([{'id': '2'}])
            _rv2 = await mock_coro(True)
            _se = await mock_coro(exp_result)
        else:
            _rv1 = asyncio.ensure_future(mock_coro([{'id': '2'}]))
            _rv2 = asyncio.ensure_future(mock_coro(True))
            _se = asyncio.ensure_future(mock_coro(exp_result))

        with patch.object(User.Objects, 'get_role_id_by_name', return_value=_rv1) as patch_role_id:
            with patch.object(User.Objects, 'update', return_value=_rv2) as patch_update:
                with patch.object(User.Objects, 'get', return_value=_se):
                    resp = await client.put('/fledge/admin/{}'.format(uid), data=json.dumps(payload),
                                            headers=ADMIN_USER_HEADER)
                    assert 200 == resp.status
                    r = await resp.text()
                    assert {"user_info": exp_result} == json.loads(r)
            patch_update.assert_called_once_with(str(uid), payload)
        patch_role_id.assert_called_once_with('admin')
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s', 'PUT', '/fledge/admin/{}'.format(
            uid))

    @pytest.mark.parametrize("request_data, msg", [
        ({}, "Current or new password is missing."),
        ({"invalid": 1}, "Current or new password is missing."),
        ({"current_password": 1}, "Current or new password is missing."),
        ({"current_password": "fledge"}, "Current or new password is missing."),
        ({"new_password": 1}, "Current or new password is missing."),
        ({"new_password": "fledge"}, "Current or new password is missing."),
        ({"current_pwd": "fledge", "new_pwd": "fledge1"}, "Current or new password is missing."),
        ({"current_password": "F0gl@mp", "new_password": "F0gl@mp"},
         "New password should not be the same as current password."),
        ({"current_password": "F0gl@mp", "new_password": "FL"}, PASSWORD_MIN_LENGTH_ERROR_MSG),
        ({"current_password": "F0gl@mp", "new_password": 1}, "New password should be a valid string.")
    ])
    async def test_update_password_with_bad_data(self, client, mocker, request_data, msg):
        uid = 2
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker, is_admin=False)
        rv1 = await mock_coro(msg) if sys.version_info.major == 3 and sys.version_info.minor >= 8 else (
            asyncio.ensure_future(mock_coro(msg)))
        with patch.object(auth, 'validate_password', return_value=rv1):
            resp = await client.put('/fledge/user/{}/password'.format(uid), data=json.dumps(request_data),
                                    headers=NORMAL_USER_HEADER)
            assert 400 == resp.status
            assert msg == resp.reason
        patch_logger_debug.assert_called_once_with('Received %s request for %s', 'PUT',
                                                   '/fledge/user/{}/password'.format(uid))
        patch_validate_token.assert_called_once_with(NORMAL_USER_HEADER['Authorization'])
        patch_refresh_token.assert_called_once_with(NORMAL_USER_HEADER['Authorization'])
        patch_user_get.assert_called_once_with(uid=uid)

    async def test_update_password_with_other_user(self, client, mocker):
        uid = 1
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker, is_admin=False)
        resp = await client.put('/fledge/user/{}/password'.format(uid),
                                data=json.dumps({"current_password": "fledge", "new_password": "newfledge"}),
                                headers=NORMAL_USER_HEADER)
        assert 401 == resp.status
        assert "Insufficient privileges to update the password for the given user." == resp.reason
        patch_logger_debug.assert_called_once_with('Received %s request for %s', 'PUT',
                                                   '/fledge/user/{}/password'.format(uid))
        patch_validate_token.assert_called_once_with(NORMAL_USER_HEADER['Authorization'])
        patch_refresh_token.assert_called_once_with(NORMAL_USER_HEADER['Authorization'])
        patch_user_get.assert_called_once_with(uid=2)

    async def test_update_password_with_invalid_current_password(self, client, mocker):
        request_data = {"current_password": "blah", "new_password": "F0gl@mp"}
        uid = 2
        msg = 'Invalid current password.'
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker, is_admin=False)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info >= (3, 8):
            rv1 = await mock_coro("")
            rv2 = await mock_coro(None)
        else:
            rv1 = asyncio.ensure_future(mock_coro(""))
            rv2 = asyncio.ensure_future(mock_coro(None))
        with patch.object(auth, 'validate_password', return_value=rv1):
            with patch.object(User.Objects, 'is_user_exists', return_value=rv2) as patch_user_exists:
                resp = await client.put('/fledge/user/{}/password'.format(uid), data=json.dumps(request_data),
                                        headers=NORMAL_USER_HEADER)
                assert 404 == resp.status
                assert msg == resp.reason
            patch_user_exists.assert_called_once_with(str(uid), request_data['current_password'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s',
                                                   'PUT', '/fledge/user/{}/password'.format(uid))
        patch_validate_token.assert_called_once_with(NORMAL_USER_HEADER['Authorization'])
        patch_refresh_token.assert_called_once_with(NORMAL_USER_HEADER['Authorization'])
        patch_user_get.assert_called_once_with(uid=uid)

    @pytest.mark.parametrize("exception_name, status_code, msg", [
        (ValueError, 400, 'None'),
        (User.DoesNotExist, 404, 'User with ID:<2> does not exist.'),
        (User.PasswordAlreadyUsed, 400, 'The new password should be different from previous 3 used.')
    ])
    async def test_update_password_exceptions(self, client, mocker, exception_name, status_code, msg):
        request_data = {"current_password": "fledge", "new_password": "F0gl@mp"}
        uid = 2
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker, is_admin=False)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info >= (3, 8):
            rv1 = await mock_coro("")
            rv2 = await mock_coro(uid)
        else:
            rv1 = asyncio.ensure_future(mock_coro(""))
            rv2 = asyncio.ensure_future(mock_coro(uid))
        with patch.object(auth, 'validate_password', return_value=rv1):
            with patch.object(User.Objects, 'is_user_exists', return_value=rv2) as patch_user_exists:
                with patch.object(User.Objects, 'update', side_effect=exception_name(msg)) as patch_update:
                    resp = await client.put('/fledge/user/{}/password'.format(uid), data=json.dumps(request_data),
                                            headers=NORMAL_USER_HEADER)
                    assert status_code == resp.status
                    assert msg == resp.reason
                patch_update.assert_called_once_with(2, {'password': request_data['new_password']})
            patch_user_exists.assert_called_once_with(str(uid), request_data['current_password'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s',
                                                   'PUT', '/fledge/user/{}/password'.format(uid))
        patch_validate_token.assert_called_once_with(NORMAL_USER_HEADER['Authorization'])
        patch_refresh_token.assert_called_once_with(NORMAL_USER_HEADER['Authorization'])
        patch_user_get.assert_called_once_with(uid=uid)

    async def test_update_password_unknown_exception(self, client, mocker):
        request_data = {"current_password": "fledge", "new_password": "F0gl@mp"}
        uid = 2
        msg = 'Something went wrong'
        logger_msg = 'Failed to update the user ID:<{}>.'.format(uid)
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker, is_admin=False)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info >= (3, 8):
            rv1 = await mock_coro("")
            rv2 = await mock_coro(uid)
        else:
            rv1 = asyncio.ensure_future(mock_coro(""))
            rv2 = asyncio.ensure_future(mock_coro(uid))
        with patch.object(auth, 'validate_password', return_value=rv1):
            with patch.object(User.Objects, 'is_user_exists', return_value=rv2) as patch_user_exists:
                with patch.object(User.Objects, 'update', side_effect=Exception(msg)) as patch_update:
                    with patch.object(auth._logger, 'error') as patch_logger:
                        resp = await client.put('/fledge/user/{}/password'.format(uid), data=json.dumps(request_data),
                                                headers=NORMAL_USER_HEADER)
                        assert 500 == resp.status
                        assert msg == resp.reason
                    args = patch_logger.call_args
                    assert logger_msg == args[0][1]
                patch_update.assert_called_once_with(2, {'password': request_data['new_password']})
            patch_user_exists.assert_called_once_with(str(uid), request_data['current_password'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s',
                                                   'PUT', '/fledge/user/{}/password'.format(uid))
        patch_validate_token.assert_called_once_with(NORMAL_USER_HEADER['Authorization'])
        patch_refresh_token.assert_called_once_with(NORMAL_USER_HEADER['Authorization'])
        patch_user_get.assert_called_once_with(uid=uid)

    async def test_update_password(self, client, mocker):
        request_data = {"current_password": "fledge", "new_password": "F0gl@mp"}
        ret_val = {'response': 'updated', 'rows_affected': 1}
        user_id = 2
        msg = "Password has been updated successfully for user ID:<{}>.".format(user_id)
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker, is_admin=False)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            rv1 = await mock_coro("")
            rv2 = await mock_coro(user_id)
            rv3 = await mock_coro(ret_val)
        else:
            rv1 = asyncio.ensure_future(mock_coro(""))
            rv2 = asyncio.ensure_future(mock_coro(user_id))
            rv3 = asyncio.ensure_future(mock_coro(ret_val))
        
        with patch.object(auth, 'validate_password', return_value=rv1):
            with patch.object(User.Objects, 'is_user_exists', return_value=rv2) as patch_user_exists:
                with patch.object(User.Objects, 'update', return_value=rv3) as patch_update:
                    with patch.object(auth._logger, 'info') as patch_auth_logger_info:
                        resp = await client.put('/fledge/user/{}/password'.format(user_id),
                                                data=json.dumps(request_data), headers=NORMAL_USER_HEADER)
                        assert 200 == resp.status
                        r = await resp.text()
                        assert {'message': msg} == json.loads(r)
                    patch_auth_logger_info.assert_called_once_with(msg)
                patch_update.assert_called_once_with(user_id, {'password': request_data['new_password']})
            patch_user_exists.assert_called_once_with(str(user_id), request_data['current_password'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s',
                                                   'PUT', '/fledge/user/{}/password'.format(user_id))
        patch_validate_token.assert_called_once_with(NORMAL_USER_HEADER['Authorization'])
        patch_refresh_token.assert_called_once_with(NORMAL_USER_HEADER['Authorization'])
        patch_user_get.assert_called_once_with(uid=user_id)

    @pytest.mark.parametrize("request_data", ['blah', '123blah'])
    async def test_delete_bad_user(self, client, mocker, request_data):
        msg = "invalid literal for int() with base 10: '{}'".format(request_data)
        ret_val = [{'id': '1'}]
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        _rv = await mock_coro(ret_val) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(ret_val))
        with patch.object(User.Objects, 'get_role_id_by_name', return_value=_rv) as patch_role_id:
            resp = await client.delete('/fledge/admin/{}/delete'.format(request_data), headers=ADMIN_USER_HEADER)
            assert 400 == resp.status
            assert msg == resp.reason
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s',
                                                   'DELETE', '/fledge/admin/{}/delete'.format(request_data))

    async def test_delete_admin_user(self, client, mocker):
        msg = "Super admin user can not be deleted."
        ret_val = [{'id': '1'}]
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        _rv = await mock_coro(ret_val) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(ret_val))
        with patch.object(User.Objects, 'get_role_id_by_name', return_value=_rv) as patch_role_id:
            with patch.object(auth._logger, 'warning') as patch_auth_logger_warn:
                resp = await client.delete('/fledge/admin/1/delete', headers=ADMIN_USER_HEADER)
                assert 403 == resp.status
                assert msg == resp.reason
            patch_auth_logger_warn.assert_called_once_with(msg)
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s', 'DELETE', '/fledge/admin/1/delete')

    async def test_delete_own_account(self, client, mocker):
        msg = "You can not delete your own account."
        ret_val = [{'id': '2'}]
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker, is_admin=False)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        _rv = await mock_coro(ret_val) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(ret_val))
        with patch.object(User.Objects, 'get_role_id_by_name', return_value=_rv) as patch_role_id:
            with patch.object(auth._logger, 'warning') as patch_auth_logger_warn:
                resp = await client.delete('/fledge/admin/2/delete', headers=NORMAL_USER_HEADER)
                assert 400 == resp.status
                assert msg == resp.reason
            patch_auth_logger_warn.assert_called_once_with(msg)
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=2)
        patch_refresh_token.assert_called_once_with(NORMAL_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(NORMAL_USER_HEADER['Authorization'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s', 'DELETE', '/fledge/admin/2/delete')

    async def test_delete_invalid_user(self, client, mocker):
        ret_val = {"response": "deleted", "rows_affected": 0}
        msg = 'User with ID:<2> does not exist.'
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await mock_coro([{'id': '1'}])
            _rv2 = await mock_coro(ret_val)
        else:
            _rv1 = asyncio.ensure_future(mock_coro([{'id': '1'}]))
            _rv2 = asyncio.ensure_future(mock_coro(ret_val))

        with patch.object(User.Objects, 'get_role_id_by_name', return_value=_rv1) as patch_role_id:
            with patch.object(User.Objects, 'delete', return_value=_rv2) as patch_user_delete:
                resp = await client.delete('/fledge/admin/2/delete', headers=ADMIN_USER_HEADER)
                assert 404 == resp.status
                assert msg == resp.reason
            patch_user_delete.assert_called_once_with(2)
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s', 'DELETE', '/fledge/admin/2/delete')

    async def test_delete_user(self, client, mocker):
        ret_val = {"response": "deleted", "rows_affected": 1}
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await mock_coro([{'id': '1'}])
            _rv2 = await mock_coro(ret_val)
        else:
            _rv1 = asyncio.ensure_future(mock_coro([{'id': '1'}]))
            _rv2 = asyncio.ensure_future(mock_coro(ret_val))

        with patch.object(User.Objects, 'get_role_id_by_name', return_value=_rv1) as patch_role_id:
            with patch.object(auth._logger, 'info') as patch_auth_logger_info:
                with patch.object(User.Objects, 'delete', return_value=_rv2) as patch_user_delete:
                    resp = await client.delete('/fledge/admin/2/delete', headers=ADMIN_USER_HEADER)
                    assert 200 == resp.status
                    r = await resp.text()
                    assert {'message': 'User has been deleted successfully.'} == json.loads(r)
                patch_user_delete.assert_called_once_with(2)
            patch_auth_logger_info.assert_called_once_with('User with ID:<2> has been deleted successfully.')
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s', 'DELETE', '/fledge/admin/2/delete')

    @pytest.mark.parametrize("exception_name, code, msg", [
        (ValueError, 400, 'None'),
        (User.DoesNotExist, 404, 'User with ID:<2> does not exist.')
    ])
    async def test_delete_user_exceptions(self, client, mocker, exception_name, code, msg):
        ret_val = [{'id': '1'}]
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        _rv = await mock_coro(ret_val) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(ret_val))
        with patch.object(User.Objects, 'get_role_id_by_name', return_value=_rv) as patch_role_id:
            with patch.object(User.Objects, 'delete', side_effect=exception_name(msg)) as patch_user_delete:
                resp = await client.delete('/fledge/admin/2/delete', headers=ADMIN_USER_HEADER)
                assert code == resp.status
                assert msg == resp.reason
            patch_user_delete.assert_called_once_with(2)
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s', 'DELETE', '/fledge/admin/2/delete')

    async def test_delete_user_unknown_exception(self, client, mocker):
        msg = 'Something went wrong'
        ret_val = [{'id': '1'}]
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        _rv = await mock_coro(ret_val) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(ret_val))
        with patch.object(User.Objects, 'get_role_id_by_name', return_value=_rv) as patch_role_id:
            with patch.object(auth._logger, 'error') as patch_logger:
                with patch.object(User.Objects, 'delete', side_effect=Exception(msg)) as patch_user_delete:
                    resp = await client.delete('/fledge/admin/2/delete', headers=ADMIN_USER_HEADER)
                    assert 500 == resp.status
                    assert msg == resp.reason
                patch_user_delete.assert_called_once_with(2)
            args = patch_logger.call_args
            assert 'Failed to delete the user ID:<2>.' == args[0][1]
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s', 'DELETE', '/fledge/admin/2/delete')

    async def test_logout(self, client, mocker):
        ret_val = {'response': 'deleted', 'rows_affected': 1}
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        _rv = await mock_coro(ret_val) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(ret_val))
        with patch.object(auth._logger, 'info') as patch_auth_logger_info:
            with patch.object(User.Objects, 'delete_user_tokens', return_value=_rv) as patch_delete_user_token:
                resp = await client.put('/fledge/2/logout', headers=ADMIN_USER_HEADER)
                assert 200 == resp.status
                r = await resp.text()
                assert {'logout': True} == json.loads(r)
            patch_delete_user_token.assert_called_once_with("2")
        patch_auth_logger_info.assert_called_once_with('User with ID:<2> has been logged out successfully.')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s', 'PUT', '/fledge/2/logout')

    async def test_logout_with_bad_user(self, client, mocker):
        ret_val = {'response': 'deleted', 'rows_affected': 0}
        user_id = 111
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        _rv = await mock_coro(ret_val) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(ret_val))
        with patch.object(User.Objects, 'delete_user_tokens', return_value=_rv) as patch_delete_user_token:
            resp = await client.put('/fledge/{}/logout'.format(user_id), headers=ADMIN_USER_HEADER)
            assert 404 == resp.status
            assert 'Not Found' == resp.reason
        patch_delete_user_token.assert_called_once_with(str(user_id))
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])

    async def test_logout_me(self, client, mocker):
        ret_val = {'response': 'deleted', 'rows_affected': 1}
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        _rv = await mock_coro(ret_val) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(ret_val))
        with patch.object(auth._logger, 'info') as patch_auth_logger_info:
            with patch.object(User.Objects, 'delete_token', return_value=_rv) as patch_delete_token:
                resp = await client.put('/fledge/logout', headers=ADMIN_USER_HEADER)
                assert 200 == resp.status
                r = await resp.text()
                assert {'logout': True} == json.loads(r)
            patch_delete_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_auth_logger_info.assert_called_once_with('User has been logged out successfully.')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s', 'PUT', '/fledge/logout')

    async def test_logout_me_with_bad_token(self, client, mocker):
        ret_val = {'response': 'deleted', 'rows_affected': 0}
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        _rv = await mock_coro(ret_val) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(ret_val))
        with patch.object(auth._logger, 'error') as patch_auth_logger:
            with patch.object(User.Objects, 'delete_token', return_value=_rv) as patch_delete_token:
                resp = await client.put('/fledge/logout', headers=ADMIN_USER_HEADER)
                assert 404 == resp.status
            patch_delete_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s', 'PUT', '/fledge/logout')

    async def test_enable_with_super_admin_user(self, client, mocker):
        msg = 'Restricted for Super Admin user.'
        ret_val = [{'id': '1'}]
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        _rv = await mock_coro(ret_val) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(ret_val))
        with patch.object(User.Objects, 'get_role_id_by_name', return_value=_rv) as patch_role_id:
            with patch.object(auth._logger, 'warning') as patch_logger_warning:
                resp = await client.put('/fledge/admin/1/enable', data=json.dumps({'role_id': 2}),
                                        headers=ADMIN_USER_HEADER)
                assert 403 == resp.status
                assert msg == resp.reason
                r = await resp.text()
                assert {'message': msg} == json.loads(r)
            patch_logger_warning.assert_called_once_with(msg)
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s', 'PUT', '/fledge/admin/1/enable')

    @pytest.mark.parametrize("request_data, msg", [
        ({}, "Nothing to enable user update."),
        ({"enable": 1}, "Nothing to enable user update."),
        ({"enabled": 1}, "Accepted values are True/False only."),
    ])
    async def test_enable_with_bad_data(self, client, mocker, request_data, msg):
        ret_val = [{'id': '1'}]
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        _rv = await mock_coro(ret_val) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(ret_val))
        with patch.object(User.Objects, 'get_role_id_by_name', return_value=_rv) as patch_role_id:
            resp = await client.put('/fledge/admin/2/enable', data=json.dumps(request_data),
                                    headers=ADMIN_USER_HEADER)
            assert 400 == resp.status
            assert msg == resp.reason
            r = await resp.text()
            assert {'message': msg} == json.loads(r)
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s', 'PUT', '/fledge/admin/2/enable')

    @pytest.mark.parametrize("request_data", [
        {"enabled": 'true'}, {"enabled": 'True'}, {"enabled": 'TRUE'}, {"enabled": 'tRUe'},
        {"enabled": 'false'}, {"enabled": 'False'}, {"enabled": 'FALSE'}, {"enabled": 'fAlSe'}
    ])
    async def test_enable_user(self, client, mocker, request_data):
        uid = 2
        if request_data['enabled'].lower() == 'true':
            _modified_enabled_val = 't'
            _text = 'enabled'
            _payload = '{"values": {"enabled": "t"}, "where": {"column": "id", "condition": "=", "value": "2"}}'
        else:
            _modified_enabled_val = 'f'
            _text = 'disabled'
            _payload = '{"values": {"enabled": "f"}, "where": {"column": "id", "condition": "=", "value": "2"}}'

        user_record = {'rows': [{'id': uid, 'role_id': '1', 'uname': 'AJ', 'enabled': 't'}], 'count': 1}
        update_user_record = {'rows': [{'id': uid, 'role_id': '1', 'uname': 'AJ',
                                        'enabled': _modified_enabled_val}], 'count': 1}
        update_result = {"rows_affected": 1, "response": "updated"}
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        audit_details = {'user_id': uid, 'old_value': {'enabled': 't'},
                         'new_value': {'enabled': _modified_enabled_val},
                         'message': "'AJ' user has been {}.".format(_text)}
        storage_client_mock = MagicMock(StorageClientAsync)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await mock_coro([{'id': '1'}])
            _rv2 = await mock_coro(update_result)
            _rv3 = await mock_coro(None)
            _se1 = await mock_coro(user_record)
            _se2 = await mock_coro(update_user_record)
        else:
            _rv1 = asyncio.ensure_future(mock_coro([{'id': '1'}]))
            _rv2 = asyncio.ensure_future(mock_coro(update_result))
            _rv3 = asyncio.ensure_future(mock_coro(None))
            _se1 = asyncio.ensure_future(mock_coro(user_record))
            _se2 = asyncio.ensure_future(mock_coro(update_user_record))

        with patch.object(User.Objects, 'get_role_id_by_name', return_value=_rv1) as patch_role_id:
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(storage_client_mock, 'query_tbl_with_payload',
                                  side_effect=[_se1, _se2]) as q_tbl_patch:
                    with patch.object(storage_client_mock, 'update_tbl',
                                      return_value=_rv2) as update_tbl_patch:
                        with patch.object(AuditLogger, '__init__', return_value=None):
                            with patch.object(AuditLogger, 'information', return_value=_rv3) as patch_audit:
                                resp = await client.put('/fledge/admin/{}/enable'.format(uid), data=json.dumps(
                                    request_data), headers=ADMIN_USER_HEADER)
                                assert 200 == resp.status
                                r = await resp.text()
                                assert {"message": "User with ID:<2> has been {} successfully.".format(_text)
                                        } == json.loads(r)
                            patch_audit.assert_called_once_with('USRCH', audit_details)
                    update_tbl_patch.assert_called_once_with('users', _payload)
                assert 2 == q_tbl_patch.call_count
                args, kwargs = q_tbl_patch.call_args_list[0]
                assert ('users', '{"return": ["id", "uname", "role_id", "enabled"], '
                                 '"where": {"column": "id", "condition": "=", "value": "2"}}') == args
                args, kwargs = q_tbl_patch.call_args_list[1]
                assert ('users', '{"return": ["id", "uname", "role_id", "enabled"], '
                                 '"where": {"column": "id", "condition": "=", "value": "2"}}') == args
            patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s', 'PUT', '/fledge/admin/2/enable')

    async def test_reset_super_admin(self, client, mocker):
        msg = 'Restricted for Super Admin user.'
        ret_val = [{'id': '1'}]
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        _rv = await mock_coro(ret_val) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(ret_val))
        with patch.object(User.Objects, 'get_role_id_by_name', return_value=_rv) as patch_role_id:
            with patch.object(auth._logger, 'warning') as patch_logger_warning:
                resp = await client.put('/fledge/admin/1/reset', data=json.dumps({'role_id': 2}),
                                        headers=ADMIN_USER_HEADER)
                assert 403 == resp.status
                assert msg == resp.reason
            patch_logger_warning.assert_called_once_with(msg)
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s', 'PUT', '/fledge/admin/1/reset')

    @pytest.mark.parametrize("request_data, msg", [
        ({}, "Nothing to update the user."),
        ({"invalid": 1}, "Nothing to update the user."),
        ({"password": "FL"}, PASSWORD_MIN_LENGTH_ERROR_MSG),
        ({"password": 1}, "New password should be in string format.")
    ])
    async def test_reset_with_bad_data(self, client, mocker, request_data, msg):
        ret_val = [{'id': '1'}]
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info >= (3, 8):
            rv1 = await mock_coro(ret_val)
            rv2 = await mock_coro(msg)
        else:
            rv1 = asyncio.ensure_future(mock_coro(ret_val))
            rv2 = asyncio.ensure_future(mock_coro(msg))
        with patch.object(User.Objects, 'get_role_id_by_name', return_value=rv1) as patch_role_id:
            with patch.object(auth, 'validate_password', return_value=rv2):
                resp = await client.put('/fledge/admin/2/reset', data=json.dumps(request_data),
                                        headers=ADMIN_USER_HEADER)
                assert 400 == resp.status
                assert msg == resp.reason
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s', 'PUT', '/fledge/admin/2/reset')

    async def test_reset_with_bad_role(self, client, mocker):
        request_data = {"role_id": "blah"}
        msg = "Invalid or bad role id."
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await mock_coro([{'id': '1'}])
            _rv2 = await mock_coro(False)
        else:
            _rv1 = asyncio.ensure_future(mock_coro([{'id': '1'}]))
            _rv2 = asyncio.ensure_future(mock_coro(False))

        with patch.object(User.Objects, 'get_role_id_by_name', return_value=_rv1) as patch_role_id:
            with patch.object(auth, 'is_valid_role', return_value=_rv2) as patch_role:
                resp = await client.put('/fledge/admin/2/reset', data=json.dumps(request_data),
                                        headers=ADMIN_USER_HEADER)
                assert 400 == resp.status
                assert msg == resp.reason
            patch_role.assert_called_once_with(request_data['role_id'])
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s', 'PUT', '/fledge/admin/2/reset')

    @pytest.mark.parametrize("exception_name, status_code, msg", [
        (ValueError, 400, 'None'),
        (User.DoesNotExist, 404, 'User with ID:<2> does not exist.'),
        (User.PasswordAlreadyUsed, 400, 'The new password should be different from previous 3 used.')
    ])
    async def test_reset_exceptions(self, client, mocker, exception_name, status_code, msg):
        request_data = {'role_id': '2'}
        user_id = 2
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            rv1 = await mock_coro([{'id': '1'}])
            rv2 = await mock_coro(True)
            rv3 = await mock_coro("")
        else:
            rv1 = asyncio.ensure_future(mock_coro([{'id': '1'}]))
            rv2 = asyncio.ensure_future(mock_coro(True))
            rv3 = asyncio.ensure_future(mock_coro(""))
        with patch.object(User.Objects, 'get_role_id_by_name', return_value=rv1) as patch_role_id:
            with patch.object(auth, 'is_valid_role', return_value=rv2) as patch_role:
                with patch.object(auth, 'validate_password', return_value=rv3):
                    with patch.object(User.Objects, 'update', side_effect=exception_name(msg)) as patch_update:
                        with patch.object(auth._logger, 'warning') as patch_logger:
                            resp = await client.put('/fledge/admin/{}/reset'.format(user_id),
                                                    data=json.dumps(request_data), headers=ADMIN_USER_HEADER)
                            assert status_code == resp.status
                            assert msg == resp.reason
                        if exception_name == User.PasswordAlreadyUsed:
                            patch_logger.assert_called_once_with(msg)
                    patch_update.assert_called_once_with(str(user_id), request_data)
            patch_role.assert_called_once_with(request_data['role_id'])
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s', 'PUT', '/fledge/admin/2/reset')

    async def test_reset_unknown_exception(self, client, mocker):
        request_data = {'role_id': '2'}
        user_id = 2
        msg = 'Something went wrong'
        logger_msg = 'Failed to reset the user ID:<{}>.'.format(user_id)

        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            rv1 = await mock_coro([{'id': '1'}])
            rv2 = await mock_coro(True)
            rv3 = await mock_coro("")
        else:
            rv1 = asyncio.ensure_future(mock_coro([{'id': '1'}]))
            rv2 = asyncio.ensure_future(mock_coro(True))
            rv3 = asyncio.ensure_future(mock_coro(""))

        with patch.object(User.Objects, 'get_role_id_by_name', return_value=rv1) as patch_role_id:
            with patch.object(auth, 'is_valid_role', return_value=rv2) as patch_role:
                with patch.object(auth, 'validate_password', return_value=rv3):
                    with patch.object(User.Objects, 'update', side_effect=Exception(msg)) as patch_update:
                        with patch.object(auth._logger, 'error') as patch_logger:
                            resp = await client.put('/fledge/admin/{}/reset'.format(user_id), data=json.dumps(request_data),
                                                    headers=ADMIN_USER_HEADER)
                            assert 500 == resp.status
                            assert msg == resp.reason
                        args = patch_logger.call_args
                        assert logger_msg == args[0][1]
                    patch_update.assert_called_once_with(str(user_id), request_data)
            patch_role.assert_called_once_with(request_data['role_id'])
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_debug.assert_called_once_with('Received %s request for %s', 'PUT', '/fledge/admin/2/reset')

    async def test_reset_role_and_password(self, client, mocker):
        request_data = {'role_id': '2', 'password': 'Test@123'}
        user_id = 2
        msg = 'User with ID:<{}> has been updated successfully.'.format(user_id)
        ret_val = {'response': 'updated', 'rows_affected': 1}
        patch_logger_debug, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            rv1 = await mock_coro([{'id': '1'}])
            rv2 = await mock_coro(True)
            rv3 = await mock_coro(ret_val)
            rv4 = await mock_coro("")
        else:
            rv1 = asyncio.ensure_future(mock_coro([{'id': '1'}]))
            rv2 = asyncio.ensure_future(mock_coro(True))
            rv3 = asyncio.ensure_future(mock_coro(ret_val))
            rv4 = asyncio.ensure_future(mock_coro(""))

        with patch.object(User.Objects, 'get_role_id_by_name', return_value=rv1) as patch_role_id:
            with patch.object(auth, 'is_valid_role', return_value=rv2) as patch_role:
                with patch.object(auth, 'validate_password', return_value=rv4):
                    with patch.object(User.Objects, 'update', return_value=rv3) as patch_update:
                        with patch.object(auth._logger, 'info') as patch_auth_logger_info:
                            resp = await client.put('/fledge/admin/{}/reset'.format(user_id),
                                                    data=json.dumps(request_data), headers=ADMIN_USER_HEADER)
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
        patch_logger_debug.assert_called_once_with('Received %s request for %s', 'PUT', '/fledge/admin/2/reset')

    @pytest.mark.parametrize("auth_method, request_data, ret_val", [
        ("certificate", "-----BEGIN CERTIFICATE----- Test -----END CERTIFICATE-----", (2, "token2", False))
    ])
    async def test_login_auth_certificate(self, client, auth_method, request_data, ret_val):
        hdr = {'content-type': 'text/plain'}

        async def async_mock():
            return ret_val

        async def async_get_user():
            return {'role_id': '2', 'id': '2', 'uname': 'user'}

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await asyncio.sleep(.1)
            _rv2 = await async_mock()
            _rv3 = await async_get_user()
        else:
            _rv1 = asyncio.ensure_future(asyncio.sleep(.1))
            _rv2 = asyncio.ensure_future(async_mock())
            _rv3 = asyncio.ensure_future(async_get_user())
        with patch.object(middleware._logger, 'info'):
            with patch.object(server.Server, "auth_method", auth_method):
                with patch.object(SSLVerifier, 'get_subject', return_value={"commonName": "user"}):
                    with patch.object(User.Objects, 'verify_certificate', return_value=_rv1):
                        with patch.object(User.Objects, 'certificate_login', return_value=_rv2):
                            with patch.object(User.Objects, 'get', return_value=_rv3):
                                with patch.object(auth._logger, 'info'):
                                    req_data = request_data
                                    resp = await client.post('/fledge/login', data=req_data, headers=hdr)
                                    assert 200 == resp.status
                                    r = await resp.text()
                                    actual = json.loads(r)
                                    assert ret_val[0] == actual['uid']
                                    assert ret_val[1] == actual['token']
                                    assert ret_val[2] == actual['admin']

    @pytest.mark.skip(reason="Request mock required")
    @pytest.mark.parametrize("auth_method, request_data, ret_val, expected", [
        ("certificate", {"username": "admin", "password": "fledge"}, (1, "token1", True),
         "Invalid authentication method, use certificate instead."),
    ])
    async def test_login_auth_exception1(self, client, auth_method, request_data, ret_val, expected):
        async def async_mock():
            return ret_val
        with patch.object(middleware._logger, 'info') as patch_logger_debug:
            with patch.object(server.Server, "auth_method", auth_method) as patch_auth_method:
                req_data = json.dumps(request_data) if isinstance(request_data, dict) else request_data
                resp = await client.post('/fledge/login', data=req_data)
                assert 401 == resp.status
                actual = await resp.text()
                assert "401: {}".format(expected) == actual

    @pytest.mark.skip(reason="Request mock required")
    @pytest.mark.parametrize("auth_method, request_data, ret_val, expected", [
        ("password", "-----BEGIN CERTIFICATE----- Test -----END CERTIFICATE-----",
         (2, "token2", False), "Invalid authentication method, use password instead.")
    ])
    async def test_login_auth_exception2(self, client, auth_method, request_data, ret_val, expected):
        TEXT_HEADER = {'content-type': 'text/plain'}

        async def async_mock():
            return ret_val
        with patch.object(middleware._logger, 'info') as patch_logger_debug:
            with patch.object(server.Server, "auth_method", auth_method) as patch_auth_method:
                req_data = request_data
                resp = await client.post('/fledge/login', data=req_data, headers=TEXT_HEADER)
                assert 401 == resp.status
                actual = await resp.text()
                assert "401: {}".format(expected) == actual

    @pytest.mark.parametrize("pwd, error_msg, policy", [
        ("pass", "Password should have minimum 6 characters.", "Any characters"),
        ("passwords", "Password should have maximum 8 characters.", "Any characters"),
        ("password", "Password must contain upper and lower case letters.", "Mixed case Alphabetic"),
        ("password", "Password must contain upper, lower case, uppercase and numeric values.", "Mixed case and numeric"),
        ("password", "Password must contain atleast one upper and lower case letter, numeric and special characters.", "Mixed case, numeric and special characters"),
    ])
    async def test_bad_validate_password(self, pwd, error_msg, policy):
        async def mock_cat():
            return {
            "policy": {
                "description": "Password policy",
                "type": "enumeration",
                "options": [
                    "Any characters",
                    "Mixed case Alphabetic",
                    "Mixed case and numeric",
                    "Mixed case, numeric and special characters"
                ],
                "default": "Any characters",
                "displayName": "Policy",
                "order": "1",
                "value": policy
            },
            "length": {
                "description": "Minimum password length",
                "type": "integer",
                "default": "6",
                "displayName": "Minimum Length",
                "minimum": "6",
                "maximum": "8",
                "order": "2",
                "value": "6"
            },
            "expiration": {
                "description": "Number of days after which passwords must be changed",
                "type": "integer",
                "default": "0",
                "displayName": "Expiry (in Days)",
                "order": "3",
                "value": "0"
            }
        }
        rv = await mock_cat() if sys.version_info.major == 3 and sys.version_info.minor >= 8 else (
            asyncio.ensure_future(mock_cat()))
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(ConfigurationManager, "get_category_all_items", return_value=rv) as patch_get_cat:
                msg = await auth.validate_password(pwd)
                assert error_msg == msg
            patch_get_cat.assert_called_once_with('password')

    @pytest.mark.parametrize("pwd, policy", [
        ("password", "Any characters"), ("Password", "Any characters"), ("Passw0rd", "Any characters"),
        ("passw0rd", "Any characters"), ("PaSsw0#d", "Any characters"), ("paSsw0#1", "Any characters"),
        ("Password", "Mixed case Alphabetic"), ("PassworD", "Mixed case Alphabetic"),
        ("Pass123", "Mixed case Alphabetic"), ("Pass!23", "Mixed case Alphabetic"),
        ("Passw0rd", "Mixed case and numeric"), ("paSSw0rd", "Mixed case and numeric"),
        ("1ass0Rd", "Mixed case and numeric"), ("PASSw0rD", "Mixed case and numeric"),
        ("pAss@!1", "Mixed case, numeric and special characters"),
        ("@Aswe12", "Mixed case, numeric and special characters"),
        ("(Aswe1)", "Mixed case, numeric and special characters"),
        ("s!@#$%G2", "Mixed case, numeric and special characters"),
        ("Fl@3737", "Mixed case, numeric and special characters")
    ])
    async def test_good_validate_password(self, pwd, policy):
        async def mock_cat():
            return {
            "policy": {
                "description": "Password policy",
                "type": "enumeration",
                "options": [
                    "Any characters",
                    "Mixed case Alphabetic",
                    "Mixed case and numeric",
                    "Mixed case, numeric and special characters"
                ],
                "default": "Any characters",
                "displayName": "Policy",
                "order": "1",
                "value": policy
            },
            "length": {
                "description": "Minimum password length",
                "type": "integer",
                "default": "6",
                "displayName": "Minimum Length",
                "minimum": "6",
                "maximum": "8",
                "order": "2",
                "value": "6"
            },
            "expiration": {
                "description": "Number of days after which passwords must be changed",
                "type": "integer",
                "default": "0",
                "displayName": "Expiry (in Days)",
                "order": "3",
                "value": "0"
            }
        }
        rv = await mock_cat() if sys.version_info.major == 3 and sys.version_info.minor >= 8 else (
            asyncio.ensure_future(mock_cat()))
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(ConfigurationManager, "get_category_all_items", return_value=rv) as patch_get_cat:
                msg = await auth.validate_password(pwd)
                assert "" == msg
            patch_get_cat.assert_called_once_with('password')

