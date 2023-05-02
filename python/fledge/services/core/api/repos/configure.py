# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import os
import platform
import json

from aiohttp import web

from fledge.common import utils
from fledge.common.common import _FLEDGE_ROOT
from fledge.common.logger import FLCoreLogger


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2020 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -------------------------------------------------------------------------------
    | POST             | /fledge/repository                                       |
    -------------------------------------------------------------------------------
"""
_LOGGER = FLCoreLogger().get_logger(__name__)


async def add_package_repo(request: web.Request) -> web.Response:
    """ configure package repo

    :Example:
        curl -X POST http://localhost:8081/fledge/repository
        data:
            url - Set a repository URL that used for installing packages via apt or yum
            version - Points to the package release version or any custom branch fixes

        curl -sX POST http://localhost:8081/fledge/repository -d '{"url":"http://archives.fledge-iot.org"}'
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
        v_list = ['nightly', 'latest']
        if not (version in v_list or version.startswith('fixes/')):
            if str(version).count('.') != 2:
                raise ValueError('Invalid version; it should be latest, '
                                 'nightly or a valid semantic version X.Y.Z i.e. major.minor.patch')

        if utils.is_redhat_based():
            pkg_mgt = 'yum'
            if 'x86_64-with-redhat' in _platform:
                os_name = "rhel7"
                architecture = "x86_64"
                extra_commands = "sudo yum-config-manager --enable 'Red Hat Enterprise Linux Server 7 RHSCL (RPMs)'"
            elif 'x86_64-with-centos' in _platform:
                os_name = "centos7"
                architecture = "x86_64"
                extra_commands = "sudo yum install -y centos-release-scl-rh epel-release"
            elif 'x86_64-with-glibc' in _platform:
                os_name = "centos-stream-9"
                architecture = "x86_64"
                extra_commands = ""
            else:
                raise ValueError("{} is not supported".format(_platform))
        else:
            pkg_mgt = 'apt'
            if 'x86_64-with-Ubuntu-18.04' in _platform:
                os_name = "ubuntu1804"
                architecture = "x86_64"
                extra_commands = ""
            elif 'x86_64-with-glib' in _platform:
                os_name = "ubuntu2004"
                architecture = "x86_64"
                extra_commands = ""
            elif 'armv7l-with-debian' in _platform:
                os_name = "buster"
                architecture = "armv7l"
                extra_commands = ""
            elif 'armv7l-with-glibc' in _platform:
                os_name = "bullseye"
                architecture = "armv7l"
                extra_commands = ""
            elif 'aarch64-with-Ubuntu-18.04' in _platform:
                os_name = "ubuntu1804"
                architecture = "aarch64"
                extra_commands = ""
            elif 'aarch64-with-Mendel' in _platform:
                os_name = "mendel"
                architecture = "aarch64"
                extra_commands = ""
            else:
                raise ValueError("{} is not supported".format(_platform))

        stdout_file_path = _FLEDGE_ROOT + "/data/configure_repo_output.txt"
        if pkg_mgt == 'yum':
            cmd = "sudo rpm --import {}/RPM-GPG-KEY-fledge > {} 2>&1".format(url, stdout_file_path)
        else:
            cmd = "wget -q -O - {}/KEY.gpg | sudo apt-key add - > {} 2>&1".format(url, stdout_file_path)
        _LOGGER.debug("Add the key that is used to verify the package with command: {}".format(cmd))
        ret_code = os.system(cmd)
        if ret_code != 0:
            raise RuntimeError("See logs in {}".format(stdout_file_path))
        full_url = "{}/{}/{}/{}".format(url, version, os_name, architecture)
        if pkg_mgt == 'yum':
            cmd = "echo -e \"[fledge]\nname=fledge Repository\nbaseurl={}\nenabled=1\ngpgkey={}/RPM-GPG-KEY-fledge\ngpgcheck=1\" | sudo tee /etc/yum.repos.d/fledge.repo >> {} 2>&1".format(full_url, url, stdout_file_path)
        else:
            cmd = "echo \"deb {}/ /\" | sudo tee /etc/apt/sources.list.d/fledge.list >> {} 2>&1".format(
                full_url, stdout_file_path)
        _LOGGER.debug("Edit the sources list with command: {}".format(cmd))
        ret_code = os.system(cmd)
        if ret_code != 0:
            raise RuntimeError("See logs in {}".format(stdout_file_path))
        if pkg_mgt == 'yum':
            cmd = "{} >> {} 2>&1".format(extra_commands, stdout_file_path)
        else:
            cmd = "sudo {} -y update >> {} 2>&1".format(pkg_mgt, stdout_file_path)
        _LOGGER.debug("Fetch the list of packages with command: {}".format(cmd))
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
        msg = "Failed to configure archive package repository setup."
        _LOGGER.error(ex, msg)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": "{} {}".format(msg, str(ex))}))
    else:
        return web.json_response({"message": "Package repository configured successfully.",
                                  "output_log": stdout_file_path})
