# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import os
import logging
import json
from datetime import datetime

from pathlib import Path
from aiohttp import web

from fledge.common.common import _FLEDGE_ROOT, _FLEDGE_DATA
from fledge.common import logger
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.services.core import connect

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
valid_actions = ('list', 'install', 'purge', 'update')
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
        curl -sX GET http://localhost:8081/fledge/package/list/status?id=6560fc22-1e69-416c-9b61-06cd4f3fd8af
        curl -sX GET http://localhost:8081/fledge/package/install/status?id=9f2f11c6-cbc4-483f-b49d-5eb57cf8001a
        curl -sX GET http://localhost:8081/fledge/package/purge/status?id=a7ca51b0-35bf-476a-84fe-60e98006875e
        curl -sX GET http://localhost:8081/fledge/package/update/status?id=f156e5de-3e43-4451-a63b-a933c65754ef
    """
    try:
        action = request.match_info.get('action', '').lower()
        if action not in valid_actions:
            raise ValueError("Accepted package actions are {}".format(valid_actions))
        select = PayloadBuilder().SELECT(("id", "name", "action", "status", "log_file_uri")).WHERE(
            ['action', '=', action]).chain_payload()
        if 'id' in request.query and request.query['id'] != '':
            select = PayloadBuilder(select).AND_WHERE(['id', '=', request.query['id']]).chain_payload()
        final_payload = PayloadBuilder(select).payload()
        storage_client = connect.get_storage_async()
        result = await storage_client.query_tbl_with_payload('packages', final_payload)
        response = result['rows']
        if not response:
            raise KeyError("No record found")
        result = []
        for r in response:
            tmp = r
            if r['status'] == 0:
                tmp['status'] = 'success'
            elif r['status'] == -1:
                tmp['status'] = 'in-progress'
            else:
                tmp['status'] = 'failed'
            tmp['logFileURI'] = r['log_file_uri']
            del tmp['log_file_uri']
            result.append(tmp)
    except ValueError as err_msg:
        raise web.HTTPBadRequest(reason=err_msg, body=json.dumps({"message": str(err_msg)}))
    except KeyError as err_msg:
        raise web.HTTPNotFound(reason=err_msg, body=json.dumps({"message": str(err_msg)}))
    except Exception as exc:
        raise web.HTTPInternalServerError(reason=str(exc))
    else:
        return web.json_response({"packageStatus": result})
