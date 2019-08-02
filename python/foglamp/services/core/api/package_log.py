# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import os
from _datetime import datetime

from pathlib import Path
from aiohttp import web

from foglamp.common.common import _FOGLAMP_ROOT, _FOGLAMP_DATA


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2019, Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -----------------------------------------------------------
    | GET            | /foglamp/package/log                   |
    | GET            | /foglamp/package/log/{name}            |
    -----------------------------------------------------------
"""
valid_extension = '.log'


async def get_logs(request: web.Request) -> web.Response:
    """ GET list of package logs

    :Example:
        curl -sX GET http://localhost:8081/foglamp/package/log
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
        t2 = t1[0].split("-foglamp")
        t3 = t2[0].split("-")
        if len(t2) >= 2:
            name = "foglamp{}".format(t2[1])
        dt = "{}-{}-{}-{}".format(t3[0], t3[1], t3[2], t3[3])
        ts = datetime.strptime(dt, "%y%m%d-%H-%M-%S").strftime('%Y-%m-%d %H:%M:%S')
        result.append({"timestamp": ts, "name": name, "filepath": f})

    return web.json_response({"logs": result})


async def get_log_by_name(request: web.Request) -> web.FileResponse:
    """ GET for a particular log file will return the content of the log file.

    :Example:
        a) Download file
        curl -O http://localhost:8081/foglamp/package/log/190802-11-45-28-foglamp-south-sinusoid.log

        b) See the content of a file
        curl -sX GET http://localhost:8081/foglamp/package/log/190802-11-45-28-foglamp-south-sinusoid.log
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
    dir_path = _FOGLAMP_DATA + _path if _FOGLAMP_DATA else _FOGLAMP_ROOT + '/data' + _path
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    logs_dir = os.path.expanduser(dir_path)
    return logs_dir
