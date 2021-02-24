# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import json
from unittest.mock import patch, MagicMock
import pytest

from aiohttp import web

from fledge.services.core import routes
from fledge.services.core.api.plugins import install as plugins_install
from fledge.services.core.api.plugins import common
from fledge.services.core.api.plugins.exceptions import *
from fledge.services.core import connect
from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.common.plugin_discovery import PluginDiscovery

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2019 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("api", "plugins", "install")
class TestPluginInstall:
    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop)
        # fill the routes table
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    @pytest.mark.parametrize("param, message", [
        ({"create": "blah"}, "file format param is required"),
        ({"format": "deb", "url": "http://blah.co.in"}, "URL, checksum params are required"),
        ({"format": "tar"}, "URL, checksum params are required"),
        ({"format": "deb", "compressed": "false"}, "URL, checksum params are required"),
        ({"format": "tar", "type": "north"}, "URL, checksum params are required"),
        ({"format": "tar", "checksum": "4015c2dea1cc71dbf70a23f6a203eeb6"},
         "URL, checksum params are required"),
        ({"format": "tar", "checksum": "4015c2dea1cc71dbf70a23f6a203eeb6"},
         "URL, checksum params are required"),
        ({"format": "tar", "compressed": "false", "checksum": "4015c2dea1cc71dbf70a23f6a203eeb6"},
         "URL, checksum params are required"),
        ({"format": "deb", "type": "north", "checksum": "4015c2dea1cc71dbf70a23f6a203eeb6"},
         "URL, checksum params are required"),
        ({"url": "http://blah.co.in", "format": "tar", "checksum": "4015c2dea1cc71dbf70a23f6a203eeb6"},
         "Plugin type param is required"),
        ({"url": "http://blah.co.in", "format": "tar", "type": "blah", "checksum": "4015c2dea1cc71dbf70a23f6a203eeb6"},
         "Invalid plugin type. Must be 'north' or 'south' or 'filter' or 'notify' or 'rule'"),
        ({"url": "http://blah.co.in", "format": "blah", "type": "filter", "checksum": "4015c2dea1cc71dbf70a23f6a203ee"},
         "Invalid format. Must be 'tar' or 'deb' or 'rpm' or 'repository'"),
        ({"url": "http://blah.co.in", "format": "tar", "type": "south", "checksum": "4015c2dea1cc71dbf70a23f6a203eeb6",
          "compressed": "blah"}, 'Only "true", "false", true, false are allowed for value of compressed.'),
        ({"format": "repository"}, "name param is required"),
        ({"format": "repository", "version": "1.6"}, "name param is required"),
        ({"format": "repository", "name": "sinusoid"}, 'name should start with "fledge-" prefix'),
        ({"format": "repository", "name": "fledge-south-sinusoid", "version": "1.6"},
         "Invalid version; it should be empty or a valid semantic version X.Y.Z i.e. major.minor.patch to install "
         "as per the configured repository"),
    ])
    async def test_bad_post_plugins_install(self, client, param, message):
        resp = await client.post('/fledge/plugins', data=json.dumps(param))
        assert 400 == resp.status
        assert message == resp.reason

    async def test_bad_checksum_post_plugins_install(self, client):
        async def async_mock():
            return [tar_file_name]

        tar_file_name = 'Benchmark.tar'
        checksum_value = "4015c2dea1cc71dbf70a23f6a203eeb6"
        url_value = "http://10.2.5.26:5000//download/c/{}".format(tar_file_name)
        param = {"url": url_value, "format": "tar", "type": "south", "checksum": checksum_value, "compressed": "true"}
        with patch.object(plugins_install, 'download', return_value=async_mock()) as download_patch:
            with patch.object(plugins_install, 'validate_checksum', return_value=False) as checksum_patch:
                resp = await client.post('/fledge/plugins', data=json.dumps(param))
                assert 400 == resp.status
                assert 'Checksum is failed.' == resp.reason
            checksum_patch.assert_called_once_with(checksum_value, tar_file_name)
        download_patch.assert_called_once_with([url_value])

    async def test_bad_post_plugins_install_with_tar(self, client):
        async def async_mock(ret_val):
            return ret_val

        def sync_mock(ret_val):
            return ret_val

        plugin_name = 'mqtt_sparkplug'
        sub_dir = 'sparkplug_b'
        tar_file_name = 'fledge-south-mqtt_sparkplug-1.5.2.tar'
        files = [plugin_name, '{}/__init__.py'.format(plugin_name), '{}/README.rst'.format(plugin_name),
                 '{}/{}.py'.format(plugin_name, plugin_name), '{}/requirements.txt'.format(plugin_name),
                 '{}/{}/__init__.py'.format(plugin_name, sub_dir), '{}/{}/{}.py'.format(plugin_name, sub_dir, sub_dir),
                 '{}/{}/{}_pb2.py'.format(plugin_name, sub_dir, sub_dir)]
        checksum_value = "77b74584e09fc28467599636e47f3fc5"
        url_value = "http://10.2.5.26:5000/download/{}".format(tar_file_name)
        msg = 'Could not find a version that satisfies the requirement pt==1.4.0'
        param = {"url": url_value, "format": "tar", "type": "south", "checksum": checksum_value}
        with patch.object(plugins_install, 'download', return_value=async_mock([tar_file_name])) as download_patch:
            with patch.object(plugins_install, 'validate_checksum', return_value=True) as checksum_patch:
                with patch.object(plugins_install, 'extract_file', return_value=sync_mock(files)) as extract_patch:
                    with patch.object(plugins_install, 'copy_file_install_requirement',
                                      return_value=(1, msg)) as copy_file_install_requirement_patch:
                        resp = await client.post('/fledge/plugins', data=json.dumps(param))
                        assert 400 == resp.status
                        assert msg == resp.reason
                    assert copy_file_install_requirement_patch.called
                extract_patch.assert_called_once_with(tar_file_name, False)
            checksum_patch.assert_called_once_with(checksum_value, tar_file_name)
        download_patch.assert_called_once_with([url_value])

    async def test_post_plugins_install_with_tar(self, client):
        async def async_mock(ret_val):
            return ret_val

        def sync_mock(ret_val):
            return ret_val

        plugin_name = 'coap'
        tar_file_name = 'fledge-south-coap-1.5.2.tar'
        files = [plugin_name, '{}/__init__.py'.format(plugin_name), '{}/README.rst'.format(plugin_name),
                 '{}/{}.py'.format(plugin_name, plugin_name), '{}/requirements.txt'.format(plugin_name)]
        checksum_value = "4015c2dea1cc71dbf70a23f6a203eeb6"
        url_value = "http://10.2.5.26:5000/download/{}".format(tar_file_name)
        param = {"url": url_value, "format": "tar", "type": "south", "checksum": checksum_value}
        with patch.object(plugins_install, 'download', return_value=async_mock([tar_file_name])) as download_patch:
            with patch.object(plugins_install, 'validate_checksum', return_value=True) as checksum_patch:
                with patch.object(plugins_install, 'extract_file', return_value=sync_mock(files)) as extract_patch:
                    with patch.object(plugins_install, 'copy_file_install_requirement', return_value=(0, 'Success')) \
                            as copy_file_install_requirement_patch:
                        resp = await client.post('/fledge/plugins', data=json.dumps(param))
                        assert 200 == resp.status
                        r = await resp.text()
                        output = json.loads(r)
                        assert '{} is successfully downloaded and installed'.format(tar_file_name) == output['message']
                    assert copy_file_install_requirement_patch.called
                extract_patch.assert_called_once_with(tar_file_name, False)
            checksum_patch.assert_called_once_with(checksum_value, tar_file_name)
        download_patch.assert_called_once_with([url_value])

    async def test_post_plugins_install_with_compressed_tar(self, client):
        async def async_mock(ret_val):
            return ret_val

        def sync_mock(ret_val):
            return ret_val

        plugin_name = 'rms'
        tar_file_name = 'fledge-filter-rms-1.5.2.tar.gz'
        files = [plugin_name, '{}/lib{}.so.1'.format(plugin_name, plugin_name),
                 '{}/lib{}.so'.format(plugin_name, plugin_name)]
        checksum_value = "2019c2dea1cc71dbf70a23f6a203fdgh"
        url_value = "http://10.2.5.26:5000/filter/download/{}".format(tar_file_name)
        param = {"url": url_value, "format": "tar", "type": "filter", "checksum": checksum_value, "compressed": "true"}
        with patch.object(plugins_install, 'download', return_value=async_mock([tar_file_name])) as download_patch:
            with patch.object(plugins_install, 'validate_checksum', return_value=True) as checksum_patch:
                with patch.object(plugins_install, 'extract_file', return_value=sync_mock(files)) as extract_patch:
                    with patch.object(plugins_install, 'copy_file_install_requirement', return_value=(0, 'Success')) \
                            as copy_file_install_requirement_patch:
                        resp = await client.post('/fledge/plugins', data=json.dumps(param))
                        assert 200 == resp.status
                        r = await resp.text()
                        output = json.loads(r)
                        assert '{} is successfully downloaded and installed'.format(tar_file_name) == output['message']
                    assert copy_file_install_requirement_patch.called
                extract_patch.assert_called_once_with(tar_file_name, True)
            checksum_patch.assert_called_once_with(checksum_value, tar_file_name)
        download_patch.assert_called_once_with([url_value])

    @pytest.mark.parametrize("plugin_name, checksum, file_format", [
        ('coap', '4015c2dea1cc71dbf70a23f6a203eeb6', 'deb'),
        ('sinusoid', '04bd924371488d981d9a60bcb093bedc', 'rpm')
    ])
    async def test_post_plugins_install_package(self, client, plugin_name, checksum, file_format):
        async def async_mock():
            return [plugin_name, '{}/__init__.py'.format(plugin_name), '{}/README.rst'.format(plugin_name),
                    '{}/{}.py'.format(plugin_name, plugin_name), '{}/requirements.txt'.format(plugin_name)]

        url_value = "http://10.2.5.26:5000/download/fledge-south-{}-1.6.0.{}".format(plugin_name, file_format)
        param = {"url": url_value, "format": file_format, "type": "south", "checksum": checksum}
        pkg_mgt = 'yum' if file_format == 'rpm' else 'apt'
        with patch.object(plugins_install, 'download', return_value=async_mock()) as download_patch:
            with patch.object(plugins_install, 'validate_checksum', return_value=True) as checksum_patch:
                with patch.object(plugins_install, 'install_package', return_value=(0, 'Success')) \
                        as install_package_patch:
                    resp = await client.post('/fledge/plugins', data=json.dumps(param))
                    assert 200 == resp.status
                    result = await resp.text()
                    response = json.loads(result)
                    assert {"message": "{} is successfully downloaded and installed".format(plugin_name)} == response
                install_package_patch.assert_called_once_with(plugin_name, pkg_mgt)
            checksum_patch.assert_called_once_with(checksum, plugin_name)
        download_patch.assert_called_once_with([url_value])

    @pytest.mark.parametrize("plugin_name, checksum, file_format", [
        ('coap', '4015c2dea1cc71dbf70a23f6a203eeb6', 'deb'),
        ('sinusoid', '04bd924371488d981d9a60bcb093bedc', 'rpm')
    ])
    async def test_bad_post_plugins_install_package(self, client, plugin_name, checksum, file_format):
        async def async_mock():
            return [plugin_name, '{}/__init__.py'.format(plugin_name), '{}/README.rst'.format(plugin_name),
                    '{}/{}.py'.format(plugin_name, plugin_name), '{}/requirements.sh'.format(plugin_name)]

        url_value = "http://10.2.5.26:5000/download/fledge-south-{}-1.6.0.{}".format(plugin_name, file_format)
        param = {"url": url_value, "format": file_format, "type": "south", "checksum": checksum}
        if file_format == 'rpm':
            pkg_mgt = 'yum'
            msg = '400: Loaded plugins: amazon-id, rhui-lb, search-disabled-reposExamining ' \
                  '/usr/local/fledge/data/plugins/fledge-south-sinusoid-1.6.0.rpm: ' \
                  'fledge-south-sinusoid-1.6.0-1.x86_64Marking ' \
                  '/usr/local/fledge/data/plugins/fledge-south-sinusoid-1.6.0-1.x86_64.rpm to be installed' \
                  'Resolving Dependencies--> Running transaction check---> Package ' \
                  'fledge-south-sinusoid.x86_64 0:1.6.0-1 will be installed--> ' \
                  'Processing Dependency: fledge >= 1.6 for package: fledge-south-sinusoid-1.6.0-1.x86_64' \
                  'You could try using --skip-broken to work around the problem ' \
                  'You could try running: rpm -Va --nofiles --nodigest'
        else:
            pkg_mgt = 'apt'
            msg = 'The following packages have unmet dependencies: fledge-south-coap:armhf : Depends: ' \
                  'fledge:armhf (>= 1.6) but it is not installableE: Unable to correct problems, ' \
                  'you have held broken packages.'

        with patch.object(plugins_install, 'download', return_value=async_mock()) as download_patch:
            with patch.object(plugins_install, 'validate_checksum', return_value=True) as checksum_patch:
                with patch.object(plugins_install, 'install_package', return_value=(256, msg)) as install_package_patch:
                    resp = await client.post('/fledge/plugins', data=json.dumps(param))
                    assert 400 == resp.status
                    assert msg == resp.reason
                install_package_patch.assert_called_once_with(plugin_name, pkg_mgt)
            checksum_patch.assert_called_once_with(checksum, plugin_name)
        download_patch.assert_called_once_with([url_value])

    async def test_post_bad_plugin_install_package_from_repo(self, client):
        async def async_mock(return_value):
            return return_value

        plugin = "fledge-south-sinusoid"
        param = {"format": "repository", "name": plugin}
        payload = {"return": ["status"], "where": {"column": "action", "condition": "=", "value": "install",
                                                   "and": {"column": "name", "condition": "=", "value": plugin}}}
        plugin_list = [{'name': 'randomwalk', 'type': 'south', 'description': 'Generate random walk data points',
                        'version': '1.8.2', 'installedDirectory': 'south/randomwalk',
                        'packageName': 'fledge-south-randomwalk'}]

        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload',
                              return_value=async_mock({'count': 0, 'rows': []})) as query_tbl_patch:
                with patch.object(PluginDiscovery, 'get_plugins_installed', return_value=plugin_list
                                  ) as plugin_installed_patch:
                    with patch.object(common, 'fetch_available_packages', return_value=(
                            async_mock(([], 'log/190801-12-41-13.log')))) as patch_fetch_available_package:
                        resp = await client.post('/fledge/plugins', data=json.dumps(param))
                        assert 404 == resp.status
                        assert "'{} plugin is not available for the configured repository'".format(plugin) == resp.reason
                    patch_fetch_available_package.assert_called_once_with()
                plugin_installed_patch.assert_called_once_with('south', False)
            args, kwargs = query_tbl_patch.call_args_list[0]
            assert 'packages' == args[0]
            assert payload == json.loads(args[1])

    @pytest.mark.parametrize("plugin_name", [
        'fledge-south-modbusc',
        'fledge-north-kafka',
        'fledge-filter-rms',
        'fledge-notify-email',
        'fledge-rule-outofbound'
    ])
    async def test_post_plugins_install_package_from_repo(self, client, plugin_name, loop):
        async def async_mock(return_value):
            return return_value

        storage_client_mock = MagicMock(StorageClientAsync)
        param = {"format": "repository", "name": plugin_name}
        insert_row_resp = {'count': 1, 'rows': [{
                "id": "c5648940-31ec-4f78-a7a5-b1707e8fe578",
                "name": plugin_name,
                "action": "install",
                "status": -1,
                "log_file_uri": ""
            }]}
        query_tbl_payload = {"return": ["status"], "where": {"column": "action", "condition": "=", "value": "install",
                                                             "and": {"column": "name", "condition": "=",
                                                                     "value": plugin_name}}}
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload',
                              side_effect=[async_mock({'count': 0, 'rows': []}), async_mock(insert_row_resp)
                                           ]) as query_tbl_patch:
                with patch.object(common, 'fetch_available_packages', return_value=(
                        async_mock(([plugin_name, "fledge-north-http", "fledge-service-notification"],
                                    'log/190801-12-41-13.log')))) as patch_fetch_available_package:
                    with patch.object(storage_client_mock, 'insert_into_tbl',
                                      return_value=async_mock({"response": "inserted", "rows_affected": 1}
                                                              )) as insert_tbl_patch:
                        with patch.object(plugins_install._LOGGER, "info") as log_info:
                            with patch('multiprocessing.Process'):
                                resp = await client.post('/fledge/plugins', data=json.dumps(param))
                                assert 200 == resp.status
                                result = await resp.text()
                                response = json.loads(result)
                                assert 'id' in response
                                assert 'Plugin installation started.' == response['message']
                                assert response['statusLink'].startswith('fledge/package/install/status?id=')
                        assert 1 == log_info.call_count
                        log_info.assert_called_once_with('{} plugin install started...'.format(plugin_name))
                    args, kwargs = insert_tbl_patch.call_args_list[0]
                    assert 'packages' == args[0]
                    actual = json.loads(args[1])
                    assert 'id' in actual
                    assert plugin_name == actual['name']
                    assert 'install' == actual['action']
                    assert -1 == actual['status']
                    assert '' == actual['log_file_uri']
                patch_fetch_available_package.assert_called_once_with()
            args, kwargs = query_tbl_patch.call_args_list[0]
            assert 'packages' == args[0]
            actual = json.loads(args[1])
            assert query_tbl_payload == actual

    async def test_plugin_install_package_from_repo_already_in_progress(self, client):
        async def async_mock(return_value):
            return return_value

        plugin_name = "fledge-north-http-north"
        param = {"format": "repository", "name": plugin_name}
        payload = {"return": ["status"], "where": {"column": "action", "condition": "=", "value": "install",
                                                   "and": {"column": "name", "condition": "=", "value": plugin_name}}}
        select_row_resp = {'count': 1, 'rows': [{
            "id": "c5648940-31ec-4f78-a7a5-b1707e8fe578",
            "name": plugin_name,
            "action": "install",
            "status": -1,
            "log_file_uri": ""
        }]}
        msg = '{} package installation already in progress'.format(plugin_name)
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload',
                              return_value=async_mock(select_row_resp)) as query_tbl_patch:
                resp = await client.post('/fledge/plugins', data=json.dumps(param))
                assert 429 == resp.status
                assert msg == resp.reason
                r = await resp.text()
                actual = json.loads(r)
                assert {'message': msg} == actual
            args, kwargs = query_tbl_patch.call_args_list[0]
            assert 'packages' == args[0]
            assert payload == json.loads(args[1])

    async def test_plugin_install_package_from_repo_already_installed(self, client):
        async def async_mock(return_value):
            return return_value

        plugin_name = "fledge-south-modbusc"
        param = {"format": "repository", "name": plugin_name}
        payload = {"return": ["status"], "where": {"column": "action", "condition": "=", "value": "install",
                                                   "and": {"column": "name", "condition": "=", "value": plugin_name}}}
        plugin_list = [{"name": "ModbusC", "type": "south", "description": "Modbus TCP and RTU C south plugin",
                        "version": "1.8.1", "installedDirectory": "south/ModbusC", "packageName": plugin_name}]
        msg = '{} package is already installed'.format(plugin_name)
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload',
                              return_value=async_mock({'count': 0, 'rows': []})) as query_tbl_patch:
                with patch.object(PluginDiscovery, 'get_plugins_installed', return_value=plugin_list
                                  ) as plugin_list_patch:
                    resp = await client.post('/fledge/plugins', data=json.dumps(param))
                    assert 400 == resp.status
                    assert msg == resp.reason
                plugin_list_patch.assert_called_once_with('south', False)
            args, kwargs = query_tbl_patch.call_args_list[0]
            assert 'packages' == args[0]
            assert payload == json.loads(args[1])
