# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import os
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


def _get_support_dir():
    if _FOGLAMP_DATA:
        support_dir = os.path.expanduser(_FOGLAMP_DATA + '/tmp/support')
    else:
        support_dir = os.path.expanduser(_FOGLAMP_ROOT + '/data/tmp/support')

    return support_dir
