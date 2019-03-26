# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test plugin discovery (north, south, filter, notificationDelivery, notificationRule) REST API """

import subprocess
import http.client
import json
from collections import Counter
import pytest


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


def install_plugin(type, plugin, branch="develop", plugin_lang="python", use_pip_cache=True):
    if plugin_lang == "python":
        path = "$FOGLAMP_ROOT/tests/system/python/scripts/install_python_plugin {} {} {} {}".format(
            branch, type, plugin, use_pip_cache)
    else:
        path = "$FOGLAMP_ROOT/tests/system/python/scripts/install_c_plugin {} {} {}".format(
            branch, type, plugin)
    try:
        subprocess.run([path], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "{} plugin installation failed".format(plugin)

    # Cleanup code
    subprocess.run(["rm -rf /tmp/foglamp-{}-{}".format(type, plugin)], shell=True, check=True)
    # TODO: FOGL-2642 - Remove notificationDelivery And notificationRule plugins


@pytest.fixture
def reset_plugins():
    subprocess.run(["rm -rf $FOGLAMP_ROOT/plugins/south"], shell=True, check=True)
    subprocess.run(["path=$FOGLAMP_ROOT/python/foglamp/plugins/south; "
                    "find $path -maxdepth 1 | grep -v \"^${path}$\" | "
                    "egrep -v '(__init__.py)' | xargs rm -rf"], shell=True, check=True)
    subprocess.run(["path=$FOGLAMP_ROOT/python/foglamp/plugins/north; "
                    "find $path -maxdepth 1 | grep -v \"^${path}$\" | "
                    "egrep -v '(pi_server|ocs|common|empty|README.rst|__init__.py)' | xargs rm -rf"],
                   shell=True, check=True)
    subprocess.run(["path=$FOGLAMP_ROOT/plugins/north; "
                    "find $path -maxdepth 1 | grep -v \"^${path}$\" | "
                    "egrep -v '(PI_Server_V2|ocs_V2)' | xargs rm -rf"],
                   shell=True, check=True)
    subprocess.run(["path=$FOGLAMP_ROOT/plugins/filter; "
                    "find $path -maxdepth 1 | grep -v \"^${path}$\" | "
                    "egrep -v '(common)' | xargs rm -rf"], shell=True, check=True)
    # TODO: FOGL-2642 - reset notificationDelivery And notificationRule plugins


class TestPluginDiscovery:

    def test_default_all_plugins_installed(self, reset_plugins, reset_and_start_foglamp, foglamp_url):
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("GET", '/foglamp/plugins/installed')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 4 == len(jdoc['plugins'])
        for plugin in jdoc['plugins']:
            assert 'north' == plugin['type']
            assert 'south' not in plugin['type']
            assert 'filter' not in plugin['type']
            assert 'notify' not in plugin['type']
            assert 'rule' not in plugin['type']
            assert 'config' not in plugin

    @pytest.mark.parametrize("method, count, config", [
        ("/foglamp/plugins/installed?type=south", 0, None),
        ("/foglamp/plugins/installed?type=filter", 0, None),
        ("/foglamp/plugins/installed?type=notify", 0, None),
        ("/foglamp/plugins/installed?type=rule", 0, None),
        ("/foglamp/plugins/installed?type=north&config=false", 4, False),
        ("/foglamp/plugins/installed?type=north&config=true", 4, True)
    ])
    def test_default_plugins_installed_by_type(self, foglamp_url, method, count, config):
        conn = http.client.HTTPConnection(foglamp_url)
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
        if count == 4:
            assert Counter(['ocs', 'pi_server', 'PI_Server_V2', 'ocs_V2']) == Counter(name)

    def test_south_plugins_installed(self, reset_plugins, foglamp_url):
        install_plugin(type='south', plugin='sinusoid', plugin_lang='python')

        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("GET", '/foglamp/plugins/installed?type=south')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        plugins = jdoc['plugins']
        assert 1 == len(plugins)
        assert 'sinusoid' == plugins[0]['name']

        install_plugin(type='south', plugin='random', plugin_lang='C')

        conn.request("GET", '/foglamp/plugins/installed?type=south')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        plugins = jdoc['plugins']
        assert 2 == len(plugins)
        assert 'sinusoid' == plugins[0]['name']
        assert 'Random' == plugins[1]['name']

    def test_north_plugins_installed(self, reset_plugins, foglamp_url):
        install_plugin(type='north', plugin='http', plugin_lang='python')

        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("GET", '/foglamp/plugins/installed?type=north')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        plugins = jdoc['plugins']
        plugin_names = [name['name'] for name in plugins]
        assert 5 == len(plugins)
        assert Counter(['ocs', 'http_north', 'pi_server', 'PI_Server_V2',
                        'ocs_V2']) == Counter(plugin_names)

        install_plugin(type='north', plugin='thingspeak', plugin_lang='c')

        conn.request("GET", '/foglamp/plugins/installed?type=north')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        plugins = jdoc['plugins']
        plugin_names = [name['name'] for name in plugins]
        assert 6 == len(plugins)
        assert Counter(['ocs', 'http_north', 'pi_server', 'PI_Server_V2', 'ThingSpeak',
                        'ocs_V2']) == Counter(plugin_names)

    def test_filter_plugins_installed(self, reset_plugins, foglamp_url):
        install_plugin(type='filter', plugin='rms', plugin_lang='c')

        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("GET", '/foglamp/plugins/installed?type=filter')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        plugins = jdoc['plugins']
        assert 1 == len(plugins)
        assert 'rms' == plugins[0]['name']

    @pytest.mark.skip(reason='FOGL-2642')
    def test_delivery_plugins_installed(self, reset_plugins, foglamp_url):
        pass

    @pytest.mark.skip(reason='FOGL-2642')
    def test_rule_plugins_installed(self, reset_plugins, foglamp_url):
        pass
