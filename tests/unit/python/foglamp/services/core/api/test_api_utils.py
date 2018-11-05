from unittest.mock import MagicMock, patch
import pytest

from foglamp.services.core.api import utils

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

    @pytest.mark.parametrize("direction, plugin_name, libs", [
        ('south', ['Random'], ['libRandom.so', 'libRandom.so.1']),
        ('north', ['HttpNorthC'], ['libHttpNorthC.so', 'libHttpNorthC.so.1'])
    ])
    def test_find_c_plugin_libs(self, direction, plugin_name, libs):
        with patch('os.walk') as mockwalk:
            mockwalk.return_value = [('', plugin_name, []),
                                     ('', [], libs)]

            assert plugin_name == utils.find_c_plugin_libs(direction)

    def test_get_plugin_info_exception(self):
        plugin_name = 'Random'
        with patch.object(utils, '_find_c_util', return_value=None) as patch_util:
            with patch.object(utils, '_find_c_lib', return_value=None) as patch_lib:
                with patch.object(utils.subprocess, "Popen", side_effect=Exception):
                    with patch.object(utils._logger, 'exception') as patch_logger:
                        assert {} == utils.get_plugin_info(plugin_name)
                    assert 1 == patch_logger.call_count
            patch_lib.assert_called_once_with(plugin_name)
        patch_util.assert_called_once_with('get_plugin_info')

    @patch('subprocess.Popen')
    def test_get_plugin_info(self, mock_subproc_popen):
        with patch.object(utils, '_find_c_util', return_value=['']) as patch_util:
            with patch.object(utils, '_find_c_lib', return_value=['']) as patch_lib:
                process_mock = MagicMock()
                attrs = {'communicate.return_value': (b'{"name": "Random", "version": "1.0.0", "type": "south", "interface": "1.0.0", "config": {"plugin" : { "description" : "Random C south plugin", "type" : "string", "default" : "Random" }, "asset" : { "description" : "Asset name", "type" : "string", "default" : "Random" } } }\n', 'error')}
                process_mock.configure_mock(**attrs)
                mock_subproc_popen.return_value = process_mock
                j = utils.get_plugin_info('Random')
                assert {'name': 'Random', 'type': 'south', 'version': '1.0.0', 'interface': '1.0.0', 'config': {'plugin': {'description': 'Random C south plugin', 'type': 'string', 'default': 'Random'}, 'asset': {'description': 'Asset name', 'type': 'string', 'default': 'Random'}}} == j
            patch_lib.assert_called_once_with('Random')
        patch_util.assert_called_once_with('get_plugin_info')
