# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import os
from aiohttp import web
from foglamp.common import logger


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
    """
    :Example:
        curl -X GET http://localhost:8081/foglamp/support/support-180301-13%3A35%3A23.tar.gz
    """
    bundle_name = request.match_info.get('bundle', None)

    if not str(bundle_name).endswith('.tar.gz'):
        return web.HTTPBadRequest(reason="Bundle file extension is invalid")

    if not os.path.isdir(_get_support_dir()):
        raise web.HTTPNotFound(reason="Support bundle directory does not exist")

    for root, dirs, files in os.walk(_get_support_dir()):
        if str(bundle_name) not in files:
            raise web.HTTPNotFound(reason='{} not found'.format(bundle_name))

    return web.json_response()


async def create_support_bundle(request):
    # TODO: FOGL-1126
    raise web.HTTPNotImplemented(reason='Create support bundle method is not implemented yet')


def _get_support_dir():
    if _FOGLAMP_DATA:
        support_dir = os.path.expanduser(_FOGLAMP_DATA + '/tmp/support')
    else:
        support_dir = os.path.expanduser(_FOGLAMP_ROOT + '/data/tmp/support')

    return support_dir
