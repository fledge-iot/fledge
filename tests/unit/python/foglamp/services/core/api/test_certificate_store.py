# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


import json
import pathlib

from unittest.mock import MagicMock, patch
from aiohttp import web
import pytest

from foglamp.services.core import connect
from foglamp.common.storage_client.storage_client import StorageClientAsync
from foglamp.services.core import routes
from foglamp.services.core.api import certificate_store
from foglamp.common.configuration_manager import ConfigurationManager

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("api", "certificate-store")
class TestCertificateStore:

    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop)
        # fill the routes table
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    @pytest.fixture
    def certs_path(self):
        return pathlib.Path(__file__).parent

    async def test_get_certs(self, client, certs_path):
        response_content = [{"cert": "foglamp.cert", "key": "foglamp.key"},
                            {"cert": "server.cert", "key": ""}]
        with patch.object(certificate_store, '_get_certs_dir', return_value=certs_path / 'certs'):
            with patch('os.walk') as mockwalk:
                mockwalk.return_value = [
                    (certs_path / 'certs', [], ['foglamp.cert', 'foglamp.key', 'foglamp.txt', 'server.cert'])
                ]
                resp = await client.get('/foglamp/certificate')
                assert 200 == resp.status
                res = await resp.text()
                jdict = json.loads(res)
                result = jdict["certificates"]
                assert 2 == len(result)
                assert response_content[0] in result
                assert response_content[1] in result
            mockwalk.assert_called_once_with(certs_path / 'certs')

    async def test_get_certs_if_dir_is_empty(self, client, certs_path):
        with patch.object(certificate_store, '_get_certs_dir', return_value=certs_path / 'certs'):
            with patch('os.walk') as mockwalk:
                mockwalk.return_value = [(certs_path / 'certs', [], [])]
                resp = await client.get('/foglamp/certificate')
                assert 200 == resp.status
                result = await resp.text()
                json_response = json.loads(result)
                assert 0 == len(json_response['certificates'])
                assert {'certificates': []} == json_response
            mockwalk.assert_called_once_with(certs_path / 'certs')

    async def test_get_certs_if_bad_extension(self, client, certs_path):
        with patch.object(certificate_store, '_get_certs_dir', return_value=certs_path / 'certs'):
            with patch('os.walk') as mockwalk:
                mockwalk.return_value = [(certs_path / 'certs', [], ['foglamp.txt'])]
                resp = await client.get('/foglamp/certificate')
                assert 200 == resp.status
                result = await resp.text()
                json_response = json.loads(result)
                assert 0 == len(json_response['certificates'])
                assert {'certificates': []} == json_response
            mockwalk.assert_called_once_with(certs_path / 'certs')

    async def test_get_certs_if_pair_is_missing(self, client, certs_path):
        actual_response = {'certificates': [{'key': '', 'cert': 'server.cert'}]}
        with patch.object(certificate_store, '_get_certs_dir', return_value=certs_path / 'certs'):
            with patch('os.walk') as mockwalk:
                mockwalk.return_value = [(certs_path / 'certs', [], ['server.cert'])]
                resp = await client.get('/foglamp/certificate')
                assert 200 == resp.status
                result = await resp.text()
                json_response = json.loads(result)
                assert 1 == len(json_response['certificates'])
                assert actual_response == json_response
            mockwalk.assert_called_once_with(certs_path / 'certs')

    async def test_upload(self, client, certs_path):
        files = {'key': open(str(certs_path / 'certs/foglamp.key'), 'rb'),
                 'cert': open(str(certs_path / 'certs/foglamp.cert'), 'rb')}
        with patch.object(certificate_store, '_get_certs_dir', return_value=certs_path / 'certs'):
            with patch.object(certificate_store, '_find_file', return_value=[]) as patch_find_file:
                resp = await client.post('/foglamp/certificate', data=files)
                assert 200 == resp.status
                result = await resp.text()
                json_response = json.loads(result)
                assert 'foglamp.key and foglamp.cert have been uploaded successfully' == json_response['result']
            assert 1 == patch_find_file.call_count
            args, kwargs = patch_find_file.call_args
            assert ('foglamp.cert', certificate_store._get_certs_dir()) == args

    async def test_file_upload_with_overwrite(self, client, certs_path):
        files = {'key': open(str(certs_path / 'certs/foglamp.key'), 'rb'),
                 'cert': open(str(certs_path / 'certs/foglamp.cert'), 'rb'),
                 'overwrite': '1'}
        with patch.object(certificate_store, '_get_certs_dir', return_value=certs_path / 'certs'):
            with patch.object(certificate_store, '_find_file', return_value=[]) as patch_find_file:
                resp = await client.post('/foglamp/certificate', data=files)
                assert 200 == resp.status
                result = await resp.text()
                json_response = json.loads(result)
                assert 'foglamp.key and foglamp.cert have been uploaded successfully' == json_response['result']
            assert 1 == patch_find_file.call_count
            args, kwargs = patch_find_file.call_args
            assert ('foglamp.cert', certificate_store._get_certs_dir()) == args

    async def test_file_upload_with_different_names(self, client, certs_path):
        files = {'key': open(str(certs_path / 'certs/foglamp.key'), 'rb'),
                 'cert': open(str(certs_path / 'certs/server.cert'), 'rb')}
        resp = await client.post('/foglamp/certificate', data=files)
        assert 400 == resp.status
        assert 'key and certs file name should match' == resp.reason

    async def test_bad_key_file_upload(self, client, certs_path):
        files = {'bad_key': open(str(certs_path / 'certs/foglamp.key'), 'rb'),
                 'cert': open(str(certs_path / 'certs/foglamp.cert'), 'rb')
                 }
        resp = await client.post('/foglamp/certificate', data=files)
        assert 400 == resp.status
        assert 'key or certs file is missing' == resp.reason

    async def test_bad_cert_file_upload(self, client, certs_path):
        files = {'bad_cert': open(str(certs_path / 'certs/foglamp.cert'), 'rb'),
                 'key': open(str(certs_path / 'certs/foglamp.key'), 'rb')}
        resp = await client.post('/foglamp/certificate', data=files)
        assert 400 == resp.status
        assert 'key or certs file is missing' == resp.reason

    async def test_bad_extension_file_upload(self, client, certs_path):
        files = {'cert': open(str(certs_path / 'certs/foglamp.txt'), 'rb'),
                 'key': open(str(certs_path / 'certs/foglamp.key'), 'rb')}
        resp = await client.post('/foglamp/certificate', data=files)
        assert 400 == resp.status
        assert 'Accepted file extensions are .key and .cert' == resp.reason

    @pytest.mark.parametrize("overwrite", ['blah', '2'])
    async def test_bad_overwrite_file_upload(self, client, certs_path, overwrite):
        files = {'cert': open(str(certs_path / 'certs/foglamp.cert'), 'rb'),
                 'key': open(str(certs_path / 'certs/foglamp.key'), 'rb'),
                 'overwrite': overwrite}
        resp = await client.post('/foglamp/certificate', data=files)
        assert 400 == resp.status
        assert 'Accepted value for overwrite is 0 or 1' == resp.reason

    async def test_upload_with_existing_and_no_overwrite(self, client, certs_path):
        files = {'key': open(str(certs_path / 'certs/foglamp.key'), 'rb'),
                 'cert': open(str(certs_path / 'certs/foglamp.cert'), 'rb')}
        with patch.object(certificate_store, '_get_certs_dir', return_value=certs_path / 'certs'):
            with patch.object(certificate_store, '_find_file', return_value=["v"]) as patch_file:
                resp = await client.post('/foglamp/certificate', data=files)
                assert 400 == resp.status
                assert 'Certificate with the same name already exists. To overwrite set the overwrite to 1' == resp.reason
            assert 1 == patch_file.call_count
            args, kwargs = patch_file.call_args
            assert ('foglamp.cert', certificate_store._get_certs_dir()) == args

    async def test_exception(self, client):
        files = {'cert': 'certs/bla.cert', 'key': 'certs/bla.key'}
        resp = await client.post('/foglamp/certificate', data=files)
        assert 500 == resp.status
        assert 'Internal Server Error' == resp.reason

    @pytest.mark.parametrize("cert_name, actual_code, actual_reason", [
        ('', 404, "Not Found"),
        ('blah', 404, "Certificate with name blah does not exist"),
    ])
    async def test_bad_delete_cert(self, client, cert_name, actual_code, actual_reason):
        resp = await client.delete('/foglamp/certificate/{}'.format(cert_name))
        assert actual_code == resp.status
        assert actual_reason == resp.reason

    async def test_bad_delete_cert_if_in_use(self, client):
        async def async_mock():
            return {'value': 'foglamp'}

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch('os.path.isfile', return_value=True):
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(c_mgr, 'get_category_item', return_value=async_mock()) as patch_cfg:
                    resp = await client.delete('/foglamp/certificate/foglamp')
                    assert 409 == resp.status
                    assert 'Certificate with name foglamp is already in use, you can not delete' == resp.reason
                assert 1 == patch_cfg.call_count
                args, kwargs = patch_cfg.call_args
                assert ({'item_name': 'certificateName', 'category_name': 'rest_api'}) == kwargs

    async def test_delete_cert(self, client):
        async def async_mock():
            return {'value': 'test'}

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_category_item', return_value=async_mock()):
                with patch('os.path.isfile', return_value=True):
                    with patch('os.remove', return_value=True) as patch_remove:
                        resp = await client.delete('/foglamp/certificate/foglamp')
                        assert 200 == resp.status
                        result = await resp.text()
                        json_response = json.loads(result)
                        assert 'foglamp.key, foglamp.cert have been deleted successfully' == json_response['result']
                    assert 2 == patch_remove.call_count
