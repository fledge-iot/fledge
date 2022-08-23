import logging
import pkg_resources
import sys
import json
import subprocess
import asyncio
import re

from aiohttp import web
from fledge.common.common import _FLEDGE_ROOT, _FLEDGE_DATA
from fledge.common import logger
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.common.storage_client.exceptions import StorageServerError
from fledge.services.core import connect
from fledge.common.audit_logger import AuditLogger
from fledge.services.core import connect

__author__ = "Himanshu Vimal"
__copyright__ = "Copyright (c) 2019, Dianomic Systems Inc."
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
    
    def get_installed_pkg_list():
        package_dict = [{'package':dist.project_name,'version': dist.version} for dist in pkg_resources.working_set]
        return package_dict

    installed_pkg_list = get_installed_pkg_list()
    return web.json_response({'packages': installed_pkg_list})


async def install_package(request: web.Request) -> web.Response:
    """
    Args:
        Request: '{ "package"   :   "numpy", 
                    "version"   :   "1.2"   #optional
                  }'

    Returns:
        Success: 

    :Example:
           curl -X POST http://localhost:8081/fledge/python/package -d '{"package":"numpy", "version":"1.23"}'
    """
    
    def get_installed_package_info(input_package):

        packages = pkg_resources.working_set

        for package in packages:
            if package.project_name == input_package.lower():
                return package.project_name, package.version

        return None, None
                    
    # def is_canonical(version):
    #     #regex in accordance with PEP-440
    #     #Refer to https://peps.python.org/pep-0440/#appendix-b-parsing-version-strings-with-regular-expressions
    #     return re.match(r'^([1-9][0-9]*!)?(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))*((a|b|rc)(0|[1-9][0-9]*))?(\.post(0|[1-9][0-9]*))?(\.dev(0|[1-9][0-9]*))?$', input_package_version) is not None

    data = await request.json()

    input_package_name = data.get('package', None)
    input_package_version = data.get('version', None)
    #regex - PEP440 check for canonical versions
    
    if len(input_package_name.strip()) == 0:
        return web.HTTPBadRequest(reason="Package name empty.")

    #check version - semver

    # if is_canonical(input_package_version) == None:
    #     return web.HTTPBadRequest(reason="Package version not in canonical form.")
    
    if input_package_version == None:
        install_cmd = input_package_name.lower()
    else:
        install_cmd = input_package_name.lower() + "==" + input_package_version.lower()
    
    installed_package, installed_version = get_installed_package_info(input_package_name)

    if installed_package != None:
         #Package already exists
        _LOGGER.info("Package: {} Version: {} already installed.".format(installed_package, installed_version))
        return web.HTTPConflict(reason="Package already installed.", 
                                body=json.dumps({"message":"Package: {} Version:{} already installed"
                                                .format(installed_package, installed_version)}))
    else:
        try:
            # code = subprocess.run([sys.executable, '-m', 'pip', 'install', install_string], capture_output=True, text=True, encoding='utf-8')
            pip_process = await asyncio.create_subprocess_exec('pip3 install', [install_cmd], stdout=asyncio.subprocess.PIPE, 
                                                                stderr=asyncio.subprocess.PIPE)
            
            pip_stdout, pip_stderr = await pip_process.communicate()
            if pip_process.returncode == 0:
                _LOGGER.info("Package: {} successfully installed", format(input_package_name))
                try:
                    #Audit log entry: PIPIN
                    storage_client = connect.get_storage_async()
                    pip_audit_log = AuditLogger(storage_client)
                    audit_message = {"message":"Package: {} Version:{} successfully installed"
                                        .format(input_package_name, input_package_version)}
                    await pip_audit_log.information('PIPIN', audit_message)
                except:
                    _LOGGER.exception("Failed to log the audit entry for PIPIN, while installing package {}", format(input_package_name))

                return web.json_response("Package: {} successfully installed".format(input_package_name, input_package_version))
            else:
            #log error and output
            #close code after output is processed
                # _LOGGER.error(code.stdout)
                _LOGGER.error(pip_stderr.decode().strip())
                return web.HTTPNotFound(reason="Invalid package name")
        except subprocess.CalledProcessError as ex:
            _LOGGER.exception("Pip install exception: {}", format(str(ex.output)))
            return web.HTTPError(reason=str(ex))
        except Exception as ex:
            return web.HTTPInternalServerError(reason=str(ex))