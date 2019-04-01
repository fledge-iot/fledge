# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Install plugin as per type, plugin name, language & add/start south service"""

import subprocess
import http.client
import json


def install(_type, plugin, branch="develop", plugin_lang="python", use_pip_cache=True):
    if plugin_lang == "python":
        path = "$FOGLAMP_ROOT/tests/system/python/scripts/install_python_plugin {} {} {} {}".format(
            branch, _type, plugin, use_pip_cache)
    else:
        path = "$FOGLAMP_ROOT/tests/system/python/scripts/install_c_plugin {} {} {}".format(
            branch, _type, plugin)
    try:
        subprocess.run([path], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "{} plugin installation failed".format(plugin)

    # Cleanup /tmp repos
    if _type == "notificationDelivery":
        _type = "notify"
    if _type == "notificationRule":
        _type = "rule"
        subprocess.run(["rm -rf /tmp/foglamp-service-notification"], shell=True, check=True)
    subprocess.run(["rm -rf /tmp/foglamp-{}-{}".format(_type, plugin)], shell=True, check=True)


def reset():
    try:
        subprocess.run(["$FOGLAMP_ROOT/tests/system/python/scripts/reset_plugins"], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "reset plugin script failed"


def add_south_service(south_plugin, foglamp_url, service_name, config=None, start_service=True):
        """Add south plugin and start the service by default"""
        _config = config if config is not None else {}
        _enabled = "true" if start_service else "false"
        data = {"name": "{}".format(service_name), "type": "South", "plugin": "{}".format(south_plugin),
                "enabled": _enabled, "config": _config}

        # Create south service
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("POST", '/foglamp/service', json.dumps(data))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        return json.loads(r)
