# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END


import sys
import asyncio
import json
import pathlib

from unittest.mock import MagicMock, patch
from collections import Counter
from aiohttp import web
import pytest

from fledge.services.core import connect
from fledge.common.web import middleware
from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.services.core import routes
from fledge.services.core.api import certificate_store
from fledge.common.configuration_manager import ConfigurationManager
from fledge.services.core.user_model import User


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


async def mock_coro(*args, **kwargs):
    return None if len(args) == 0 else args[0]


@pytest.fixture
def certs_path():
    return pathlib.Path(__file__).parent


ADMIN_USER_HEADER = {'content-type': 'application/json', 'Authorization': 'admin_user_token'}
REST_API_CAT_INFO = {'certificateName': {'value': 'fledge'}, 'authCertificateName': {'value': 'ca'}}


@pytest.allure.feature("unit")
@pytest.allure.story("api", "certificate-store")
class TestCertificateStore:
    @pytest.fixture
    def client(self, loop, aiohttp_server, aiohttp_client):
        app = web.Application(loop=loop, middlewares=[middleware.optional_auth_middleware])
        # fill the routes table
        routes.setup(app)
        server = loop.run_until_complete(aiohttp_server(app))
        loop.run_until_complete(server.start_server(loop=loop))
        client = loop.run_until_complete(aiohttp_client(server))
        return client

    async def test_get_certs(self, client, certs_path):
        response_content = {'keys': ['fledge.key', 'rsa_private.pem'],
                            'certs': ['fledge.cert', 'test.cer', 'test.crt', 'test.json', 'fledge.pem']}
        with patch.object(certificate_store, '_get_certs_dir', side_effect=[certs_path / 'certs',
                                                                            certs_path / 'json', certs_path / 'pem']):
            with patch('os.walk') as mockwalk:
                mockwalk.return_value = [(str(certs_path / 'certs'), [], ['fledge.cert', 'test.cer', 'test.crt']),
                                         (str(certs_path / 'certs/pem'), [], ['fledge.pem']),
                                         (str(certs_path / 'certs/json'), [], ['test.json']),
                                         (str(certs_path / 'certs'), [], ['fledge.key', 'rsa_private.pem'])
                                         ]
                with patch('os.listdir') as mocked_listdir:
                    mocked_listdir.return_value = ['test.json', 'fledge.pem']
                    resp = await client.get('/fledge/certificate')
                    assert 200 == resp.status
                    res = await resp.text()
                    jdict = json.loads(res)
                    cert = jdict["certs"]
                    assert 5 == len(cert)
                    assert Counter(response_content['certs']) == Counter(cert)
                    key = jdict["keys"]
                    assert 2 == len(key)
                    assert Counter(response_content['keys']) == Counter(key)
                assert 2 == mocked_listdir.call_count
            mockwalk.assert_called_once_with(certs_path / 'certs')

    @pytest.mark.parametrize("files", [
        [], ['fledge.txt']
    ])
    async def test_get_bad_certs(self, client, certs_path, files):
        with patch.object(certificate_store, '_get_certs_dir', side_effect=[certs_path / 'certs',
                                                                            certs_path / 'json', certs_path / 'pem']):

            with patch('os.walk') as mockwalk:
                mockwalk.return_value = [(str(certs_path / 'certs'), [], files),
                                         (str(certs_path / 'certs/pem'), [], files),
                                         (str(certs_path / 'certs/json'), [], files),
                                         (str(certs_path / 'certs'), [], files)
                                         ]
                with patch('os.listdir') as mocked_listdir:
                    mocked_listdir.return_value = []
                    resp = await client.get('/fledge/certificate')
                    assert 200 == resp.status
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert 0 == len(json_response['certs'])
                    assert 0 == len(json_response['keys'])
                    assert {'certs': [], 'keys': []} == json_response
                assert 2 == mocked_listdir.call_count
            mockwalk.assert_called_once_with(certs_path / 'certs')

    async def test_bad_cert_file_upload(self, client, certs_path):
        files = {'bad_cert': open(str(certs_path / 'certs/fledge.cert'), 'rb'),
                 'key': open(str(certs_path / 'certs/fledge.key'), 'rb')}
        resp = await client.post('/fledge/certificate', data=files)
        assert 400 == resp.status
        assert 'Cert file is missing' == resp.reason

    async def test_bad_extension_cert_file_upload(self, client, certs_path):
        cert_valid_extensions = ('.cert', '.cer', '.csr', '.crl', '.crt', '.der', '.json', '.pem', '.p12', '.pfx')
        files = {'cert': open(str(certs_path / 'certs/fledge.txt'), 'rb'),
                 'key': open(str(certs_path / 'certs/fledge.key'), 'rb')}
        resp = await client.post('/fledge/certificate', data=files)
        assert 400 == resp.status
        assert 'Accepted file extensions are {} for cert file'.format(cert_valid_extensions) == resp.reason

    @pytest.mark.parametrize("overwrite", ['blah', '2'])
    async def test_bad_overwrite_file_upload(self, client, certs_path, overwrite):
        files = {'cert': open(str(certs_path / 'certs/fledge.cert'), 'rb'),
                 'key': open(str(certs_path / 'certs/fledge.key'), 'rb'),
                 'overwrite': overwrite}
        resp = await client.post('/fledge/certificate', data=files)
        assert 400 == resp.status
        assert 'Accepted value for overwrite is 0 or 1' == resp.reason

    async def test_exception(self, client, certs_path):
        with pytest.raises(Exception) as excinfo:
            files = {'cert': open(str(certs_path / 'certs/{}'.format("bla.key")), 'rb')}
            resp = await client.post('/fledge/certificate', data=files)
            assert 500 == resp.status
            assert 'Internal Server Error' == resp.reason
        assert excinfo.type is FileNotFoundError
        assert "No such file or directory:" in str(excinfo)

    @pytest.mark.parametrize("cert_name, actual_code, actual_reason", [
        ('root.pem', 404, "Certificate with name root.pem does not exist"),
        ('rsa_private.key', 404, "Certificate with name rsa_private.key does not exist")
    ])
    async def test_bad_delete_cert_with_invalid_filename(self, client, cert_name, actual_code, actual_reason):
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        _rv = await mock_coro(REST_API_CAT_INFO) if sys.version_info >= (3, 8) else asyncio.ensure_future(
            mock_coro(REST_API_CAT_INFO))
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_category_all_items', return_value=_rv) as patch_get_cat_all_items:
                resp = await client.delete('/fledge/certificate/{}'.format(cert_name))
                assert actual_code == resp.status
                assert actual_reason == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {"message": actual_reason} == json_response
            patch_get_cat_all_items.assert_called_once_with(category_name='rest_api')

    @pytest.mark.parametrize("cert_name, actual_code, actual_reason", [
        ('root.txt', 400, "Accepted file extensions are "
                          "('.cert', '.cer', '.csr', '.crl', '.crt', '.der', '.json', '.key', '.pem', '.p12', '.pfx')")
    ])
    async def test_bad_delete_cert(self, client, cert_name, actual_code, actual_reason):
        resp = await client.delete('/fledge/certificate/{}'.format(cert_name))
        assert actual_code == resp.status
        assert actual_reason == resp.reason
        result = await resp.text()
        json_response = json.loads(result)
        assert {"message": actual_reason} == json_response

    async def test_bad_delete_cert_if_in_use(self, client):
        cert_name = 'fledge.cert'
        with patch.object(certificate_store._logger, 'warning') as patch_logger:
            resp = await client.delete('/fledge/certificate/{}'.format(cert_name))
            assert 403 == resp.status
            assert certificate_store.FORBIDDEN_MSG == resp.reason
            result = await resp.text()
            json_response = json.loads(result)
            assert {"message": certificate_store.FORBIDDEN_MSG} == json_response
        patch_logger.assert_called_once_with(certificate_store.FORBIDDEN_MSG)

    async def test_bad_type_delete_cert(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        msg = 'Only cert and key are allowed for the value of type param'
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        _rv = await mock_coro(REST_API_CAT_INFO) if sys.version_info >= (3, 8) else asyncio.ensure_future(
            mock_coro(REST_API_CAT_INFO))
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_category_all_items', return_value=_rv) as patch_get_cat_all_items:
                resp = await client.delete('/fledge/certificate/server.cert?type=pem')
                assert 400 == resp.status
                assert msg == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {"message": msg} == json_response
            patch_get_cat_all_items.assert_called_once_with(category_name='rest_api')

    @pytest.mark.parametrize("cert_name, param", [
        ('fledge.json', '?type=cert'),
        ('fledge.pem', '?type=cert'),
        ('test.cer', '?type=cert'),
        ('test.crt', '?type=cert'),
        ('rsa_private.pem', '?type=key'),
    ])
    async def test_delete_cert_with_type(self, client, cert_name, param):
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        cat_info = {'certificateName': {'value': 'foo'}, 'authCertificateName': {'value': 'ca'}}
        _rv = await mock_coro(cat_info) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(cat_info))
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_category_all_items', return_value=_rv) as patch_get_cat_all_items:
                with patch('os.path.isfile', return_value=True):
                    with patch('os.remove', return_value=True) as patch_remove:
                        resp = await client.delete('/fledge/certificate/{}{}'.format(cert_name, param))
                        assert 200 == resp.status
                        result = await resp.text()
                        json_response = json.loads(result)
                        assert '{} has been deleted successfully'.format(cert_name) == json_response['result']
                    assert 1 == patch_remove.call_count
            patch_get_cat_all_items.assert_called_once_with(category_name='rest_api')

    async def test_delete_cert(self, client, certs_path, cert_name='server.cert'):
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        _rv = await mock_coro(REST_API_CAT_INFO) if sys.version_info >= (3, 8) else asyncio.ensure_future(
            mock_coro(REST_API_CAT_INFO))
        with patch.object(certificate_store, '_get_certs_dir', return_value=str(certs_path / 'certs') + '/'):
            with patch('os.walk') as mockwalk:
                mockwalk.return_value = [(str(certs_path / 'certs'), [], [cert_name])]
                with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                    with patch.object(c_mgr, 'get_category_all_items', return_value=_rv) as patch_get_cat_all_items:
                        with patch('os.remove', return_value=True) as patch_remove:
                            resp = await client.delete('/fledge/certificate/{}'.format(cert_name))
                            assert 200 == resp.status
                            result = await resp.text()
                            json_response = json.loads(result)
                            assert '{} has been deleted successfully'.format(cert_name) == json_response['result']
                        assert 1 == patch_remove.call_count
                    patch_get_cat_all_items.assert_called_once_with(category_name='rest_api')

    async def test_default_upload(self, client, certs_path):
        files = {'key': open(str(certs_path / 'certs/fledge.key'), 'rb'),
                 'cert': open(str(certs_path / 'certs/fledge.cert'), 'rb')}
        with patch.object(certificate_store._logger, 'warning') as patch_logger:
            resp = await client.post('/fledge/certificate', data=files)
            assert 403 == resp.status
            assert certificate_store.FORBIDDEN_MSG == resp.reason
            result = await resp.text()
            json_response = json.loads(result)
            assert {"message": certificate_store.FORBIDDEN_MSG} == json_response
        patch_logger.assert_called_once_with(certificate_store.FORBIDDEN_MSG)


@pytest.allure.feature("unit")
@pytest.allure.story("api", "upload-certificate-store-with-authentication-mandatory")
class TestUploadCertStoreIfAuthenticationIsMandatory:
    AUTH_HEADER = {'Authorization': 'admin_user_token'}

    @pytest.fixture
    def client(self, loop, aiohttp_server, aiohttp_client):
        app = web.Application(loop=loop, middlewares=[middleware.auth_middleware])
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
        patch_logger_info = mocker.patch.object(middleware._logger, 'info')
        patch_validate_token = mocker.patch.object(User.Objects, 'validate_token', return_value=_rv1)
        patch_refresh_token = mocker.patch.object(User.Objects, 'refresh_token_expiry', return_value=_rv2)
        patch_user_get = mocker.patch.object(User.Objects, 'get', return_value=_rv3)
        return patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get

    async def test_bad_upload_when_admin_role_is_required(self, client, certs_path, mocker):
        files = {'key': open(str(certs_path / 'certs/fledge.key'), 'rb'),
                 'cert': open(str(certs_path / 'certs/fledge.cert'), 'rb')}
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker, is_admin=False)
        msg = 'admin role permissions required to overwrite the default installed auth/TLS certificates.'
        with patch.object(certificate_store._logger, 'warning') as patch_logger:
            resp = await client.post('/fledge/certificate', data=files, headers=self.AUTH_HEADER)
            assert 403 == resp.status
            assert msg == resp.reason
            result = await resp.text()
            json_response = json.loads(result)
            assert {"message": msg} == json_response
        patch_logger.assert_called_once_with(msg)
        patch_user_get.assert_called_once_with(uid=2)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/fledge/certificate')

    async def test_bad_upload_when_cert_in_use_and_with_non_admin_role(self, client, certs_path, mocker):
        files = {'cert': open(str(certs_path / 'certs/test.cer'), 'rb')}
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker, is_admin=False)
        msg = 'Certificate with name test.cer is configured to be used, ' \
              'An `admin` role permissions required to add/overwrite.'
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        cat_info = {'certificateName':  {'value': 'test'},  'authCertificateName':  {'value': 'foo'}}
        _rv = await mock_coro(cat_info) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(cat_info))
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        with patch.object(certificate_store._logger, 'warning') as patch_logger:
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(c_mgr, 'get_category_all_items', return_value=_rv) as patch_get_cat_all_items:
                    resp = await client.post('/fledge/certificate', data=files, headers=self.AUTH_HEADER)
                    assert 403 == resp.status
                    assert msg == resp.reason
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert {"message": msg} == json_response
                patch_get_cat_all_items.assert_called_once_with(category_name='rest_api')
        patch_logger.assert_called_once_with(msg)
        patch_user_get.assert_called_once_with(uid=2)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/fledge/certificate')

    async def test_upload_as_admin(self, client, certs_path, mocker):
        files = {'key': open(str(certs_path / 'certs/fledge.key'), 'rb'),
                 'cert': open(str(certs_path / 'certs/fledge.cert'), 'rb')}
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        with patch.object(certificate_store, '_get_certs_dir', return_value=certs_path / 'certs'):
            with patch.object(certificate_store, '_find_file', return_value=[]) as patch_find_file:
                resp = await client.post('/fledge/certificate', data=files, headers=self.AUTH_HEADER)
                assert 200 == resp.status
            result = await resp.text()
            json_response = json.loads(result)
            assert 'fledge.key and fledge.cert have been uploaded successfully' == json_response['result']
            assert 2 == patch_find_file.call_count
            args, kwargs = patch_find_file.call_args_list[0]
            assert ('fledge.cert', certificate_store._get_certs_dir('/certs/')) == args
            args, kwargs = patch_find_file.call_args_list[1]
            assert ('fledge.key', certificate_store._get_certs_dir('/certs/')) == args
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/fledge/certificate')

    @pytest.mark.parametrize("filename", ["fledge.pem", "fledge.cert", "test.cer", "test.crt"])
    async def test_upload_with_cert_only(self, client, certs_path, mocker, filename):
        files = {'cert': open(str(certs_path / 'certs/{}'.format(filename)), 'rb')}
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        with patch.object(certificate_store, '_get_certs_dir', return_value=certs_path / 'certs/pem'):
            with patch.object(certificate_store, '_find_file', return_value=[]) as patch_find_file:
                resp = await client.post('/fledge/certificate', data=files, headers=self.AUTH_HEADER)
                assert 200 == resp.status
                result = await resp.text()
                json_response = json.loads(result)
                assert '{} has been uploaded successfully'.format(filename) == json_response['result']
            assert 1 == patch_find_file.call_count
            args, kwargs = patch_find_file.call_args
            assert (filename, certificate_store._get_certs_dir('/certs/pem')) == args
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/fledge/certificate')

    async def test_file_upload_with_overwrite(self, client, certs_path, mocker):
        files = {'key': open(str(certs_path / 'certs/fledge.key'), 'rb'),
                 'cert': open(str(certs_path / 'certs/fledge.cert'), 'rb'),
                 'overwrite': '1'}
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        with patch.object(certificate_store, '_get_certs_dir', return_value=certs_path / 'certs'):
            with patch.object(certificate_store, '_find_file', return_value=[]) as patch_find_file:
                resp = await client.post('/fledge/certificate', data=files, headers=self.AUTH_HEADER)
                assert 200 == resp.status
                result = await resp.text()
                json_response = json.loads(result)
                assert 'fledge.key and fledge.cert have been uploaded successfully' == json_response['result']
            assert 2 == patch_find_file.call_count
            args, kwargs = patch_find_file.call_args_list[0]
            assert ('fledge.cert', certificate_store._get_certs_dir('/certs/')) == args
            args, kwargs = patch_find_file.call_args_list[1]
            assert ('fledge.key', certificate_store._get_certs_dir('/certs/')) == args
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/fledge/certificate')

    async def test_bad_extension_key_file_upload(self, client, certs_path, mocker):
        key_valid_extensions = ('.key', '.pem')
        files = {'cert': open(str(certs_path / 'certs/fledge.cert'), 'rb'),
                 'key': open(str(certs_path / 'certs/fledge.txt'), 'rb')}
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        resp = await client.post('/fledge/certificate', data=files, headers=self.AUTH_HEADER)
        assert 400 == resp.status
        assert 'Accepted file extensions are {} for key file'.format(key_valid_extensions) == resp.reason
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/fledge/certificate')

    async def test_upload_with_existing_and_no_overwrite(self, client, certs_path, mocker):
        files = {'key': open(str(certs_path / 'certs/fledge.key'), 'rb'),
                 'cert': open(str(certs_path / 'certs/fledge.cert'), 'rb')}
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        with patch.object(certificate_store, '_get_certs_dir', return_value=certs_path / 'certs'):
            with patch.object(certificate_store, '_find_file', return_value=["v"]) as patch_file:
                resp = await client.post('/fledge/certificate', data=files, headers=self.AUTH_HEADER)
                assert 400 == resp.status
                assert 'Certificate with the same name already exists! To overwrite, set the ' \
                       'overwrite flag' == resp.reason
            assert 1 == patch_file.call_count
            args, kwargs = patch_file.call_args
            assert ('fledge.cert', certificate_store._get_certs_dir('/certs')) == args
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'POST', '/fledge/certificate')


@pytest.allure.feature("unit")
@pytest.allure.story("api", "delete-certificate-store-with-authentication-mandatory")
class TestDeleteCertStoreIfAuthenticationIsMandatory:
    @pytest.fixture
    def client(self, loop, aiohttp_server, aiohttp_client):
        app = web.Application(loop=loop, middlewares=[middleware.auth_middleware])
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
        patch_logger_info = mocker.patch.object(middleware._logger, 'info')
        patch_validate_token = mocker.patch.object(User.Objects, 'validate_token', return_value=_rv1)
        patch_refresh_token = mocker.patch.object(User.Objects, 'refresh_token_expiry', return_value=_rv2)
        patch_user_get = mocker.patch.object(User.Objects, 'get', return_value=_rv3)
        return patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get

    @pytest.mark.parametrize("cert_name, actual_code, actual_reason", [
        ('root.pem', 404, "Certificate with name root.pem does not exist"),
        ('rsa_private.key', 404, "Certificate with name rsa_private.key does not exist")
    ])
    async def test_bad_delete_cert_with_invalid_filename(self, client, mocker, cert_name, actual_code, actual_reason):
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await mock_coro([{'id': '1'}])
            _rv2 = await mock_coro(REST_API_CAT_INFO)
        else:
            _rv1 = asyncio.ensure_future(mock_coro([{'id': '1'}]))
            _rv2 = asyncio.ensure_future(mock_coro(REST_API_CAT_INFO))
        with patch.object(User.Objects, 'get_role_id_by_name', return_value=_rv1) as patch_role_id:
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(c_mgr, 'get_category_all_items', return_value=_rv2) as patch_get_cat_all_items:
                    resp = await client.delete('/fledge/certificate/{}'.format(cert_name), headers=ADMIN_USER_HEADER)
                    assert actual_code == resp.status
                    assert actual_reason == resp.reason
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert {"message": actual_reason} == json_response
                patch_get_cat_all_items.assert_called_once_with(category_name='rest_api')
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'DELETE',
                                                  '/fledge/certificate/{}'.format(cert_name))

    @pytest.mark.parametrize("cert_name, actual_code, actual_reason", [
        ('root.txt', 400, "Accepted file extensions are "
                          "('.cert', '.cer', '.csr', '.crl', '.crt', '.der', '.json', '.key', '.pem', '.p12', '.pfx')")
    ])
    async def test_bad_delete_cert(self, client, mocker, cert_name, actual_code, actual_reason):
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        _payload = [{'id': '1'}]
        _rv = await mock_coro(_payload) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(_payload))
        with patch.object(User.Objects, 'get_role_id_by_name', return_value=_rv):
            resp = await client.delete('/fledge/certificate/{}'.format(cert_name), headers=ADMIN_USER_HEADER)
            assert actual_code == resp.status
            assert actual_reason == resp.reason
            result = await resp.text()
            json_response = json.loads(result)
            assert {"message": actual_reason} == json_response
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'DELETE',
                                                  '/fledge/certificate/{}'.format(cert_name))

    async def test_delete_cert_if_configured_to_use(self, client, mocker):
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        cert_name = 'fledge.cert'
        msg = 'Certificate with name {} is configured for use, you can not delete but overwrite if required.'.format(
            cert_name)
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await mock_coro([{'id': '1'}])
            _rv2 = await mock_coro(REST_API_CAT_INFO)
        else:
            _rv1 = asyncio.ensure_future(mock_coro([{'id': '1'}]))
            _rv2 = asyncio.ensure_future(mock_coro(REST_API_CAT_INFO))
        with patch.object(User.Objects, 'get_role_id_by_name', return_value=_rv1) as patch_role_id:
            with patch('os.path.isfile', return_value=True):
                with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                    with patch.object(c_mgr, 'get_category_all_items', return_value=_rv2) as patch_get_cat_all_items:
                        resp = await client.delete('/fledge/certificate/{}'.format(cert_name),
                                                   headers=ADMIN_USER_HEADER)
                        assert 409 == resp.status
                        assert msg == resp.reason
                        result = await resp.text()
                        json_response = json.loads(result)
                        assert {"message": msg} == json_response
                    patch_get_cat_all_items.assert_called_once_with(category_name='rest_api')
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'DELETE',
                                                  '/fledge/certificate/{}'.format(cert_name))

    async def test_bad_type_delete_cert(self, client, mocker):
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        cert_name = 'server.cert'
        msg = 'Only cert and key are allowed for the value of type param'
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await mock_coro([{'id': '1'}])
            _rv2 = await mock_coro(REST_API_CAT_INFO)
        else:
            _rv1 = asyncio.ensure_future(mock_coro([{'id': '1'}]))
            _rv2 = asyncio.ensure_future(mock_coro(REST_API_CAT_INFO))
        
        with patch.object(User.Objects, 'get_role_id_by_name', return_value=_rv1) as patch_role_id:
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(c_mgr, 'get_category_all_items', return_value=_rv2) as patch_get_cat_all_items:
                    resp = await client.delete('/fledge/certificate/{}?type=pem'.format(cert_name),
                                               headers=ADMIN_USER_HEADER)
                    assert 400 == resp.status
                    assert msg == resp.reason
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert {"message": msg} == json_response
                patch_get_cat_all_items.assert_called_once_with(category_name='rest_api')
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'DELETE',
                                                  '/fledge/certificate/{}'.format(cert_name))

    @pytest.mark.parametrize("cert_name, param", [
        ('fledge.json', '?type=cert'),
        ('fledge.pem', '?type=cert'),
        ('test.cer', '?type=cert'),
        ('test.crt', '?type=cert'),
        ('rsa_private.pem', '?type=key'),
    ])
    async def test_delete_cert_with_type(self, client, mocker, cert_name, param):
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        cat_info = {'certificateName':  {'value': 'foo'},  'authCertificateName':  {'value': 'ca'}}
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await mock_coro([{'id': '1'}])
            _rv2 = await mock_coro(cat_info)
        else:
            _rv1 = asyncio.ensure_future(mock_coro([{'id': '1'}]))
            _rv2 = asyncio.ensure_future(mock_coro(cat_info))
        with patch.object(User.Objects, 'get_role_id_by_name', return_value=_rv1) as patch_role_id:
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(c_mgr, 'get_category_all_items', return_value=_rv2) as patch_get_cat_all_items:
                    with patch('os.path.isfile', return_value=True):
                        with patch('os.remove', return_value=True) as patch_remove:
                            resp = await client.delete('/fledge/certificate/{}{}'.format(cert_name, param),
                                                       headers=ADMIN_USER_HEADER)
                            assert 200 == resp.status
                            result = await resp.text()
                            json_response = json.loads(result)
                            assert '{} has been deleted successfully'.format(cert_name) == json_response['result']
                        assert 1 == patch_remove.call_count
                patch_get_cat_all_items.assert_called_once_with(category_name='rest_api')
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'DELETE',
                                                  '/fledge/certificate/{}'.format(cert_name))

    async def test_delete_cert(self, client, mocker, certs_path, cert_name='server.cert'):
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        patch_logger_info, patch_validate_token, patch_refresh_token, patch_user_get = await self.auth_token_fixture(
            mocker)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await mock_coro([{'id': '1'}])
            _rv2 = await mock_coro(REST_API_CAT_INFO)
        else:
            _rv1 = asyncio.ensure_future(mock_coro([{'id': '1'}]))
            _rv2 = asyncio.ensure_future(mock_coro(REST_API_CAT_INFO))
        
        with patch.object(User.Objects, 'get_role_id_by_name', return_value=_rv1) as patch_role_id:
            with patch.object(certificate_store, '_get_certs_dir', return_value=str(certs_path / 'certs') + '/'):
                with patch('os.walk') as mockwalk:
                    mockwalk.return_value = [(str(certs_path / 'certs'), [], [cert_name])]
                    with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                        with patch.object(c_mgr, 'get_category_all_items',
                                          return_value=_rv2) as patch_get_cat_all_items:
                            with patch('os.remove', return_value=True) as patch_remove:
                                resp = await client.delete('/fledge/certificate/{}'.format(cert_name),
                                                           headers=ADMIN_USER_HEADER)
                                assert 200 == resp.status
                                result = await resp.text()
                                json_response = json.loads(result)
                                assert '{} has been deleted successfully'.format(cert_name) == json_response['result']
                            assert 1 == patch_remove.call_count
                        patch_get_cat_all_items.assert_called_once_with(category_name='rest_api')
        patch_role_id.assert_called_once_with('admin')
        patch_user_get.assert_called_once_with(uid=1)
        patch_refresh_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_validate_token.assert_called_once_with(ADMIN_USER_HEADER['Authorization'])
        patch_logger_info.assert_called_once_with('Received %s request for %s', 'DELETE',
                                                  '/fledge/certificate/{}'.format(cert_name))    


