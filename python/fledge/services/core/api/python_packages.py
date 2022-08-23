import logging
import sys
import pkg_resources
import json
import subprocess
import asyncio

from aiohttp import web
from fledge.common import logger
from fledge.services.core import connect
from fledge.common.audit_logger import AuditLogger
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
_LOGGER = logger.setup(__name__, level=logging.INFO)

async def get_python_packages(request: web.Request) -> web.Response:
    """
    Args:
       request:

    Returns:
           List of python distributions installed.

    :Example:
           curl -X GET http://localhost:8081/fledge/python/packages
    """
    #update current working_set after any new installation
    for entry in sys.path:
        pkg_resources.working_set.add_entry(entry)    
    installed_pkgs = [{'package':dist.project_name,'version': dist.version} for dist in pkg_resources.working_set]
    return web.json_response({'packages': installed_pkgs})


async def install_package(request: web.Request) -> web.Response:
    """
    Args:
        Request: '{ "package"   :   "numpy", 
                    "version"   :   "1.2"   #optional
                  }'

    Returns:
        Json response with message key  

    :Example:
           curl -X POST http://localhost:8081/fledge/python/package -d '{"package":"numpy", "version":"1.23"}'
    """
    
    def get_installed_package_info(input_package):
        for entry in sys.path:
            pkg_resources.working_set.add_entry(entry)
        
        packages = pkg_resources.working_set
        for package in packages:
            if package.project_name == input_package.lower():
                return package.project_name, package.version
        return None, None
                    
    data = await request.json()
    
    input_package_version = ""
    input_package_name = data.get('package', None).strip()
    input_package_version = data.get('version', None).strip()
    
    if len(input_package_name) == 0:
        return web.HTTPBadRequest(reason="Package name empty.")

    install_args = input_package_name
    if input_package_version:
        install_args = input_package_name + "==" + input_package_version
    
    installed_package, installed_version = get_installed_package_info(input_package_name)

    if installed_package is None:
        #Package not found, install package via pip
        try:
            pip_process = await asyncio.create_subprocess_shell('python3 -m pip install '+ install_args, 
                                                                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            
            stdout, stderr = await pip_process.communicate()
            if pip_process.returncode == 0:
                _LOGGER.info("Package: {} successfully installed", format(input_package_name))
                try:
                    #Audit log entry: PIPIN
                    storage_client = connect.get_storage_async()
                    pip_audit_log = AuditLogger(storage_client)
                    audit_message = {"package":input_package_name, "status": "Success"}
                    if input_package_version:
                        audit_message["version"] = input_package_version
                    await pip_audit_log.information('PIPIN', audit_message)
                except:
                    _LOGGER.exception("Failed to log the audit entry for PIPIN, for package {} install", format(input_package_name))
                response = "Package {} version {} installed successfully.".format(input_package_name, input_package_version)
                if not input_package_version:
                    response = "Package {} installed successfully.".format(input_package_name)
                return web.json_response({"message": response})
            else:
                response = "Error while installing package {} version {}.".format(input_package_name, input_package_version)
                if not input_package_version:
                    response = "Error while installing package {}.".format(input_package_name)
                return web.HTTPNotFound(reason=response, body=json.dumps({"message": stderr.decode()}))
        except subprocess.CalledProcessError as ex:
            _LOGGER.exception("Pip install exception: {}".format(str(ex.output)))
            return web.HTTPError(reason=str(ex))
        except Exception as ex:
            return web.HTTPInternalServerError(reason=str(ex))
    else:
         #Package already exists
        _LOGGER.info("Package: {} Version: {} already installed.".format(installed_package, installed_version))
        return web.HTTPConflict(reason="Package already installed.", 
                                body=json.dumps({"message":"Package {} version {} already installed."
                                                .format(installed_package, installed_version)}))
