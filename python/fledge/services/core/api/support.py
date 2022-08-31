# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import os
import platform
import subprocess
import json
import logging
import datetime
import urllib.parse
from pathlib import Path
from aiohttp import web

from fledge.common import logger
from fledge.common.common import _FLEDGE_ROOT, _FLEDGE_DATA
from fledge.services.core.support import SupportBuilder

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_logger = logger.setup(__name__, level=logging.DEBUG)

_SYSLOG_FILE = '/var/log/syslog'
if any(x in platform.platform() for x in ['centos', 'redhat']):
    _SYSLOG_FILE = '/var/log/messages'

__DEFAULT_LIMIT = 20
__DEFAULT_OFFSET = 0
__DEFAULT_LOG_SOURCE = 'Fledge'

# Debug and above
__GET_SYSLOG_CMD_TEMPLATE = "grep -a -E '({})\[' {} | head -n {} | tail -n {}"
__GET_SYSLOG_TOTAL_MATCHED_LINES = "grep -a -c -E '({})\[' {}"
__GET_SYSLOG_TEMPLATE_WITH_NON_TOTALS = "grep -a -E '({})\[' {} | head -n -{} | tail -n {}"
# Info and above
__GET_SYSLOG_CMD_WITH_INFO_TEMPLATE = "grep -a -E '({})\[.*].* (INFO|WARNING|ERROR|FATAL)' {} | head -n {} | tail -n {}"
__GET_SYSLOG_INFO_MATCHED_LINES = "grep -a -c -E '({})\[.*].* (INFO|WARNING|ERROR|FATAL)' {}"
__GET_SYSLOG_INFO_TEMPLATE_WITH_NON_TOTALS = "grep -a -E '({})\[.*].* (INFO|WARNING|ERROR|FATAL)' {} | head -n -{} | tail -n {}"
# Error and above
__GET_SYSLOG_CMD_WITH_ERROR_TEMPLATE = "grep -a -E '({})\[.*].* (ERROR|FATAL)' {} | head -n {} | tail -n {}"
__GET_SYSLOG_ERROR_MATCHED_LINES = "grep -a -c -E '({})\[.*].* (ERROR|FATAL)' {}"
__GET_SYSLOG_ERROR_TEMPLATE_WITH_NON_TOTALS = "grep -a -E '({})\[.*].* (ERROR|FATAL)' {} | head -n -{} | tail -n {}"
# Warning and above
__GET_SYSLOG_CMD_WITH_WARNING_TEMPLATE = "grep -a -E '({})\[.*].* (WARNING|ERROR|FATAL)' {} | head -n {} | tail -n {}"
__GET_SYSLOG_WARNING_MATCHED_LINES = "grep -a -c -E '({})\[.*].* (WARNING|ERROR|FATAL)' {}"
__GET_SYSLOG_WARNING_TEMPLATE_WITH_NON_TOTALS = "grep -a -E '({})\[.*].* (WARNING|ERROR|FATAL)' {} | head -n -{} | tail -n {}"

_help = """
    ------------------------------------------------------------------------------
    | GET POST        | /fledge/support                                          |
    | GET             | /fledge/support/{bundle}                                 |
    | GET             | /fledge/syslog                                           |
    ------------------------------------------------------------------------------
"""


async def fetch_support_bundle(request):
    """ get list of available support bundles

    :Example:
        curl -X GET http://localhost:8081/fledge/support
    """
    # Get support directory path
    support_dir = _get_support_dir()
    valid_extension = '.tar.gz'
    found_files = []
    for root, dirs, files in os.walk(support_dir):
        found_files = [f for f in files if f.endswith(valid_extension)]

    return web.json_response({"bundles": found_files})


async def fetch_support_bundle_item(request):
    """ check existence of a bundle support by name

    :Example:
        curl -O http://localhost:8081/fledge/support/support-180301-13-35-23.tar.gz

        curl -X GET http://localhost:8081/fledge/support/support-180311-18-03-36.tar.gz
        -H "Accept-Encoding: gzip" --write-out "size_download=%{size_download}\n" --compressed
    """
    bundle_name = request.match_info.get('bundle', None)

    if not str(bundle_name).endswith('.tar.gz'):
        return web.HTTPBadRequest(reason="Bundle file extension is invalid")

    if not os.path.isdir(_get_support_dir()):
        raise web.HTTPNotFound(reason="Support bundle directory does not exist")

    for root, dirs, files in os.walk(_get_support_dir()):
        if str(bundle_name) not in files:
            raise web.HTTPNotFound(reason='{} not found'.format(bundle_name))

    p = Path(_get_support_dir()) / str(bundle_name)
    return web.FileResponse(path=p)


async def create_support_bundle(request):
    """ Create a support bundle by name

    :Example:
        curl -X POST http://localhost:8081/fledge/support
    """
    support_dir = _get_support_dir()
    try:
        bundle_name = await SupportBuilder(support_dir).build()
    except Exception as ex:
        raise web.HTTPInternalServerError(reason='Support bundle could not be created. {}'.format(str(ex)))

    return web.json_response({"bundle created": bundle_name})


async def get_syslog_entries(request):
    """ Returns a list of syslog trail entries sorted with most recent first and total count
        (including the criteria search if applied)

    :Example:
        curl -X GET http://localhost:8081/fledge/syslog
        curl -X GET "http://localhost:8081/fledge/syslog?limit=5"
        curl -X GET "http://localhost:8081/fledge/syslog?offset=5"
        curl -X GET "http://localhost:8081/fledge/syslog?source=storage"
        curl -X GET "http://localhost:8081/fledge/syslog?source=<svc_name>|<task_name>"
        curl -X GET "http://localhost:8081/fledge/syslog?level=error"
        curl -X GET "http://localhost:8081/fledge/syslog?limit=5&source=storage"
        curl -X GET "http://localhost:8081/fledge/syslog?limit=5&offset=5&source=storage"
        curl -sX GET "http://localhost:8081/fledge/syslog?nontotals=true"
        curl -sX GET "http://localhost:8081/fledge/syslog?nontotals=true&source=<svc_name>|<task_name>"
        curl -sX GET "http://localhost:8081/fledge/syslog?nontotals=true&limit=5"
        curl -sX GET "http://localhost:8081/fledge/syslog?nontotals=true&limit=100&offset=50"
        curl -sX GET "http://localhost:8081/fledge/syslog?nontotals=true&source=<svc_name>|<task_name>&limit=10&offset=50"
        curl -sX GET "http://localhost:8081/fledge/syslog?nontotals=true&source=<svc_name>|<task_name>"
    """
    try:
        # limit
        limit = int(request.query['limit']) if 'limit' in request.query and request.query[
            'limit'] != '' else __DEFAULT_LIMIT
        if limit < 0:
            raise ValueError('Limit must be a positive integer.')

        # offset
        offset = int(request.query['offset']) if 'offset' in request.query and request.query[
            'offset'] != '' else __DEFAULT_OFFSET
        if offset < 0:
            raise ValueError('Offset must be a positive integer OR Zero.')

        # source
        source = urllib.parse.unquote(request.query['source']) if 'source' in request.query and request.query[
            'source'] != '' else __DEFAULT_LOG_SOURCE
        if source.lower() in ['fledge', 'storage']:
            source = source.lower()
            valid_source = {'fledge': "Fledge.*", 'storage': 'Fledge Storage'}
        else:
            valid_source = {source: "Fledge {}".format(source)}

        # Get filtered lines
        template = __GET_SYSLOG_CMD_TEMPLATE
        lines = __GET_SYSLOG_TOTAL_MATCHED_LINES
        non_total_template = __GET_SYSLOG_TEMPLATE_WITH_NON_TOTALS
        level = "debug" # default log level
        if 'level' in request.query and request.query['level'] != '':
            level = request.query['level'].lower()
            supported_level = ['info', 'warning', 'error', 'debug']
            if level not in supported_level:
                raise ValueError('{} is invalid level. Supported levels are {}'.format(level, supported_level))
            if level == 'info':
                template = __GET_SYSLOG_CMD_WITH_INFO_TEMPLATE
                lines = __GET_SYSLOG_INFO_MATCHED_LINES
                # non_total_template = __GET_SYSLOG_INFO_TEMPLATE_WITH_NON_TOTALS
            elif level == 'warning':
                template = __GET_SYSLOG_CMD_WITH_WARNING_TEMPLATE
                lines = __GET_SYSLOG_WARNING_MATCHED_LINES
                # non_total_template = __GET_SYSLOG_WARNING_TEMPLATE_WITH_NON_TOTALS
            elif level == 'error':
                template = __GET_SYSLOG_CMD_WITH_ERROR_TEMPLATE
                lines = __GET_SYSLOG_ERROR_MATCHED_LINES
                # non_total_template = __GET_SYSLOG_ERROR_TEMPLATE_WITH_NON_TOTALS
        response = {}
        # nontotals
        non_totals = request.query['nontotals'].lower() if 'nontotals' in request.query and request.query[
            'nontotals'] != '' else "false"
        if non_totals not in ("true", "false"):
            raise ValueError('nontotals must either be in True or False.')

        log_file = os.path.join(_get_logs_dir(), "{}.log".format(level))
        if non_totals != "true":
            # Get total lines
            cmd = lines.format(valid_source[source], log_file)
            _logger.debug("cmd 1={}".format(cmd))
            t = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout.readlines()
            total_lines = int(t[0].decode())
            response['count'] = total_lines
            cmd = template.format(valid_source[source], log_file, total_lines - offset, limit)
            _logger.debug("cmd 2={}".format(cmd))
        else:
            cmd = non_total_template.format(valid_source[source], log_file, offset, limit)
            _logger.debug("cmd={}".format(cmd))

        t1 = datetime.datetime.now()
        a = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout.readlines()
        t2 = datetime.datetime.now()
        _logger.debug('********* Time taken for extracting logs: {} msec'.format((t2 - t1).total_seconds()*1000))
        c = [b.decode() for b in a]  # Since "a" contains return value in bytes, convert it to string
        response['logs'] = c
    except ValueError as err:
        msg = str(err)
        raise web.HTTPBadRequest(body=json.dumps({"message": msg}), reason=msg)
    except (OSError, Exception) as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(body=json.dumps({"message": msg}), reason=msg)

    return web.json_response(response)


def _get_support_dir():
    if _FLEDGE_DATA:
        support_dir = os.path.expanduser(_FLEDGE_DATA + '/support')
    else:
        support_dir = os.path.expanduser(_FLEDGE_ROOT + '/data/support')

    return support_dir

def _get_logs_dir():
    if _FLEDGE_DATA:
        logs_dir = os.path.expanduser(_FLEDGE_DATA + '/logs')
    else:
        logs_dir = os.path.expanduser(_FLEDGE_ROOT + '/data/logs')

    return logs_dir
