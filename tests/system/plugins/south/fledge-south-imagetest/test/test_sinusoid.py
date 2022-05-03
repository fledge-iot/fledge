# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

from unittest.mock import patch
import pytest

from python.fledge.plugins.south.sinusoid import sinusoid

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2018 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

config = sinusoid._DEFAULT_CONFIG


def test_plugin_contract():
    # Evaluates if the plugin has all the required methods
    assert callable(getattr(sinusoid, 'plugin_info'))
    assert callable(getattr(sinusoid, 'plugin_init'))
    assert callable(getattr(sinusoid, 'plugin_poll'))
    assert callable(getattr(sinusoid, 'plugin_shutdown'))
    assert callable(getattr(sinusoid, 'plugin_reconfigure'))


def test_plugin_info():
    assert sinusoid.plugin_info() == {
        'name': 'Sinusoid Poll plugin',
        'version': '1.9.2',
        'mode': 'poll',
        'type': 'south',
        'interface': '1.0',
        'config': config
    }


def test_plugin_init():
    assert sinusoid.plugin_init(config) == config


@pytest.mark.skip(reason="To be implemented")
def test_plugin_poll():
    pass


@pytest.mark.skip(reason="To be implemented")
def test_plugin_reconfigure():
    pass


def test_plugin_shutdown():
    with patch.object(sinusoid._LOGGER, 'info') as patch_logger_info:
        sinusoid.plugin_shutdown(config)
    patch_logger_info.assert_called_once_with('sinusoid plugin shut down.')
