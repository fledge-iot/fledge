# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import os
import platform
import logging
import json

from aiohttp import web

from fledge.common.common import _FLEDGE_ROOT
from fledge.common import logger


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2020 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -------------------------------------------------------------------------------
    | POST             | /fledge/repository                                       |
    -------------------------------------------------------------------------------
"""
_LOGGER = logger.setup(__name__, level=logging.INFO)


async def add_package_repo(request: web.Request) -> web.Response:
    """ configure package repo

    :Example:
        curl -X POST http://localhost:8081/fledge/repository
        data:
            url - Set a repository URL that used for installing packages via apt or yum
            version - Points to the package release version or any custom branch fixes

        curl -sX POST http://localhost:8081/fledge/repository -d '{"url":"http://archives.fledge-iot.org"'
        curl -sX POST http://localhost:8081/fledge/repository -d '{"url":"http://archives.fledge-iot.org", "version":"latest"}'
    """
    try:
        data = await request.json()
        url = data.get('url', None)
        # By default version is latest
        version = data.get('version', 'latest')
        if not url:
            raise ValueError('url param is required')

        _platform = platform.platform()
        pkg_mgt = 'yum' if 'centos' in _platform or 'redhat' in _platform else 'apt'

        v_list = ['nightly', 'latest']
        if not (version in v_list or version.startswith('fixes/')):
            if str(version).count('.') != 2:
                raise ValueError('Invalid version; it should be latest, nightly or a valid semantic version X.Y.Z i.e. major.minor.patch')

        if 'x86_64-with-Ubuntu-18.04' in _platform:
            os_name = "ubuntu1804"
            architecture = "x86_64"
        elif 'armv7l-with-debian' in _platform:
            os_name = "buster"
            architecture = "armv7l"
        elif 'aarch64-with-Ubuntu-18.04' in _platform:
            os_name = "ubuntu1804"
            architecture = "aarch64"
        elif 'x86_64-with-redhat' in _platform:
            os_name = "rhel76"
            architecture = "x86_64"
        elif 'aarch64-with-Mendel' in _platform:
            os_name = "mendel"
            architecture = "aarch64"
        elif 'x86_64-with-centos' in _platform:
            os_name = "centos76"
            architecture = "x86_64"
        else:
            raise ValueError("{} is not supported".format(_platform))

        # TODO: FOGL-4176 RPM support
        stdout_file_path = _FLEDGE_ROOT + "/data/configure_repo_output.txt"
        cmd = "wget -q -O - {}/KEY.gpg | sudo apt-key add - > {} 2>&1".format(url, stdout_file_path)
        _LOGGER.debug("CMD....{}".format(cmd))
        ret_code = os.system(cmd)
        if ret_code != 0:
            raise RuntimeError("See logs in {}".format(stdout_file_path))
        full_url = "{}/{}/{}/{}".format(url, version, os_name, architecture)
        cmd = "echo \"deb {}/ /\" | sudo tee /etc/apt/sources.list.d/fledge.list >> {} 2>&1".format(full_url,
                                                                                                    stdout_file_path)
        _LOGGER.debug("CMD....{}".format(cmd))
        ret_code = os.system(cmd)
        if ret_code != 0:
            raise RuntimeError("See logs in {}".format(stdout_file_path))
        cmd = "sudo {} -y update >> {} 2>&1".format(pkg_mgt, stdout_file_path)
        _LOGGER.debug("CMD....{}".format(cmd))
        ret_code = os.system(cmd)
        if ret_code != 0:
            raise RuntimeError("See logs in {}".format(stdout_file_path))
        # TODO: audit log entry?
    except ValueError as err:
        msg = str(err)
        raise web.HTTPBadRequest(body=json.dumps({"message": msg}), reason=msg)
    except RuntimeError as err:
        msg = str(err)
        raise web.HTTPBadRequest(body=json.dumps({"message": "Failed to configure package repository",
                                                  "output_log": msg}), reason=msg)
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=str(ex))
    else:
        return web.json_response({"message": "Package repository configured successfully.",
                                  "output_log": stdout_file_path})

