# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test plugin discovery (north, south, filter, notify, rule) REST API """

import subprocess
import http.client
import json
from collections import Counter
import pytest


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


def install_plugin(_type, plugin, branch="develop", plugin_lang="python", use_pip_cache=True):
    if plugin_lang == "python":
        path = "$FLEDGE_ROOT/tests/system/python/scripts/install_python_plugin {} {} {} {}".format(
            branch, _type, plugin, use_pip_cache)
    else:
        path = "$FLEDGE_ROOT/tests/system/python/scripts/install_c_plugin {} {} {}".format(
            branch, _type, plugin)
    try:
        subprocess.run([path], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "{} plugin installation failed".format(plugin)

    # Cleanup /tmp repos
    if _type == "rule":
        subprocess.run(["rm -rf /tmp/fledge-service-notification"], shell=True, check=True)
    subprocess.run(["rm -rf /tmp/fledge-{}-{}".format(_type, plugin)], shell=True, check=True)


@pytest.fixture
def reset_plugins():
    try:
        subprocess.run(["$FLEDGE_ROOT/tests/system/python/scripts/reset_plugins"], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "reset plugin script failed"


class TestPluginDiscovery:

    def test_cleanup(self, reset_plugins, reset_and_start_fledge):
        # TODO: Remove this workaround
        # Use better setup & teardown methods
        pass

    @pytest.mark.parametrize("param, config", [
        ("", False),
        ("?config=false", False),
        ("?config=true", True)
    ])
    def test_default_all_plugins_installed(self, fledge_url, param, config):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/plugins/installed{}'.format(param))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        # Only north plugins (1-C based and 2-Python based) are expected by default
        assert 3 == len(jdoc['plugins'])
        for plugin in jdoc['plugins']:
            assert 'north' == plugin['type']
            assert plugin['type'] not in ['south', 'filter', 'notify', 'rule']
            # config is not expected by default
            assert 'config' in plugin if config else 'config' not in plugin

    @pytest.mark.parametrize("method, count, config", [
        ("/fledge/plugins/installed?type=south", 0, None),
        ("/fledge/plugins/installed?type=filter", 0, None),
        ("/fledge/plugins/installed?type=notify", 0, None),
        ("/fledge/plugins/installed?type=rule", 0, None),
        ("/fledge/plugins/installed?type=north&config=false", 3, False),
        ("/fledge/plugins/installed?type=north&config=true", 3, True)
    ])
    def test_default_plugins_installed_by_type(self, fledge_url, method, count, config):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", method)
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert count == len(jdoc['plugins'])
        name = []
        for plugin in jdoc['plugins']:
            assert 'config' in plugin if config else 'config' not in plugin
            name.append(plugin['name'])
        # Verify only 3 north plugins when type is north
        if count == 3:
            assert Counter(['ocs', 'pi_server', 'OMF']) == Counter(name)

    def test_south_plugins_installed(self, fledge_url, _type='south'):
        # install south plugin (Python version)
        install_plugin(_type, plugin='sinusoid', plugin_lang='python')
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/plugins/installed?type={}'.format(_type))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        plugins = jdoc['plugins']
        assert 1 == len(plugins)
        assert 'sinusoid' == plugins[0]['name']
        assert 'south' == plugins[0]['type']
        assert 'south/sinusoid' == plugins[0]['installedDirectory']
        assert 'fledge-south-sinusoid' == plugins[0]['packageName']

        # install one more south plugin (C version)
        install_plugin(_type, plugin='random', plugin_lang='C')
        conn.request("GET", '/fledge/plugins/installed?type={}'.format(_type))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        plugins = jdoc['plugins']
        assert 2 == len(plugins)
        assert 'sinusoid' == plugins[0]['name']
        assert 'south' == plugins[0]['type']
        assert 'south/sinusoid' == plugins[0]['installedDirectory']
        assert 'fledge-south-sinusoid' == plugins[0]['packageName']
        assert 'Random' == plugins[1]['name']
        assert 'south' == plugins[1]['type']
        assert 'south/Random' == plugins[1]['installedDirectory']
        assert 'fledge-south-random' == plugins[1]['packageName']

    def test_north_plugins_installed(self, fledge_url, _type='north'):
        # install north plugin (Python version)
        install_plugin(_type, plugin='http', plugin_lang='python')
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/plugins/installed?type={}'.format(_type))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        plugins = jdoc['plugins']
        plugin_names = [name['name'] for name in plugins]
        # verify north plugins which is 3 by default and a new one (http)
        assert 4 == len(plugins)
        assert Counter(['ocs', 'http_north', 'pi_server', 'OMF']) == Counter(plugin_names)

        # install one more north plugin (C version)
        install_plugin(_type, plugin='thingspeak', plugin_lang='C')
        conn.request("GET", '/fledge/plugins/installed?type={}'.format(_type))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        plugins = jdoc['plugins']
        plugin_names = [name['name'] for name in plugins]
        # verify north plugins which is 4 by default and 2 new one (Python & C version)
        assert 5 == len(plugins)
        assert Counter(['ocs', 'http_north', 'pi_server', 'OMF', 'ThingSpeak']) == Counter(plugin_names)

    def test_filter_plugins_installed(self, fledge_url, _type='filter'):
        # install rms filter plugin
        install_plugin(_type, plugin='rms', plugin_lang='C')
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/plugins/installed?type={}'.format(_type))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        plugins = jdoc['plugins']
        assert 1 == len(plugins)
        assert 'rms' == plugins[0]['name']

    def test_delivery_plugins_installed(self, fledge_url, _type='notify'):
        # install slack delivery plugin
        install_plugin(_type, plugin='slack', plugin_lang='C')
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/plugins/installed?type={}'.format(_type))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        plugins = jdoc['plugins']
        assert 1 == len(plugins)
        assert 'slack' == plugins[0]['name']
        assert 'notify' == plugins[0]['type']
        assert 'notificationDelivery/slack' == plugins[0]['installedDirectory']
        assert 'fledge-notify-slack' == plugins[0]['packageName']

    def test_rule_plugins_installed(self, fledge_url, _type='rule'):
        # install OutOfBound rule plugin
        install_plugin(_type, plugin='outofbound', plugin_lang='C')
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/plugins/installed?type={}'.format(_type))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        plugins = jdoc['plugins']
        assert 1 == len(plugins)
        assert 'OutOfBound' == plugins[0]['name']
        assert 'rule' == plugins[0]['type']
        assert 'notificationRule/OutOfBound' == plugins[0]['installedDirectory']
        assert 'fledge-rule-outofbound' == plugins[0]['packageName']
