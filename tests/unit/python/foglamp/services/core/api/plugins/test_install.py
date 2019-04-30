# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import json
from unittest.mock import patch
import pytest

from aiohttp import web

from foglamp.services.core import routes
from foglamp.services.core.api.plugins import install as plugins_install


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
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
        ({"create": "blah"}, "URL, checksum and format post params are mandatory."),
        ({"url": "http://blah.co.in"}, "URL, checksum and format post params are mandatory."),
        ({"format": "tar"}, "URL, checksum and format post params are mandatory."),
        ({"compressed": "false"}, "URL, checksum and format post params are mandatory."),
        ({"type": "north"}, "URL, checksum and format post params are mandatory."),
        ({"checksum": "4015c2dea1cc71dbf70a23f6a203eeb6"},
         "URL, checksum and format post params are mandatory."),
        ({"url": "http://blah.co.in", "checksum": "4015c2dea1cc71dbf70a23f6a203eeb6"},
         "URL, checksum and format post params are mandatory."),
        ({"format": "tar", "checksum": "4015c2dea1cc71dbf70a23f6a203eeb6"},
         "URL, checksum and format post params are mandatory."),
        ({"format": "tar", "compressed": "false", "checksum": "4015c2dea1cc71dbf70a23f6a203eeb6"},
         "URL, checksum and format post params are mandatory."),
        ({"type": "north", "checksum": "4015c2dea1cc71dbf70a23f6a203eeb6"},
         "URL, checksum and format post params are mandatory."),
        ({"url": "http://blah.co.in", "format": "tar", "checksum": "4015c2dea1cc71dbf70a23f6a203eeb6"},
         "Plugin type param is required."),
        ({"url": "http://blah.co.in", "format": "tar", "type": "blah", "checksum": "4015c2dea1cc71dbf70a23f6a203eeb6"},
         "Invalid plugin type. Must be 'north' or 'south' or 'filter' or 'notificationDelivery' or 'notificationRule'"),
        ({"url": "http://blah.co.in", "format": "blah", "type": "filter", "checksum": "4015c2dea1cc71dbf70a23f6a203ee"},
         "Invalid format. Must be 'tar' or 'deb'"),
        ({"url": "http://blah.co.in", "format": "tar", "type": "south", "checksum": "4015c2dea1cc71dbf70a23f6a203eeb6",
          "compressed": "blah"}, 'Only "true", "false", true, false are allowed for value of compressed.')
    ])
    async def test_bad_post_plugins_install(self, client, param, message):
        resp = await client.post('/foglamp/plugins', data=json.dumps(param))
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
                resp = await client.post('/foglamp/plugins', data=json.dumps(param))
                assert 400 == resp.status
                assert 'Checksum is failed.' == resp.reason
            checksum_patch.assert_called_once_with(checksum_value, tar_file_name)
        download_patch.assert_called_once_with([url_value])

    async def test_bad_post_plugins_install_with_tar(self, client):
        async def async_mock(ret_val):
            return ret_val

        plugin_name = 'mqtt_sparkplug'
        sub_dir = 'sparkplug_b'
        tar_file_name = 'foglamp-south-mqtt_sparkplug-1.5.2.tar'
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
                with patch.object(plugins_install, 'extract_file', return_value=async_mock(files)) as extract_patch:
                    with patch.object(plugins_install, 'copy_file_install_requirement',
                                      return_value=(1, msg)) as copy_file_install_requirement_patch:
                        resp = await client.post('/foglamp/plugins', data=json.dumps(param))
                        assert 400 == resp.status
                        assert msg == resp.reason
                    assert copy_file_install_requirement_patch.called
                extract_patch.assert_called_once_with(tar_file_name, False)
            checksum_patch.assert_called_once_with(checksum_value, tar_file_name)
        download_patch.assert_called_once_with([url_value])

    async def test_post_plugins_install_with_tar(self, client):
        async def async_mock(ret_val):
            return ret_val

        plugin_name = 'coap'
        tar_file_name = 'foglamp-south-coap-1.5.2.tar'
        files = [plugin_name, '{}/__init__.py'.format(plugin_name), '{}/README.rst'.format(plugin_name),
                 '{}/{}.py'.format(plugin_name, plugin_name), '{}/requirements.txt'.format(plugin_name)]
        checksum_value = "4015c2dea1cc71dbf70a23f6a203eeb6"
        url_value = "http://10.2.5.26:5000/download/{}".format(tar_file_name)
        param = {"url": url_value, "format": "tar", "type": "south", "checksum": checksum_value}
        with patch.object(plugins_install, 'download', return_value=async_mock([tar_file_name])) as download_patch:
            with patch.object(plugins_install, 'validate_checksum', return_value=True) as checksum_patch:
                with patch.object(plugins_install, 'extract_file', return_value=async_mock(files)) as extract_patch:
                    with patch.object(plugins_install, 'copy_file_install_requirement', return_value=(0, 'Success')) \
                            as copy_file_install_requirement_patch:
                        resp = await client.post('/foglamp/plugins', data=json.dumps(param))
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

        plugin_name = 'rms'
        tar_file_name = 'foglamp-filter-rms-1.5.2.tar.gz'
        files = [plugin_name, '{}/lib{}.so.1'.format(plugin_name, plugin_name),
                 '{}/lib{}.so'.format(plugin_name, plugin_name)]
        checksum_value = "2019c2dea1cc71dbf70a23f6a203fdgh"
        url_value = "http://10.2.5.26:5000/filter/download/{}".format(tar_file_name)
        param = {"url": url_value, "format": "tar", "type": "filter", "checksum": checksum_value, "compressed": "true"}
        with patch.object(plugins_install, 'download', return_value=async_mock([tar_file_name])) as download_patch:
            with patch.object(plugins_install, 'validate_checksum', return_value=True) as checksum_patch:
                with patch.object(plugins_install, 'extract_file', return_value=async_mock(files)) as extract_patch:
                    with patch.object(plugins_install, 'copy_file_install_requirement', return_value=(0, 'Success')) \
                            as copy_file_install_requirement_patch:
                        resp = await client.post('/foglamp/plugins', data=json.dumps(param))
                        assert 200 == resp.status
                        r = await resp.text()
                        output = json.loads(r)
                        assert '{} is successfully downloaded and installed'.format(tar_file_name) == output['message']
                    assert copy_file_install_requirement_patch.called
                extract_patch.assert_called_once_with(tar_file_name, True)
            checksum_patch.assert_called_once_with(checksum_value, tar_file_name)
        download_patch.assert_called_once_with([url_value])

    async def test_post_plugins_install_with_debian(self, client):
        async def async_mock():
            return [plugin_name, '{}/__init__.py'.format(plugin_name), '{}/README.rst'.format(plugin_name),
                    '{}/{}.py'.format(plugin_name, plugin_name), '{}/requirements.txt'.format(plugin_name)]

        plugin_name = 'coap'
        checksum_value = "4015c2dea1cc71dbf70a23f6a203eeb6"
        url_value = "http://10.2.5.26:5000/download/foglamp-south-coap-1.5.2.deb"
        param = {"url": url_value, "format": "deb", "type": "south", "checksum": checksum_value}
        with patch.object(plugins_install, 'download', return_value=async_mock()) as download_patch:
            with patch.object(plugins_install, 'validate_checksum', return_value=True) as checksum_patch:
                with patch.object(plugins_install, 'install_deb', return_value=(0, 'Success')) as debian_patch:
                    resp = await client.post('/foglamp/plugins', data=json.dumps(param))
                    assert 200 == resp.status
                debian_patch.assert_called_once_with(plugin_name)
            checksum_patch.assert_called_once_with(checksum_value, plugin_name)
        download_patch.assert_called_once_with([url_value])

    async def test_bad_post_plugins_install_with_debian(self, client):
        async def async_mock():
            return [plugin_name, '{}/__init__.py'.format(plugin_name), '{}/README.rst'.format(plugin_name),
                    '{}/{}.py'.format(plugin_name, plugin_name), '{}/requirements.sh'.format(plugin_name)]

        plugin_name = 'coap'
        checksum_value = "4015c2dea1cc71dbf70a23f6a203eeb6"
        url_value = "http://10.2.5.26:5000/download/foglamp-south-coap-1.5.2.deb"
        param = {"url": url_value, "format": "deb", "type": "south", "checksum": checksum_value}
        msg = 'The following packages have unmet dependencies: foglamp-south-coap:armhf : Depends: ' \
              'foglamp:armhf (>= 1.5) but it is not installableE: Unable to correct problems, ' \
              'you have held broken packages.'
        with patch.object(plugins_install, 'download', return_value=async_mock()) as download_patch:
            with patch.object(plugins_install, 'validate_checksum', return_value=True) as checksum_patch:
                with patch.object(plugins_install, 'install_deb', return_value=(256, msg)) as debian_patch:
                    resp = await client.post('/foglamp/plugins', data=json.dumps(param))
                    assert 400 == resp.status
                    assert msg == resp.reason
                debian_patch.assert_called_once_with(plugin_name)
            checksum_patch.assert_called_once_with(checksum_value, plugin_name)
        download_patch.assert_called_once_with([url_value])
