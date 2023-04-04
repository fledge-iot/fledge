# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import copy
import json
from aiohttp import web

from fledge.common.logger import FLCoreLogger
from fledge.common.configuration_manager import ConfigurationManager
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.common.storage_client.exceptions import StorageServerError
from fledge.services.core import connect

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2023 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_logger = FLCoreLogger().get_logger(__name__)


def setup(app):
    app.router.add_route('GET', '/fledge/control/lookup', get_lookup)


async def get_lookup(request: web.Request) -> web.Response:
    """List of supported control source and destinations

    :Example:
        curl -sX GET http://localhost:8081/fledge/control/lookup
        curl -sX GET http://localhost:8081/fledge/control/lookup?type=source
        curl -sX GET http://localhost:8081/fledge/control/lookup?type=destination
    """
    try:
        _type = request.query.get('type')
        if _type is None or not _type:
            lookup = await _get_all_lookups()
            response = {'controlLookup': lookup}
        else:
            table_name = None
            if _type == "source":
                table_name = "control_source"
            elif _type == "destination":
                table_name = "control_destination"
            if table_name:
                lookup = await _get_all_lookups(table_name)
                response = lookup
            else:
                lookup = await _get_all_lookups()
                response = {'controlLookup': lookup}
    except Exception as ex:
        msg = str(ex)
        _logger.error("Failed to get all control lookups. {}".format(msg))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response(response)


async def _get_all_lookups(tbl_name=None):
    storage = connect.get_storage_async()
    if tbl_name:
        res = await storage.query_tbl(tbl_name)
        lookup = res["rows"]
        return lookup
    result = await storage.query_tbl("control_source")
    source_lookup = result["rows"]
    result = await storage.query_tbl("control_destination")
    des_lookup = result["rows"]
    return {"source": source_lookup, "destination": des_lookup}
