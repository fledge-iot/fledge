# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import os
import platform
import subprocess
import logging
import asyncio
import tarfile
import hashlib
import json

from aiohttp import web
import aiohttp
import async_timeout

from foglamp.common.common import _FOGLAMP_ROOT, _FOGLAMP_DATA
from foglamp.services.core.api.plugins import common
from foglamp.common import logger
from foglamp.services.core.api.plugins.exceptions import *


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2019 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -------------------------------------------------------------------------------
    | POST             | /foglamp/plugins                                         |
    -------------------------------------------------------------------------------
"""
_TIME_OUT = 120
_CHUNK_SIZE = 1024
_PATH = _FOGLAMP_DATA + '/plugins/' if _FOGLAMP_DATA else _FOGLAMP_ROOT + '/data/plugins/'
_LOGGER = logger.setup(__name__, level=logging.INFO)


async def add_plugin(request: web.Request) -> web.Response:
    """ add plugin

    :Example:
        curl -X POST http://localhost:8081/foglamp/plugins
        data:
            URL - The URL to pull the plugin file from
            format - the format of the file. One of tar or package (deb, rpm) or repository
            compressed - option boolean this is used to indicate the package is a compressed gzip image
            checksum - the checksum of the file, used to verify correct upload

        curl -sX POST http://localhost:8081/foglamp/plugins -d '{"format":"repository", "name": "foglamp-south-sinusoid"}'
        curl -sX POST http://localhost:8081/foglamp/plugins -d '{"format":"repository", "name": "foglamp-notify-slack", "version":"1.6.0"}'
    """
    try:
        data = await request.json()
        url = data.get('url', None)
        file_format = data.get('format', None)
        compressed = data.get('compressed', None)
        plugin_type = data.get('type', None)
        checksum = data.get('checksum', None)
        if not file_format:
            raise TypeError('file format param is required')
        if file_format not in ["tar", "deb", "rpm", "repository"]:
            raise ValueError("Invalid format. Must be 'tar' or 'deb' or 'rpm' or 'repository'")
        if file_format == 'repository':
            name = data.get('name', None)
            if name is None:
                raise ValueError('name param is required')
            version = data.get('version', None)
            if version:
                delimiter = '.'
                if str(version).count(delimiter) != 2:
                    raise ValueError('Plugin semantic version is incorrect; it should be like X.Y.Z')

            plugins, log_path = common.fetch_available_packages()
            if name not in plugins:
                raise KeyError('{} plugin is not available for the given repository'.format(name))

            _platform = platform.platform()
            pkg_mgt = 'yum' if 'centos' in _platform or 'redhat' in _platform else 'apt'
            code, link = install_package_from_repo(name, pkg_mgt, version)
            if code != 0:
                raise PackageError(link)

            message = "{} is successfully installed".format(name)
        else:
            if not url or not checksum:
                raise TypeError('URL, checksum params are required')
            if file_format == "tar" and not plugin_type:
                raise ValueError("Plugin type param is required")
            if file_format == "tar" and plugin_type not in ['south', 'north', 'filter', 'notificationDelivery',
                                                            'notificationRule']:
                raise ValueError("Invalid plugin type. Must be 'north' or 'south' or 'filter' "
                                 "or 'notificationDelivery' or 'notificationRule'")
            if compressed:
                if compressed not in ['true', 'false', True, False]:
                    raise ValueError('Only "true", "false", true, false are allowed for value of compressed.')
            is_compressed = ((isinstance(compressed, str) and compressed.lower() in ['true']) or (
                (isinstance(compressed, bool) and compressed is True)))

            # All stuff goes into _PATH
            if not os.path.exists(_PATH):
                os.makedirs(_PATH)

            result = await download([url])
            file_name = result[0]

            # validate checksum with MD5sum
            if validate_checksum(checksum, file_name) is False:
                raise ValueError("Checksum is failed.")

            _LOGGER.debug("Found {} format with compressed {}".format(file_format, is_compressed))
            if file_format == 'tar':
                files = extract_file(file_name, is_compressed)
                _LOGGER.debug("Files {} {}".format(files, type(files)))
                code, msg = copy_file_install_requirement(files, plugin_type, file_name)
                if code != 0:
                    raise ValueError(msg)
            else:
                pkg_mgt = 'yum' if file_format == 'rpm' else 'apt'
                code, msg = install_package(file_name, pkg_mgt)
                if code != 0:
                    raise ValueError(msg)

            message = "{} is successfully downloaded and installed".format(file_name)
    except (FileNotFoundError, KeyError) as ex:
        raise web.HTTPNotFound(reason=str(ex))
    except (TypeError, ValueError) as ex:
        raise web.HTTPBadRequest(reason=str(ex))
    except PackageError as e:
        msg = "Plugin installation request failed"
        raise web.HTTPBadRequest(body=json.dumps({"message": msg, "link": str(e)}), reason=msg)
    except Exception as ex:
        raise web.HTTPException(reason=str(ex))
    else:
        return web.json_response({"message": message})


async def get_url(url: str, session: aiohttp.ClientSession) -> str:
    file_name = str(url.split("/")[-1])
    async with async_timeout.timeout(_TIME_OUT):
        async with session.get(url) as response:
            with open(_PATH + file_name, 'wb') as fd:
                async for data in response.content.iter_chunked(_CHUNK_SIZE):
                    fd.write(data)
    return file_name


async def download(urls: list) -> asyncio.gather:
    async with aiohttp.ClientSession() as session:
        tasks = [get_url(url, session) for url in urls]
        return await asyncio.gather(*tasks)


def validate_checksum(checksum: str, file_name: str) -> bool:
    original = hashlib.md5(open(_PATH + file_name, 'rb').read()).hexdigest()
    return True if original == checksum else False


def extract_file(file_name: str, is_compressed: bool) -> list:
    mode = "r:gz" if is_compressed else "r"
    tar = tarfile.open(_PATH + file_name, mode)
    _LOGGER.debug("Extracted to {}".format(_PATH))
    tar.extractall(_PATH)
    return tar.getnames()


def install_package(file_name: str, pkg_mgt: str) -> tuple:
    pkg_file_path = "/data/plugins/{}".format(file_name)
    stdout_file_path = "/data/plugins/output.txt"
    cmd = "sudo {} -y install {} > {} 2>&1".format(pkg_mgt, _FOGLAMP_ROOT + pkg_file_path, _FOGLAMP_ROOT + stdout_file_path)
    _LOGGER.debug("CMD....{}".format(cmd))
    ret_code = os.system(cmd)
    _LOGGER.debug("Return Code....{}".format(ret_code))
    msg = ""
    with open("{}".format(_FOGLAMP_ROOT + stdout_file_path), 'r') as fh:
        for line in fh:
            line = line.rstrip("\n")
            msg += line
    _LOGGER.debug("Message.....{}".format(msg))
    # Remove stdout file
    cmd = "{}/extras/C/cmdutil rm {}".format(_FOGLAMP_ROOT, stdout_file_path)
    subprocess.run([cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

    # Remove downloaded debian file
    cmd = "{}/extras/C/cmdutil rm {}".format(_FOGLAMP_ROOT, pkg_file_path)
    subprocess.run([cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    return ret_code, msg


def copy_file_install_requirement(dir_files: list, plugin_type: str, file_name: str) -> tuple:
    py_file = any(f.endswith(".py") for f in dir_files)
    so_1_file = any(f.endswith(".so.1") for f in dir_files)  # regular file
    so_file = any(f.endswith(".so") for f in dir_files)  # symlink file

    if not py_file and not so_file:
        raise FileNotFoundError("Invalid plugin directory structure found, please check the contents of your tar file.")

    if so_1_file:
        if not so_file:
            _LOGGER.error("Symlink file is missing")
            raise FileNotFoundError("Symlink file is missing")
    _dir = []
    for s in dir_files:
        _dir.append(s.split("/")[-1])

    assert len(_dir), "No data found"
    plugin_name = _dir[0]
    _LOGGER.debug("Plugin name {} and Dir {} ".format(plugin_name, _dir))
    plugin_path = "python/foglamp/plugins" if py_file else "plugins"
    full_path = "{}/{}/{}/".format(_FOGLAMP_ROOT, plugin_path, plugin_type)
    dest_path = "{}/{}/".format(plugin_path, plugin_type)

    # Check if plugin dir exists then remove (for cleanup ONLY) otherwise create dir
    if os.path.exists(full_path + plugin_name) and os.path.isdir(full_path + plugin_name):
        cmd = "{}/extras/C/cmdutil rm {}".format(_FOGLAMP_ROOT, dest_path + plugin_name)
        subprocess.run([cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    else:
        cmd = "{}/extras/C/cmdutil mkdir {}".format(_FOGLAMP_ROOT, dest_path + plugin_name)
        subprocess.run([cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

    # copy plugin files to the relative plugins directory.
    cmd = "{}/extras/C/cmdutil cp {} {}".format(_FOGLAMP_ROOT, _PATH + plugin_name, dest_path)
    subprocess.run([cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    _LOGGER.debug("{} File copied to {}".format(cmd, full_path))

    # TODO: FOGL-2760 Handle external dependency for plugins which can be installed via tar file
    # Use case: plugins like opcua, usb4704 (external dep)
    # dht11- For pip packages we have requirements.txt file, as this plugin needs wiringpi apt package to install
    py_req = filter(lambda x: x.startswith('requirement') and x.endswith('.txt'), _dir)
    requirement = list(py_req)
    code = 0
    msg = ""
    if requirement:
        cmd = "{}/extras/C/cmdutil pip3-req {}{}/{}".format(_FOGLAMP_ROOT, _PATH, plugin_name, requirement[0])
        s = subprocess.run([cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        code = s.returncode
        msg = s.stderr.decode("utf-8") if code != 0 else s.stdout.decode("utf-8")
        msg = msg.replace("\n", "").strip()
        _LOGGER.debug("Return code {} and msg {}".format(code, msg))

    # Also removed downloaded and extracted tar file
    cmd = "{}/extras/C/cmdutil rm /data/plugins/{}".format(_FOGLAMP_ROOT, file_name)
    subprocess.run([cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    cmd = "{}/extras/C/cmdutil rm /data/plugins/{}".format(_FOGLAMP_ROOT, plugin_name)
    subprocess.run([cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

    return code, msg


def install_package_from_repo(name: str, pkg_mgt: str, version: str) -> tuple:
    stdout_file_path = common.create_log_file(name)
    cmd = "sudo {} update > {} 2>&1".format(pkg_mgt, stdout_file_path)
    ret_code = os.system(cmd)
    # sudo apt/yum -y install only happens when update is without any error
    if ret_code == 0:
        cmd = "sudo {} -y install {}".format(pkg_mgt, name)
        if version:
            cmd = "sudo {} -y install {}={}".format(pkg_mgt, name, version)

        ret_code = os.system(cmd + " >> {} 2>&1".format(stdout_file_path))

    # Replace .log extension from the log filename and return relative link
    link = stdout_file_path.split("/")[-1].replace(".log", "")
    link = "log/" + link
    return ret_code, link
