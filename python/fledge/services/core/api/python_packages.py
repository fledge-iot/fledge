import sys
import logging

import pkg_resources
from aiohttp import web

from fledge.common.common import _FLEDGE_ROOT, _FLEDGE_DATA
from fledge.common import logger
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.services.core import connect
from fledge.common.audit_logger import AuditLogger

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

'''
async def install_package(request)

    input_package_name = 'test'
    input_package_version = ''
    
    def check_installed_package(input_package):
        if len(input_package.strip()) == 0:
            return False

        package_list = [dist.project_name for dist in pkg_resources.working_set]

        if input_package.lower() in package_list:  
            _LOGGER.info("Input package already installed.")
            return True
        else:
            _LOGGER.info("Input package not found.")
            return False

    if len(input_package_version.strip()) == 0:
        install_string = input_package_name
    else:
        install_string = input_package_name + '==' + input_package_version

    if check_installed_package(input_package_name):
    #package installed, do audit log and return
        _LOGGER.info("Package already installed")
    else:
        #install package
        try:
            code = subprocess.run([sys.executable, '-m', 'pip', 'install', install_string], capture_output=True, text=True, encoding='utf-8')
            if code.returncode != 0:
            #log error and output
                _LOGGER.error(code.stdout)
                _LOGGER.error(code.stderr)
            #close code after output is processed
            else:
                _LOGGER.info("Package: {} successfully installed", format(input_package))
        except subprocess.CalledProcessError as e:
            _LOGGER.exception("Pip install exception: {}", format(str(e.output)))

'''
