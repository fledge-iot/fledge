# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import os
import platform
import subprocess
import logging
import asyncio
import tarfile
import hashlib
import json
import uuid
import multiprocessing

from aiohttp import web
import aiohttp
import async_timeout
from typing import Dict
from datetime import datetime

from fledge.common.common import _FLEDGE_ROOT, _FLEDGE_DATA
from fledge.services.core.api.plugins import common
from fledge.common import logger
from fledge.services.core.api.plugins.exceptions import *
from fledge.services.core import connect
from fledge.common.configuration_manager import ConfigurationManager
from fledge.common.audit_logger import AuditLogger
from fledge.services.core import server
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.common.storage_client.exceptions import StorageServerError
from fledge.common.plugin_discovery import PluginDiscovery

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2019 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -------------------------------------------------------------------------------
    | POST             | /fledge/plugins                                         |
    -------------------------------------------------------------------------------
"""
_TIME_OUT = 120
_CHUNK_SIZE = 1024
_PATH = _FLEDGE_DATA + '/plugins/' if _FLEDGE_DATA else _FLEDGE_ROOT + '/data/plugins/'
_LOGGER = logger.setup(__name__, level=logging.INFO)


async def add_plugin(request: web.Request) -> web.Response:
    """ add plugin

    :Example:
        curl -X POST http://localhost:8081/fledge/plugins
        data:
            format - the format of the file. One of tar or package (deb, rpm) or repository
            name - the plugin package name to pull from repository
            version - (optional) the plugin version to install from repository
            url - The url to pull the plugin file from if format is not a repository
            compressed - (optional) boolean this is used to indicate the package is a compressed gzip image
            checksum - the checksum of the file, used to verify correct upload

        curl -sX POST http://localhost:8081/fledge/plugins -d '{"format":"repository", "name": "fledge-south-sinusoid"}'
        curl -sX POST http://localhost:8081/fledge/plugins -d '{"format":"repository", "name": "fledge-notify-slack", "version":"1.6.0"}'
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
            if not name.startswith("fledge-"):
                raise ValueError('name should start with "fledge-" prefix')
            version = data.get('version', None)
            if version:
                if str(version).count('.') != 2:
                    raise ValueError('Invalid version; it should be empty or a valid semantic version X.Y.Z '
                                     'i.e. major.minor.patch to install as per the configured repository')

            # Check Pre-conditions from Packages table
            # if status is -1 (Already in progress) then return as rejected request
            action = "install"
            storage = connect.get_storage_async()
            select_payload = PayloadBuilder().SELECT("status").WHERE(['action', '=', action]).AND_WHERE(
                ['name', '=', name]).payload()
            result = await storage.query_tbl_with_payload('packages', select_payload)
            response = result['rows']
            if response:
                exit_code = response[0]['status']
                if exit_code == -1:
                    msg = "{} package installation already in progress".format(name)
                    return web.HTTPTooManyRequests(reason=msg, body=json.dumps({"message": msg}))
                # Remove old entry from table for other cases
                delete_payload = PayloadBuilder().WHERE(['action', '=', action]).AND_WHERE(
                    ['name', '=', name]).payload()
                await storage.delete_from_tbl("packages", delete_payload)

            # Check If requested plugin is already installed and then return immediately
            plugin_type = name.split('fledge-')[1].split('-')[0]
            plugins_list = PluginDiscovery.get_plugins_installed(plugin_type, False)
            for p in plugins_list:
                if p['packageName'] == name:
                    msg = "{} package is already installed".format(name)
                    return web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
            # Check If requested plugin is available for configured APT repository
            plugins, log_path = await common.fetch_available_packages()
            if name not in plugins:
                raise KeyError('{} plugin is not available for the configured repository'.format(name))

            _platform = platform.platform()
            pkg_mgt = 'yum' if 'centos' in _platform or 'redhat' in _platform else 'apt'
            # Insert record into Packages table
            insert_payload = PayloadBuilder().INSERT(id=str(uuid.uuid4()), name=name, action=action, status=-1,
                                                     log_file_uri="").payload()
            result = await storage.insert_into_tbl("packages", insert_payload)
            response = result['response']
            if response:
                # GET id from Packages table to track the installation response
                select_payload = PayloadBuilder().SELECT("id").WHERE(['action', '=', action]).AND_WHERE(
                    ['name', '=', name]).payload()
                result = await storage.query_tbl_with_payload('packages', select_payload)
                response = result['rows']
                if response:
                    pn = "{}-{}".format(action, name)
                    uid = response[0]['id']
                    # process based parallelism
                    p = multiprocessing.Process(name=pn, target=install_package_from_repo,
                                                args=(name, pkg_mgt, version, uid, storage))
                    p.daemon = True
                    p.start()
                    _LOGGER.info("{} plugin {} started...".format(name, action))
                    msg = "Plugin installation started."
                    status_link = "fledge/package/{}/status?id={}".format(action, uid)
                    result_payload = {"message": msg, "id": uid, "statusLink": status_link}
            else:
                raise StorageServerError
        else:
            if not url or not checksum:
                raise TypeError('URL, checksum params are required')
            if file_format == "tar" and not plugin_type:
                raise ValueError("Plugin type param is required")
            if file_format == "tar" and plugin_type not in ['south', 'north', 'filter', 'notify', 'rule']:
                raise ValueError("Invalid plugin type. Must be 'north' or 'south' or 'filter' or 'notify' or 'rule'")
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

            result_payload = {"message": "{} is successfully downloaded and installed".format(file_name)}
    except StorageServerError as err:
        msg = str(err)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": "Storage error: {}".format(msg)}))
    except (FileNotFoundError, KeyError) as ex:
        raise web.HTTPNotFound(reason=str(ex))
    except (TypeError, ValueError) as ex:
        raise web.HTTPBadRequest(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=str(ex))
    else:
        return web.json_response(result_payload)


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
    cmd = "sudo {} -y install {} > {} 2>&1".format(pkg_mgt, _FLEDGE_ROOT + pkg_file_path, _FLEDGE_ROOT + stdout_file_path)
    _LOGGER.debug("CMD....{}".format(cmd))
    ret_code = os.system(cmd)
    _LOGGER.debug("Return Code....{}".format(ret_code))
    msg = ""
    with open("{}".format(_FLEDGE_ROOT + stdout_file_path), 'r') as fh:
        for line in fh:
            line = line.rstrip("\n")
            msg += line
    _LOGGER.debug("Message.....{}".format(msg))
    # Remove stdout file
    cmd = "{}/extras/C/cmdutil rm {}".format(_FLEDGE_ROOT, stdout_file_path)
    subprocess.run([cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

    # Remove downloaded debian file
    cmd = "{}/extras/C/cmdutil rm {}".format(_FLEDGE_ROOT, pkg_file_path)
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
    plugin_path = "python/fledge/plugins" if py_file else "plugins"
    full_path = "{}/{}/{}/".format(_FLEDGE_ROOT, plugin_path, plugin_type)
    dest_path = "{}/{}/".format(plugin_path, plugin_type)

    # Check if plugin dir exists then remove (for cleanup ONLY) otherwise create dir
    if os.path.exists(full_path + plugin_name) and os.path.isdir(full_path + plugin_name):
        cmd = "{}/extras/C/cmdutil rm {}".format(_FLEDGE_ROOT, dest_path + plugin_name)
        subprocess.run([cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    else:
        cmd = "{}/extras/C/cmdutil mkdir {}".format(_FLEDGE_ROOT, dest_path + plugin_name)
        subprocess.run([cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

    # copy plugin files to the relative plugins directory.
    cmd = "{}/extras/C/cmdutil cp {} {}".format(_FLEDGE_ROOT, _PATH + plugin_name, dest_path)
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
        cmd = "{}/extras/C/cmdutil pip3-req {}{}/{}".format(_FLEDGE_ROOT, _PATH, plugin_name, requirement[0])
        s = subprocess.run([cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        code = s.returncode
        msg = s.stderr.decode("utf-8") if code != 0 else s.stdout.decode("utf-8")
        msg = msg.replace("\n", "").strip()
        _LOGGER.debug("Return code {} and msg {}".format(code, msg))

    # Also removed downloaded and extracted tar file
    cmd = "{}/extras/C/cmdutil rm /data/plugins/{}".format(_FLEDGE_ROOT, file_name)
    subprocess.run([cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    cmd = "{}/extras/C/cmdutil rm /data/plugins/{}".format(_FLEDGE_ROOT, plugin_name)
    subprocess.run([cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

    return code, msg


def install_package_from_repo(name: str, pkg_mgt: str, version: str, uid: uuid, storage: connect) -> None:
    stdout_file_path = common.create_log_file(action="install", plugin_name=name)
    link = "log/" + stdout_file_path.split("/")[-1]
    msg = "installed"
    loop = asyncio.new_event_loop()
    cat = loop.run_until_complete(check_upgrade_on_install())
    upgrade_install_cat_item = cat["upgradeOnInstall"]
    max_upgrade_cat_item = cat['maxUpdate']
    if 'value' in upgrade_install_cat_item:
        if upgrade_install_cat_item['value'] == "true":
            pkg_cache_mgr = server.Server._package_cache_manager
            last_accessed_time = pkg_cache_mgr['upgrade']['last_accessed_time']
            now = datetime.now()
            then = last_accessed_time if last_accessed_time else now
            duration_in_sec = (now - then).total_seconds()
            # If max upgrade per day is set to 1, then an upgrade can not occurs until 24 hours after the last accessed upgrade.
            # If set to 2 then this drops to 12 hours between upgrades, 3 would result in 8 hours between calls and so on.
            if duration_in_sec > (24 / int(max_upgrade_cat_item['value'])) * 60 * 60 or not last_accessed_time:
                _LOGGER.info("Attempting upgrade on {}".format(now))
                cmd = "sudo {} -y upgrade".format(pkg_mgt) if pkg_mgt == 'apt' else "sudo {} -y update".format(pkg_mgt)
                ret_code = os.system(cmd + " > {} 2>&1".format(stdout_file_path))
                if ret_code != 0:
                    # Update record in Packages table for given uid only in case of APT upgrade fails
                    payload = PayloadBuilder().SET(status=ret_code, log_file_uri=link).WHERE(['id', '=', uid]).payload()
                    loop.run_until_complete(storage.update_tbl("packages", payload))
                    return
                else:
                    pkg_cache_mgr['upgrade']['last_accessed_time'] = now
            else:
                _LOGGER.warning("Maximum upgrade exceeds the limit for the day")
            msg = "updated"
    cmd = "sudo {} -y install {}".format(pkg_mgt, name)
    if version:
        cmd = "sudo {} -y install {}={}".format(pkg_mgt, name, version)

    ret_code = os.system(cmd + " >> {} 2>&1".format(stdout_file_path))
    # Update record in Packages table for given uid
    payload = PayloadBuilder().SET(status=ret_code, log_file_uri=link).WHERE(['id', '=', uid]).payload()
    loop.run_until_complete(storage.update_tbl("packages", payload))
    if ret_code == 0:
        # Audit info
        audit = AuditLogger(storage)
        audit_detail = {'packageName': name}
        log_code = 'PKGUP' if msg == 'updated' else 'PKGIN'
        loop.run_until_complete(audit.information(log_code, audit_detail))
        _LOGGER.info('{} plugin {} successfully'.format(name, msg))


async def check_upgrade_on_install() -> Dict:
    cf_mgr = ConfigurationManager(connect.get_storage_async())
    category = await cf_mgr.get_category_all_items("Installation")
    return category
