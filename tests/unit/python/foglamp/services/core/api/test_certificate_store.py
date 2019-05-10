# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


import json
import pathlib

from unittest.mock import MagicMock, patch
from collections import Counter
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
        response_content = {'keys': ['foglamp.key', 'rsa_private.pem'],
                            'certs': ['foglamp.cert', 'test.json', 'foglamp.pem']}
        with patch.object(certificate_store, '_get_certs_dir', return_value=certs_path / 'certs'):
            with patch('os.walk') as mockwalk:
                mockwalk.return_value = [(str(certs_path / 'certs'), [], ['foglamp.cert']),
                                         (str(certs_path / 'certs/pem'), [], ['foglamp.pem']),
                                         (str(certs_path / 'certs/json'), [], ['test.json']),
                                         (str(certs_path / 'certs'), [], ['foglamp.key', 'rsa_private.pem'])
                                         ]
                resp = await client.get('/foglamp/certificate')
                assert 200 == resp.status
                res = await resp.text()
                jdict = json.loads(res)
                cert = jdict["certs"]
                assert 3 == len(cert)
                assert Counter(response_content['certs']) == Counter(cert)
                key = jdict["keys"]
                assert 2 == len(key)
                assert Counter(response_content['keys']) == Counter(key)
            mockwalk.assert_called_once_with(certs_path / 'certs')

    @pytest.mark.parametrize("files", [
        [], ['foglamp.txt'],
    ])
    async def test_get_bad_certs(self, client, certs_path, files):
        with patch.object(certificate_store, '_get_certs_dir', return_value=certs_path / 'certs'):
            with patch('os.walk') as mockwalk:
                mockwalk.return_value = [(str(certs_path / 'certs'), [], files),
                                         (str(certs_path / 'certs/pem'), [], files),
                                         (str(certs_path / 'certs/json'), [], files),
                                         (str(certs_path / 'certs'), [], files)
                                         ]
                resp = await client.get('/foglamp/certificate')
                assert 200 == resp.status
                result = await resp.text()
                json_response = json.loads(result)
                assert 0 == len(json_response['certs'])
                assert 0 == len(json_response['keys'])
                assert {'certs': [], 'keys': []} == json_response
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
            assert 2 == patch_find_file.call_count
            args, kwargs = patch_find_file.call_args_list[0]
            assert ('foglamp.cert', certificate_store._get_certs_dir('/certs/')) == args
            args, kwargs = patch_find_file.call_args_list[1]
            assert ('foglamp.key', certificate_store._get_certs_dir('/certs/')) == args

    async def test_upload_with_cert_only(self, client, certs_path):
        files = {'cert': open(str(certs_path / 'certs/foglamp.pem'), 'rb')}
        with patch.object(certificate_store, '_get_certs_dir', return_value=certs_path / 'certs/pem'):
            with patch.object(certificate_store, '_find_file', return_value=[]) as patch_find_file:
                resp = await client.post('/foglamp/certificate', data=files)
                assert 200 == resp.status
                result = await resp.text()
                json_response = json.loads(result)
                assert 'foglamp.pem has been uploaded successfully' == json_response['result']
            assert 1 == patch_find_file.call_count
            args, kwargs = patch_find_file.call_args
            assert ('foglamp.pem', certificate_store._get_certs_dir('/certs/pem')) == args

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
            assert 2 == patch_find_file.call_count
            args, kwargs = patch_find_file.call_args_list[0]
            assert ('foglamp.cert', certificate_store._get_certs_dir('/certs/')) == args
            args, kwargs = patch_find_file.call_args_list[1]
            assert ('foglamp.key', certificate_store._get_certs_dir('/certs/')) == args

    async def test_bad_key_file_upload(self, client, certs_path):
        files = {'bad_key': open(str(certs_path / 'certs/foglamp.key'), 'rb'),
                 'cert': open(str(certs_path / 'certs/foglamp.cert'), 'rb')
                 }
        resp = await client.post('/foglamp/certificate', data=files)
        assert 400 == resp.status
        assert 'key file is missing, or upload certificate with .pem or .json extension' == resp.reason

    async def test_bad_cert_file_upload(self, client, certs_path):
        files = {'bad_cert': open(str(certs_path / 'certs/foglamp.cert'), 'rb'),
                 'key': open(str(certs_path / 'certs/foglamp.key'), 'rb')}
        resp = await client.post('/foglamp/certificate', data=files)
        assert 400 == resp.status
        assert 'Cert file is missing' == resp.reason

    async def test_bad_extension_cert_file_upload(self, client, certs_path):
        files = {'cert': open(str(certs_path / 'certs/foglamp.txt'), 'rb'),
                 'key': open(str(certs_path / 'certs/foglamp.key'), 'rb')}
        resp = await client.post('/foglamp/certificate', data=files)
        assert 400 == resp.status
        assert 'Accepted file extensions are .cert, .json and .pem for cert file' == resp.reason

    async def test_bad_extension_key_file_upload(self, client, certs_path):
        files = {'cert': open(str(certs_path / 'certs/foglamp.cert'), 'rb'),
                 'key': open(str(certs_path / 'certs/foglamp.txt'), 'rb')}
        resp = await client.post('/foglamp/certificate', data=files)
        assert 400 == resp.status
        assert 'Accepted file extensions are .key and .pem for key file' == resp.reason

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
                assert 'Certificate with the same name already exists. To overwrite set the ' \
                       'overwrite to 1' == resp.reason
            assert 1 == patch_file.call_count
            args, kwargs = patch_file.call_args
            assert ('foglamp.cert', certificate_store._get_certs_dir('/certs')) == args

    async def test_exception(self, client):
        files = {'cert': 'certs/bla.cert', 'key': 'certs/bla.key'}
        resp = await client.post('/foglamp/certificate', data=files)
        assert 500 == resp.status
        assert 'Internal Server Error' == resp.reason

    @pytest.mark.parametrize("cert_name, actual_code, actual_reason", [
        ('', 404, "Not Found"),
        ('root.txt', 400, "Accepted file extensions are ('.cert', '.json', '.key', '.pem')"),
        ('root.pem', 404, "Certificate with name root.pem does not exist"),
        ('rsa_private.key', 404, "Certificate with name rsa_private.key does not exist"),
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
                    resp = await client.delete('/foglamp/certificate/foglamp.cert')
                    assert 409 == resp.status
                    assert 'Certificate with name foglamp.cert is already in use, you can not delete' == resp.reason
                assert 1 == patch_cfg.call_count
                args, kwargs = patch_cfg.call_args
                assert ({'item_name': 'certificateName', 'category_name': 'rest_api'}) == kwargs

    async def test_bad_type_delete_cert(self, client):
        resp = await client.delete('/foglamp/certificate/foglamp.key?type=pem')
        assert 400 == resp.status
        assert 'Only cert and key are allowed for the value of type param' == resp.reason

    @pytest.mark.parametrize("cert_name, param", [
        ('foglamp.cert', '?type=cert'),
        ('foglamp.json', '?type=cert'),
        ('foglamp.pem', '?type=cert'),
        ('foglamp.key', '?type=key'),
        ('rsa_private.pem', '?type=key'),
    ])
    async def test_delete_cert_with_type(self, client, cert_name, param):
        async def async_mock():
            return {'value': 'test'}

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, 'get_category_item', return_value=async_mock()):
                with patch('os.path.isfile', return_value=True):
                    with patch('os.remove', return_value=True) as patch_remove:
                        resp = await client.delete('/foglamp/certificate/{}{}'.format(cert_name, param))
                        assert 200 == resp.status
                        result = await resp.text()
                        json_response = json.loads(result)
                        assert '{} has been deleted successfully'.format(cert_name) == json_response['result']
                    assert 1 == patch_remove.call_count

    async def test_delete_cert(self, client, certs_path, cert_name='server.cert'):
        async def async_mock():
            return {'value': 'test'}

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(certificate_store, '_get_certs_dir', return_value=str(certs_path / 'certs') + '/'):
            with patch('os.walk') as mockwalk:
                mockwalk.return_value = [(str(certs_path / 'certs'), [], [cert_name])]
                with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                    with patch.object(c_mgr, 'get_category_item', return_value=async_mock()):
                        with patch('os.remove', return_value=True) as patch_remove:
                            resp = await client.delete('/foglamp/certificate/{}'.format(cert_name))
                            assert 200 == resp.status
                            result = await resp.text()
                            json_response = json.loads(result)
                            assert '{} has been deleted successfully'.format(cert_name) == json_response['result']
                        assert 1 == patch_remove.call_count
