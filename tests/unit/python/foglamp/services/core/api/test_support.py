# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


import json
import pathlib
from pathlib import PosixPath

from unittest.mock import patch, mock_open, Mock, MagicMock

from aiohttp import web
import pytest

from foglamp.services.core import routes
from foglamp.services.core.api import support
from foglamp.services.core.support import *

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("api", "bundle-support")
class TestBundleSupport:

    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop)
        # fill the routes table
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    @pytest.fixture
    def support_bundles_dir_path(self):
        return pathlib.Path(__file__).parent

    @pytest.mark.parametrize("data, expected_content, expected_count", [
        (['support-180301-13-35-23.tar.gz', 'support-180301-13-13-13.tar.gz'], {'bundles': ['support-180301-13-35-23.tar.gz', 'support-180301-13-13-13.tar.gz']}, 2),
        (['support-180301-15-25-02.tar.gz', 'foglamp.txt'], {'bundles': ['support-180301-15-25-02.tar.gz']}, 1),
        (['foglamp.txt'], {'bundles': []}, 0),
        ([], {'bundles': []}, 0)
    ])
    async def test_get_support_bundle(self, client, support_bundles_dir_path, data, expected_content, expected_count):
        path = support_bundles_dir_path / 'support'
        with patch.object(support, '_get_support_dir', return_value=path):
            with patch('os.walk') as mockwalk:
                mockwalk.return_value = [(path, [], data)]
                resp = await client.get('/foglamp/support')
                assert 200 == resp.status
                res = await resp.text()
                jdict = json.loads(res)
                assert expected_count == len(jdict['bundles'])
                assert expected_content == jdict
            mockwalk.assert_called_once_with(path)

    async def test_get_support_bundle_by_name(self, client, support_bundles_dir_path):
        gz_filepath = Mock()
        gz_filepath.open = mock_open()
        gz_filepath.is_file.return_value = True
        gz_filepath.stat.return_value = MagicMock()
        gz_filepath.stat.st_size = 1024

        bundle_name = 'support-180301-13-35-23.tar.gz'

        filepath = Mock()
        filepath.name = bundle_name
        filepath.open = mock_open()
        filepath.with_name.return_value = gz_filepath

        with patch("aiohttp.web.FileResponse", return_value=web.FileResponse(path=filepath)) as f_res:
            path = support_bundles_dir_path / 'support'
            with patch.object(support, '_get_support_dir', return_value=path):
                with patch('os.path.isdir', return_value=True):
                    with patch('os.walk') as mockwalk:
                        mockwalk.return_value = [(path, [], [bundle_name])]
                        resp = await client.get('/foglamp/support/{}'.format(bundle_name))
                        assert 200 == resp.status
                        assert 'OK' == resp.reason
                mockwalk.assert_called_once_with(path)
                args, kwargs = f_res.call_args
                assert {'path': PosixPath(pathlib.Path(path) / str(bundle_name))} == kwargs
                assert 1 == f_res.call_count

    @pytest.mark.parametrize("data, request_bundle_name", [
        (['support-180301-13-35-23.tar.gz'], 'xsupport-180301-01-15-13.tar.gz'),
        ([], 'support-180301-13-13-13.tar.gz')
    ])
    async def test_get_support_bundle_by_name_not_found(self, client, support_bundles_dir_path, data, request_bundle_name):
        path = support_bundles_dir_path / 'support'
        with patch.object(support, '_get_support_dir', return_value=path):
            with patch('os.path.isdir', return_value=True):
                with patch('os.walk') as mockwalk:
                    mockwalk.return_value = [(path, [], data)]
                    resp = await client.get('/foglamp/support/{}'.format(request_bundle_name))
                    assert 404 == resp.status
                    assert '{} not found'.format(request_bundle_name) == resp.reason
            mockwalk.assert_called_once_with(path)

    async def test_get_support_bundle_by_name_bad_request(self, client):
        resp = await client.get('/foglamp/support/support-180301-13-35-23.tar')
        assert 400 == resp.status
        assert 'Bundle file extension is invalid' == resp.reason

    async def test_get_support_bundle_by_name_no_dir(self, client, support_bundles_dir_path):
        path = support_bundles_dir_path / 'invalid'
        with patch.object(support, '_get_support_dir', return_value=path):
            with patch('os.path.isdir', return_value=False) as mockisdir:
                resp = await client.get('/foglamp/support/bla.tar.gz')
                assert 404 == resp.status
                assert 'Support bundle directory does not exist' == resp.reason
            mockisdir.assert_called_once_with(path)

    async def test_create_support_bundle(self, client):
        async def mock_build():
            return 'support-180301-13-35-23.tar.gz'

        with patch.object(SupportBuilder, "__init__", return_value=None):
            with patch.object(SupportBuilder, "build", return_value=mock_build()):
                resp = await client.post('/foglamp/support')
                res = await resp.text()
                jdict = json.loads(res)
                assert 200 == resp.status
                assert {"bundle created": "support-180301-13-35-23.tar.gz"} == jdict

    async def test_create_support_bundle_exception(self, client):
        with patch.object(SupportBuilder, "__init__", return_value=None):
            with patch.object(SupportBuilder, "build", side_effect=RuntimeError("blah")):
                resp = await client.post('/foglamp/support')
                res = await resp.text()
                assert 500 == resp.status
                assert "Support bundle could not be created. blah" == resp.reason
