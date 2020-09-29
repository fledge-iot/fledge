# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge.readthedocs.io/
# FLEDGE_END

import os
import logging
import json
from datetime import datetime

from pathlib import Path
from aiohttp import web

from fledge.common.common import _FLEDGE_ROOT, _FLEDGE_DATA
from fledge.common import logger
from fledge.services.core import server


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2019, Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    ----------------------------------------------------------
    | GET            | /fledge/package/log                   |
    | GET            | /fledge/package/log/{name}            |
    | GET            | /fledge/package/{action}/status       |
    ----------------------------------------------------------
"""
valid_extension = '.log'
_LOGGER = logger.setup(__name__, level=logging.INFO)


async def get_logs(request: web.Request) -> web.Response:
    """ GET list of package logs

    :Example:
        curl -sX GET http://localhost:8081/fledge/package/log
    """
    # Get logs directory path
    logs_root_dir = _get_logs_dir()
    found_files = []

    for root, dirs, files in os.walk(logs_root_dir):
        found_files = [f for f in files if f.endswith(valid_extension)]

    result = []
    for f in found_files:
        # Empty log name for update cmd
        name = ""
        t1 = f.split(".log")
        t2 = t1[0].split("-fledge")
        t3 = t2[0].split("-")
        t4 = t1[0].split("-list")
        if len(t2) >= 2:
            name = "fledge{}".format(t2[1])
        if len(t4) >= 2:
            name = "list"
        dt = "{}-{}-{}-{}".format(t3[0], t3[1], t3[2], t3[3])
        ts = datetime.strptime(dt, "%y%m%d-%H-%M-%S").strftime('%Y-%m-%d %H:%M:%S')
        result.append({"timestamp": ts, "name": name, "filename": f})

    return web.json_response({"logs": result})


async def get_log_by_name(request: web.Request) -> web.FileResponse:
    """ GET for a particular log file will return the content of the log file.

    :Example:
        a) Download file
        curl -O http://localhost:8081/fledge/package/log/190802-11-45-28-fledge-south-sinusoid.log

        b) See the content of a file
        curl -sX GET http://localhost:8081/fledge/package/log/190802-11-45-28-fledge-south-sinusoid.log
    """
    # Get logs directory path
    file_name = request.match_info.get('name', None)
    if not file_name.endswith(valid_extension):
        raise web.HTTPBadRequest(reason="Accepted file extension is {}".format(valid_extension))

    logs_root_dir = _get_logs_dir()
    for root, dirs, files in os.walk(logs_root_dir):
        if str(file_name) not in files:
            raise web.HTTPNotFound(reason='{} file not found'.format(file_name))

    fp = Path(logs_root_dir + "/" + str(file_name))
    return web.FileResponse(path=fp)


def _get_logs_dir(_path: str = '/logs/') -> str:
    dir_path = _FLEDGE_DATA + _path if _FLEDGE_DATA else _FLEDGE_ROOT + '/data' + _path
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    logs_dir = os.path.expanduser(dir_path)
    return logs_dir


async def get_package_status(request: web.Request) -> web.Response:
    """ GET list of package status

    :Example:
        curl -sX GET http://localhost:8081/fledge/package/list/status
        curl -sX GET http://localhost:8081/fledge/package/install/status
        curl -sX GET http://localhost:8081/fledge/package/purge/status
        curl -sX GET http://localhost:8081/fledge/package/update/status
        curl -sX GET http://localhost:8081/fledge/package/install/status?name=foglamp-south-sinusoid
        curl -sX GET http://localhost:8081/fledge/package/purge/status?name=foglamp-south-sinusoid
        curl -sX GET http://localhost:8081/fledge/package/update/status?name=foglamp-south-sinusoid
    """
    try:
        
        response = server.Server._package_manager._packages_map_list
        if 'name' in request.query and request.query['name'] != '':
            name = request.query['name']
            with open(_FLEDGE_ROOT  + '/data/plugins/install-' + name +'.json', 'r') as outfile:
                response = json.load(outfile)
                _LOGGER.exception("READ JSON: {}".format(response))

            if response is None:
                msg = "No status found for requested package {}".format(name)
                raise ValueError(msg)
    except ValueError as err_msg:
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": str(err_msg)}))
    except Exception as exc:
        raise web.HTTPInternalServerError(reason=str(exc))
    else:
        return web.json_response({"packageStatus": response})
