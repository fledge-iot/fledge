# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import os

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

    return web.json_response({"logs": found_files})


async def get_log_by_name(request: web.Request) -> web.Response:
    """ GET for a particular log file will return the content of the log file.

    :Example:
        curl -sX GET http://localhost:8081/foglamp/package/log/190801-13-27-36-foglamp-south-randomwalk.log
    """
    # Get logs directory path
    file_name = request.match_info.get('name', None)
    if not file_name.endswith(valid_extension):
        raise web.HTTPBadRequest(reason="Accepted file extension is {}".format(valid_extension))

    for root, dirs, files in os.walk(_get_logs_dir()):
        if str(file_name) not in files:
            raise web.HTTPNotFound(reason='{} file not found'.format(file_name))

    file_content = []
    with open("{}{}".format(_get_logs_dir(), file_name), 'r') as fh:
        for line in fh:
            line = line.rstrip("\n")
            file_content.append(line)
    return web.json_response({"result": file_content})


def _get_logs_dir(_path: str = '/logs/') -> str:
    dir_path = _FOGLAMP_DATA + _path if _FOGLAMP_DATA else _FOGLAMP_ROOT + '/data' + _path
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    logs_dir = os.path.expanduser(dir_path)
    return logs_dir
