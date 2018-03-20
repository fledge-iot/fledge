# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import os
import subprocess
from pathlib import Path
from aiohttp import web
from foglamp.common import logger
from foglamp.services.core.support import SupportBuilder

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_FOGLAMP_DATA = os.getenv("FOGLAMP_DATA", default=None)
_FOGLAMP_ROOT = os.getenv("FOGLAMP_ROOT", default='/usr/local/foglamp')
_SYSLOG_FILE = '/var/log/syslog'
__DEFAULT_LIMIT = 20
__DEFAULT_OFFSET = 0
__DEFAULT_LOG_TYPE = 'FogLAMP'
__GET_SYSLOG_CMD_TEMPLATE = "grep -n '{}\[' {} | tail -n {} | head -n {}"
__GET_SYSLOG_TOTAL_MATCHED_LINES = "grep -n '{}\[' {} | wc -l"

_logger = logger.setup(__name__, level=20)

_help = """
    -------------------------------------------------------------------------------
    | GET POST        | /foglamp/support                                          |
    | GET             | /foglamp/support/{bundle}                                 |
    -------------------------------------------------------------------------------
"""


async def fetch_support_bundle(request):
    """ get list of available support bundles

    :Example:
        curl -X GET http://localhost:8081/foglamp/support
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
        curl -O http://localhost:8081/foglamp/support/support-180301-13-35-23.tar.gz

        curl -X GET http://localhost:8081/foglamp/support/support-180311-18-03-36.tar.gz
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
        curl -X POST http://localhost:8081/foglamp/support
    """
    support_dir = _get_support_dir()
    base_url = "{}://{}:{}/foglamp".format(request.url.scheme, request.url.host, request.url.port)
    try:
        bundle_name = await SupportBuilder(support_dir, base_url).build()
    except Exception as ex:
        raise web.HTTPInternalServerError(reason='Support bundle could not be created. {}'.format(str(ex)))

    return web.json_response({"bundle created": bundle_name})


async def get_syslog_entries(request):
    """ Returns a list of syslog trail entries sorted with most recent first and total count
        (including the criteria search if applied)

    :Example:
        curl -X GET http://localhost:8081/foglamp/syslog
        curl -X GET "http://localhost:8081/foglamp/syslog?limit=5"
        curl -X GET "http://localhost:8081/foglamp/syslog?offset=5"
        curl -X GET "http://localhost:8081/foglamp/syslog?source=storage"
        curl -X GET "http://localhost:8081/foglamp/syslog?limit=5&source=storage"
        curl -X GET "http://localhost:8081/foglamp/syslog?limit=5&offset=5&source=storage"
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

    try:
        source = request.query['source'] if 'source' in request.query and request.query['source'] != '' else __DEFAULT_LOG_TYPE
        if source.lower() not in ['foglamp', 'storage', 'foglamp storage']:
            raise ValueError
        valid_source = {'foglamp': "FogLAMP", 'storage': 'Storage', 'foglamp storage': 'FogLAMP Storage'}
    except ValueError:
        raise web.HTTPBadRequest(reason="{} is not a valid source".format(source))

    try:
        # Get total lines
        cmd = __GET_SYSLOG_TOTAL_MATCHED_LINES.format(valid_source[source.lower()], _SYSLOG_FILE)
        t = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout.readlines()
        tot_lines = int(t[0].decode())
        if offset >= (tot_lines - limit):
            raise ValueError
    except ValueError:
        raise web.HTTPBadRequest(reason="Offset {} must be less than (total line count - limit) {}".format(offset, tot_lines - limit))
    except (OSError, Exception) as ex:
        raise web.HTTPException(reason=str(ex))

    try:
        cmd = __GET_SYSLOG_CMD_TEMPLATE.format(valid_source[source.lower()], _SYSLOG_FILE, limit+offset, limit)
        a = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout.readlines()
        c = [b.decode() for b in a]  # Since "a" contains return value in bytes, convert it to string
    except (OSError, Exception) as ex:
        raise web.HTTPException(reason=str(ex))

    return web.json_response({'logs': c, 'count': tot_lines})


def _get_support_dir():
    if _FOGLAMP_DATA:
        support_dir = os.path.expanduser(_FOGLAMP_DATA + '/tmp/support')
    else:
        support_dir = os.path.expanduser(_FOGLAMP_ROOT + '/data/tmp/support')

    return support_dir
