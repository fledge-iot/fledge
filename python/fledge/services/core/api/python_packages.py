# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import asyncio
import json
from typing import List
import pkg_resources
from aiohttp import web

from fledge.common.audit_logger import AuditLogger
from fledge.common.logger import FLCoreLogger
from fledge.services.core import connect

__author__ = "Himanshu Vimal"
__copyright__ = "Copyright (c) 2022, Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    ----------------------------------------------------------
    | GET            | /fledge/python/packages               |
    | POST           | /fledge/python/package                |
    ----------------------------------------------------------
"""
_LOGGER = FLCoreLogger().get_logger(__name__)


def get_packages_installed() -> List:
    package_ws = pkg_resources.WorkingSet()
    installed_pkgs = [{'package': dist.project_name, 'version': dist.version} for dist in package_ws]
    return installed_pkgs


async def get_packages(request: web.Request) -> web.Response:
    """
    Args:
       request:

    Returns:
           List of python distributions installed.

    :Example:
           curl -X GET http://localhost:8081/fledge/python/packages
    """
    return web.json_response({'packages': get_packages_installed()})


async def install_package(request: web.Request) -> web.Response:
    """
    Args:
        request: '{ "package"   :   "numpy",
                    "version"   :   "1.2"   #optional
                  }'

    Returns:
        Json response with message key  

    :Example:
           curl -X POST http://localhost:8081/fledge/python/package -d '{"package":"numpy", "version":"1.23"}'
    """
    data = await request.json()
    input_package_name = data.get('package', "").strip()
    input_package_version = data.get('version', "").strip()
    
    if len(input_package_name) == 0:
        return web.HTTPBadRequest(reason="Package name empty.")

    def get_installed_package_info(input_package):
        packages = pkg_resources.WorkingSet()
        for package in packages:
            if package.project_name.lower() == input_package.lower():
                return package.project_name, package.version
        return None, None
    
    install_args = input_package_name
    if input_package_version:
        install_args = input_package_name + "==" + input_package_version
    
    installed_package, installed_version = get_installed_package_info(input_package_name)

    if installed_package:
        # Package already exists
        _LOGGER.info("Package: {} Version: {} already installed.".format(installed_package, installed_version))
        return web.HTTPConflict(reason="Package already installed.", 
                                body=json.dumps({"message": "Package {} version {} already installed."
                                                .format(installed_package, installed_version)}))

    # Package not found, install package via pip
    pip_process = await asyncio.create_subprocess_shell('python3 -m pip install ' + install_args,
                                                        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    
    stdout, stderr = await pip_process.communicate()
    if pip_process.returncode == 0:
        _LOGGER.info("Package: {} successfully installed.", format(input_package_name))
        try:
            # Audit log entry: PIPIN
            storage_client = connect.get_storage_async()
            pip_audit_log = AuditLogger(storage_client)
            audit_message = {"package": input_package_name, "status": "Success"}
            if input_package_version:
                audit_message["version"] = input_package_version
            await pip_audit_log.information('PIPIN', audit_message)
        except:
            _LOGGER.exception("Failed to log the audit entry for PIPIN, for package {} install", format(
                input_package_name))

        response = "Package {} version {} installed successfully.".format(input_package_name, input_package_version)
        if not input_package_version:
            response = "Package {} installed successfully.".format(input_package_name)        
        return web.json_response({"message": response})
    else:
        response = "Error while installing package {} version {}.".format(input_package_name, input_package_version)
        if not input_package_version:
            response = "Error while installing package {}.".format(input_package_name)        
        _LOGGER.error(response)
        return web.HTTPNotFound(reason=response, body=json.dumps({"message": stderr.decode(encoding='utf-8')}))
        
