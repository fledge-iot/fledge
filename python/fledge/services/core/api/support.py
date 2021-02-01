# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import os
import platform
import subprocess
import json
from pathlib import Path
from aiohttp import web
import urllib.parse

from fledge.services.core.support import SupportBuilder

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_FLEDGE_DATA = os.getenv("FLEDGE_DATA", default=None)
_FLEDGE_ROOT = os.getenv("FLEDGE_ROOT", default='/usr/local/fledge')

_SYSLOG_FILE = '/var/log/syslog'

if ('centos' in platform.platform()) or ('redhat' in platform.platform()):
    _SYSLOG_FILE = '/var/log/messages'

__DEFAULT_LIMIT = 20
__DEFAULT_OFFSET = 0
__DEFAULT_LOG_SOURCE = 'Fledge'
__GET_SYSLOG_CMD_TEMPLATE = "grep -a -E '({})\[' {} | head -n {} | tail -n {}"
__GET_SYSLOG_CMD_WITH_INFO_TEMPLATE = "grep -a -E '({})\[' {} | grep -a -E -i '(info|warning|error|fatal)' | head -n {} | tail -n {}"
__GET_SYSLOG_CMD_WITH_ERROR_TEMPLATE = "grep -a -E '({})\[' {} | grep -a -E -i '(error|fatal)' | head -n {} | tail -n {}"
__GET_SYSLOG_CMD_WITH_WARNING_TEMPLATE = "grep -a -E '({})\[' {} | grep -a -E -i '(warning|error|fatal)' | head -n {} | tail -n {}"

__GET_SYSLOG_TOTAL_MATCHED_LINES = "grep -a -E '({})\[' {} | wc -l"
__GET_SYSLOG_INFO_MATCHED_LINES = "grep -a -E '({})\[' {} | grep -a -E -i '(info|warning|error|fatal)' | wc -l"
__GET_SYSLOG_ERROR_MATCHED_LINES = "grep -a -E '({})\[' {} | grep -a -E -i '(error|fatal)' | wc -l"
__GET_SYSLOG_WARNING_MATCHED_LINES = "grep -a -E '({})\[' {} | grep -a -E -i '(warning|error|fatal)' | wc -l"

_help = """
    ------------------------------------------------------------------------------
    | GET POST        | /fledge/support                                          |
    | GET             | /fledge/support/{bundle}                                 |
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
    base_url = "{}://{}:{}/fledge".format(request.url.scheme, request.url.host, request.url.port)
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
    """

    try:
        limit = int(request.query['limit']) if 'limit' in request.query and request.query['limit'] != '' else __DEFAULT_LIMIT
        if limit < 0:
            raise ValueError
    except (Exception, ValueError):
        raise web.HTTPBadRequest(reason="Limit must be a positive integer")

    try:
        offset = int(request.query['offset']) if 'offset' in request.query and request.query['offset'] != '' else __DEFAULT_OFFSET
        if offset < 0:
            raise ValueError
    except (Exception, ValueError):
        raise web.HTTPBadRequest(reason="Offset must be a positive integer OR Zero")

    source = urllib.parse.unquote(request.query['source']) if 'source' in request.query and request.query['source'] != '' else __DEFAULT_LOG_SOURCE
    if source.lower() in ['fledge', 'storage']:
        source = source.lower()
        valid_source = {'fledge': "Fledge.*", 'storage': 'Fledge Storage'}
    else:
        valid_source = {source: "Fledge {}".format(source)}

    try:
        # Get filtered lines
        template = __GET_SYSLOG_CMD_TEMPLATE
        lines = __GET_SYSLOG_TOTAL_MATCHED_LINES
        if 'level' in request.query and request.query['level'] != '':
            level = request.query['level'].lower()
            supported_level = ['info', 'warning', 'error', 'debug']
            if level not in supported_level:
                raise ValueError('{} is invalid level. Supported levels are {}'.format(level, supported_level))
            if level == 'info':
                template = __GET_SYSLOG_CMD_WITH_INFO_TEMPLATE
                lines = __GET_SYSLOG_INFO_MATCHED_LINES
            elif level == 'warning':
                template = __GET_SYSLOG_CMD_WITH_WARNING_TEMPLATE
                lines = __GET_SYSLOG_WARNING_MATCHED_LINES
            elif level == 'error':
                template = __GET_SYSLOG_CMD_WITH_ERROR_TEMPLATE
                lines = __GET_SYSLOG_ERROR_MATCHED_LINES

        # Get total lines
        cmd = lines.format(valid_source[source], _SYSLOG_FILE)
        t = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout.readlines()
        total_lines = int(t[0].decode())
        cmd = template.format(valid_source[source], _SYSLOG_FILE, total_lines - offset, limit)
        a = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout.readlines()
        c = [b.decode() for b in a]  # Since "a" contains return value in bytes, convert it to string
    except ValueError as err:
        raise web.HTTPBadRequest(body=json.dumps({"message": str(err)}), reason=str(err))
    except (OSError, Exception) as ex:
        raise web.HTTPInternalServerError(reason=str(ex))

    return web.json_response({'logs': c, 'count': total_lines})


def _get_support_dir():
    if _FLEDGE_DATA:
        support_dir = os.path.expanduser(_FLEDGE_DATA + '/support')
    else:
        support_dir = os.path.expanduser(_FLEDGE_ROOT + '/data/support')

    return support_dir
