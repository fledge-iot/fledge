# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import os
import platform
import subprocess
import logging

from aiohttp import web
from foglamp.common.plugin_discovery import PluginDiscovery
from foglamp.services.core.api import utils
from foglamp.common.common import _FOGLAMP_ROOT, _FOGLAMP_DATA
from foglamp.common import logger

__author__ = "Amarendra K Sinha, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_help = """
    -------------------------------------------------------------------------------
    | GET             | /foglamp/plugins/installed                                |
    | GET             | /foglamp/plugins/available                                |
    -------------------------------------------------------------------------------
"""
_logger = logger.setup(__name__, level=logging.INFO)


async def get_plugins_installed(request):
    """ get list of installed plugins

    :Example:
        curl -X GET http://localhost:8081/foglamp/plugins/installed
        curl -X GET http://localhost:8081/foglamp/plugins/installed?config=true
        curl -X GET http://localhost:8081/foglamp/plugins/installed?type=north|south|filter|notificationDelivery|notificationRule
        curl -X 'GET http://localhost:8081/foglamp/plugins/installed?type=north&config=true'
    """

    plugin_type = None
    is_config = False
    if 'type' in request.query and request.query['type'] != '':
        plugin_type = request.query['type'].lower() if request.query['type'] not in ['notificationDelivery', 'notificationRule'] else request.query['type']

    if plugin_type is not None and plugin_type not in ['north', 'south', 'filter', 'notificationDelivery', 'notificationRule']:
        raise web.HTTPBadRequest(reason="Invalid plugin type. Must be 'north' or 'south' or 'filter' or 'notificationDelivery' or 'notificationRule'.")

    if 'config' in request.query:
        config = request.query['config']
        if config not in ['true', 'false', True, False]:
                raise web.HTTPBadRequest(reason='Only "true", "false", true, false'
                                                ' are allowed for value of config.')
        is_config = True if ((type(config) is str and config.lower() in ['true']) or (
            (type(config) is bool and config is True))) else False

    plugins_list = PluginDiscovery.get_plugins_installed(plugin_type, is_config)

    return web.json_response({"plugins": plugins_list})


async def get_plugins_available(request: web.Request) -> web.Response:
    """ get list of a available plugins via package management i.e apt or yum

        :Example:
            curl -X GET http://localhost:8081/foglamp/plugins/available
            curl -X GET http://localhost:8081/foglamp/plugins/available?type=north | south | filter | notify | rule | service
    """
    try:
        package_type = None
        if 'type' in request.query and request.query['type'] != '':
            package_type = request.query['type'].lower()

        if package_type is not None and package_type not in ['north', 'south', 'filter', 'notify', 'rule', 'service']:
            raise ValueError("Invalid package type. Must be 'north' or 'south' or 'filter' or 'notify' or 'rule' or 'service'.")

        plugins_list = []
        plugin_dir = '/plugins/'
        _PATH = _FOGLAMP_DATA + plugin_dir if _FOGLAMP_DATA else _FOGLAMP_ROOT + '/data{}'.format(plugin_dir)
        stdout_file_name = "output.txt"
        stdout_file_path = "/{}/{}".format(_PATH, stdout_file_name)

        if not os.path.exists(_PATH):
            os.makedirs(_PATH)

        _platform = platform.platform()

        pkg_type = "" if package_type is None else package_type
        if 'centos' in _platform or 'redhat' in _platform:
            cmd = "sudo yum list available foglamp-{}\* | grep foglamp | cut -d . -f1 > {} 2>&1".format(pkg_type, stdout_file_path)
        else:
            cmd = "sudo apt list | grep foglamp-{} | grep -v installed | cut -d / -f1  > {} 2>&1".format(pkg_type, stdout_file_path)

        ret_code = os.system(cmd)
        if ret_code != 0:
            raise ValueError

        with open("{}".format(stdout_file_path), 'r') as fh:
            for line in fh:
                line = line.rstrip("\n")
                plugins_list.append(line)

        # Remove stdout file
        arg1 = utils._find_c_util('cmdutil')
        # FIXME: (low priority) special case for cmdutil when FOGLAMP_DATA as we do not need absolute path for filename to delete
        # and cmdutil commands only works with make install
        # arg2 = plugin_dir if _FOGLAMP_DATA else '/data{}'.format(plugin_dir)
        arg2 = '/data{}'.format(plugin_dir)
        cmd = "{} rm {}{}".format(arg1, arg2, stdout_file_name)
        subprocess.run([cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    except ValueError as ex:
        raise web.HTTPBadRequest(reason=ex)
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=ex)

    return web.json_response({"plugins": plugins_list})
