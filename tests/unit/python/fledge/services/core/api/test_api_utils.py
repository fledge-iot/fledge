import subprocess

from unittest.mock import MagicMock, patch
import pytest

from fledge.services.core.api import utils

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("api", "utils")
class TestUtils:

    @pytest.mark.parametrize("direction", ['south', 'north'])
    def test_find_c_plugin_libs_if_empty(self, direction):
        with patch('os.walk') as mockwalk:
            mockwalk.return_value = [([], [], [])]
            assert [] == utils.find_c_plugin_libs(direction)

    @pytest.mark.parametrize("direction, plugin_name, plugin_type, libs", [
        ('south', ['Random'], 'binary', ['libRandom.so', 'libRandom.so.1']),
        ('south', ['FlirAX8'], 'json', ['FlirAX8.json']),
        ('north', ['HttpNorthC'], 'binary', ['libHttpNorthC.so', 'libHttpNorthC.so.1'])
    ])
    def test_find_c_plugin_libs(self, direction, plugin_name, plugin_type, libs):
        with patch('os.walk') as mockwalk:
            mockwalk.return_value = [('', plugin_name, []),
                                     ('', [], libs)]

            assert plugin_name, plugin_type == utils.find_c_plugin_libs(direction)

    def test_get_plugin_info_value_error(self):
        plugin_name = 'Random'
        with patch.object(utils, '_find_c_util', return_value='plugins/utils/get_plugin_info') as patch_util:
            with patch.object(utils, '_find_c_lib', return_value=None) as patch_lib:
                assert {} == utils.get_plugin_info(plugin_name, dir='south')
            patch_lib.assert_called_once_with(plugin_name, 'south')
        patch_util.assert_called_once_with('get_plugin_info')

    @pytest.mark.parametrize("exc_name, msg", [
        (Exception, ""),
        (OSError, ""),
        (subprocess.CalledProcessError, "__init__() missing 2 required positional arguments: 'returncode' and 'cmd'")
    ])
    def test_get_plugin_info_exception(self, exc_name, msg):
        plugin_name = 'OMF'
        plugin_lib_path = 'fledge/plugins/north/{}/lib{}'.format(plugin_name, plugin_name)
        with patch.object(utils, '_find_c_util', return_value='plugins/utils/get_plugin_info') as patch_util:
            with patch.object(utils, '_find_c_lib', return_value=plugin_lib_path) as patch_lib:
                with patch.object(utils.subprocess, "Popen", side_effect=exc_name):
                    with patch.object(utils._logger, 'error') as patch_logger:
                        assert {} == utils.get_plugin_info(plugin_name, dir='south')
                    assert 1 == patch_logger.call_count
                    args, kwargs = patch_logger.call_args
                    assert '{} C plugin get info failed due to {}'.format(plugin_name, msg) == args[0]
            patch_lib.assert_called_once_with(plugin_name, 'south')
        patch_util.assert_called_once_with('get_plugin_info')

    @patch('subprocess.Popen')
    def test_get_plugin_info(self, mock_subproc_popen):
        with patch.object(utils, '_find_c_util', return_value='plugins/utils/get_plugin_info') as patch_util:
            with patch.object(utils, '_find_c_lib', return_value='fledge/plugins/south/Random/libRandom') as patch_lib:
                process_mock = MagicMock()
                attrs = {'communicate.return_value': (b'{"name": "Random", "version": "1.0.0", "type": "south", '
                                                      b'"interface": "1.0.0", "config": {"plugin" : '
                                                      b'{ "description" : "Random C south plugin", "type" : "string", '
                                                      b'"default" : "Random" }, "asset" : { "description" : '
                                                      b'"Asset name", "type" : "string", '
                                                      b'"default" : "Random" } } }\n', 'error')}
                process_mock.configure_mock(**attrs)
                mock_subproc_popen.return_value = process_mock
                j = utils.get_plugin_info('Random', dir='south')
                assert {'name': 'Random', 'type': 'south', 'version': '1.0.0', 'interface': '1.0.0',
                        'config': {'plugin': {'description': 'Random C south plugin', 'type': 'string',
                                              'default': 'Random'},
                                   'asset': {'description': 'Asset name', 'type': 'string', 'default': 'Random'}}} == j
            patch_lib.assert_called_once_with('Random', 'south')
        patch_util.assert_called_once_with('get_plugin_info')
